from flask import Flask, jsonify, g
from flask_sqlalchemy import SQLAlchemy

_app = Flask(__name__)
_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temp.db'
_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(_app)

class Response:
    @staticmethod
    def format(obj, **kwargs):
        return jsonify({
            'data': obj,
            'notifications': kwargs.get('notifications'),
            'token': g.identity_token
        })

    @staticmethod
    def empty():
        return format(None)
