from celery import shared_task
from django.utils.timezone import now
from .models import ScheduledExam

@shared_task
def publish_scheduled_exams():
    """Activate exams that are scheduled for now or earlier."""
    exams = ScheduledExam.objects.filter(scheduled_datetime__lte=now())

    for scheduled_exam in exams:
        print(f"Publishing exam: {scheduled_exam.exam.title}")
        # Here you can add logic to mark the exam as published, notify users, etc.
        scheduled_exam.delete()  # Remove after publishing

    return f"{exams.count()} exams published."
