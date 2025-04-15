from .models import *
from datetime import datetime, timedelta, time, date
from django.utils.timezone import now, localtime
import random
from django.utils import timezone

def phone_or_email():
  username = ''
  user = request.user.objects.get(email=username) if '@' in username else request.user.objects.get(phone_number=username)

  if username == email:
    user.send_otp_email()  # Send OTP
    messages.success(request, 'OTP sent to your email. Verify your account.')
    return redirect('verify_otp', user_id=user.id)
  else:
    return redirect("home")

def set_price_and_duration(plan):
    price = 0
    duration = 0
    if plan == 'Daily':
        price = 500
        duration = 1
    elif plan == 'Weekly':
        price = 2000
        duration = 7
    elif plan == 'Monthly':
        price = 5000
        duration = 30
    else:
        price = 10000
        duration = None
    return price, duration

# app/utils.py


def check_exam_availability(hour):
    """
    Determine whether an exam is available at a given hour.

    This function checks for any ScheduledExam objects scheduled on the current day
    whose scheduled_datetime falls within the provided hour (24-hour format). If at
    least one such exam exists, the function returns True.

    Args:
        hour (int): The hour (in 24-hour format) to check for an available exam.

    Returns:
        bool: True if at least one exam is scheduled for that hour today, otherwise False.
    """
    # Get the current date.
    today = timezone.now().date()
    
    # Query for scheduled exams on today's date where the scheduled hour matches.
    exam_exists = ScheduledExam.objects.filter(
        scheduled_datetime__date=today,
        scheduled_datetime__hour=hour
    ).exists()

    return exam_exists

def auto_schedule_recent_exams():
    recent_exams = Exam.objects.filter(for_scheduling=True).order_by('-created_at')[:11]
    today = timezone.localtime(timezone.now()).date()

    for exam in recent_exams:
        scheduled_time = timezone.make_aware(
            datetime.combine(today, time(hour=exam.schedule_hour.hour, minute=0))
        )

        ScheduledExam.objects.update_or_create(
            exam=exam,
            defaults={'scheduled_datetime': scheduled_time}
        )