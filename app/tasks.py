from celery import shared_task , Celery
from django.utils import timezone
from .models import ScheduledExam
from celery.schedules import crontab
from mwami.celery import celery_app

@shared_task
def publish_scheduled_exams():
    """Publishes exams that are scheduled but not yet published"""
    now = timezone.now()
    scheduled_exams = ScheduledExam.objects.filter(scheduled_datetime__lte=now, is_published=False)

    for scheduled_exam in scheduled_exams:
        scheduled_exam.publish()


celery_app.conf.beat_schedule = {
    "publish-exams-every-minute": {
        "task": "app.tasks.publish_scheduled_exams",
        "schedule": crontab(minute="*"),  # Runs every minute
    },
}
