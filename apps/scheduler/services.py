import importlib,traceback
from zoneinfo import ZoneInfo
from croniter import croniter
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import ScheduledTask,TaskRun
def next_run(task,base=None):
    base=base or timezone.now(); zone=ZoneInfo(task.timezone); local=base.astimezone(zone); return croniter(task.cron_expression,local).get_next(type(local)).astimezone(timezone.get_current_timezone())
def dependencies_satisfied(task):
    return all((r:=d.runs.order_by('-scheduled_for').first()) and r.status==TaskRun.Status.SUCCESS for d in task.dependencies.all())
def execute_task(task,scheduled_for=None,attempt=1):
    scheduled_for=scheduled_for or task.next_run_at or timezone.now(); key=f'task:{task.pk}:{scheduled_for.isoformat()}:attempt:{attempt}'; existing=TaskRun.objects.filter(idempotency_key=key).first()
    if existing:return existing
    if not dependencies_satisfied(task):return TaskRun.objects.create(task=task,scheduled_for=scheduled_for,idempotency_key=key,status=TaskRun.Status.SKIPPED,output='Dependencies are not satisfied.',finished_at=timezone.now())
    run=TaskRun.objects.create(task=task,scheduled_for=scheduled_for,idempotency_key=key,attempt=attempt)
    try:
        if task.task_type==ScheduledTask.TaskType.EMAIL:
            recipients=(task.payload or {}).get('to') or []; send_mail((task.payload or {}).get('subject',task.name),(task.payload or {}).get('body',''),settings.DEFAULT_FROM_EMAIL,recipients,fail_silently=False); output=f'Email sent to {len(recipients)} recipients.'
        elif task.task_type==ScheduledTask.TaskType.SLA:
            from apps.tickets.models import Ticket
            from apps.tickets.services import process_sla_ticket
            for ticket in Ticket.objects.exclude(status__in=[Ticket.Status.CLOSED,Ticket.Status.CANCELLED]).filter(due_at__isnull=False).select_related('category__sla_plan').iterator():process_sla_ticket(ticket)
            output='SLA evaluation complete.'
        else:
            path=task.callable_path.strip()
            if not any(path.startswith(p+'.') or path==p for p in settings.ALYUSR_TASK_CALLABLE_ALLOWLIST):raise PermissionError(f'Callable {path!r} is not allowlisted.')
            module,name=path.rsplit('.',1); output=str(getattr(importlib.import_module(module),name)(task=task,payload=task.payload or {}) or '')
        run.status=TaskRun.Status.SUCCESS;run.output=output
    except Exception as exc:
        run.error=f'{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}'
        if attempt<=task.max_retries:run.status=TaskRun.Status.RETRY;run.retry_at=timezone.now()+timezone.timedelta(seconds=task.backoff_seconds*(2**(attempt-1)))
        else:run.status=TaskRun.Status.FAILED
    run.finished_at=timezone.now();run.save();return run
@transaction.atomic
def run_due_tasks(now=None):
    now=now or timezone.now();results=[]
    for task in ScheduledTask.objects.select_for_update(skip_locked=True).filter(is_active=True,next_run_at__lte=now).order_by('execution_order','next_run_at'):
        results.append(execute_task(task,task.next_run_at));task.last_run_at=now;task.next_run_at=next_run(task,now);task.save()
    for old in TaskRun.objects.select_for_update(skip_locked=True).filter(status=TaskRun.Status.RETRY,retry_at__lte=now):
        old.status=TaskRun.Status.FAILED;old.save(update_fields=['status','updated_at']);results.append(execute_task(old.task,old.scheduled_for,old.attempt+1))
    return results
