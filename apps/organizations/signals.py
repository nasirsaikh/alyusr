from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Membership,Organization,Role,UserProfile
User=get_user_model()
@receiver(post_save,sender=User)
def ensure_profile(sender,instance,created,**kwargs): UserProfile.objects.get_or_create(user=instance)
@receiver(user_logged_in)
def ensure_guest_membership(sender,request,user,**kwargs):
    if Membership.objects.filter(user=user,is_active=True).exists():return
    org=Organization.objects.filter(is_default_for_guests=True,is_active=True).first()
    if org:
        Membership.objects.get_or_create(organization=org,user=user,defaults={'role':Role.GUEST}); profile,_=UserProfile.objects.get_or_create(user=user)
        if not profile.default_organization_id: profile.default_organization=org; profile.save(update_fields=['default_organization','updated_at'])
