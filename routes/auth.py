from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from ext import limiter
from services.AuthService import AuthService

auth_bp = Blueprint('auth', __name__)

VALID_ROLES = {'employee', 'manager', 'finance'}

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("10 per minute")
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'employee')
    department_id = data.get('department_id')

    # src: https://www.geeksforgeeks.org/python/python-all-function/
    if not all([email, password, first_name, last_name]):
        return jsonify({"message": "email, password, first_name and last_name are required"}), 400

    if role not in VALID_ROLES:
        return jsonify({"message": "role must be employee, manager or finance"}), 400

    if role in ('employee', 'manager') and not department_id:
        return jsonify({"message": "department_id is required"}), 400

    user, error = AuthService.register_user(email, password, first_name, last_name, role, department_id)
    if error:
        return jsonify({"message": error}), 409 if "already" in error else 400

    return jsonify({
        "message": "registered successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "department_id": user.department_id
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "email and password are required"}), 400

    user, error = AuthService.authenticate_user(email, password)
    if error:
        return jsonify({"message": error}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "department_id": user.department_id
        }
    }), 200