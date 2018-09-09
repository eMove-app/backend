from flask import request, g
import facebook
from .common import _app as app, db, Response
from .models.user import User, AssociatedAccount, Car, AddressType, Address
from .models.rides import Ride, RideStatus, RidePoint, PointType, JoinRequest, JoinRequestStatus
from .hooks import *
from .helpers import find_rides, directions
from datetime import time


@app.route('/me', methods=['GET'], endpoint='me')
def me():
    u = g.current_user
    if u is not None:
        return Response.format(u.to_dict(False))
    return Response.empty(code=403)


@app.route('/me', methods=['PUT'], endpoint='update_profile')
def update_profile():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    allowed = ('phone', 'leaves_from_home', 'leaves_from_work')
    fields = { k: v for k, v in request.form.items() if k in allowed }
    time_names = ('hour', 'minute', 'second')
    for k in ('leaves_from_home', 'leaves_from_work'):
        if k in fields:
            fields[k] = time(**dict(zip(time_names, map(int, fields[k].split(':')))))
    for k, v in fields.items():
        setattr(user, k, v)
    db.session.commit()
    return Response.format(True)


@app.route('/login', methods=['POST'], endpoint='login')
def login():
    try:
        graph = facebook.GraphAPI(access_token=request.form['token'])
        fb_user = graph.get_object(id='me', fields='email,name,picture')
        associated_account = AssociatedAccount.query.filter_by(external_id=fb_user['id']).first()
        created = False
        if associated_account is None:
            user = User(email=fb_user["email"], name=fb_user["name"], profile_picture_url=fb_user['picture']['data']['url'])
            associated_account = AssociatedAccount(external_id=fb_user['id'], user=user)
            db.session.add(associated_account)
            db.session.commit()
            created = True
        else:
            user = associated_account.user
        g.identity_token = identity_token(user)
        d = user.to_dict(False)
        d['created'] = created
        return Response.format(d)
    except Exception as e:
        app.logger.error("Login error", exc_info=True)
        return Response.format(None)


@app.route('/car', methods=['POST', 'PUT'], endpoint='add_update_car')
def add_car():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    fields = request.form
    forbidden = ('id', 'user_id')
    for k in forbidden:
        if k in fields:
            del fields[k]
    if user.car:
        car = user.car
    else:
        car = Car()
        car.user = user
    for k, v in fields.items():
        setattr(car, k, v)
    db.session.commit()
    return Response.format(True)


@app.route('/addresses', methods=['POST'], endpoint='add_address')
def add_address():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    forbidden = ('id', 'user_id')
    fields = { k: v for k, v in request.form.items() if k not in forbidden }
    if 'type' in fields:
        fields['type'] = AddressType[fields['type']]
    address = Address(**fields)
    address.user = user
    db.session.add(address)
    db.session.commit()
    return Response.format(True)


@app.route('/addresses/<int:id>', methods=['PUT'], endpoint='edit_address')
def edit_address(id):
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    forbidden = ('id', 'user_id')
    fields = { k: v for k, v in request.form.items() if k not in forbidden }
    if 'type' in fields:
        fields['type'] = AddressType[fields['type']]
    address = Address.query.filter_by(id=id, user_id=user.id).first()
    if not address:
        return Response.empty(code=404)
    for k, v in fields.items():
        setattr(address, k, v)
    db.session.commit()
    return Response.format(True)


@app.route('/addresses/<int:id>', methods=['DELETE'], endpoint='delete_address')
def delete_address(id):
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    address = Address.query.filter_by(id=id, user_id=user.id).first()
    if not address:
        return Response.empty(code=404)
    db.session.delete(address)
    db.session.commit()
    return Response.format(True)


