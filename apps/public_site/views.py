from django.http import HttpResponse
from django.shortcuts import render
from .models import CarrierTrustBadge,NavigationItem,Service,SiteSettings,Statistic,Testimonial
def home(request):
    return render(request,'public/home.html',{'site_settings':SiteSettings.load(),'public_navigation':NavigationItem.objects.filter(area=NavigationItem.Area.PUBLIC,is_active=True),'services':Service.objects.filter(is_active=True),'statistics':Statistic.objects.filter(is_active=True),'testimonials':Testimonial.objects.filter(is_active=True),'carrier_badges':CarrierTrustBadge.objects.filter(is_active=True)})
def theme_css(request):
    s=SiteSettings.load(); return HttpResponse(f':root{{--alyusr-primary:{s.primary_color};--alyusr-secondary:{s.secondary_color};--alyusr-accent:{s.accent_color};--alyusr-surface:{s.surface_color};}}',content_type='text/css; charset=utf-8')
