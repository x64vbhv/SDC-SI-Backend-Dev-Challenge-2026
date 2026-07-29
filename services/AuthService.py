from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Department
from ext import db

VALID_ROLES = {'employee', 'manager', 'finance'}

class AuthService:
    @staticmethod
    def register_user(email, password, first_name, last_name, role='employee', department_id=None):
        if role not in VALID_ROLES:
            return None, f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"

        if User.query.filter_by(email=email).first():
            return None, "Email already exists"

        if role in ('manager', 'employee') and not department_id:
            return None, f"department_id is required for {role}"

        if department_id and not Department.query.get(department_id):
            return None, "Department not found"

        hashed = generate_password_hash(password)
        user = User(
            email=email,
            password_hash=hashed,
            first_name=first_name,
            last_name=last_name,
            role=role,
            department_id=department_id if role != 'finance' else None
        )
        db.session.add(user)
        db.session.commit()
        return user, None

    @staticmethod
    def authenticate_user(email, password):
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            return user, None
        return None, "Invalid credentials"
