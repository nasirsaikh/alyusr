from django.contrib import admin
from django.utils import timezone
from .models import DataSource, FormDefinition, FormSubmission, FormVersion


@admin.action(description="Publish selected form versions")
def publish_selected(modeladmin, request, queryset):
    for obj in queryset:
        obj.full_clean()
        obj.definition.versions.exclude(pk=obj.pk).update(is_published=False)
        obj.is_published = True
        obj.published_at = timezone.now()
        obj.save()


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "module", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(FormVersion)
class FormVersionAdmin(admin.ModelAdmin):
    list_display = ("definition", "version", "is_published", "published_at")
    list_filter = ("is_published", "definition__module")
    search_fields = ("definition__name", "definition__code")
    actions = (publish_selected,)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("form_version", "submitted_by", "organization_id", "is_valid", "created_at")
    list_filter = ("is_valid", "created_at")
    search_fields = ("organization_id", "submitted_by__email", "form_version__definition__name")
