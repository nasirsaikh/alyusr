from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.organizations.models import Role
from .models import ScheduledTask, TaskRun
from .services import execute_task


def _visible_tasks(user):
    qs = ScheduledTask.objects.select_related(
        "organization", "client", "client_product__product", "ticket_category", "last_generated_ticket", "last_generated_quote", "created_by"
    ).prefetch_related("quote_carriers", "dependencies")
    if user.is_superuser:
        return qs
    orgs = user.organization_memberships.filter(is_active=True).values_list("organization_id", flat=True)
    return qs.filter(organization_id__in=orgs)


def _can_manage_tasks(user, task=None):
    if user.is_superuser:
        return True
    memberships = user.organization_memberships.filter(is_active=True, role__in=[Role.ADMIN, Role.PROJECT_MANAGER])
    if task and task.organization_id:
        memberships = memberships.filter(organization=task.organization)
    return memberships.exists()


@login_required
def task_list(request):
    tasks = _visible_tasks(request.user)
    task_type = request.GET.get("type", "").strip()
    state = request.GET.get("state", "").strip()
    search = request.GET.get("q", "").strip()
    if task_type:
        tasks = tasks.filter(task_type=task_type)
    if state == "active":
        tasks = tasks.filter(is_active=True)
    elif state == "inactive":
        tasks = tasks.filter(is_active=False)
    if search:
        tasks = tasks.filter(Q(name__icontains=search) | Q(client__name__icontains=search) | Q(client_product__reference_name__icontains=search))
    recent_runs = TaskRun.objects.filter(task__in=tasks).select_related("task", "generated_ticket", "generated_quote").order_by("-created_at")[:12]
    return render(request, "scheduler/list.html", {
        "tasks": tasks[:300],
        "recent_runs": recent_runs,
        "task_types": ScheduledTask.TaskType.choices,
        "filters": {"type": task_type, "state": state, "q": search},
        "can_manage": _can_manage_tasks(request.user),
    })


@login_required
def task_detail(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    runs = task.runs.select_related("generated_ticket", "generated_quote").order_by("-scheduled_for", "-created_at")[:100]
    return render(request, "scheduler/detail.html", {"task": task, "runs": runs, "can_manage": _can_manage_tasks(request.user, task)})


@login_required
@require_POST
def run_task_now(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    if not _can_manage_tasks(request.user, task):
        return HttpResponseForbidden("You do not have permission to execute this task.")
    execute_task(task, scheduled_for=timezone.now())
    return redirect("scheduler:detail", pk=task.pk)
