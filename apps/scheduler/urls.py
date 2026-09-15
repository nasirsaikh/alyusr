from django.urls import path
from . import views
app_name='scheduler';urlpatterns=[path('',views.task_list,name='list')]
