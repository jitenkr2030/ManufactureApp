# Manufacturing ERP — Version 2

A full-stack Django manufacturing ERP foundation with PostgreSQL as the default
database, Bootstrap 5 interface, modular CRUD screens, API, inventory ledger,
multi-level BOM/MRP, production calendar, approval records, reports and exports.

## Included business areas
Dashboard; company/branch/factory/department; product/category/unit masters;
BOM and BOM components; warehouse/location/inventory; stock movements;
supplier/customer; purchase requisitions, purchase orders and GRN; work centers,
machines, routing and operations; production orders and schedules; material
issues; job work; shop-floor execution; batch/serial/genealogy; QC and defects;
WIP; finished goods; scrap/rework; production cost sheets; sales/dispatch;
maintenance; workforce/shifts/attendance; approvals; documents; expenses and
basic journal entities; returns/warranty; safety; notifications and audit trail.

## Windows setup (PostgreSQL)
1. Install PostgreSQL 15+ and create a database and user:
   ```sql
   CREATE DATABASE manufacturing_erp;
   CREATE USER erp_user WITH PASSWORD 'replace-this-password';
   GRANT ALL PRIVILEGES ON DATABASE manufacturing_erp TO erp_user;
   ```
   For PostgreSQL 15+, connect to the database and grant schema access:
   ```sql
   GRANT ALL ON SCHEMA public TO erp_user;
   ```
2. Extract ZIP and open the project folder in terminal.
3. Create environment:
   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   ```
   Python 3.12/3.13/3.14 can be used with a compatible current Django release.
4. Install packages:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env`, then set DB_USER, DB_PASSWORD, DB_NAME,
   DB_HOST and DB_PORT to your PostgreSQL settings. Set DB_ENGINE=postgresql.
6. Generate and apply migrations:
   ```powershell
   python manage.py makemigrations erp
   python manage.py migrate
   ```
7. Create administrator:
   ```powershell
   python manage.py createsuperuser\n   python manage.py setup_erp_roles
   ```
8. Run:
   ```powershell
   python manage.py runserver
   ```

Open http://127.0.0.1:8000/ . Sign in with the superuser credentials.
The administration/setup panel remains available at /admin/ for initial master
configuration and advanced model maintenance; normal users work in the ERP UI.

## SQLite quick evaluation
Set DB_ENGINE=sqlite and DB_NAME=db.sqlite3 in `.env`, then run migrations and
server. PostgreSQL is the recommended production database.

## Main screens
- `/` dashboard
- `/module/<module>/` module list/search
- `/mrp/` recursive multi-level MRP explosion
- `/planning/calendar/` production schedule list/calendar data
- `/reports/` KPI, Excel and PDF exports
- `/audit/` audit trail
- `/api/` REST API
- `/admin/` system setup

## CRUD modules
The sidebar provides user-facing list/create/edit/delete/search pages (Django model permissions are enforced; run `setup_erp_roles` to create role groups) for
master data, procurement, inventory, manufacturing, traceability, QC, costing,
sales, maintenance, workforce, finance, documents and workflow records.

## Posting operations
GRN, material issue and stock transfer records can be posted from their module
lists. Posting creates immutable stock movement ledger entries and prevents
negative stock. Finished-goods receipts are available at
`/production/finished-goods/receive/`. Product QR labels are available at `/products/<product-id>/qr.png`.

## Security and production readiness
This is a substantial runnable ERP foundation, not a fully certified ERP or
accounting system. Role and module permission enforcement must be configured
with Django Groups/Permissions for each deployment; the included login is
authentication, and approval requests provide a basic decision workflow.
Before production use, add company/factory/warehouse row-level isolation,
permission tests, approval policies, idempotency keys, concurrency tests,
statutory GST/accounting rules, invoice/payment posting, robust serial/batch
genealogy validations, Celery worker/Beat deployment, Redis, backup/restore
automation, object storage, email/SMS provider credentials, HTTPS, secure
cookies, monitoring, and load/security testing. Never expose DEBUG=True or the
development SECRET_KEY on the public internet.
