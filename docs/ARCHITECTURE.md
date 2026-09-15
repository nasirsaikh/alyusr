# Alyusr architecture

Alyusr is server-rendered Django. HTMX is used for partial interactions and Alpine CSP for lightweight local state.

Domain apps: `public_site`, `organizations`, `forms_engine`, `tickets`, `quotations`, `clients`, `scheduler`, `knowledge`, `common`, and `portal`.

Operational records are organization-scoped. Ticket access begins from `Ticket.objects.visible_to(user)`, not unrestricted primary-key queries. Dynamic form versions preserve historical schemas; ticket form schemas must contain exactly four steps. Datasources accept static values or explicitly allowlisted Django models and reject SQL/query keys.

SLA plans calculate ticket due times and the scheduler processes warnings/breaches. Scheduled tasks have deterministic idempotency keys, dependency checks, execution order, retries and allowlisted Python callables.

Payment/autopay records contain external processor references only; card numbers and CVVs are not part of the data model.
