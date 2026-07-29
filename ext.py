from flask import request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()

# shukriya: https://flask-jwt-extended.readthedocs.io/en/stable/blocklist_and_token_revoking.html
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    from models import TokenBlocklist
    return TokenBlocklist.query.filter_by(jti=jwt_payload['jti']).first() is not None


limiter = Limiter(key_func=get_remote_address)