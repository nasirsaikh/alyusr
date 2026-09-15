from django.urls import path
from . import views
app_name='portal';urlpatterns=[path('',views.dashboard,name='dashboard'),path('client/',views.client_center,name='client_center'),path('notifications/feed/',views.notification_feed,name='notification_feed')]
