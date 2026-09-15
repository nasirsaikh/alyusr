from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.common.utils import notify, record_audit
from apps.forms_engine.services import visible_schema_for_user
from apps.organizations.models import Membership, Role, SupportGroup
from .models import Category, Ticket, TicketActivity, TicketApproval, TicketAttachment, TicketComment, validate_attachment
from .services import create_ticket, masked_dynamic_data, prepare_dynamic_data, takeover_ticket


def _can_manage_ticket(user, ticket):
    if user.is_superuser:
        return True
    return user.organization_memberships.filter(
        organization=ticket.organization,
        is_active=True,
        role__in=[Role.ADMIN, Role.PROJECT_MANAGER, Role.SUPPORT_AGENT],
    ).exists() or ticket.assigned_users.filter(pk=user.pk).exists() or ticket.assigned_groups.filter(members=user).exists()


def _can_decide_approval(user, approval):
    if user.is_superuser:
        return True
    if approval.approver_user_id == user.pk:
        return True
    if approval.approver_group_id and approval.approver_group.members.filter(pk=user.pk).exists():
        return True
    return user.organization_memberships.filter(
        organization=approval.ticket.organization,
        is_active=True,
        role__in=[Role.ADMIN, Role.PROJECT_MANAGER],
    ).exists()


def _assignment_context(ticket):
    memberships = Membership.objects.filter(organization=ticket.organization, is_active=True).select_related("user").order_by("user__first_name", "user__username")
    groups = SupportGroup.objects.filter(organization=ticket.organization, is_active=True).prefetch_related("members").order_by("name")
    return {"assignment_memberships": memberships, "assignment_groups": groups}


def _save_comment_attachments(ticket, comment, user, uploaded_files):
    created = []
    for uploaded in uploaded_files:
        validate_attachment(uploaded)
        attachment = TicketAttachment.objects.create(
            ticket=ticket,
            comment=comment,
            uploaded_by=user,
            file=uploaded,
            original_name=uploaded.name,
            content_type=getattr(uploaded, "content_type", "") or "",
            size_bytes=getattr(uploaded, "size", 0) or 0,
        )
        created.append(attachment)
    return created


@login_required
def ticket_list(request):
    qs = Ticket.objects.visible_to(request.user).select_related("organization", "category", "project", "requester", "client", "client_product__product").prefetch_related("assigned_users", "assigned_groups")
    status = request.GET.get("status", "").strip()
    work_type = request.GET.get("type", "").strip()
    priority = request.GET.get("priority", "").strip()
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if work_type:
        qs = qs.filter(work_type=work_type)
    if priority:
        qs = qs.filter(priority=priority)
    if q:
        qs = qs.filter(Q(subject__icontains=q) | Q(reference__icontains=q) | Q(client__name__icontains=q) | Q(client_product__reference_name__icontains=q))
    return render(request, "tickets/list.html", {
        "tickets": qs[:300],
        "statuses": Ticket.Status.choices,
        "work_types": Ticket.WorkType.choices,
        "priorities": Ticket.Priority.choices,
        "filters": {"status": status, "type": work_type, "priority": priority, "q": q},
    })


