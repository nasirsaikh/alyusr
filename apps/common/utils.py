import re
from typing import Any
from .models import AuditEvent,Notification

def client_ip(request):
    if not request:return None
    forwarded=request.META.get('HTTP_X_FORWARDED_FOR',''); return (forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')) or None

def record_audit(*,actor,action,obj,summary='',metadata=None,request=None,organization_id=''):
    return AuditEvent.objects.create(actor=actor if getattr(actor,'is_authenticated',False) else None,action=action,object_type=obj._meta.label,object_id=str(obj.pk),organization_id=str(organization_id or getattr(obj,'organization_id','') or ''),summary=summary,metadata=metadata or {},ip_address=client_ip(request))
def notify(user,title,message='',*,level=Notification.Level.INFO,url='',event_key=''):
    return Notification.objects.create(user=user,title=title,message=message,level=level,url=url,event_key=event_key) if user and user.pk else None
def mask_sensitive(value:Any):
    if value in (None,''):return value
    text=str(value)
    if '@' in text:
        local,_,domain=text.partition('@'); return f'{local[:2]}***@{domain}'
    if len(re.sub(r'\D','',text))>=6:return f'***{text[-4:]}'
    return '****' if len(text)<=4 else f'{text[:2]}***{text[-2:]}'
