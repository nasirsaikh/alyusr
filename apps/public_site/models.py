from django.core.exceptions import ValidationError
from django.db import models
from apps.common.models import UUIDTimeStampedModel
class SiteSettings(UUIDTimeStampedModel):
    site_name_en=models.CharField(max_length=120,default='Alyusr'); site_name_ar=models.CharField(max_length=120,default='اليسر'); short_name=models.CharField(max_length=30,default='Alyusr'); tagline_en=models.CharField(max_length=220,blank=True); tagline_ar=models.CharField(max_length=220,blank=True); contact_email=models.EmailField(blank=True); contact_phone=models.CharField(max_length=40,blank=True); whatsapp_number=models.CharField(max_length=40,blank=True); address_en=models.CharField(max_length=255,blank=True); address_ar=models.CharField(max_length=255,blank=True); city=models.CharField(max_length=100,default='Muscat'); map_embed_url=models.URLField(blank=True); logo=models.ImageField(upload_to='site/',blank=True); favicon=models.ImageField(upload_to='site/',blank=True); hero_image=models.ImageField(upload_to='site/hero/',blank=True); hero_title_en=models.CharField(max_length=180,blank=True); hero_title_ar=models.CharField(max_length=180,blank=True); hero_text_en=models.TextField(blank=True); hero_text_ar=models.TextField(blank=True); primary_cta_label_en=models.CharField(max_length=80,default='Get a Quote'); primary_cta_label_ar=models.CharField(max_length=80,default='اطلب عرض سعر'); primary_cta_url=models.CharField(max_length=255,default='/portal/quotations/'); agency_registration_number=models.CharField(max_length=120,blank=True); years_in_business=models.PositiveSmallIntegerField(default=0); primary_color=models.CharField(max_length=7,default='#166534'); secondary_color=models.CharField(max_length=7,default='#0f766e'); accent_color=models.CharField(max_length=7,default='#d97706'); surface_color=models.CharField(max_length=7,default='#ffffff'); enable_dark_mode=models.BooleanField(default=True); enable_motion=models.BooleanField(default=True)
    class Meta: verbose_name_plural='Site settings'
    def clean(self):
        if not self.pk and SiteSettings.objects.exists():raise ValidationError('Only one SiteSettings record is allowed.')
    @classmethod
    def load(cls):return cls.objects.first() or cls()
    def __str__(self):return self.site_name_en
class NavigationItem(UUIDTimeStampedModel):
    class Area(models.TextChoices): PUBLIC='public','Public Header'; PORTAL='portal','Portal Sidebar'; FOOTER='footer','Footer'
    area=models.CharField(max_length=12,choices=Area.choices,default=Area.PUBLIC); label_en=models.CharField(max_length=80); label_ar=models.CharField(max_length=80,blank=True); url=models.CharField(max_length=255); icon=models.CharField(max_length=80,blank=True); sort_order=models.PositiveSmallIntegerField(default=10); is_active=models.BooleanField(default=True); open_new_window=models.BooleanField(default=False); requires_login=models.BooleanField(default=False)
    class Meta: ordering=('area','sort_order','label_en')
    def __str__(self):return self.label_en
class Service(UUIDTimeStampedModel):
    title_en=models.CharField(max_length=120); title_ar=models.CharField(max_length=120,blank=True); description_en=models.TextField(blank=True); description_ar=models.TextField(blank=True); icon=models.CharField(max_length=80,blank=True); url=models.CharField(max_length=255,blank=True); sort_order=models.PositiveSmallIntegerField(default=10); is_active=models.BooleanField(default=True)
    class Meta: ordering=('sort_order','title_en')
    def __str__(self):return self.title_en
class Statistic(UUIDTimeStampedModel):
    label_en=models.CharField(max_length=100); label_ar=models.CharField(max_length=100,blank=True); value=models.CharField(max_length=50); sort_order=models.PositiveSmallIntegerField(default=10); is_active=models.BooleanField(default=True)
    class Meta: ordering=('sort_order',)
class Testimonial(UUIDTimeStampedModel):
    client_name=models.CharField(max_length=120); client_title=models.CharField(max_length=120,blank=True); quote_en=models.TextField(); quote_ar=models.TextField(blank=True); photo=models.ImageField(upload_to='testimonials/',blank=True); is_active=models.BooleanField(default=True); sort_order=models.PositiveSmallIntegerField(default=10)
    class Meta: ordering=('sort_order','client_name')
class CarrierTrustBadge(UUIDTimeStampedModel):
    name=models.CharField(max_length=120); logo=models.ImageField(upload_to='carrier_badges/',blank=True); url=models.URLField(blank=True); is_active=models.BooleanField(default=True); sort_order=models.PositiveSmallIntegerField(default=10)
    class Meta: ordering=('sort_order','name')
