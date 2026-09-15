import importlib
import traceback
from zoneinfo import ZoneInfo
from croniter import croniter
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import ScheduledTask, TaskRun


def next_run(task, base=None):
    base = base or timezone.now()
    zone = ZoneInfo(task.timezone)
    local = base.astimezone(zone)
    return croniter(task.cron_expression, local).get_next(type(local)).astimezone(timezone.get_current_timezone())


def dependencies_satisfied(task):
    return all((r := d.runs.order_by("-scheduled_for").first()) and r.status == TaskRun.Status.SUCCESS for d in task.dependencies.all())


def _task_requester(task):
    if task.created_by_id:
        return task.created_by
    if task.client_id and task.client.portal_user_id:
        return task.client.portal_user
    if task.client_product_id and task.client_product.client.portal_user_id:
        return task.client_product.client.portal_user
    raise ValueError("The scheduled task needs a created_by user or a client portal user to own generated work.")


@transaction.atomic
def _generate_ticket(task, scheduled_for, *, work_type="task", origin="task", subject=None):
    from apps.tickets.models import Ticket
    from apps.tickets.services import create_ticket

    if not task.organization_id or not task.ticket_category_id:
        raise ValueError("Ticket-generating tasks require organization and ticket_category.")
    source_reference = f"TASK:{task.pk}:{scheduled_for.isoformat()}"
    existing = Ticket.objects.filter(organization=task.organization, source_reference=source_reference).first()
    if existing:
        return existing
    client = task.client or (task.client_product.client if task.client_product_id else None)
    subject = subject or (task.payload or {}).get("subject") or task.name
    description = (task.payload or {}).get("description", "")
    priority = (task.payload or {}).get("priority", Ticket.Priority.NORMAL)
    return create_ticket(
        user=_task_requester(task),
        organization=task.organization,
        category=task.ticket_category,
        subject=subject,
        description=description,
        priority=priority,
        dynamic_data=(task.payload or {}).get("dynamic_data", {}),
        work_type=work_type,
        origin=origin,
        client=client,
        client_product=task.client_product,
        source_reference=source_reference,
        renewal_due_on=task.client_product.next_renewal_date if task.client_product_id else None,
    )


@transaction.atomic
def _generate_quote(task, scheduled_for, renewal=False):
    from apps.quotations.models import QuoteParticipant, QuoteRequest
    from apps.tickets.models import Ticket

    if not task.client_product_id:
        raise ValueError("Quotation-generating tasks require client_product.")
    client_product = task.client_product
    client = client_product.client
    ticket = _generate_ticket(
        task,
        scheduled_for,
        work_type=Ticket.WorkType.RENEWAL if renewal else Ticket.WorkType.QUOTATION,
        origin=Ticket.Origin.RENEWAL if renewal else Ticket.Origin.TASK,
        subject=(task.payload or {}).get("subject") or f"{'Renewal' if renewal else 'Quotation'} - {client.name} - {client_product.product.name_en}",
    )
    quote, _ = QuoteRequest.objects.get_or_create(
        ticket=ticket,
        defaults={
            "organization": task.organization,
            "requester": _task_requester(task),
            "client": client,
            "client_product": client_product,
            "renewal_of_policy": client_product.current_policy,
            "request_type": QuoteRequest.RequestType.RENEWAL if renewal else QuoteRequest.RequestType.NEW,
            "client_name": client.name,
            "client_email": client.email,
            "client_phone": client.phone,
            "line_of_business": client_product.product.name_en,
            "status": QuoteRequest.Status.DRAFT,
            "market_due_at": (task.payload or {}).get("market_due_at"),
            "dynamic_data": (task.payload or {}).get("dynamic_data", {}),
        },
    )
    for carrier in task.quote_carriers.filter(is_active=True):
        QuoteParticipant.objects.get_or_create(quote_request=quote, carrier=carrier)
    task.last_generated_ticket = ticket
    task.last_generated_quote = quote
    task.save(update_fields=["last_generated_ticket", "last_generated_quote", "updated_at"])
    return ticket, quote


