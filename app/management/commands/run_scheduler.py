from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from app.scheduler import job_auto_schedule_exams, job_notify_new_published_exams

class Command(BaseCommand):
    help = "Starts the APScheduler for auto-scheduling and email notifications"

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler(timezone=ZoneInfo("Africa/Kigali"))

        # 1. Schedule daily exam auto-scheduling at midnight
        scheduler.add_job(job_auto_schedule_exams, CronTrigger(hour=0, minute=0), id="auto_schedule_exams")

        # 2. Email notification every 30 minutes from 7:00 to 17:00
        scheduler.add_job(job_notify_new_published_exams, CronTrigger(minute='20', hour='8-16'), id="notify_emails")

        self.stdout.write(self.style.SUCCESS("✅ Scheduler started..."))
        scheduler.start()

        # Keep the scheduler alive
        import time
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
