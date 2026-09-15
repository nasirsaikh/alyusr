from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.forms_engine.services import visible_schema_for_user
from apps.organizations.models import Membership
from .models import Category,Ticket,TicketComment
from .services import create_ticket,masked_dynamic_data,prepare_dynamic_data,takeover_ticket
@login_required
def ticket_list(request):
    qs=Ticket.objects.visible_to(request.user).select_related('organization','category','project','requester'); status=request.GET.get('status'); q=request.GET.get('q','').strip()
    if status:qs=qs.filter(status=status)
    if q:qs=qs.filter(subject__icontains=q)|qs.filter(reference__icontains=q)
    return render(request,'tickets/list.html',{'tickets':qs[:200],'statuses':Ticket.Status.choices})
@login_required
def ticket_detail(request,pk):
    ticket=get_object_or_404(Ticket.objects.visible_to(request.user),pk=pk)
    if request.method=='POST' and request.POST.get('action')=='comment':
        body=request.POST.get('body','').strip()
        if body:TicketComment.objects.create(ticket=ticket,author=request.user,body=body,is_internal=bool(request.POST.get('is_internal')))
        if request.headers.get('HX-Request'):return render(request,'tickets/_comments.html',{'ticket':ticket})
        return redirect('tickets:detail',pk=ticket.pk)
    return render(request,'tickets/detail.html',{'ticket':ticket,'dynamic_data':masked_dynamic_data(ticket,request.user)})
@login_required
def ticket_create(request):
    membership=Membership.objects.filter(user=request.user,is_active=True).select_related('organization').first()
    if not membership:return HttpResponseForbidden('Your account is not assigned to an active organization.')
    categories=Category.objects.filter(organization=membership.organization,is_active=True); category=None; form_version=None; schema={'steps':[{'title':f'Step {i}','fields':[]} for i in range(1,5)]}; cid=request.GET.get('category') or request.POST.get('category')
    if cid:
        category=get_object_or_404(categories,pk=cid); form_version=category.form_definition.active_version if category.form_definition_id else None
        if form_version:schema=visible_schema_for_user(form_version,request.user,membership.organization)
    if request.method=='POST' and category:
        data,errors,schema=prepare_dynamic_data(form_version,request.user,membership.organization,request.POST); subject=request.POST.get('subject','').strip()
        if not subject:errors['subject']='Subject is required.'
        if not errors:
            ticket=create_ticket(user=request.user,organization=membership.organization,category=category,subject=subject,description=request.POST.get('description',''),priority=request.POST.get('priority',Ticket.Priority.NORMAL),dynamic_data=data,form_version=form_version,request=request); return redirect('tickets:detail',pk=ticket.pk)
        messages.error(request,'Please correct the form.')
    return render(request,'tickets/create.html',{'categories':categories,'selected_category':category,'schema':schema,'priorities':Ticket.Priority.choices})
@login_required
@require_POST
def takeover(request,pk):
    ticket=get_object_or_404(Ticket.objects.visible_to(request.user),pk=pk)
    try:takeover_ticket(ticket,request.user,request=request)
    except PermissionError:return HttpResponseForbidden('You are not in an assigned support group.')
    return redirect('tickets:detail',pk=ticket.pk)
