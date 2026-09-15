from django.core.mail import EmailMultiAlternatives
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils import timezone
from apps.clients.models import ClientProduct
from .models import QuoteParticipant, QuoteRequest


def quotation_dashboard_context(organization):
    today = timezone.localdate()
    now = timezone.now()
    quotes = QuoteRequest.objects.filter(organization=organization)
    active_statuses = [
        QuoteRequest.Status.DRAFT,
        QuoteRequest.Status.SUBMITTED,
        QuoteRequest.Status.UNDER_REVIEW,
        QuoteRequest.Status.NEGOTIATION,
        QuoteRequest.Status.APPROVAL,
        QuoteRequest.Status.AWARDED,
        QuoteRequest.Status.BOUND,
    ]
    active = quotes.filter(status__in=active_statuses)
    renewals = active.filter(request_type=QuoteRequest.RequestType.RENEWAL)
    upcoming_limit = today + timezone.timedelta(days=60)
    upcoming_renewals = ClientProduct.objects.filter(
        client__organization=organization,
        is_active=True,
        next_renewal_date__isnull=False,
        next_renewal_date__lte=upcoming_limit,
    ).select_related("client", "product", "current_policy").order_by("next_renewal_date")[:15]
    participants = QuoteParticipant.objects.filter(quote_request__organization=organization)
    participant_summary = list(participants.values("status").annotate(total=Count("id")).order_by("status"))
    recent_quotes = quotes.select_related("client", "client_product__product", "selected_quote__carrier").order_by("-updated_at")[:15]
    return {
        "organization": organization,
        "generated_at": now,
        "active_quote_count": active.count(),
        "renewal_quote_count": renewals.count(),
        "awarded_count": quotes.filter(status=QuoteRequest.Status.AWARDED).count(),
        "market_overdue_count": active.filter(market_due_at__lt=now).count(),
        "upcoming_renewals": upcoming_renewals,
        "participant_summary": participant_summary,
        "recent_quotes": recent_quotes,
    }


def send_quotation_dashboard(*, task, payload=None):
    payload = payload or {}
    if not task.organization_id:
        raise ValueError("Quotation dashboard tasks require an organization.")
    recipients = payload.get("to") or task.notify_emails or []
    if not recipients:
        raise ValueError("Quotation dashboard task has no recipients.")
    context = quotation_dashboard_context(task.organization)
    subject = payload.get("subject") or f"Alyusr Quotation Dashboard - {task.organization.name} - {timezone.localdate():%d %b %Y}"
    html = render_to_string("quotations/email_dashboard.html", context)
    text = f"Alyusr quotation dashboard for {task.organization.name}. Active quotations: {context['active_quote_count']}. Renewals: {context['renewal_quote_count']}."
    message = EmailMultiAlternatives(subject=subject, body=text, to=recipients)
    message.attach_alternative(html, "text/html")
    message.send(fail_silently=False)
    return f"Quotation dashboard emailed to {len(recipients)} recipient(s)."
