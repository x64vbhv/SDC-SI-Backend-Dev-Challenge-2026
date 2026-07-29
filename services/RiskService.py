from datetime import datetime, timedelta
from difflib import SequenceMatcher
from models import Expense
from ext import db
from services.ExpenseService import ExpenseService

# src: https://safebooks.ai/resources/fraud-detection/expense-fraud-and-errors-how-to-detect-and-prevent-financial-loss/
# https://www.emburse.com/resources/complete-guide-to-expense-fraud-detection
# had 0 knowledge of finance fraud before this, so i researched and added 5 basic rules:
# 1. duplicate submissions: similar title + amount from same employee within 7 days
# 2. split expenses: multiple small same-category expenses in a day that add up to a large total
# 3. unusual amounts: way above the employee's own average for that category
# 4. odd submission times: late night or weekends
# 5. round numbers: suspiciously clean amounts like $500, $1000


def _similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.75


class RiskService:

    @staticmethod
    def _rule_duplicate(exp, amt):
        since = datetime.utcnow() - timedelta(days=7)
        recent = Expense.query.filter(
            Expense.author_id == exp.author_id,
            Expense.id != exp.id,
            Expense.submitted_at >= since,
            Expense.amount.between(amt * 0.9, amt * 1.1)
        ).all()

        for other in recent:
            if _similar(exp.title, other.title):
                return ["Duplicate submission"], 30

        return [], 0

    @staticmethod
    def _rule_split(exp, amt):
        d_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sim_tday = Expense.query.filter(
            Expense.author_id == exp.author_id,
            Expense.category == exp.category,
            Expense.submitted_at >= d_start,
            Expense.submitted_at < d_start + timedelta(days=1),
            Expense.amount < 500,
            Expense.id != exp.id
        ).all()

        if not sim_tday:
            return [], 0

        total = amt
        for e in sim_tday:
            total += float(e.amount)

        if total > 1000:
            return [f"{len(sim_tday) + 1} small {exp.category} expenses today totalling ${total:.2f}"], 25

        return [], 0

    @staticmethod
    def _rule_unusual(exp, amt):
        six_mo_ago = datetime.utcnow() - timedelta(days=180)
        past_expen = Expense.query.filter(
            Expense.author_id == exp.author_id,
            Expense.category == exp.category,
            Expense.submitted_at >= six_mo_ago,
            Expense.status == 'approved',
            Expense.id != exp.id
        ).all()

        if not past_expen:
            return [], 0

        total = 0.0
        for e in past_expen:
            total += float(e.amount)
        avg = total / len(past_expen)

        if avg > 0 and amt > 3 * avg:
            return [f"${amt:.0f} is {amt / avg:.1f}x their usual (avg ${avg:.0f})"], 20

        return [], 0

    @staticmethod
    def _rule_time(exp, amt):
        if not exp.submitted_at:
            return [], 0

        reasons = []
        score = 0
        hr = exp.submitted_at.hour

        if hr >= 22 or hr < 6:
            reasons.append(f"Submitted at {hr:02d}:00")
            score += 15

        if exp.submitted_at.weekday() >= 5:
            reasons.append("Submitted on a weekend")
            score += 10

        return reasons, score

    @staticmethod
    def _rule_round(exp, amt):
        if amt > 1000 and amt % 100 == 0:
            return [f"Round number (${amt:.0f})"], 10
        return [], 0

    @staticmethod
    def analyze(exp_id):
        exp = Expense.query.get(exp_id)
        if not exp:
            return None, "Expense not found"

        amt = float(exp.amount)
        reasons = []
        score = 0

        rules = [
            RiskService._rule_duplicate,
            RiskService._rule_split,
            RiskService._rule_unusual,
            RiskService._rule_time,
            RiskService._rule_round,
        ]

        for rule in rules:
            r_reasons, r_score = rule(exp, amt)
            reasons.extend(r_reasons)
            score += r_score

        score = min(score, 100)

        if score > 80:
            level = 'critical'
        elif score > 50:
            level = 'high'
        elif score > 20:
            level = 'medium'
        else:
            level = 'low'

        exp.risk_score = score
        exp.risk_level = level
        exp.risk_reasons = reasons
        exp.analyzed_at = datetime.utcnow()
        db.session.commit()

        return {
            'risk_score': score,
            'risk_level': level,
            'risk_reasons': reasons,
            'analyzed_at': exp.analyzed_at.isoformat()
        }, None

    @staticmethod
    def get_flagged(min_score=50, page=1, limit=20):
        pg = Expense.query.filter(
            Expense.risk_score >= min_score
        ).paginate(page=page, per_page=limit, error_out=False)

        data = []
        for item in pg.items:
            data.append(ExpenseService._to_dict(item))

        return {
            'total': pg.total,
            'page': page,
            'limit': limit,
            'data': data
        }

    @staticmethod
    def get_breakdown(exp_id):
        exp = Expense.query.get(exp_id)
        if not exp:
            return None, "Expense not found"

        return {
            'risk_score': exp.risk_score,
            'risk_level': exp.risk_level,
            'risk_reasons': exp.risk_reasons,
            'analyzed_at': exp.analyzed_at.isoformat() if exp.analyzed_at else None
        }, None