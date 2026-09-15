from django.contrib import admin
from .models import Carrier,CarrierQuote,QuoteDocument,QuoteRequest
admin.site.register(Carrier);admin.site.register(CarrierQuote);admin.site.register(QuoteDocument);admin.site.register(QuoteRequest)
