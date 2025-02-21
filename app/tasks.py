from apscheduler.schedulers.background import BackgroundScheduler
from django.utils.timezone import now
from .models import ScheduledExam

def publish_scheduled_exams():
    """Activates exams that are scheduled for the current time."""
    current_time = now()
    exams_to_publish = ScheduledExam.objects.filter(scheduled_datetime__lte=current_time, is_published=False)

    for scheduled_exam in exams_to_publish:
        scheduled_exam.publish()

def start_scheduler():
    """Starts the APScheduler to check exams every minute."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(publish_scheduled_exams, 'interval', minutes=1)  # Runs every minute
    scheduler.start()
