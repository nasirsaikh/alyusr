from django.db.utils import OperationalError,ProgrammingError
from .models import Notification

def platform_context(request):
    context={'notification_unread_count':0,'recent_notifications':[],'site_settings_global':None,'portal_navigation':[]}
    try:
        from apps.public_site.models import NavigationItem,SiteSettings
        context['site_settings_global']=SiteSettings.load(); context['portal_navigation']=list(NavigationItem.objects.filter(area=NavigationItem.Area.PORTAL,is_active=True))
    except (OperationalError,ProgrammingError):pass
    if getattr(request.user,'is_authenticated',False):
        try:
            qs=Notification.objects.filter(user=request.user,read_at__isnull=True); context['notification_unread_count']=qs.count(); context['recent_notifications']=list(qs[:8])
        except (OperationalError,ProgrammingError):pass
    return context
