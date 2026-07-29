from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from services.DepartmentService import DepartmentService
from ext import limiter

department_bp = Blueprint('departments', __name__)

def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

@department_bp.route('/', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def create_department():
    user = get_current_user()
    if not user or user.role != 'finance':
        return jsonify({"message": "Only finance can create departments"}), 403

    data = request.get_json() or {}
    name = data.get('name')
    monthly_budget = data.get('monthly_budget')

    if not name:
        return jsonify({"message": "name is required"}), 400

    dept, error = DepartmentService.create(name, monthly_budget)
    if error:
        return jsonify({"message": error}), 409

    return jsonify(DepartmentService._to_dict(dept)), 201

@department_bp.route('/', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def list_departments():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 401

    departments = DepartmentService.get_all()
    return jsonify([DepartmentService._to_dict(d) for d in departments]), 200