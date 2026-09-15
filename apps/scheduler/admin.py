from django.contrib import admin
from .models import ScheduledTask, TaskRun


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ("name", "task_type", "organization", "cron_expression", "next_run_at", "last_run_at", "is_active")
    list_filter = ("task_type", "organization", "is_active")
    search_fields = ("name", "callable_path", "client__name", "client_product__reference_name")
    filter_horizontal = ("dependencies", "quote_carriers")
    autocomplete_fields = ("created_by", "ticket_category", "client", "client_product", "last_generated_ticket", "last_generated_quote")
    fieldsets = (
        ("Schedule", {"fields": ("organization", "name", "task_type", "cron_expression", "timezone", "execution_order", "is_active")} ),
        ("Generated Work", {"fields": ("ticket_category", "client", "client_product", "quote_carriers", "last_generated_ticket", "last_generated_quote")} ),
        ("Execution", {"fields": ("payload", "callable_path", "dependencies", "max_retries", "backoff_seconds", "next_run_at", "last_run_at", "created_by")} ),
        ("Notifications", {"fields": ("notify_emails",)} ),
    )


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = ("task", "scheduled_for", "status", "attempt", "generated_ticket", "generated_quote", "finished_at")
    list_filter = ("status", "scheduled_for")
    search_fields = ("task__name", "idempotency_key", "generated_ticket__reference", "generated_quote__reference")
    readonly_fields = ("idempotency_key", "started_at", "finished_at", "output", "error")
