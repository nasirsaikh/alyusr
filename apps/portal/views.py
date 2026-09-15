import json
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from apps.clients.models import BillingTransaction, Claim, Client, ClientProduct, Policy
from apps.common.models import Notification
from apps.quotations.models import QuoteParticipant, QuoteRequest
from apps.scheduler.models import ScheduledTask, TaskRun
from apps.tickets.models import Ticket


def _chart_json(queryset, field):
    return json.dumps(list(queryset.values(field).annotate(value=Count("id")).order_by(field)))


@login_required
def dashboard(request):
    now = timezone.now()
    tickets = Ticket.objects.visible_to(request.user).select_related("client", "client_product__product", "category")
    open_tickets = tickets.exclude(status__in=[Ticket.Status.CLOSED, Ticket.Status.CANCELLED])
    sla_total = open_tickets.filter(due_at__isnull=False).count()
    breached = open_tickets.filter(sla_breached_at__isnull=False).count()
    overdue = open_tickets.filter(due_at__lt=now).count()

    membership_org_ids = list(request.user.organization_memberships.filter(is_active=True).values_list("organization_id", flat=True))
    if request.user.is_superuser:
        quotes = QuoteRequest.objects.all()
        tasks = ScheduledTask.objects.all()
        runs = TaskRun.objects.all()
        client_products = ClientProduct.objects.filter(is_active=True)
    elif request.user.is_staff:
        quotes = QuoteRequest.objects.filter(organization_id__in=membership_org_ids)
        tasks = ScheduledTask.objects.filter(Q(organization_id__in=membership_org_ids) | Q(organization__isnull=True))
        runs = TaskRun.objects.filter(task__in=tasks)
        client_products = ClientProduct.objects.filter(client__organization_id__in=membership_org_ids, is_active=True)
    else:
        quotes = QuoteRequest.objects.filter(requester=request.user)
        tasks = ScheduledTask.objects.none()
        runs = TaskRun.objects.none()
        client_products = ClientProduct.objects.filter(client__portal_user=request.user, is_active=True)

    active_quote_statuses = [
        QuoteRequest.Status.DRAFT,
        QuoteRequest.Status.SUBMITTED,
        QuoteRequest.Status.UNDER_REVIEW,
        QuoteRequest.Status.NEGOTIATION,
        QuoteRequest.Status.APPROVAL,
        QuoteRequest.Status.AWARDED,
        QuoteRequest.Status.BOUND,
    ]
    active_quotes = quotes.filter(status__in=active_quote_statuses)
    renewal_quotes = quotes.filter(request_type=QuoteRequest.RequestType.RENEWAL, status__in=active_quote_statuses)
    participants = QuoteParticipant.objects.filter(quote_request__in=quotes)
    renewal_limit = timezone.localdate() + timezone.timedelta(days=60)
    upcoming_renewals = client_products.filter(next_renewal_date__isnull=False, next_renewal_date__lte=renewal_limit).select_related("client", "product", "current_policy").order_by("next_renewal_date")

    context = {
        "ticket_count": tickets.count(),
        "open_ticket_count": open_tickets.count(),
        "overdue_ticket_count": overdue,
        "quote_count": quotes.count(),
        "active_quote_count": active_quotes.count(),
        "renewal_quote_count": renewal_quotes.count(),
        "upcoming_renewal_count": upcoming_renewals.count(),
        "sla_compliance": round((sla_total - breached) / sla_total * 100, 1) if sla_total else 100,
        "task_count": tasks.filter(is_active=True).count(),
        "task_failure_count": runs.filter(status=TaskRun.Status.FAILED, created_at__gte=now - timezone.timedelta(days=7)).count(),
        "status_chart_json": _chart_json(tickets, "status"),
        "priority_chart_json": _chart_json(open_tickets, "priority"),
        "work_type_chart_json": _chart_json(tickets, "work_type"),
        "quote_status_chart_json": _chart_json(quotes, "status"),
        "participant_chart_json": _chart_json(participants, "status"),
        "task_status_chart_json": _chart_json(runs.filter(created_at__gte=now - timezone.timedelta(days=30)), "status"),
        "recent_tickets": tickets[:8],
        "recent_quotes": quotes.select_related("client", "client_product__product", "selected_quote__carrier").order_by("-created_at")[:8],
        "upcoming_renewals": upcoming_renewals[:8],
        "recent_task_runs": runs.select_related("task", "generated_ticket", "generated_quote").order_by("-created_at")[:8],
    }
    return render(request, "portal/dashboard.html", context)


@login_required
def notification_feed(request):
    return render(request, "portal/_notifications.html", {"notifications": Notification.objects.filter(user=request.user)[:20]})


@login_required
def client_center(request):
    client = get_object_or_404(Client, portal_user=request.user, is_active=True)
    return render(
        request,
        "portal/client_center.html",
        {
            "client": client,
            "client_products": ClientProduct.objects.filter(client=client, is_active=True).select_related("product", "current_policy"),
            "policies": Policy.objects.filter(client=client).select_related("carrier", "product"),
            "claims": Claim.objects.filter(policy__client=client).select_related("policy")[:20],
            "billing": BillingTransaction.objects.filter(policy__client=client).select_related("policy")[:20],
        },
    )
