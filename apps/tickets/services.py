from django.db import transaction
from django.utils import timezone
from apps.common.utils import mask_sensitive,notify,record_audit
from apps.forms_engine.models import FormSubmission
from apps.forms_engine.services import validate_submission,visible_schema_for_user
from .models import Ticket,TicketActivity,TicketSLAEvent

def prepare_dynamic_data(form_version,user,organization,post_data):
    if not form_version:return {},{},None
    schema=visible_schema_for_user(form_version,user,organization); data={}
    for step in schema.get('steps',[]):
        for field in step.get('fields',[]):
            key=field['key']; typ=field.get('type')
            if typ=='multiselect':data[key]=post_data.getlist(f'field__{key}')
            elif typ=='checkbox':data[key]=bool(post_data.get(f'field__{key}'))
            elif typ=='number':
                value=post_data.get(f'field__{key}'); data[key]=float(value) if value not in (None,'') else None
            else:data[key]=post_data.get(f'field__{key}','')
    valid,errors=validate_submission(schema,data); return data,errors,schema
@transaction.atomic
def create_ticket(*,user,organization,category,subject,description,priority,dynamic_data=None,form_version=None,request=None):
    due_at=timezone.now()+timezone.timedelta(minutes=category.sla_plan.resolution_minutes) if category.sla_plan_id else None
    ticket=Ticket.objects.create(organization=organization,project=category.project,category=category,requester=user,subject=subject,description=description,priority=priority,dynamic_data=dynamic_data or {},form_version=form_version,due_at=due_at)
    if category.default_group_id:
        ticket.assigned_groups.add(category.default_group)
        for member in category.default_group.members.all():notify(member,f'Ticket assigned: {ticket.reference}',ticket.subject,url=f'/portal/tickets/{ticket.pk}/')
    if form_version:FormSubmission.objects.create(form_version=form_version,submitted_by=user,organization_id=str(organization.pk),data=dynamic_data or {},is_valid=True)
    TicketActivity.objects.create(ticket=ticket,actor=user,action='created',summary='Ticket created'); record_audit(actor=user,action='ticket.created',obj=ticket,summary=ticket.subject,request=request,organization_id=organization.pk); return ticket
def masked_dynamic_data(ticket,user):
    data=dict(ticket.dynamic_data or {})
    if user.is_superuser or ticket.assigned_users.filter(pk=user.pk).exists() or ticket.assigned_groups.filter(members=user).exists():return data
    schema=(ticket.form_version.schema if ticket.form_version_id else {}) or {}; sensitive={f['key'] for s in schema.get('steps',[]) for f in s.get('fields',[]) if f.get('sensitive')}
    for key in sensitive:
        if key in data:data[key]=mask_sensitive(data[key])
    return data
def takeover_ticket(ticket,user,request=None):
    if not ticket.assigned_groups.filter(members=user).exists() and not user.is_superuser:raise PermissionError
    ticket.assigned_users.add(user); TicketActivity.objects.create(ticket=ticket,actor=user,action='takeover',summary=f'{user} took ownership'); record_audit(actor=user,action='ticket.takeover',obj=ticket,request=request,organization_id=ticket.organization_id); return ticket
def process_sla_ticket(ticket):
    if not ticket.due_at or not ticket.is_open or not ticket.sla_plan:return None
    now=timezone.now(); plan=ticket.sla_plan; total=max((ticket.due_at-ticket.created_at).total_seconds(),1); percent=max((now-ticket.created_at).total_seconds(),0)/total*100
    if now>=ticket.due_at and not ticket.sla_breached_at:
        ticket.sla_breached_at=now; ticket.save(update_fields=['sla_breached_at','updated_at']); TicketSLAEvent.objects.create(ticket=ticket,event='breach',threshold_percent=100)
        if plan.escalation_group_id and plan.auto_reassign_on_breach:ticket.assigned_groups.add(plan.escalation_group)
        return 'breach'
    if percent>=plan.warning_percent and not ticket.sla_warning_sent_at:
        ticket.sla_warning_sent_at=now; ticket.save(update_fields=['sla_warning_sent_at','updated_at']); TicketSLAEvent.objects.create(ticket=ticket,event='warning',threshold_percent=percent); return 'warning'
