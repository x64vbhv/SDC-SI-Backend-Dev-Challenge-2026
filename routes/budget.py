from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from services.BudgetService import BudgetService
from datetime import datetime
from ext import limiter

budget_bp = Blueprint('budget', __name__)

def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

@budget_bp.route('/department', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_department_budget():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 401

    dept_id = request.args.get('department_id', type=int)
    month = request.args.get('month')

    if user.role == 'manager':
        dept_id = user.department_id
    elif user.role == 'finance':
        if not dept_id:
            return jsonify({"message": "department_id is required"}), 400
    else:
        return jsonify({"message": "Insufficient permissions"}), 403

    if month:
        try:
            month_date = datetime.strptime(month, '%Y-%m').date().replace(day=1)
        except ValueError:
            return jsonify({"message": "Invalid month format, expected YYYY-MM"}), 400
    else:
        month_date = datetime.utcnow().date().replace(day=1)

    info, err = BudgetService.get_budget_info(dept_id, month_date)
    if err:
        return jsonify({"message": err}), 404
    return jsonify(info), 200
