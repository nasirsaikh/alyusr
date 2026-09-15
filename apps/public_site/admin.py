from django.contrib import admin
from .models import SiteSettings,NavigationItem,Service,Statistic,Testimonial,CarrierTrustBadge
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self,request):return not SiteSettings.objects.exists()
@admin.register(NavigationItem)
class NavigationAdmin(admin.ModelAdmin):list_display=('label_en','area','url','sort_order','is_active');list_editable=('sort_order','is_active')
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):list_display=('title_en','sort_order','is_active');list_editable=('sort_order','is_active')
admin.site.register(Statistic);admin.site.register(Testimonial);admin.site.register(CarrierTrustBadge)
