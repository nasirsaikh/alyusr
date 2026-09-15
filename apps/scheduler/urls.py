from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("<uuid:pk>/", views.task_detail, name="detail"),
    path("<uuid:pk>/run/", views.run_task_now, name="run_now"),
]
