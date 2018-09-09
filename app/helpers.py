from .models.rides import Ride, RidePoint, RideStatus, PointType
import googlemaps
from datetime import datetime
from .common import _app as app


gmaps = googlemaps.Client(key=app.config["MAPS_API_KEY"])
threshhold = 0.3


def find_rides(lat, lng):
    rides = Ride.query.filter_by(status=RideStatus.active).all()
    eligible_rides = []
    current_point = (lat, lng)
    for ride in rides:
        if ride.user.car is None or len(ride.points) >= ride.user.car.seats:
            continue
        points = sorted(ride.points, key=lambda p: p.rank)
        coordinates = [p.coordinates() for p in points]
        current_directions = directions(coordinates)[0]
        current_values = { 'distance': 0, 'duration': 0 }
        for leg in current_directions["legs"]:
            for k in current_values.keys():
                current_values[k] += leg[k]["value"]
        new_directions = directions([coordinates[0]] + [current_point] + coordinates[1:])[0]
        new_values = { 'distance': 0, 'duration': 0 }
        for leg in new_directions["legs"]:
            for k in new_values.keys():
                new_values[k] += leg[k]["value"]
        if current_values['duration'] * (1 + threshhold) > new_values['duration']:
            eligible_rides.append({
                'user': ride.user.to_dict(True),
                'initial': {
                    'values': current_values,
                    'directions': current_directions
                },
                'updated': {
                    'values': new_values,
                    'directions': new_directions
                }
            })
    return sorted(eligible_rides, key=lambda ride: ride['updated']['values']['duration'] - ride['initial']['values']['duration'])

def directions(coordinates):
    now = datetime.now()
    waypoints = coordinates[1:-1]
    if len(waypoints) > 1:
        waypoints.insert(0, 'optimize:true')
    d = gmaps.directions(coordinates[0], coordinates[-1], waypoints=coordinates[1:-1], mode="driving", departure_time=now)
    keep = ("start_location", "end_location", "polyline", "distance", "duration")
    for leg in d[0]["legs"]:
        for k in list(leg.keys()):
            if k not in keep:
                del leg[k]
    return d