@login_required
@transaction.atomic
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.visible_to(request.user).select_related(
            "organization", "project", "category__sla_plan", "requester", "client", "client_product__product", "form_version"
        ).prefetch_related("assigned_users", "assigned_groups", "attachments", "approvals__approver_user", "approvals__approver_group", "activities__actor", "comments__author", "comments__attachments"),
        pk=pk,
    )
    can_manage = _can_manage_ticket(request.user, ticket)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        if action == "comment":
            body = request.POST.get("body", "").strip()
            uploads = request.FILES.getlist("attachments")
            if body or uploads:
                comment = TicketComment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    body=body or "Attachment uploaded",
                    is_internal=bool(request.POST.get("is_internal")) and can_manage,
                )
                _save_comment_attachments(ticket, comment, request.user, uploads)
                TicketActivity.objects.create(ticket=ticket, actor=request.user, action="commented", summary="Internal note added" if comment.is_internal else "Ticket update posted", metadata={"attachments": len(uploads)})
                if not comment.is_internal and ticket.requester_id != request.user.pk:
                    notify(ticket.requester, f"Ticket updated: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")
                record_audit(actor=request.user, action="ticket.comment", obj=ticket, summary="Ticket conversation updated", request=request, organization_id=ticket.organization_id)
            if request.headers.get("HX-Request"):
                refreshed = Ticket.objects.prefetch_related("comments__author", "comments__attachments").get(pk=ticket.pk)
                return render(request, "tickets/_comments.html", {"ticket": refreshed})
            return redirect("tickets:detail", pk=ticket.pk)

        if action == "approval":
            approval = get_object_or_404(TicketApproval.objects.select_related("ticket", "approver_user", "approver_group"), pk=request.POST.get("approval"), ticket=ticket)
            if not _can_decide_approval(request.user, approval):
                return HttpResponseForbidden("You are not an approver for this level.")
            decision = request.POST.get("decision")
            if approval.status != TicketApproval.Status.PENDING or decision not in {TicketApproval.Status.APPROVED, TicketApproval.Status.REJECTED}:
                messages.error(request, "This approval action is no longer available.")
                return redirect("tickets:detail", pk=ticket.pk)
            lower_pending = ticket.approvals.filter(level__lt=approval.level).exclude(status=TicketApproval.Status.APPROVED).exists()
            if lower_pending:
                messages.error(request, "Earlier approval levels must be approved first.")
                return redirect("tickets:detail", pk=ticket.pk)
            approval.status = decision
            approval.decided_at = timezone.now()
            approval.note = request.POST.get("note", "").strip()
            approval.save(update_fields=["status", "decided_at", "note", "updated_at"])
            TicketActivity.objects.create(ticket=ticket, actor=request.user, action=f"approval.{decision}", summary=f"Approval level {approval.level} {decision}", metadata={"approval_id": str(approval.pk)})
            if decision == TicketApproval.Status.REJECTED:
                ticket.status = Ticket.Status.PENDING
                ticket.save(update_fields=["status", "updated_at"])
            elif not ticket.approvals.exclude(status=TicketApproval.Status.APPROVED).exists() and ticket.status == Ticket.Status.APPROVAL:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save(update_fields=["status", "updated_at"])
            notify(ticket.requester, f"Approval update: {ticket.reference}", f"Level {approval.level}: {approval.get_status_display()}", url=f"/portal/tickets/{ticket.pk}/")
            record_audit(actor=request.user, action=f"ticket.approval.{decision}", obj=ticket, summary=f"Approval level {approval.level}", request=request, organization_id=ticket.organization_id)
            return redirect("tickets:detail", pk=ticket.pk)

        if not can_manage:
            return HttpResponseForbidden("You do not have permission to manage this ticket.")

        if action == "status":
            new_status = request.POST.get("status", "")
            valid_statuses = {value for value, _ in Ticket.Status.choices}
            if new_status not in valid_statuses:
                messages.error(request, "Invalid ticket status.")
            else:
                old_status = ticket.status
                if old_status in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED} and new_status not in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED}:
                    closed_at = ticket.closed_at or ticket.resolved_at
                    if closed_at and timezone.now() > closed_at + timezone.timedelta(days=ticket.category.reopen_window_days):
                        messages.error(request, f"This ticket can only be reopened within {ticket.category.reopen_window_days} days.")
                        return redirect("tickets:detail", pk=ticket.pk)
                if new_status in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED} and ticket.approvals.filter(status=TicketApproval.Status.PENDING).exists():
                    messages.error(request, "Pending approval levels must be completed before resolution/closure.")
                    return redirect("tickets:detail", pk=ticket.pk)
                ticket.status = new_status
                now = timezone.now()
                if new_status == Ticket.Status.RESOLVED and not ticket.resolved_at:
                    ticket.resolved_at = now
                if new_status == Ticket.Status.CLOSED and not ticket.closed_at:
                    ticket.closed_at = now
                if old_status in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED} and new_status not in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED}:
                    ticket.reopened_at = now
                ticket.save()
                TicketActivity.objects.create(ticket=ticket, actor=request.user, action="status.changed", summary=f"Status changed from {old_status} to {new_status}")
                record_audit(actor=request.user, action="ticket.status_changed", obj=ticket, summary=f"{old_status} → {new_status}", request=request, organization_id=ticket.organization_id)
                notify(ticket.requester, f"Ticket status: {ticket.reference}", ticket.get_status_display(), url=f"/portal/tickets/{ticket.pk}/")

        elif action == "assign_user":
            membership = get_object_or_404(Membership, pk=request.POST.get("membership"), organization=ticket.organization, is_active=True)
            ticket.assigned_users.add(membership.user)
            TicketActivity.objects.create(ticket=ticket, actor=request.user, action="assigned.user", summary=f"Assigned to {membership.user}")
            notify(membership.user, f"Ticket assigned: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")

        elif action == "unassign_user":
            user_id = request.POST.get("user")
            assigned = ticket.assigned_users.filter(pk=user_id).first()
            if assigned:
                ticket.assigned_users.remove(assigned)
                TicketActivity.objects.create(ticket=ticket, actor=request.user, action="unassigned.user", summary=f"Unassigned {assigned}")

        elif action == "assign_group":
            group = get_object_or_404(SupportGroup, pk=request.POST.get("group"), organization=ticket.organization, is_active=True)
            ticket.assigned_groups.add(group)
            TicketActivity.objects.create(ticket=ticket, actor=request.user, action="assigned.group", summary=f"Assigned group {group.name}")
            for member in group.members.all():
                notify(member, f"Group ticket assigned: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")

        elif action == "unassign_group":
            group = ticket.assigned_groups.filter(pk=request.POST.get("group")).first()
            if group:
                ticket.assigned_groups.remove(group)
                TicketActivity.objects.create(ticket=ticket, actor=request.user, action="unassigned.group", summary=f"Unassigned group {group.name}")

        return redirect("tickets:detail", pk=ticket.pk)

    approvals = list(ticket.approvals.all())
    context = {
        "ticket": ticket,
        "dynamic_data": masked_dynamic_data(ticket, request.user),
        "can_manage": can_manage,
        "status_choices": Ticket.Status.choices,
        "approval_actions": {approval.pk: _can_decide_approval(request.user, approval) and approval.status == TicketApproval.Status.PENDING for approval in approvals},
    }
    if can_manage:
        context.update(_assignment_context(ticket))
    return render(request, "tickets/detail.html", context)


