from app import app
from ext import db
from models import Department, User, Expense
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    if Department.query.first():
        print("Database already seeded. Run with --force to re-seed.")
        import sys
        if '--force' not in sys.argv:
            exit()

    db.drop_all()
    db.create_all()

    # Departments
    eng = Department(name="Engineering", monthly_budget=50000)
    mkt = Department(name="Marketing", monthly_budget=30000)
    hr = Department(name="HR", monthly_budget=20000)
    db.session.add_all([eng, mkt, hr])
    db.session.commit()

    # Users
    pw = generate_password_hash("password123")
    users = [
        User(email="finance@test.com", password_hash=pw, first_name="Alice", last_name="Finance", role="finance"),
        User(email="emp.eng@test.com", password_hash=pw, first_name="Bob", last_name="Dev", role="employee", department_id=eng.id),
        User(email="mgr.eng@test.com", password_hash=pw, first_name="Carol", last_name="Lead", role="manager", department_id=eng.id),
        User(email="emp.mkt@test.com", password_hash=pw, first_name="Dave", last_name="Mkt", role="employee", department_id=mkt.id),
        User(email="mgr.mkt@test.com", password_hash=pw, first_name="Eve", last_name="MktLead", role="manager", department_id=mkt.id),
        User(email="emp.hr@test.com", password_hash=pw, first_name="Frank", last_name="Hr", role="employee", department_id=hr.id),
    ]
    db.session.add_all(users)
    db.session.commit()

    # Expenses
    now = datetime.utcnow()
    expenses = [
        # Engineering - draft
        Expense(title="New monitor", amount=350, currency="USD", category="equipment", status="draft", author_id=users[1].id, department_id=eng.id, notes="Need a second monitor"),
        # Engineering - submitted
        Expense(title="Team lunch", amount=120, currency="USD", category="meals", status="submitted", author_id=users[1].id, department_id=eng.id, submitted_at=now - timedelta(days=1), notes="Client meeting"),
        # Engineering - approved
        Expense(title="AWS credits", amount=500, currency="USD", category="software", status="approved", author_id=users[1].id, department_id=eng.id, submitted_at=now - timedelta(days=5), approved_at=now - timedelta(days=3)),
        # Engineering - rejected
        Expense(title="Gaming chair", amount=800, currency="USD", category="equipment", status="rejected", author_id=users[1].id, department_id=eng.id, submitted_at=now - timedelta(days=2), rejected_at=now - timedelta(days=1), rejection_reason="Not essential equipment"),
        # Engineering - another submitted (for testing cross-dept)
        Expense(title="Conference tickets", amount=1500, currency="USD", category="travel", status="submitted", author_id=users[1].id, department_id=eng.id, submitted_at=now - timedelta(hours=5)),
        # Marketing - draft
        Expense(title="Social media ads", amount=2000, currency="USD", category="software", status="draft", author_id=users[3].id, department_id=mkt.id),
        # Marketing - submitted
        Expense(title="Print materials", amount=450, currency="USD", category="other", status="submitted", author_id=users[3].id, department_id=mkt.id, submitted_at=now - timedelta(hours=12)),
        # Marketing - approved
        Expense(title="Trade show booth", amount=3000, currency="USD", category="travel", status="approved", author_id=users[3].id, department_id=mkt.id, submitted_at=now - timedelta(days=10), approved_at=now - timedelta(days=8)),
        # HR - submitted
        Expense(title="Onboarding lunch", amount=200, currency="USD", category="meals", status="submitted", author_id=users[5].id, department_id=hr.id, submitted_at=now - timedelta(hours=3)),
        # Engineering - high-value round number (triggers risk)
        Expense(title="Laptop upgrade", amount=2000, currency="USD", category="equipment", status="submitted", author_id=users[1].id, department_id=eng.id, submitted_at=now - timedelta(hours=1)),
    ]
    db.session.add_all(expenses)
    db.session.commit()

    print("Seeded successfully!")
    print()
    print("Users:")
    for u in User.query.all():
        print(f"  {u.email:30s} | {u.role:10s} | dept_id={u.department_id}")
    print()
    print("Expenses:")
    for e in Expense.query.all():
        print(f"  id={e.id:2d} | {e.title:25s} | ${e.amount:>6.2f} | {e.category:10s} | {e.status:10s} | dept_id={e.department_id}")
