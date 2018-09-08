from .common import db, Model
import uuid
from sqlalchemy.event import listens_for


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    profile_picture_url = db.Column(db.String(255))

    def to_dict(self):
        return {
            'uuid': self.uuid,
            'email': self.email,
            'name': self.name,
            'profile_picture_url': self.profile_picture_url
        }


@listens_for(User, 'before_insert')
def add_uuid(mapper, connect, target):
    target.uuid = str(uuid.uuid4())


class AssociatedAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('associated_account', lazy=True))