import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import Organization
from apps.tickets.models import Ticket,validate_attachment

def quote_reference():return f'QTE-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}'
class Carrier(UUIDTimeStampedModel):
    name=models.CharField(max_length=160); code=models.SlugField(max_length=60,unique=True); logo=models.ImageField(upload_to='carriers/',blank=True); license_number=models.CharField(max_length=120,blank=True); regions_covered=models.JSONField(default=list,blank=True); lines_of_business=models.JSONField(default=list,blank=True); appointment_start=models.DateField(null=True,blank=True); appointment_end=models.DateField(null=True,blank=True); contact_email=models.EmailField(blank=True); contact_phone=models.CharField(max_length=40,blank=True); is_active=models.BooleanField(default=True)
    class Meta: ordering=('name',)
    def __str__(self):return self.name
class QuoteRequest(UUIDTimeStampedModel):
    class Status(models.TextChoices): DRAFT='draft','Draft'; SUBMITTED='submitted','Submitted'; UNDER_REVIEW='under_review','Under Review'; APPROVED='approved','Approved'; BOUND='bound','Bound'; ISSUED='issued','Issued'; EXPIRED='expired','Expired'; CANCELLED='cancelled','Cancelled'
    reference=models.CharField(max_length=40,unique=True,default=quote_reference,editable=False); organization=models.ForeignKey(Organization,on_delete=models.PROTECT,related_name='quote_requests'); requester=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='quote_requests'); client_name=models.CharField(max_length=180); client_email=models.EmailField(blank=True); client_phone=models.CharField(max_length=40,blank=True); line_of_business=models.CharField(max_length=80); status=models.CharField(max_length=20,choices=Status.choices,default=Status.DRAFT,db_index=True); form_version=models.ForeignKey('forms_engine.FormVersion',null=True,blank=True,on_delete=models.PROTECT,related_name='quote_requests'); dynamic_data=models.JSONField(default=dict,blank=True); expires_at=models.DateTimeField(null=True,blank=True,db_index=True); selected_quote=models.ForeignKey('CarrierQuote',null=True,blank=True,on_delete=models.SET_NULL,related_name='selected_for_requests'); converted_ticket=models.OneToOneField(Ticket,null=True,blank=True,on_delete=models.SET_NULL,related_name='source_quote')
    class Meta: ordering=('-created_at',)
    def __str__(self):return f'{self.reference} · {self.client_name}'
class CarrierQuote(UUIDTimeStampedModel):
    quote_request=models.ForeignKey(QuoteRequest,on_delete=models.CASCADE,related_name='carrier_quotes'); carrier=models.ForeignKey(Carrier,on_delete=models.PROTECT,related_name='quotes'); quote_number=models.CharField(max_length=120,blank=True); premium=models.DecimalField(max_digits=14,decimal_places=3); deductible=models.DecimalField(max_digits=14,decimal_places=3,null=True,blank=True); sum_insured=models.DecimalField(max_digits=16,decimal_places=3,null=True,blank=True); currency=models.CharField(max_length=3,default='OMR'); coverage_summary=models.TextField(blank=True); exclusions=models.TextField(blank=True); valid_until=models.DateField(null=True,blank=True); is_recommended=models.BooleanField(default=False); metadata=models.JSONField(default=dict,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['quote_request','carrier'],name='uniq_request_carrier_quote')]; ordering=('premium',)
class QuoteDocument(UUIDTimeStampedModel):
    quote_request=models.ForeignKey(QuoteRequest,on_delete=models.CASCADE,related_name='documents'); carrier_quote=models.ForeignKey(CarrierQuote,null=True,blank=True,on_delete=models.CASCADE,related_name='documents'); uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='quote_documents'); document_type=models.CharField(max_length=80,blank=True); file=models.FileField(upload_to='quotations/%Y/%m/',validators=[validate_attachment]); is_client_visible=models.BooleanField(default=True)