# Rides
@app.route('/rides/action/start', methods=['POST'], endpoint='start_ride')
def start_ride():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    ride = Ride()
    ride.user = user
    ride.status = RideStatus.active
    time_names = ('hour', 'minute', 'second')
    if request.is_json:
        form = request.get_json()
    else:
        form = { k: v for k, v in request.form.items() }
        for k1 in ('start_point', 'end_point'):
            form[k1] = {}
            for k2 in ('lat', 'lng'):
                form[k1][k2] = form.get("{0}[{1}]".format(k1, k2))
    ride.start_time = time(**dict(zip(time_names, map(int, form['start_time'].split(':')))))
    start_point = RidePoint()
    start_point.type = PointType.start
    start_point.rank = 0
    end_point = RidePoint()
    end_point.type = PointType.end
    end_point.rank = 1
    points = { 'start_point': start_point, 'end_point': end_point }
    forbidden = ('id', 'ride_id', 'user_id')
    for key, point in points.items():
        point.ride = ride
        point.user = user
        fields = { k: v for k, v in form[key].items() if k not in forbidden }
        for k, v in fields.items():
            setattr(point, k, v)
    ride.points = [start_point, end_point]
    db.session.add(ride)
    db.session.flush()
    db.session.refresh(ride)
    db.session.commit()
    r = ride.to_dict()
    r['directions'] = directions([start_point.coordinates(), end_point.coordinates()])
    del r['directions'][0]['legs']
    return Response.format(r)


@app.route('/rides/<int:id>', methods=['GET'], endpoint='get_ride')
def get_ride(id):
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    ride = Ride.query.filter_by(id=id).first()
    if not ride:
        return Response.empty(code=404)
    visible = ride.user == user
    if ride.user != user:
        for point in ride.points:
            if point.user == user:
                visible = True
    if not visible:
        return Response.empty(code=403)
    r = ride.to_dict()
    r['directions'] = directions([p.coordinates() for p in ride.points])
    del r['directions'][0]['legs']
    return Response.format(r)


@app.route('/find-ride', methods=['GET'], endpoint='find_ride')
def find_ride():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    lat = float(request.args.get('lat', 0))
    lng = float(request.args.get('lng', 0))
    return Response.format(find_rides(lat, lng))


# Join requests
@app.route('/join-requests', methods=['POST'], endpoint='add_join_request')
def add_join_request():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    if request.is_json:
        fields = request.get_json()
    else:
        fields = request.form
    forbidden = ('id', 'user_id', 'status')
    for k in forbidden:
        if k in fields:
            del fields[k]
    req = JoinRequest()
    for k, v in fields.items():
        setattr(req, k, v)
    req.user = user
    req.status = JoinRequestStatus.pending
    db.session.add(req)
    db.session.commit()
    db.session.refresh(req)
    return Response.format(req.to_dict())


@app.route('/join-requests/<int:id>', methods=['GET'], endpoint='get_join_request')
def get_join_request(id):
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    req = JoinRequest.query.filter_by(id=id).first()
    if req is None:
        return Response.empty(code=404)
    if req.user != user and req.ride.user != user:
        return Response.empty(code=403)
    return Response.format(req.to_dict())


@app.route('/join-requests/<int:id>/actions/<action>', methods=['GET'], endpoint='action_request')
def request_action(id, action):
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    req = JoinRequest.query.filter_by(id=id).first()
    if req is None:
        return Response.empty(code=404)
    if req.ride.user != user:
        return Response.empty(code=403)
    status = JoinRequestStatus[action]
    req.status = status
    if status == JoinRequestStatus.accepted:
        ride = req.ride
        points = ride.points
        points.sort(key=lambda p: p.rank)
        points[-1].rank += 1
        new_point = RidePoint(lat=req.lat, lng=req.lng, type=PointType.passenger, rank=points[-1].rank-1)
        new_point.ride = ride
        new_point.user = req.user
        points.insert(len(points)-2, new_point)
        coordinates = [p.coordinates() for p in points]
        d = directions(coordinates)
        if 'waypoint_order' in d:
            new_ranks = dict(zip(d['waypoint_order'], range(len(d['waypoint_order']))))
            for i in range(1, len(points) - 1):
                points[i].rank = 1 + new_ranks[i]
            points[-1].rank += 1
        db.session.add(new_point)
    db.session.commit()
    return Response.format(True)


@app.route('/join-requests', methods=['GET'], endpoint='get_join_requests')
def get_join_requests():
    user = g.current_user
    if not user:
        return Response.empty(code=403)
    ride_id = int(request.args.get('ride_id', 0))
    if ride_id < 0:
        return Response.empty(code=400)
    requests = JoinRequest.query.filter_by(status=JoinRequestStatus.pending, ride_id=ride_id).all()
    return Response.format([r.to_dict() for r in requests])
