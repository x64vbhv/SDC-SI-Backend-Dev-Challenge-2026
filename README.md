# SDC-SI Expense Management System

**Submission for SDC-SI Backend Dev Challenge — Wildcard Round, AKGEC**

A role-based expense approval backend that enforces strict access control, a well-defined approval state machine, and includes optional fraud detection and budget tracking features.

---

## Tech Stack

**Python 3.11 · Flask · Flask-SQLAlchemy · Flask-JWT-Extended · Flask-Limiter · SQLite**

Project structure follows separation of concerns — routes (HTTP layer), services (business logic), models (data layer).

---

## Setup

```bash
pip install -r requirements.txt
python seed.py          # seed sample data
python app.py           # starts on http://localhost:5000
```

Interactive API docs at [http://localhost:5000/docs](http://localhost:5000/docs) (Swagger UI).

---

## Seed Data

6 users (password: `password123`), 10 expenses across all statuses and departments.

| Email | Role | Department |
|---|---|---|
| finance@test.com | finance | — |
| emp.eng@test.com | employee | Engineering |
| mgr.eng@test.com | manager | Engineering |
| emp.mkt@test.com | employee | Marketing |
| mgr.mkt@test.com | manager | Marketing |
| emp.hr@test.com | employee | HR |

| ID | Title | Amount | Status | Department |
|---|---|---|---|---|
| 1 | New monitor | $350 | draft | Engineering |
| 2 | Team lunch | $120 | submitted | Engineering |
| 3 | AWS credits | $500 | approved | Engineering |
| 4 | Gaming chair | $800 | rejected | Engineering |
| 5 | Conference tickets | $1,500 | submitted | Engineering |
| 6 | Social media ads | $2,000 | draft | Marketing |
| 7 | Print materials | $450 | submitted | Marketing |
| 8 | Trade show booth | $3,000 | approved | Marketing |
| 9 | Onboarding lunch | $200 | submitted | HR |
| 10 | Laptop upgrade | $2,000 | submitted | Engineering |

---

## Features Implemented

### 1. Authentication & Authorization
JWT-based auth with register, login, and logout (token blocklist). Three strictly-enforced roles. Passwords hashed via Werkzeug. Role and department checks happen server-side on every protected route — never trusts client-supplied role data.

- **Employee** — create, edit (if draft), delete (if draft), view own expenses
- **Manager** — approve/reject within own department, cannot self-approve, view department expenses
- **Finance** — read-only across all departments, can filter by department, view budget usage

### 2. Expense Management
Each expense carries title, amount, currency (ISO 4217 validated), category (travel/meals/equipment/software/other), status, author, department (derived from employee), timestamps, and optional receipt URL, notes, rejection reason.

### 3. Approval Workflow (State Machine)

```
draft ──→ submitted ──→ approved
           submitted ──→ rejected ──→ draft (reopen)
```

Every state transition is validated. Invalid transitions (e.g. approving a draft, rejecting an already-approved expense) return **HTTP 422** with a descriptive message. Rejection requires a reason.

### 4. Filtering & Pagination
List endpoint supports: `start_date`, `end_date`, `category`, `status`, `min_amount`, `max_amount`, `department_id` (finance only), `sort_by`, `sort_order`, `page`, `limit` (default 20, max 100). All list responses use envelope format: `{total, page, limit, data: [...]}`.

### 5. Fraud & Anomaly Detection (Bonus)
Rule-based risk engine that runs automatically on submission and on-demand via `POST /api/expenses/:id/analyze`. Detects:

- **Duplicate submissions** — similar title + amount, same employee, within 7 days
- **Structuring** — multiple sub-$500 expenses, same category, same day, summing over $1,000
- **Statistical outliers** — amount >3x the employee's category average
- **Suspicious timing** — late night (22:00–06:00) or weekend submissions
- **Round-number bias** — amounts over $1,000 that are clean multiples of 100

Returns `risk_score` (0–100), `risk_level` (low/medium/high/critical), and human-readable `risk_reasons`. Advisory only — never blocks approval. Manager/Finance can view flagged expenses via `GET /api/expenses/flagged` and full breakdown via `GET /api/expenses/:id/risk`.

### 6. Monthly Budget Caps (Bonus)
Departments have an optional `monthly_budget`. Approved spend is tracked per department-month. On approval past the cap, the request succeeds but returns a `warning` field. Budget info endpoint returns: `{budget, spent, remaining, over_budget}`.

---

## Security

- Passwords hashed, never stored in plain text
- JWT required on all protected routes
- Role checks enforced server-side
- Managers scoped to their own department — cross-department access returns 403/404
- Rate limiting on every endpoint (Flask-Limiter)
- Input validation on all mutation endpoints (category, currency, status, required fields)

---

## Project Structure

```
├── app.py                  # Flask app, blueprints, error handlers
├── config.py               # Configuration (DB, JWT secret)
├── ext.py                  # Extension init (db, jwt, limiter)
├── models.py               # User, Expense, Department, BudgetUsage
├── seed.py                 # Sample data seeder
├── swagger.json            # OpenAPI 3.0 specification
├── requirements.txt
├── routes/
│   ├── auth.py             # POST /api/auth/register, /api/auth/login
│   ├── expenses.py         # /api/expenses/* — CRUD, workflow, risk
│   ├── budget.py           # GET /api/budgets/department
│   └── departments.py      # GET/POST /api/departments
└── services/
    ├── AuthService.py      # Registration, authentication
    ├── ExpenseService.py   # CRUD, status transitions, filtering
    ├── BudgetService.py    # Monthly budget tracking
    ├── DepartmentService.py
    └── RiskService.py      # Rule-based fraud detection engine
```
