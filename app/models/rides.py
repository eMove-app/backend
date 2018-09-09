from .common import db
from enum import Enum


class RideStatus(Enum):
    active = 0
    ended = 1
    canceled = 2


class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('rides', lazy=True))
    status = db.Column(db.Enum(RideStatus))
    start_time = db.Column(db.Time)
    directions = db.Column(db.Text)

    def to_dict(self):
        d = {
            'id': self.id,
            'user': self.user.to_dict(),
            'start_time': self.start_time.isoformat(),
            'points': [p.to_dict() for p in sorted(self.points, key=lambda p: p.rank)],
            'directions': self.directions
        }
        return d


class PointType(Enum):
    start = 0
    end = 1
    passenger = 2


class RidePoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('ride_points', lazy=False))
    type = db.Column(db.Enum(PointType))
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    ride = db.relationship('Ride', backref=db.backref('points', lazy=False))
    rank = db.Column(db.Integer)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    def to_dict(self):
        d = {
            'id': self.id,
            'user': self.user.to_dict(),
            'type': self.type.name,
            'lat': self.lat,
            'lng': self.lng
        }
        return d

    def coordinates(self):
        return self.lat, self.lng


class JoinRequestStatus(Enum):
    pending = 0
    accepted = 1
    declined = 2


class JoinRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('join_requests', lazy=True))
    status = db.Column(db.Enum(JoinRequestStatus))
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    ride = db.relationship('Ride', backref=db.backref('join_requests', lazy=False))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    def to_dict(self):
        d = {
            'id': self.id,
            'user': self.user.to_dict(True),
            'status': self.status.name,
            'lat': self.lat,
            'lng': self.lng
        }
        return d

