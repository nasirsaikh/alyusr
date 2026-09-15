from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import Article
@login_required
def article_list(request):
    qs=Article.objects.filter(status=Article.Status.PUBLISHED); q=request.GET.get('q','').strip()
    if not request.user.is_superuser:
        orgs=request.user.organization_memberships.filter(is_active=True).values_list('organization_id',flat=True); qs=qs.filter(Q(organization__isnull=True)|Q(organization_id__in=orgs))
    if q:qs=qs.filter(Q(title_en__icontains=q)|Q(title_ar__icontains=q)|Q(summary_en__icontains=q)|Q(body_en__icontains=q))
    return render(request,'knowledge/list.html',{'articles':qs[:100],'q':q})
