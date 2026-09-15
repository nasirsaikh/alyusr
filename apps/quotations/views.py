from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import QuoteRequest
@login_required
def quote_list(request):
    if request.user.is_superuser:qs=QuoteRequest.objects.all()
    else:
        orgs=request.user.organization_memberships.filter(is_active=True).values_list('organization_id',flat=True); qs=QuoteRequest.objects.filter(organization_id__in=orgs).filter(Q(requester=request.user)|Q(organization__memberships__user=request.user,organization__memberships__role__in=['admin','project_manager','support_agent'])).distinct()
    return render(request,'quotations/list.html',{'quotes':qs.prefetch_related('carrier_quotes__carrier')[:200]})
