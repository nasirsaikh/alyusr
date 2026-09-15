from django.contrib import admin
from .models import BillingTransaction,Claim,Client,ClientDocument,Policy
admin.site.register(Client);admin.site.register(Policy);admin.site.register(Claim);admin.site.register(ClientDocument);admin.site.register(BillingTransaction)