def execute_task(task, scheduled_for=None, attempt=1):
    scheduled_for = scheduled_for or task.next_run_at or timezone.now()
    key = f"task:{task.pk}:{scheduled_for.isoformat()}:attempt:{attempt}"
    existing = TaskRun.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    if not dependencies_satisfied(task):
        return TaskRun.objects.create(task=task, scheduled_for=scheduled_for, idempotency_key=key, status=TaskRun.Status.SKIPPED, output="Dependencies are not satisfied.", finished_at=timezone.now())
    run = TaskRun.objects.create(task=task, scheduled_for=scheduled_for, idempotency_key=key, attempt=attempt)
    try:
        if task.task_type == ScheduledTask.TaskType.EMAIL:
            recipients = (task.payload or {}).get("to") or task.notify_emails or []
            send_mail((task.payload or {}).get("subject", task.name), (task.payload or {}).get("body", ""), settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
            output = f"Email sent to {len(recipients)} recipients."
        elif task.task_type == ScheduledTask.TaskType.SLA:
            from apps.tickets.models import Ticket
            from apps.tickets.services import process_sla_ticket
            for ticket in Ticket.objects.exclude(status__in=[Ticket.Status.CLOSED, Ticket.Status.CANCELLED]).filter(due_at__isnull=False).select_related("category__sla_plan").iterator():
                process_sla_ticket(ticket)
            output = "SLA evaluation complete."
        elif task.task_type == ScheduledTask.TaskType.TICKET:
            ticket = _generate_ticket(task, scheduled_for)
            run.generated_ticket = ticket
            task.last_generated_ticket = ticket
            task.save(update_fields=["last_generated_ticket", "updated_at"])
            output = f"Generated ticket {ticket.reference}."
        elif task.task_type == ScheduledTask.TaskType.QUOTATION:
            ticket, quote = _generate_quote(task, scheduled_for, renewal=False)
            run.generated_ticket = ticket
            run.generated_quote = quote
            output = f"Generated quotation {quote.reference} under ticket {ticket.reference}."
        elif task.task_type == ScheduledTask.TaskType.RENEWAL:
            ticket, quote = _generate_quote(task, scheduled_for, renewal=True)
            run.generated_ticket = ticket
            run.generated_quote = quote
            output = f"Generated renewal quotation {quote.reference} under ticket {ticket.reference}."
        else:
            path = task.callable_path.strip()
            if not any(path.startswith(p + ".") or path == p for p in settings.ALYUSR_TASK_CALLABLE_ALLOWLIST):
                raise PermissionError(f"Callable {path!r} is not allowlisted.")
            module, name = path.rsplit(".", 1)
            output = str(getattr(importlib.import_module(module), name)(task=task, payload=task.payload or {}) or "")
        run.status = TaskRun.Status.SUCCESS
        run.output = output
    except Exception as exc:
        run.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}"
        if attempt <= task.max_retries:
            run.status = TaskRun.Status.RETRY
            run.retry_at = timezone.now() + timezone.timedelta(seconds=task.backoff_seconds * (2 ** (attempt - 1)))
        else:
            run.status = TaskRun.Status.FAILED
    run.finished_at = timezone.now()
    run.save()
    return run


@transaction.atomic
def run_due_tasks(now=None):
    now = now or timezone.now()
    results = []
    for task in ScheduledTask.objects.select_for_update(skip_locked=True).filter(is_active=True, next_run_at__lte=now).order_by("execution_order", "next_run_at"):
        results.append(execute_task(task, task.next_run_at))
        task.last_run_at = now
        task.next_run_at = next_run(task, now)
        task.save()
    for old in TaskRun.objects.select_for_update(skip_locked=True).filter(status=TaskRun.Status.RETRY, retry_at__lte=now):
        old.status = TaskRun.Status.FAILED
        old.save(update_fields=["status", "updated_at"])
        results.append(execute_task(old.task, old.scheduled_for, old.attempt + 1))
    return results
