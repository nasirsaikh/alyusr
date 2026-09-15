from django.http import HttpResponse
from django.shortcuts import render
from .models import (
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


def home(request):
    context = {
        "site_settings": SiteSettings.load(),
        "public_navigation": NavigationItem.objects.filter(area=NavigationItem.Area.PUBLIC, is_active=True),
        "footer_navigation": NavigationItem.objects.filter(area=NavigationItem.Area.FOOTER, is_active=True),
        "services": Service.objects.filter(is_active=True),
        "statistics": Statistic.objects.filter(is_active=True),
        "testimonials": Testimonial.objects.filter(is_active=True),
        "carrier_badges": CarrierTrustBadge.objects.filter(is_active=True),
        "client_logos": ClientLogo.objects.filter(is_active=True),
        "management": ManagementMember.objects.filter(is_active=True),
        "page_sections": PageSection.objects.filter(is_active=True),
        "faqs": FAQ.objects.filter(is_active=True),
    }
    return render(request, "public/home.html", context)


def theme_css(request):
    s = SiteSettings.load()
    css = f"""
:root {{
  --alyusr-primary: {s.primary_color};
  --alyusr-secondary: {s.secondary_color};
  --alyusr-accent: {s.accent_color};
  --alyusr-surface: {s.surface_color};
}}
"""
    return HttpResponse(css, content_type="text/css; charset=utf-8")
