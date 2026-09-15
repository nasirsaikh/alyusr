from django.contrib import admin
from .models import Membership,Organization,SupportGroup,UserProfile
admin.site.register(Organization)
admin.site.register(Membership)
admin.site.register(SupportGroup)
admin.site.register(UserProfile)
