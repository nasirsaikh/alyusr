from django.urls import path
from . import views

app_name = "quotations"

urlpatterns = [
    path("", views.quote_list, name="list"),
    path("<uuid:pk>/", views.quote_detail, name="detail"),
    path("<uuid:pk>/award/<uuid:carrier_quote_pk>/", views.award_quote, name="award"),
]
