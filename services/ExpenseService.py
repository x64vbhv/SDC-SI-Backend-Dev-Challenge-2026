from datetime import datetime
from models import Expense
from ext import db
from services.RiskService import RiskService

VALID_CATEGORIES = {'travel', 'meals', 'equipment', 'software', 'other'}
VALID_CURRENCIES = {
    'USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'JPY', 'CHF', 'CNY', 'SGD',
    'AED', 'HKD', 'NZD', 'MXN', 'BRL', 'ZAR', 'SEK', 'NOK', 'DKK', 'PLN'
}
VALID_SORT_FIELDS = {'title', 'amount', 'status', 'category', 'created_at', 'submitted_at', 'approved_at'}

# src: https://www.geeksforgeeks.org/python/how-to-implement-filtering-sorting-and-pagination-in-flask/

class ExpenseService:
    @staticmethod
    def create(data, user):
        category = data.get('category', '')
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")

        currency = data.get('currency', 'USD').upper()
        if currency not in VALID_CURRENCIES:
            raise ValueError(f"Invalid currency code: {currency}")

        status = data.get('status', 'draft')
        if status not in ('draft', 'submitted'):
            raise ValueError("Status on creation must be 'draft' or 'submitted'")

        exp = Expense(
            title=data['title'],
            amount=data['amount'],
            currency=currency,
            category=category,
            status=status,
            author_id=user.id,
            department_id=user.department_id,
            receipt_url=data.get('receipt_url'),
            notes=data.get('notes')
        )
        if exp.status == 'submitted':
            exp.submitted_at = datetime.utcnow()
        db.session.add(exp)
        db.session.commit()
        return exp

    @staticmethod
    def get_by_id(exp_id, user):
        exp = Expense.query.get(exp_id)
        if not exp:
            return None, "Expense not found"
        if user.role == 'employee' and exp.author_id != user.id:
            return None, "Not authorized"
        if user.role == 'manager' and exp.department_id != user.department_id:
            return None, "Not authorized"
        return exp, None

    @staticmethod
    def get_all(filters, pagination, user):
        query = Expense.query
        if user.role == 'employee':
            query = query.filter_by(author_id=user.id)
        elif user.role == 'manager':
            query = query.filter_by(department_id=user.department_id)

        if filters.get('start_date'):
            query = query.filter(Expense.created_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(Expense.created_at <= filters['end_date'])
        if filters.get('category'):
            query = query.filter_by(category=filters['category'])
        if filters.get('status'):
            query = query.filter_by(status=filters['status'])
        if filters.get('min_amount') is not None:
            query = query.filter(Expense.amount >= filters['min_amount'])
        if filters.get('max_amount') is not None:
            query = query.filter(Expense.amount <= filters['max_amount'])
        if user.role == 'finance' and filters.get('department_id'):
            query = query.filter_by(department_id=filters['department_id'])

        sort_by = filters.get('sort_by', 'created_at')
        if sort_by not in VALID_SORT_FIELDS:
            sort_by = 'created_at'
        sort_order = filters.get('sort_order', 'desc')
        column = getattr(Expense, sort_by)
        query = query.order_by(db.desc(column)) if sort_order == 'desc' else query.order_by(column)

        page = pagination.get('page', 1)
        limit = min(pagination.get('limit', 20), 100)
        paginated = query.paginate(page=page, per_page=limit, error_out=False)

        return {
            'total': paginated.total,
            'page': page,
            'limit': limit,
            'data': [ExpenseService._to_dict(e) for e in paginated.items]
        }

    @staticmethod
    def update(exp_id, data, user):
        exp, err = ExpenseService.get_by_id(exp_id, user)
        if err:
            return None, err
        if exp.status != 'draft':
            return None, "Only draft expenses can be edited"

        if 'category' in data and data['category'] not in VALID_CATEGORIES:
            return None, f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"
        if 'currency' in data and data['currency'].upper() not in VALID_CURRENCIES:
            return None, f"Invalid currency code: {data['currency']}"

        for field in ['title', 'amount', 'receipt_url', 'notes']:
            if field in data:
                setattr(exp, field, data[field])
        if 'currency' in data:
            exp.currency = data['currency'].upper()
        if 'category' in data:
            exp.category = data['category']
        db.session.commit()
        return exp, None

    @staticmethod
    def delete(exp_id, user):
        exp, err = ExpenseService.get_by_id(exp_id, user)
        if err:
            return False, err
        if exp.status != 'draft':
            return False, "Only draft expenses can be deleted"
        db.session.delete(exp)
        db.session.commit()
        return True, None

    @staticmethod
    def submit(exp_id, user):
        exp, err = ExpenseService.get_by_id(exp_id, user)
        if err:
            return None, err
        if exp.status != 'draft':
            return None, "Only draft expenses can be submitted"
        exp.status = 'submitted'
        exp.submitted_at = datetime.utcnow()
        db.session.commit()

        RiskService.analyze(exp.id)
        db.session.refresh(exp)
                           
        return exp, None

    @staticmethod
    def approve(exp_id, user):
        exp = Expense.query.get(exp_id)
        if not exp:
            return None, "Expense not found"
        if exp.author_id == user.id:
            return None, "Cannot approve your own expense"
        if user.department_id != exp.department_id:
            return None, "Not your department"
        if exp.status != 'submitted':
            return None, "Only submitted expenses can be approved"
        exp.status = 'approved'
        exp.approved_at = datetime.utcnow()
        db.session.commit()
        return exp, None

    @staticmethod
    def reject(exp_id, user, reason):
        exp = Expense.query.get(exp_id)
        if not exp:
            return None, "Expense not found"
        if exp.author_id == user.id:
            return None, "Cannot reject your own expense"
        if user.department_id != exp.department_id:
            return None, "Not your department"
        if exp.status != 'submitted':
            return None, "Only submitted expenses can be rejected"
        exp.status = 'rejected'
        exp.rejection_reason = reason
        exp.rejected_at = datetime.utcnow()
        db.session.commit()
        return exp, None

    @staticmethod
    def reopen(exp_id, user):
        exp, err = ExpenseService.get_by_id(exp_id, user)
        if err:
            return None, err
        if exp.status != 'rejected':
            return None, "Only rejected expenses can be reopened"
        exp.status = 'draft'
        exp.rejection_reason = None
        db.session.commit()
        return exp, None

    @staticmethod
    def _to_dict(exp):
        return {
            'id': exp.id,
            'title': exp.title,
            'amount': float(exp.amount),
            'currency': exp.currency,
            'category': exp.category,
            'status': exp.status,
            'author_id': exp.author_id,
            'department_id': exp.department_id,
            'receipt_url': exp.receipt_url,
            'notes': exp.notes,
            'rejection_reason': exp.rejection_reason,
            'submitted_at': exp.submitted_at.isoformat() if exp.submitted_at else None,
            'approved_at': exp.approved_at.isoformat() if exp.approved_at else None,
            'rejected_at': exp.rejected_at.isoformat() if exp.rejected_at else None,
            'created_at': exp.created_at.isoformat() if exp.created_at else None,
            'updated_at': exp.updated_at.isoformat() if exp.updated_at else None,
            'risk_score': exp.risk_score,
            'risk_level': exp.risk_level,
            'risk_reasons': exp.risk_reasons,
            'analyzed_at': exp.analyzed_at.isoformat() if exp.analyzed_at else None
        }
