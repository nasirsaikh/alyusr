from django.contrib import admin
from .models import Carrier, CarrierQuote, QuoteDocument, QuoteParticipant, QuoteRequest


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "license_number", "contact_email", "appointment_end", "is_active")
    list_filter = ("is_active", "appointment_end")
    search_fields = ("name", "name_ar", "code", "license_number", "contact_email")
    prepopulated_fields = {"code": ("name",)}


class QuoteParticipantInline(admin.TabularInline):
    model = QuoteParticipant
    extra = 0
    autocomplete_fields = ("carrier", "assigned_to")


class CarrierQuoteInline(admin.TabularInline):
    model = CarrierQuote
    extra = 0
    autocomplete_fields = ("carrier",)
    fields = ("carrier", "quote_number", "premium", "currency", "deductible", "sum_insured", "valid_until", "score", "is_recommended", "is_winner")


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("reference", "client_name", "line_of_business", "request_type", "status", "winning_carrier", "market_due_at", "created_at")
    list_filter = ("organization", "request_type", "status", "line_of_business")
    search_fields = ("reference", "client_name", "client__client_number", "client__name", "ticket__reference")
    autocomplete_fields = ("ticket", "requester", "client", "client_product", "renewal_of_policy", "selected_quote")
    inlines = (QuoteParticipantInline, CarrierQuoteInline)


@admin.register(QuoteParticipant)
class QuoteParticipantAdmin(admin.ModelAdmin):
    list_display = ("quote_request", "carrier", "status", "invited_at", "response_due_at", "responded_at")
    list_filter = ("status", "carrier")
    search_fields = ("quote_request__reference", "quote_request__client_name", "carrier__name")
    autocomplete_fields = ("quote_request", "carrier", "assigned_to")


@admin.register(CarrierQuote)
class CarrierQuoteAdmin(admin.ModelAdmin):
    list_display = ("quote_request", "carrier", "premium", "currency", "valid_until", "score", "is_recommended", "is_winner")
    list_filter = ("currency", "is_recommended", "is_winner", "carrier")
    search_fields = ("quote_request__reference", "carrier__name", "quote_number")
    autocomplete_fields = ("quote_request", "participant", "carrier")


@admin.register(QuoteDocument)
class QuoteDocumentAdmin(admin.ModelAdmin):
    list_display = ("quote_request", "document_type", "carrier_quote", "uploaded_by", "is_client_visible", "created_at")
    list_filter = ("document_type", "is_client_visible")
    search_fields = ("quote_request__reference", "document_type")
