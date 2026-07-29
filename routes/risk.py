from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from services.RiskService import RiskService
from ext import limiter

risk_bp = Blueprint('risk', __name__)

def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

@risk_bp.route('/expenses/<int:id>/analyze', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def analyze_expense(id):
    user = get_current_user()
    if not user or user.role not in ['manager', 'finance']:
        return jsonify({"message": "Forbidden"}), 403

    result, error = RiskService.analyze(id)
    if error:
        return jsonify({"message": error}), 404
    return jsonify(result), 200

@risk_bp.route('/expenses/flagged', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_flagged_expenses():
    user = get_current_user()
    if not user or user.role not in ['manager', 'finance']:
        return jsonify({"message": "Forbidden"}), 403

    min_score = request.args.get('min_score', 50, type=int)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit, 100)

    result = RiskService.get_flagged(min_score, page, limit)
    return jsonify(result), 200

@risk_bp.route('/expenses/<int:id>/risk', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_risk_breakdown(id):
    user = get_current_user()
    if not user or user.role not in ['manager', 'finance']:
        return jsonify({"message": "Forbidden"}), 403

    result, error = RiskService.get_breakdown(id)
    if error:
        return jsonify({"message": error}), 404
    return jsonify(result), 200