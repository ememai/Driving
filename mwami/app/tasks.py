from celery import shared_task
from django.utils.timezone import now
from .models import ScheduledExam

#periodic task
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

@shared_task
def publish_scheduled_exams():
    """Publish exams that have reached their upload time."""
    exams = ScheduledExam.objects.filter(is_published=False, upload_time__lte=now())
    for exam in exams:
        exam.publish()
    return f"Published {exams.count()} exams"

# Create schedule if it doesn't exist
schedule, created = IntervalSchedule.objects.get_or_create(
    every=1,
    period=IntervalSchedule.MINUTES,  # Runs every minute
)

# Create task
PeriodicTask.objects.create(
    interval=schedule,
    name="Publish Scheduled Exams",
    task="exams.tasks.publish_scheduled_exams",
    args=json.dumps([]),
)