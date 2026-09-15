import json
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404,render
from django.utils import timezone
from apps.clients.models import Client,Policy,Claim,BillingTransaction
from apps.common.models import Notification
from apps.quotations.models import QuoteRequest
from apps.scheduler.models import TaskRun
from apps.tickets.models import Ticket
@login_required
def dashboard(request):
    tickets=Ticket.objects.visible_to(request.user);open_tickets=tickets.exclude(status__in=[Ticket.Status.CLOSED,Ticket.Status.CANCELLED]);sla_total=open_tickets.filter(due_at__isnull=False).count();breached=open_tickets.filter(sla_breached_at__isnull=False).count()
    return render(request,'portal/dashboard.html',{'open_ticket_count':open_tickets.count(),'quote_count':QuoteRequest.objects.filter(requester=request.user).count(),'sla_compliance':round((sla_total-breached)/sla_total*100,1) if sla_total else 100,'task_failure_count':TaskRun.objects.filter(status='failed',created_at__gte=timezone.now()-timezone.timedelta(days=7)).count() if request.user.is_staff else 0,'status_chart_json':json.dumps(list(tickets.values('status').annotate(value=Count('id')))),'priority_chart_json':json.dumps(list(open_tickets.values('priority').annotate(value=Count('id')))),'recent_tickets':tickets[:8]})
@login_required
def notification_feed(request):return render(request,'portal/_notifications.html',{'notifications':Notification.objects.filter(user=request.user)[:20]})
@login_required
def client_center(request):
    client=get_object_or_404(Client,portal_user=request.user,is_active=True);return render(request,'portal/client_center.html',{'client':client,'policies':Policy.objects.filter(client=client),'claims':Claim.objects.filter(policy__client=client)[:20],'billing':BillingTransaction.objects.filter(policy__client=client)[:20]})
