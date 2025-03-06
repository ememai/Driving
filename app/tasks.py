from celery import shared_task
from django.utils.timezone import now
from app.models import ScheduledExam

@shared_task
def publish_scheduled_exams():
    """Activates exams that are scheduled for the current time."""
    current_time = now()
    exams_to_publish = ScheduledExam.objects.filter(scheduled_datetime__lte=current_time, is_published=False)

    for exam in exams_to_publish:
        exam.publish()
        print(f"Published exam: {exam.name} at {current_time}")  # Debugging
