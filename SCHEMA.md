# Database Schema

## departments

Stores company departments with optional monthly budget caps.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PK, AUTO | |
| name | VARCHAR(100) | NOT NULL, UNIQUE | |
| monthly_budget | NUMERIC(12,2) | NULLABLE | Monthly spending cap |
| created_at | DATETIME | DEFAULT now | |
| updated_at | DATETIME | DEFAULT now, ON UPDATE now | |

## users

System users with role-based access control.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PK, AUTO | |
| email | VARCHAR(255) | NOT NULL, UNIQUE | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | Werkzeug-generated hash |
| first_name | VARCHAR(100) | NOT NULL | |
| last_name | VARCHAR(100) | NOT NULL | |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'employee' | employee / manager / finance |
| department_id | INTEGER | FK → departments.id, NULLABLE | NULL for finance role |
| created_at | DATETIME | DEFAULT now | |
| updated_at | DATETIME | DEFAULT now, ON UPDATE now | |

## expenses

Core expense records with status tracking and risk analysis fields.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PK, AUTO | |
| title | VARCHAR(200) | NOT NULL | Short description |
| amount | NUMERIC(12,2) | NOT NULL | |
| currency | VARCHAR(3) | NOT NULL | ISO 4217 code |
| category | VARCHAR(20) | NOT NULL | travel / meals / equipment / software / other |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | draft / submitted / approved / rejected |
| author_id | INTEGER | FK → users.id, NOT NULL | Creator |
| department_id | INTEGER | FK → departments.id, NULLABLE | Derived from author |
| receipt_url | VARCHAR(500) | NULLABLE | |
| notes | TEXT | NULLABLE | |
| rejection_reason | TEXT | NULLABLE | Required on reject |
| submitted_at | DATETIME | NULLABLE | Set on submit |
| approved_at | DATETIME | NULLABLE | Set on approve |
| rejected_at | DATETIME | NULLABLE | Set on reject |
| created_at | DATETIME | DEFAULT now | |
| updated_at | DATETIME | DEFAULT now, ON UPDATE now | |
| risk_score | INTEGER | NULLABLE | 0–100 |
| risk_level | VARCHAR(20) | NULLABLE | low / medium / high / critical |
| risk_reasons | JSON | NULLABLE | Human-readable list |
| analyzed_at | DATETIME | NULLABLE | Last analysis timestamp |

### Status State Machine

```
draft → submitted → approved
        submitted → rejected → draft (reopen)
```

Invalid transitions return HTTP 422.

## budget_usage

Tracks approved spend per department per month. Updated on each approval.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PK, AUTO | |
| department_id | INTEGER | FK → departments.id, NOT NULL | |
| month | DATE | NOT NULL | First day of the month (e.g. 2026-07-01) |
| approved_amount | NUMERIC(12,2) | NOT NULL, DEFAULT 0 | Cumulative approved spend |
| updated_at | DATETIME | DEFAULT now, ON UPDATE now | |

**Unique constraint:** (department_id, month)

## token_blocklist

Stores revoked JWT token identifiers for logout enforcement.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PK, AUTO | |
| jti | VARCHAR(36) | NOT NULL, UNIQUE | JWT token ID (UUID) |
| created_at | DATETIME | DEFAULT now | |

---

## Entity Relationships

```
Department ──< User         (department_id)
Department ──< Expense      (department_id)
User ────────< Expense      (author_id)
Department ──< BudgetUsage  (department_id)
```
