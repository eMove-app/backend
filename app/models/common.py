from ..common import db
# from sqlalchemy.ext.declarative import declared_attr

class Model(db.Model):
    __abstract__ = True