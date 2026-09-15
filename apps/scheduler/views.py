from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import ScheduledTask
@login_required
def task_list(request):
    if request.user.is_superuser:tasks=ScheduledTask.objects.all()
    else:
        orgs=request.user.organization_memberships.filter(is_active=True).values_list('organization_id',flat=True);tasks=ScheduledTask.objects.filter(organization_id__in=orgs)
    return render(request,'scheduler/list.html',{'tasks':tasks[:200]})
