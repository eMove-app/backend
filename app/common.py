from flask import Flask, jsonify, g
from flask_sqlalchemy import SQLAlchemy
import os
import json

_app = Flask(__name__)

with open(os.environ.get('CONFIG_FILE'), "r") as config_f:
    config = json.load(config_f)
    for k, v in config.items():
        _app.config[k] = v

db = SQLAlchemy(_app)


class Response:
    @staticmethod
    def format(obj, **kwargs):
        return jsonify({
            'data': obj,
            'notifications': kwargs.get('notifications'),
            'token': g.identity_token
        }), kwargs.get('code', 200)

    @staticmethod
    def empty(**kwargs):
        return Response.format(None, **kwargs)
