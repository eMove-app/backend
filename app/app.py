from flask import request, g
import facebook
from .common import _app as app, db, Response
from .models.user import User, AssociatedAccount
from .hooks import *

@app.route('/me')
def me():
    u = g.current_user
    if u is not None:
        return Response.format(u.to_dict())
    return Response.empty()


@app.route('/login', methods=['POST'])
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
        d = user.to_dict()
        d['created'] = created
        return Response.format(d)
    except Exception as e:
        app.logger.error("Login error", exc_info=True)
        return Response.format(None)