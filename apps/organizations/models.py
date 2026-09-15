from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.common.models import UUIDTimeStampedModel

class Organization(UUIDTimeStampedModel):
    name=models.CharField(max_length=180); name_ar=models.CharField(max_length=180,blank=True); code=models.SlugField(max_length=60,unique=True); registration_number=models.CharField(max_length=120,blank=True); email=models.EmailField(blank=True); phone=models.CharField(max_length=40,blank=True); is_active=models.BooleanField(default=True); is_default_for_guests=models.BooleanField(default=False)
    class Meta: ordering=('name',)
    def clean(self):
        if self.is_default_for_guests and Organization.objects.exclude(pk=self.pk).filter(is_default_for_guests=True).exists(): raise ValidationError({'is_default_for_guests':'Only one organization can be the default guest organization.'})
    def __str__(self):return self.name
class Role(models.TextChoices):
    SUPER_ADMIN='super_admin','Super Admin'; ADMIN='admin','Admin'; PROJECT_MANAGER='project_manager','Project Manager'; SUPPORT_AGENT='support_agent','Support Agent'; REQUESTER='requester','Requester / User'; VIEWER='viewer','Viewer / Auditor'; GUEST='guest','Guest'
class Membership(UUIDTimeStampedModel):
    organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name='memberships'); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='organization_memberships'); role=models.CharField(max_length=24,choices=Role.choices,default=Role.GUEST); is_active=models.BooleanField(default=True); title=models.CharField(max_length=120,blank=True); department=models.CharField(max_length=120,blank=True); reporting_manager=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='reporting_members')
    class Meta: constraints=[models.UniqueConstraint(fields=['organization','user'],name='uniq_org_user_membership')]
    def __str__(self):return f'{self.user} · {self.organization} · {self.get_role_display()}'
class SupportGroup(UUIDTimeStampedModel):
    organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name='support_groups'); name=models.CharField(max_length=120); code=models.SlugField(max_length=80); members=models.ManyToManyField(settings.AUTH_USER_MODEL,blank=True,related_name='alyusr_support_groups'); manager=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='managed_support_groups'); is_active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['organization','code'],name='uniq_org_support_group_code')]
    def __str__(self):return f'{self.organization.code} / {self.name}'
class UserProfile(UUIDTimeStampedModel):
    class Theme(models.TextChoices): SYSTEM='system','System'; LIGHT='light','Light'; DARK='dark','Dark'
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='alyusr_profile'); default_organization=models.ForeignKey(Organization,null=True,blank=True,on_delete=models.SET_NULL,related_name='default_profiles'); avatar=models.ImageField(upload_to='profiles/%Y/%m/',blank=True); preferred_language=models.CharField(max_length=5,choices=(('en','English'),('ar','العربية')),default='en'); theme=models.CharField(max_length=10,choices=Theme.choices,default=Theme.SYSTEM); notify_email=models.BooleanField(default=True); notify_browser=models.BooleanField(default=True); notify_assignments=models.BooleanField(default=True); notify_sla=models.BooleanField(default=True)
    def __str__(self):return f'Profile: {self.user}'
