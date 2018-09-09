from .common import db
import uuid
from sqlalchemy.event import listens_for
from enum import Enum


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(255))
    profile_picture_url = db.Column(db.String(255))
    leaves_from_home = db.Column(db.Time)
    leaves_from_work = db.Column(db.Time)

    def to_dict(self, public=True):
        d = {
            'uuid': self.uuid,
            'name': self.name,
            'phone': self.phone,
            'profile_picture_url': self.profile_picture_url
        }
        if self.leaves_from_home:
            d['leaves_from_home'] = self.leaves_from_home.isoformat()
        if self.leaves_from_work:
            d['leaves_from_work'] = self.leaves_from_work.isoformat()
        if not public:
            d['email'] = self.email
            d['addresses'] = [a.to_dict() for a in self.addresses]
            if self.car:
                d['car'] = self.car.to_dict()
        return d


@listens_for(User, 'before_insert')
def add_uuid(mapper, connect, target):
    target.uuid = str(uuid.uuid4())


class AssociatedAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('associated_account', lazy=True))


class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('car', uselist=False, lazy=True))
    make = db.Column(db.String(255))
    model = db.Column(db.String(255))
    color = db.Column(db.String(255))
    registration_number = db.Column(db.String(255))
    seats = db.Column(db.Integer)
    extra_info = db.Column(db.Text)

    def to_dict(self):
        exclude = ['id', 'user_id']
        return { k: v for k, v in self.__dict__.items() if not k.startswith('_') and k not in exclude }


class AddressType(Enum):
    work = 0
    home = 1


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('addresses', lazy=True))
    name = db.Column(db.String(255))
    type = db.Column(db.Enum(AddressType))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    def to_dict(self):
        exclude = ['user_id', 'type']
        d = { k: v for k, v in self.__dict__.items() if not k.startswith('_') and k not in exclude }
        d['type'] = self.type.name
        return d