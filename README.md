# Alyusr — Enterprise Insurance Broker Platform

A bilingual English/Arabic, RTL-ready Django platform for insurance brokers using Django templates, Bootstrap, HTMX and Alpine CSP. No React/Vue/Next.js SPA.

## Implemented foundation

- Django 6.1 project with SQLite development and SQL Server production configuration
- django CMS public-page integration and django-allauth email/Google/Microsoft support
- organization-scoped RBAC: Admin, Project Manager, Support Agent, Requester, Viewer/Auditor and Guest
- support groups, project membership and automatic Guest organization assignment
- exactly four-step, versioned JSON ticket forms with role-aware fields
- secure datasource registry with static/allowlisted model lookups; raw SQL keys are rejected
- ticket visibility enforced server-side by organization/requester/assignee/group/project
- multi-user/multi-group assignment, takeover, sanitized comments, attachments, approvals, audit records and secure-share model
- executable SLA warning/breach engine and escalation groups
- multi-carrier quotation comparison models
- client/policy/claim/document-vault/billing models; payment fields store external references only
- idempotent cron-style scheduler with dependencies, execution order and exponential retry
- bilingual knowledge base and version model
- admin-managed theme/site/navigation/services/trust content
- idempotent `seed_demo` command and GitHub Actions validation

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py cms check
python manage.py runserver
```

Run `python manage.py run_due_tasks` every minute via Windows Task Scheduler/cron. See `docs/DEPLOYMENT.md` and `docs/ARCHITECTURE.md`.
