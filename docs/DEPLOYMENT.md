# Deployment

## Development

Install requirements, copy `.env.example` to `.env`, run `makemigrations`, `migrate`, `createsuperuser`, optional `seed_demo`, then `cms check` and `runserver`.

## SQL Server

Set `DB_ENGINE=mssql`, `DB_NAME`, `DB_HOST`, `DB_USER`, `DB_PASSWORD` and `DB_DRIVER`. Install Microsoft ODBC Driver 18 and use a least-privilege application login. Run migrations as a controlled deployment step and `collectstatic --noinput`.

## Scheduler

Invoke `python manage.py run_due_tasks` every minute using Windows Task Scheduler or cron. SLA checking may be configured as a scheduled task.

## OAuth

Configure the Django `Site` and Google/Microsoft Social Applications in Django Admin. Keep client secrets outside Git.

## IIS

Use a WSGI/FastCGI bridge pointing to `config.wsgi.application`; terminate HTTPS in IIS, forward `X-Forwarded-Proto: https`, and serve static/media through approved storage.
