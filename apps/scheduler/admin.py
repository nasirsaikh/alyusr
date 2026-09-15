from django.contrib import admin
from .models import ScheduledTask,TaskRun
admin.site.register(ScheduledTask);admin.site.register(TaskRun)
