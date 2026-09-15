from django.contrib import admin
from .models import BillingTransaction, Claim, Client, ClientDocument, ClientProduct, InsuranceProduct, Policy


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("client_number", "name", "client_type", "organization", "account_manager", "is_active")
    list_filter = ("organization", "client_type", "is_active")
    search_fields = ("client_number", "name", "name_ar", "email", "phone")


@admin.register(InsuranceProduct)
class InsuranceProductAdmin(admin.ModelAdmin):
    list_display = ("name_en", "code", "category", "organization", "default_renewal_lead_days", "is_active")
    list_filter = ("organization", "category", "is_active")
    prepopulated_fields = {"code": ("name_en",)}


@admin.register(ClientProduct)
class ClientProductAdmin(admin.ModelAdmin):
    list_display = ("client", "product", "reference_name", "next_renewal_date", "renewal_lead_days", "assigned_to", "is_active")
    list_filter = ("product", "is_active", "next_renewal_date")
    search_fields = ("client__name", "client__client_number", "reference_name", "external_reference")
    autocomplete_fields = ("client", "product", "assigned_to", "current_policy")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("policy_number", "client", "product", "carrier", "start_date", "end_date", "premium", "status")
    list_filter = ("status", "product", "carrier", "end_date")
    search_fields = ("policy_number", "client__name", "client__client_number")
    autocomplete_fields = ("client", "client_product", "product", "carrier", "source_quote_request")


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("claim_number", "policy", "loss_date", "status", "settlement_amount")
    list_filter = ("status", "loss_date")
    search_fields = ("claim_number", "policy__policy_number", "policy__client__name")


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "category", "expires_on", "client_visible")
    list_filter = ("category", "client_visible", "expires_on")
    search_fields = ("title", "client__name")


@admin.register(BillingTransaction)
class BillingTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "policy", "tx_type", "transaction_date", "amount", "currency")
    list_filter = ("tx_type", "transaction_date", "currency")
    search_fields = ("reference", "policy__policy_number", "policy__client__name")
