from django.core.management.base import BaseCommand
from .utils import auto_schedule_recent_exams

class Command(BaseCommand):
    help = 'Auto schedules the most recent exams daily'

    def handle(self, *args, **kwargs):
        auto_schedule_recent_exams()
        self.stdout.write(self.style.SUCCESS('✅ Exams scheduled successfully.'))
