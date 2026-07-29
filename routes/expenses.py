from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from services.ExpenseService import ExpenseService
from services.RiskService import RiskService
from services.BudgetService import BudgetService
from ext import limiter

expense_bp = Blueprint('expenses', __name__)

def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

@expense_bp.route('/', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def list_expenses():
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 401

    filters = {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'category': request.args.get('category'),
        'status': request.args.get('status'),
        'min_amount': request.args.get('min_amount', type=float),
        'max_amount': request.args.get('max_amount', type=float),
        'department_id': request.args.get('department_id', type=int),
        'sort_by': request.args.get('sort_by', 'created_at'),
        'sort_order': request.args.get('sort_order', 'desc')
    }
    pagination = {
        'page': request.args.get('page', 1, type=int),
        'limit': request.args.get('limit', 20, type=int)
    }

    result = ExpenseService.get_all(filters, pagination, user)
    return jsonify(result), 200

@expense_bp.route('/', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def create_expense():
    user = get_current_user()
    if not user or user.role != 'employee':
        return jsonify({"message": "Only employees can create expenses"}), 403

    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'amount', 'category')):
        return jsonify({"message": "title, amount, and category are required"}), 400

    try:
        exp = ExpenseService.create(data, user)
    except ValueError as e:
        return jsonify({"message": str(e)}), 422
    return jsonify(ExpenseService._to_dict(exp)), 201

@expense_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_expense(id):
    user = get_current_user()
    if not user:
        return jsonify({"message": "User not found"}), 401

    exp, err = ExpenseService.get_by_id(id, user)
    if err:
        return jsonify({"message": err}), 404
    return jsonify(ExpenseService._to_dict(exp)), 200

@expense_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@limiter.limit("10 per minute")
def update_expense(id):
    user = get_current_user()
    if not user or user.role != 'employee':
        return jsonify({"message": "Only employees can update expenses"}), 403

    data = request.get_json()
    exp, err = ExpenseService.update(id, data, user)
    if err:
        return jsonify({"message": err}), 422
    return jsonify(ExpenseService._to_dict(exp)), 200

@expense_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("10 per minute")
def delete_expense(id):
    user = get_current_user()
    if not user or user.role != 'employee':
        return jsonify({"message": "Only employees can delete expenses"}), 403

    ok, err = ExpenseService.delete(id, user)
    if not ok:
        return jsonify({"message": err}), 422
    return '', 204

@expense_bp.route('/<int:id>/submit', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def submit_expense(id):
    user = get_current_user()
    if not user or user.role != 'employee':
        return jsonify({"message": "Only employees can submit expenses"}), 403

    exp, err = ExpenseService.submit(id, user)
    if err:
        return jsonify({"message": err}), 422
    return jsonify(ExpenseService._to_dict(exp)), 200

@expense_bp.route('/<int:id>/approve', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def approve_expense(id):
    user = get_current_user()
    if not user or user.role != 'manager':
        return jsonify({"message": "Only managers can approve expenses"}), 403

    exp, err = ExpenseService.approve(id, user)
    if err:
        return jsonify({"message": err}), 422

    over_budget = BudgetService.add_approved_expense(exp.department_id, exp.amount)
    response = ExpenseService._to_dict(exp)
    if over_budget:
        response['warning'] = "This approval has pushed the department over its monthly budget"
    return jsonify(response), 200

@expense_bp.route('/<int:id>/reject', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def reject_expense(id):
    user = get_current_user()
    if not user or user.role != 'manager':
        return jsonify({"message": "Only managers can reject expenses"}), 403

    data = request.get_json()
    reason = data.get('rejection_reason') if data else None
    if not reason:
        return jsonify({"message": "rejection_reason is required"}), 400

    exp, err = ExpenseService.reject(id, user, reason)
    if err:
        return jsonify({"message": err}), 422
    return jsonify(ExpenseService._to_dict(exp)), 200

@expense_bp.route('/<int:id>/reopen', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def reopen_expense(id):
    user = get_current_user()
    if not user or user.role != 'employee':
        return jsonify({"message": "Only employees can reopen expenses"}), 403

    exp, err = ExpenseService.reopen(id, user)
    if err:
        return jsonify({"message": err}), 422
    return jsonify(ExpenseService._to_dict(exp)), 200

@expense_bp.route('/flagged', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_flagged_expenses():
    user = get_current_user()
    if not user or user.role not in ('manager', 'finance'):
        return jsonify({"message": "Forbidden"}), 403

    min_score = request.args.get('min_score', 50, type=int)
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 20, type=int), 100)

    result = RiskService.get_flagged(min_score, page, limit)
    return jsonify(result), 200

@expense_bp.route('/<int:id>/analyze', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def analyze_expense(id):
    user = get_current_user()
    if not user or user.role not in ('manager', 'finance'):
        return jsonify({"message": "Forbidden"}), 403

    result, error = RiskService.analyze(id)
    if error:
        return jsonify({"message": error}), 404
    return jsonify(result), 200

@expense_bp.route('/<int:id>/risk', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_risk_breakdown(id):
    user = get_current_user()
    if not user or user.role not in ('manager', 'finance'):
        return jsonify({"message": "Forbidden"}), 403

    result, error = RiskService.get_breakdown(id)
    if error:
        return jsonify({"message": error}), 404
    return jsonify(result), 200
