from datetime import datetime
from models import Department, BudgetUsage
from ext import db

class BudgetService:
    @staticmethod
    def get_budget_info(department_id, month=None):
        if month is None:
            month = datetime.utcnow().replace(day=1).date()
        dept = Department.query.get(department_id)
        if not dept:
            return None, "Department not found"
        usage = BudgetUsage.query.filter_by(department_id=department_id, month=month).first()
        if not usage:
            usage = BudgetUsage(department_id=department_id, month=month, approved_amount=0)
            db.session.add(usage)
            db.session.commit()
        budget = float(dept.monthly_budget) if dept.monthly_budget else None
        spent = float(usage.approved_amount)
        if budget is not None:
            remaining = max(budget - spent, 0)
            over_budget = spent > budget
        else:
            remaining = None
            over_budget = False
        return {
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'over_budget': over_budget
        }, None

    @staticmethod
    def add_approved_expense(department_id, amount):
        month = datetime.utcnow().replace(day=1).date()
        usage = BudgetUsage.query.filter_by(department_id=department_id, month=month).first()
        if not usage:
            usage = BudgetUsage(department_id=department_id, month=month, approved_amount=0)
            db.session.add(usage)
        usage.approved_amount = float(usage.approved_amount) + float(amount)
        db.session.commit()
        dept = Department.query.get(department_id)
        if dept and dept.monthly_budget:
            return float(usage.approved_amount) > float(dept.monthly_budget)
        return False
