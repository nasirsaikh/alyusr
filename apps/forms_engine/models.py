from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.common.models import UUIDTimeStampedModel
class DataSource(UUIDTimeStampedModel):
    class Kind(models.TextChoices): STATIC='static','Static values'; MODEL='model','Allowlisted Django model'
    name=models.CharField(max_length=120,unique=True); code=models.SlugField(max_length=80,unique=True); kind=models.CharField(max_length=20,choices=Kind.choices,default=Kind.STATIC); config=models.JSONField(default=dict,blank=True); is_active=models.BooleanField(default=True)
    def clean(self):
        lowered={str(k).lower() for k in (self.config or {}).keys()}
        if lowered.intersection({'sql','query','raw_sql','statement'}): raise ValidationError({'config':'SQL execution is not permitted in datasource configuration.'})
        if self.kind==self.Kind.MODEL and (self.config or {}).get('model','') not in settings.ALYUSR_ALLOWED_DATASOURCE_MODELS: raise ValidationError({'config':'Datasource model is not allowlisted.'})
    def __str__(self):return self.name
class FormDefinition(UUIDTimeStampedModel):
    class Module(models.TextChoices): TICKET='ticket','Ticket'; QUOTATION='quotation','Quotation'; LEAD='lead','Lead'; CLIENT='client','Client'; CLAIM='claim','Claim'
    name=models.CharField(max_length=160); code=models.SlugField(max_length=80,unique=True); module=models.CharField(max_length=24,choices=Module.choices); description=models.TextField(blank=True); is_active=models.BooleanField(default=True)
    @property
    def active_version(self):return self.versions.filter(is_published=True).order_by('-version').first()
    def __str__(self):return self.name
class FormVersion(UUIDTimeStampedModel):
    definition=models.ForeignKey(FormDefinition,on_delete=models.CASCADE,related_name='versions'); version=models.PositiveIntegerField(); schema=models.JSONField(default=dict); migration_map=models.JSONField(default=dict,blank=True); is_published=models.BooleanField(default=False); published_at=models.DateTimeField(null=True,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='created_form_versions')
    class Meta: constraints=[models.UniqueConstraint(fields=['definition','version'],name='uniq_form_definition_version')]
    def clean(self):
        from .services import validate_schema_definition
        validate_schema_definition(self.definition.module if self.definition_id else None,self.schema)
    def __str__(self):return f'{self.definition} v{self.version}'
class FormSubmission(UUIDTimeStampedModel):
    form_version=models.ForeignKey(FormVersion,on_delete=models.PROTECT,related_name='submissions'); submitted_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='form_submissions'); organization_id=models.CharField(max_length=120,blank=True,db_index=True); data=models.JSONField(default=dict); is_valid=models.BooleanField(default=True); validation_errors=models.JSONField(default=dict,blank=True)
