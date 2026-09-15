from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.common.utils import notify, record_audit
from apps.organizations.models import Role
from apps.tickets.models import Ticket, TicketActivity
from .models import CarrierQuote, QuoteRequest


def _visible_quotes(user):
    qs = QuoteRequest.objects.select_related("organization", "ticket", "client", "client_product__product", "renewal_of_policy", "selected_quote__carrier")
    if user.is_superuser:
        return qs
    orgs = user.organization_memberships.filter(is_active=True).values_list("organization_id", flat=True)
    staff_roles = [Role.ADMIN, Role.PROJECT_MANAGER, Role.SUPPORT_AGENT]
    return qs.filter(organization_id__in=orgs).filter(Q(requester=user) | Q(organization__memberships__user=user, organization__memberships__role__in=staff_roles)).distinct()


def _can_manage_quote(user, quote):
    if user.is_superuser:
        return True
    return user.organization_memberships.filter(organization=quote.organization, is_active=True, role__in=[Role.ADMIN, Role.PROJECT_MANAGER, Role.SUPPORT_AGENT]).exists()


@login_required
def quote_list(request):
    qs = _visible_quotes(request.user)
    status = request.GET.get("status", "").strip()
    request_type = request.GET.get("type", "").strip()
    search = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if request_type:
        qs = qs.filter(request_type=request_type)
    if search:
        qs = qs.filter(Q(reference__icontains=search) | Q(client_name__icontains=search) | Q(client__client_number__icontains=search) | Q(line_of_business__icontains=search))
    return render(request, "quotations/list.html", {"quotes": qs.prefetch_related("participants__carrier", "carrier_quotes__carrier")[:300], "status_choices": QuoteRequest.Status.choices, "type_choices": QuoteRequest.RequestType.choices, "filters": {"status": status, "type": request_type, "q": search}})


@login_required
def quote_detail(request, pk):
    quote = get_object_or_404(_visible_quotes(request.user), pk=pk)
    return render(request, "quotations/detail.html", {"quote": quote, "participants": quote.participants.select_related("carrier", "assigned_to").all(), "carrier_quotes": quote.carrier_quotes.select_related("carrier", "participant").all(), "documents": quote.documents.select_related("carrier_quote__carrier", "uploaded_by").all(), "can_manage": _can_manage_quote(request.user, quote)})


@login_required
@require_POST
@transaction.atomic
def award_quote(request, pk, carrier_quote_pk):
    quote = get_object_or_404(_visible_quotes(request.user).select_for_update(), pk=pk)
    if not _can_manage_quote(request.user, quote):
        return HttpResponseForbidden("You do not have permission to award this quotation.")
    selected = get_object_or_404(CarrierQuote.objects.select_for_update(), pk=carrier_quote_pk, quote_request=quote)
    quote.carrier_quotes.update(is_winner=False)
    selected.is_winner = True
    selected.save(update_fields=["is_winner", "updated_at"])
    quote.selected_quote = selected
    quote.status = QuoteRequest.Status.AWARDED
    quote.awarded_at = timezone.now()
    quote.save(update_fields=["selected_quote", "status", "awarded_at", "updated_at"])
    if quote.ticket_id:
        quote.ticket.status = Ticket.Status.IN_PROGRESS
        quote.ticket.save(update_fields=["status", "updated_at"])
        TicketActivity.objects.create(ticket=quote.ticket, actor=request.user, action="quotation.awarded", summary=f"Quotation awarded to {selected.carrier.name}", metadata={"carrier_quote_id": str(selected.pk), "premium": str(selected.premium), "currency": selected.currency})
    record_audit(actor=request.user, action="quotation.awarded", obj=quote, summary=f"Awarded to {selected.carrier.name}", request=request, organization_id=quote.organization_id)
    notify(quote.requester, f"Quotation awarded: {quote.reference}", f"Selected insurer: {selected.carrier.name}", url=f"/portal/quotations/{quote.pk}/")
    return redirect("quotations:detail", pk=quote.pk)
