from django.contrib import admin
from .models import (
    AnimationPreset,
    CarrierTrustBadge,
    ClientLogo,
    FAQ,
    ManagementMember,
    NavigationItem,
    PageSection,
    Service,
    SiteSettings,
    Statistic,
    Testimonial,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identity", {"fields": ("site_name_en", "site_name_ar", "short_name", "tagline_en", "tagline_ar", "logo", "favicon")} ),
        ("Hero", {"fields": ("hero_eyebrow_en", "hero_eyebrow_ar", "hero_title_en", "hero_title_ar", "hero_text_en", "hero_text_ar", "hero_image", "primary_cta_label_en", "primary_cta_label_ar", "primary_cta_url", "secondary_cta_label_en", "secondary_cta_label_ar", "secondary_cta_url")} ),
        ("About & Trust", {"fields": ("about_title_en", "about_title_ar", "about_text_en", "about_text_ar", "trust_title_en", "trust_title_ar", "trust_text_en", "trust_text_ar", "years_in_business", "agency_registration_number")} ),
        ("Contact", {"fields": ("contact_email", "contact_phone", "whatsapp_number", "address_en", "address_ar", "city", "map_embed_url", "linkedin_url", "instagram_url", "facebook_url")} ),
        ("Footer", {"fields": ("footer_text_en", "footer_text_ar")} ),
        ("Theme", {"fields": ("primary_color", "secondary_color", "accent_color", "surface_color", "enable_dark_mode", "enable_motion")} ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(NavigationItem)
class NavigationAdmin(admin.ModelAdmin):
    list_display = ("label_en", "area", "url", "sort_order", "is_active")
    list_filter = ("area", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("label_en", "label_ar", "url")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title_en", "badge_en", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title_en", "title_ar")


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = ("title_en", "section_type", "sort_order", "is_active")
    list_filter = ("section_type", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title_en", "title_ar", "body_en", "body_ar")


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ("value", "label_en", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("client_name", "client_title", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(CarrierTrustBadge)
class CarrierTrustBadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(ClientLogo)
class ClientLogoAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(ManagementMember)
class ManagementMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "title_en", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question_en", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("question_en", "question_ar", "answer_en", "answer_ar")


@admin.register(AnimationPreset)
class AnimationPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "css_class", "duration_ms", "is_safe", "is_active")
    list_editable = ("duration_ms", "is_active")
