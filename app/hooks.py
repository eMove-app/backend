from flask import request, g
from .common import _app as app
import jwt
from .models.user import User


def identity_token(user):
    return jwt.encode({'id': user.id}, app.config['JWT_SECRET'], algorithm='HS256').decode('utf-8')


@app.before_request
def set_current_identity():
    g.current_user = None
    g.identity_token = None
    try:
        token = request.headers.get('x-token')
        g.identity_token = token
        if token:
            payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            if payload is not None:
                uid = payload.get('id')
                g.current_user = User.query.filter_by(id=uid).first()
    except:
        pass