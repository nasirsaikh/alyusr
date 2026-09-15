from django.urls import path
from . import views
app_name='public_site'
urlpatterns=[path('',views.home,name='home'),path('assets/theme.css',views.theme_css,name='theme_css')]