@login_required
def ticket_create(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related("organization").first()
    if not membership:
        return HttpResponseForbidden("Your account is not assigned to an active organization.")
    categories = Category.objects.filter(organization=membership.organization, is_active=True)
    category = None
    form_version = None
    schema = {"steps": [{"title": f"Step {i}", "fields": []} for i in range(1, 5)]}
    cid = request.GET.get("category") or request.POST.get("category")
    if cid:
        category = get_object_or_404(categories, pk=cid)
        form_version = category.form_definition.active_version if category.form_definition_id else None
        if form_version:
            schema = visible_schema_for_user(form_version, request.user, membership.organization)
    if request.method == "POST" and category:
        data, errors, schema = prepare_dynamic_data(form_version, request.user, membership.organization, request.POST)
        subject = request.POST.get("subject", "").strip()
        if not subject:
            errors["subject"] = "Subject is required."
        if not errors:
            client = getattr(request.user, "insurance_client", None)
            ticket = create_ticket(
                user=request.user,
                organization=membership.organization,
                category=category,
                subject=subject,
                description=request.POST.get("description", ""),
                priority=request.POST.get("priority", Ticket.Priority.NORMAL),
                dynamic_data=data,
                form_version=form_version,
                request=request,
                client=client,
            )
            return redirect("tickets:detail", pk=ticket.pk)
        messages.error(request, "Please correct the form.")
    return render(request, "tickets/create.html", {"categories": categories, "selected_category": category, "schema": schema, "priorities": Ticket.Priority.choices})


@login_required
@require_POST
def takeover(request, pk):
    ticket = get_object_or_404(Ticket.objects.visible_to(request.user), pk=pk)
    try:
        takeover_ticket(ticket, request.user, request=request)
    except PermissionError:
        return HttpResponseForbidden("You are not in an assigned support group.")
    return redirect("tickets:detail", pk=ticket.pk)
