from django.core.management.base import BaseCommand
from apps.scheduler.services import run_due_tasks
class Command(BaseCommand):
    help='Run due Alyusr scheduled tasks and retries.'
    def handle(self,*args,**options):self.stdout.write(self.style.SUCCESS(f'Processed {len(run_due_tasks())} task runs.'))
