from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.common.utils import mask_sensitive, notify, record_audit
from apps.forms_engine.models import FormSubmission
from apps.forms_engine.services import validate_submission, visible_schema_for_user
from apps.organizations.models import SupportGroup
from .models import Ticket, TicketActivity, TicketApproval, TicketSLAEvent


def prepare_dynamic_data(form_version, user, organization, post_data):
    if not form_version:
        return {}, {}, None
    schema = visible_schema_for_user(form_version, user, organization)
    data = {}
    for step in schema.get("steps", []):
        for field in step.get("fields", []):
            key = field["key"]
            typ = field.get("type")
            if typ == "multiselect":
                data[key] = post_data.getlist(f"field__{key}")
            elif typ == "checkbox":
                data[key] = bool(post_data.get(f"field__{key}"))
            elif typ == "number":
                value = post_data.get(f"field__{key}")
                data[key] = float(value) if value not in (None, "") else None
            else:
                data[key] = post_data.get(f"field__{key}", "")
    valid, errors = validate_submission(schema, data)
    return data, errors, schema


def _create_approvals(ticket, category, organization):
    User = get_user_model()
    created = []
    for index, config in enumerate(category.approval_levels or [], start=1):
        if not isinstance(config, dict):
            continue
        approver_user = None
        approver_group = None
        if config.get("user_id"):
            approver_user = User.objects.filter(pk=config["user_id"]).first()
        if config.get("group_id"):
            approver_group = SupportGroup.objects.filter(pk=config["group_id"], organization=organization, is_active=True).first()
        if not approver_user and not approver_group:
            continue
        approval = TicketApproval.objects.create(
            ticket=ticket,
            level=int(config.get("level") or index),
            approver_user=approver_user,
            approver_group=approver_group,
        )
        created.append(approval)
        if approver_user:
            notify(approver_user, f"Approval required: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")
        if approver_group:
            for member in approver_group.members.all():
                notify(member, f"Group approval required: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")
    return created


@transaction.atomic
def create_ticket(
    *,
    user,
    organization,
    category,
    subject,
    description="",
    priority=Ticket.Priority.NORMAL,
    dynamic_data=None,
    form_version=None,
    request=None,
    work_type=Ticket.WorkType.SERVICE,
    origin=Ticket.Origin.MANUAL,
    client=None,
    client_product=None,
    source_reference="",
    parent_ticket=None,
    renewal_due_on=None,
):
    due_at = timezone.now() + timezone.timedelta(minutes=category.sla_plan.resolution_minutes) if category.sla_plan_id else None
    ticket = Ticket.objects.create(
        organization=organization,
        project=category.project,
        category=category,
        requester=user,
        subject=subject,
        description=description,
        priority=priority,
        dynamic_data=dynamic_data or {},
        form_version=form_version,
        due_at=due_at,
        work_type=work_type,
        origin=origin,
        client=client,
        client_product=client_product,
        source_reference=source_reference,
        parent_ticket=parent_ticket,
        renewal_due_on=renewal_due_on,
    )
    if category.default_group_id:
        ticket.assigned_groups.add(category.default_group)
        for member in category.default_group.members.all():
            notify(member, f"Ticket assigned: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")
    if form_version:
        FormSubmission.objects.create(form_version=form_version, submitted_by=user, organization_id=str(organization.pk), data=dynamic_data or {}, is_valid=True)
    approvals = _create_approvals(ticket, category, organization)
    TicketActivity.objects.create(ticket=ticket, actor=user, action="created", summary="Ticket created", metadata={"work_type": work_type, "origin": origin, "approval_levels": len(approvals)})
    record_audit(actor=user, action="ticket.created", obj=ticket, summary=ticket.subject, request=request, organization_id=organization.pk)
    return ticket


def masked_dynamic_data(ticket, user):
    data = dict(ticket.dynamic_data or {})
    if user.is_superuser or ticket.assigned_users.filter(pk=user.pk).exists() or ticket.assigned_groups.filter(members=user).exists():
        return data
    schema = (ticket.form_version.schema if ticket.form_version_id else {}) or {}
    sensitive = {f["key"] for s in schema.get("steps", []) for f in s.get("fields", []) if f.get("sensitive")}
    for key in sensitive:
        if key in data:
            data[key] = mask_sensitive(data[key])
    return data


def takeover_ticket(ticket, user, request=None):
    if not ticket.assigned_groups.filter(members=user).exists() and not user.is_superuser:
        raise PermissionError
    ticket.assigned_users.add(user)
    TicketActivity.objects.create(ticket=ticket, actor=user, action="takeover", summary=f"{user} took ownership")
    record_audit(actor=user, action="ticket.takeover", obj=ticket, request=request, organization_id=ticket.organization_id)
    return ticket


def process_sla_ticket(ticket):
    if not ticket.due_at or not ticket.is_open or not ticket.sla_plan:
        return None
    now = timezone.now()
    plan = ticket.sla_plan
    total = max((ticket.due_at - ticket.created_at).total_seconds(), 1)
    percent = max((now - ticket.created_at).total_seconds(), 0) / total * 100
    if now >= ticket.due_at and not ticket.sla_breached_at:
        ticket.sla_breached_at = now
        ticket.save(update_fields=["sla_breached_at", "updated_at"])
        TicketSLAEvent.objects.create(ticket=ticket, event=TicketSLAEvent.Event.BREACH, threshold_percent=100)
        if plan.escalation_group_id and plan.auto_reassign_on_breach:
            ticket.assigned_groups.add(plan.escalation_group)
        if plan.escalate_to_reporting_manager:
            for assigned in ticket.assigned_users.all():
                membership = assigned.organization_memberships.filter(organization=ticket.organization, is_active=True).select_related("reporting_manager").first()
                if membership and membership.reporting_manager_id:
                    ticket.assigned_users.add(membership.reporting_manager)
                    notify(membership.reporting_manager, f"SLA breach: {ticket.reference}", ticket.subject, url=f"/portal/tickets/{ticket.pk}/")
        return "breach"
    if percent >= plan.warning_percent and not ticket.sla_warning_sent_at:
        ticket.sla_warning_sent_at = now
        ticket.save(update_fields=["sla_warning_sent_at", "updated_at"])
        TicketSLAEvent.objects.create(ticket=ticket, event=TicketSLAEvent.Event.WARNING, threshold_percent=percent)
        return "warning"
    return None
