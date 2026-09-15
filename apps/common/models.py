import uuid
from django.conf import settings
from django.db import models

class TimeStampedModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True,db_index=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: abstract=True
class UUIDTimeStampedModel(TimeStampedModel):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    class Meta: abstract=True
class Notification(UUIDTimeStampedModel):
    class Level(models.TextChoices): INFO='info','Info'; SUCCESS='success','Success'; WARNING='warning','Warning'; DANGER='danger','Danger'
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='alyusr_notifications'); title=models.CharField(max_length=160); message=models.TextField(blank=True); level=models.CharField(max_length=12,choices=Level.choices,default=Level.INFO); url=models.CharField(max_length=500,blank=True); read_at=models.DateTimeField(null=True,blank=True); event_key=models.CharField(max_length=160,blank=True,db_index=True)
    class Meta: ordering=('-created_at',); indexes=[models.Index(fields=['user','read_at','-created_at'])]
    def __str__(self): return self.title
class AuditEvent(UUIDTimeStampedModel):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='alyusr_audit_events'); action=models.CharField(max_length=80,db_index=True); object_type=models.CharField(max_length=120,db_index=True); object_id=models.CharField(max_length=120,db_index=True); organization_id=models.CharField(max_length=120,blank=True,db_index=True); summary=models.CharField(max_length=255,blank=True); metadata=models.JSONField(default=dict,blank=True); ip_address=models.GenericIPAddressField(null=True,blank=True)
    class Meta: ordering=('-created_at',); indexes=[models.Index(fields=['object_type','object_id','-created_at'])]
    def __str__(self): return f'{self.action}: {self.object_type}#{self.object_id}'
