from models import Department
from ext import db

class DepartmentService:
    @staticmethod
    def create(name, monthly_budget=None):
        if Department.query.filter_by(name=name).first():
            return None, "Department already exists"

        dept = Department(name=name, monthly_budget=monthly_budget)
        db.session.add(dept)
        db.session.commit()
        return dept, None

    @staticmethod
    def get_all():
        return Department.query.order_by(Department.name).all()

    @staticmethod
    def _to_dict(dept):
        return {
            'id': dept.id,
            'name': dept.name,
            'monthly_budget': float(dept.monthly_budget) if dept.monthly_budget else None,
            'created_at': dept.created_at.isoformat() if dept.created_at else None,
            'updated_at': dept.updated_at.isoformat() if dept.updated_at else None
        }