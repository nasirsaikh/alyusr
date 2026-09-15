from django.contrib import admin
from .models import AuditEvent,Notification
admin.site.register(Notification)
@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display=('action','object_type','object_id','actor','created_at');readonly_fields=tuple(f.name for f in AuditEvent._meta.fields)
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
