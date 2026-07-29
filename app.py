from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from config import Flask_Config
from ext import db, limiter, jwt
from flask_cors import CORS

from routes.auth import auth_bp
from routes.expenses import expense_bp
from routes.budget import budget_bp
from routes.departments import department_bp

app = Flask(__name__)
app.config.from_object(Flask_Config)
CORS(app)
app.url_map.strict_slashes = False

db.init_app(app)
limiter.init_app(app)
jwt.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(expense_bp, url_prefix='/api/expenses')
app.register_blueprint(budget_bp, url_prefix='/api/budgets')
app.register_blueprint(department_bp, url_prefix='/api/departments')

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "Expense Management System for Wildcard Round of SDC-SI, AKGEC"

@app.errorhandler(Exception)
def handle_global_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({
            "status": e.code,
            "error": e.name,
            "message": e.description
        }), e.code

    return jsonify({
        "status": 500,
        "error": "Internal Server Error",
        "message": str(e)
    }), 500

if __name__ == '__main__':
    debug = __import__('os').getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host="0.0.0.0", debug=debug)
