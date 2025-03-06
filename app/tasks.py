from celery import shared_task
from django.utils.timezone import now
from app.models import ScheduledExam

@shared_task
def publish_scheduled_exams():
    """Activates exams that are scheduled for the current time."""
    current_time = now()
    exams_to_publish = ScheduledExam.objects.filter(scheduled_datetime__lte=current_time, is_published=False)

    for exam in exams_to_publish:
        try:
            exam.publish()
            logger.info(f"Published exam: {exam.name} at {current_time}")
        except Exception as e:
            logger.error(f"Error publishing exam {exam.name}: {e}")