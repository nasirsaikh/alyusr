from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import Organization
class ScheduledTask(UUIDTimeStampedModel):
    class TaskType(models.TextChoices): EMAIL='email','Email sending'; TICKET='ticket','Ticket generation'; PYTHON='python','Allowlisted Python callable'; RENEWAL='renewal','Policy renewal reminder'; SLA='sla','SLA compliance check'; REPORT='report','Report generation'; SYNC='sync','External data synchronization'
    organization=models.ForeignKey(Organization,null=True,blank=True,on_delete=models.CASCADE,related_name='scheduled_tasks'); name=models.CharField(max_length=160); task_type=models.CharField(max_length=20,choices=TaskType.choices); cron_expression=models.CharField(max_length=80); timezone=models.CharField(max_length=64,default='Asia/Muscat'); payload=models.JSONField(default=dict,blank=True); callable_path=models.CharField(max_length=255,blank=True); dependencies=models.ManyToManyField('self',symmetrical=False,blank=True,related_name='dependents'); max_retries=models.PositiveSmallIntegerField(default=3); backoff_seconds=models.PositiveIntegerField(default=60); execution_order=models.PositiveIntegerField(default=100); next_run_at=models.DateTimeField(null=True,blank=True,db_index=True); last_run_at=models.DateTimeField(null=True,blank=True); is_active=models.BooleanField(default=True); notify_emails=models.JSONField(default=list,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='created_scheduled_tasks')
    class Meta: ordering=('execution_order','name')
    def __str__(self):return self.name
class TaskRun(UUIDTimeStampedModel):
    class Status(models.TextChoices): RUNNING='running','Running'; SUCCESS='success','Success'; FAILED='failed','Failed'; SKIPPED='skipped','Skipped'; RETRY='retry','Retry scheduled'
    task=models.ForeignKey(ScheduledTask,on_delete=models.CASCADE,related_name='runs'); scheduled_for=models.DateTimeField(db_index=True); idempotency_key=models.CharField(max_length=255,unique=True); status=models.CharField(max_length=16,choices=Status.choices,default=Status.RUNNING); attempt=models.PositiveSmallIntegerField(default=1); started_at=models.DateTimeField(auto_now_add=True); finished_at=models.DateTimeField(null=True,blank=True); output=models.TextField(blank=True); error=models.TextField(blank=True); retry_at=models.DateTimeField(null=True,blank=True,db_index=True)
    class Meta: ordering=('-scheduled_for','-created_at')
