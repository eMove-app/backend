from flask import request, g
import facebook
from .common import _app as app, db, Response
from .models.user import User, AssociatedAccount, Car, AddressType, Address
from .hooks import *
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
        return Response.empty(403)
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
        return Response.empty(403)
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
        return Response.empty(403)
    forbidden = ('id', 'user_id')
    fields = { k: v for k, v in request.form.items() if k not in forbidden }
    if 'type' in fields:
        fields['type'] = AddressType[fields['type']]
    address = Address.query.filter_by(id=id, user_id=user.id).first()
    if not address:
        return Response.empty(404)
    for k, v in fields.items():
        setattr(address, k, v)
    db.session.commit()
    return Response.format(True)


@app.route('/addresses/<int:id>', methods=['DELETE'], endpoint='delete_address')
def delete_address(id):
    user = g.current_user
    if not user:
        return Response.empty(403)
    address = Address.query.filter_by(id=id, user_id=user.id).first()
    if not address:
        return Response.empty(404)
    db.session.delete(address)
    db.session.commit()
    return Response.format(True)