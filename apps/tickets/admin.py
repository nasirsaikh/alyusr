from django.contrib import admin
from .models import Category, Project, SLAPlan, Ticket, TicketActivity, TicketApproval, TicketAttachment, TicketComment, TicketShare, TicketSLAEvent


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("reference", "work_type", "subject", "client", "client_product", "organization", "category", "priority", "status", "requester", "due_at")
    list_filter = ("organization", "work_type", "origin", "status", "priority", "category")
    search_fields = ("reference", "source_reference", "subject", "requester__email", "client__name", "client__client_number")
    filter_horizontal = ("assigned_users", "assigned_groups")
    autocomplete_fields = ("client", "client_product", "parent_ticket", "requester", "category", "project", "form_version")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "code", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}
    filter_horizontal = ("members", "support_groups")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "organization", "project", "default_group", "sla_plan", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name_en", "name_ar", "code")
    prepopulated_fields = {"code": ("name_en",)}


@admin.register(SLAPlan)
class SLAPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "response_minutes", "resolution_minutes", "warning_percent", "auto_reassign_on_breach", "is_active")
    list_filter = ("organization", "auto_reassign_on_breach", "business_hours_only", "is_active")
    search_fields = ("name",)


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    list_display = ("ticket", "action", "actor", "summary", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("ticket__reference", "summary")


@admin.register(TicketApproval)
class TicketApprovalAdmin(admin.ModelAdmin):
    list_display = ("ticket", "level", "approver_user", "approver_group", "status", "decided_at")
    list_filter = ("status", "level")
    search_fields = ("ticket__reference", "note")


admin.site.register(TicketAttachment)
admin.site.register(TicketComment)
admin.site.register(TicketShare)
admin.site.register(TicketSLAEvent)
