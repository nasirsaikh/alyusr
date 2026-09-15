from django.contrib import admin
from .models import Category,Project,SLAPlan,Ticket,TicketActivity,TicketApproval,TicketAttachment,TicketComment,TicketShare,TicketSLAEvent
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display=('reference','subject','organization','category','priority','status','requester','due_at');list_filter=('organization','status','priority','category');search_fields=('reference','subject','requester__email');filter_horizontal=('assigned_users','assigned_groups')
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):list_display=('name','organization','code','is_active');prepopulated_fields={'code':('name',)};filter_horizontal=('members','support_groups')
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):list_display=('name_en','organization','project','default_group','sla_plan','is_active');prepopulated_fields={'code':('name_en',)}
admin.site.register(SLAPlan);admin.site.register(TicketActivity);admin.site.register(TicketApproval);admin.site.register(TicketAttachment);admin.site.register(TicketComment);admin.site.register(TicketShare);admin.site.register(TicketSLAEvent)
