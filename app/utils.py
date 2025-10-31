from .models import *
from datetime import datetime, timedelta, time, date
from django.utils.timezone import now, localtime
import random
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import re
from django.db import connections

# Configure logger for this module
logger = logging.getLogger(__name__)


session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
session.mount('https://', HTTPAdapter(max_retries=retries))


def validate_whats_api_credentials():
    """Validate whats_api credentials before use"""
    try:
        response = session.get(
            f"{settings.WHATSAPP_API_URL}/waInstance{settings.INSTANCE_ID}/getStateInstance/{settings.API_TOKEN}",
            timeout=15
        )
        if response.status_code == 200:
            return True
        logger.error(f"whats_api credentials validation failed: {response.text}")
        return False
    except Exception as e:
        logger.error(f"whats_api connection test failed: {str(e)}")
        return False


def get_unverified_subscription(user):
    if not user.is_authenticated:
        return None
    return Subscription.objects.filter(
        user=user,
        otp_code__isnull=False,
        otp_verified=False
    ).first()


def clean_phone_number(number):
    """Clean and validate Rwandan phone number to E.164 format"""
    number = re.sub(r'\D', '', number)  # Remove non-digit characters

    if number.startswith('0') and len(number) == 10:
        # Local format like 0781234567
        return '+250' + number[1:]
    elif number.startswith('250') and len(number) == 12:
        # National format like 250781234567
        return '+' + number
    elif number.startswith('250') and len(number) < 12:
        # Possibly missing digits 
        raise ValueError("Incomplete phone number.")
    elif number.startswith('+250') and len(number) == 13:
        # Already in E.164 format
        return number
    else:
        raise ValueError("Invalid phone number format.")

   
def notify_admin(message):
    """Send admin notifications via whats_api with improved error handling"""
    admin_number = re.sub(r'\D', '', settings.ADMIN_PHONE_NUMBER ) 
     
    if not validate_whats_api_credentials():
        logger.error("Cannot send admin notification - whats_api credentials invalid")
        return

    try:
        response = session.post(
            f"{settings.WHATSAPP_API_URL}/waInstance{settings.INSTANCE_ID}/sendMessage/{settings.API_TOKEN}",
            json={
                "chatId": f"{admin_number}@c.us",
                "message": message
            },
            timeout=30  # Increased timeout
        )
        
        if response.status_code == 200:
            logger.info("✅ Admin notification sent")
        else:
            logger.error(f"❌ whats_api admin error (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        logger.error(f"🚨 Admin notification failed: {str(e)}", exc_info=True)


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
        price = 1000
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

# def auto_create_exams(number):
#     exams_created = 0
#     for i in range(0, number):
#         try:
#             exam_type, _ = ExamType.objects.get_or_create(name='Ibivanze')
#             questions = Question.objects.order_by('?')[:20]

#             if questions.count() < 20:
#                 print("‼️Not enough questions to create the exam.")
#                 # return redirect('create_exam')
            
#             # Determine next available hour for exam scheduling
#             last_exam = Exam.objects.filter(for_scheduling=True).order_by('-created_at').first()

#             if last_exam and last_exam.schedule_hour:
#                 try:
#                     last_hour = last_exam.schedule_hour.hour
#                     next_hour = last_hour + 1
#                     if next_hour > 17:
#                         next_hour = 7
#                 except (ValueError, AttributeError):
#                     next_hour = 7

#             else:
#                 next_hour = 7

#             from datetime import time
#             exam_schedule_hour = time(next_hour, 0)

                
#             exam = Exam.objects.create(
#                 exam_type=exam_type,
#                 schedule_hour=exam_schedule_hour,
#                 duration=20,
#                 for_scheduling=True,
#                 is_active=False,
#             )
#             exam.questions.set(questions)
#             exam.save()
#             questions_list = list(questions.values_list('id', flat=True))
#             exams_created += 1

#             print(f"🏁 Exam '{exam.schedule_hour}' created successfully!")
            
#         except Exception as e:
#             print(f"Error: {str(e)}")
#     print(f"✅{exams_created} Exams Created successfully!")
#     return exams_created

def auto_create_exams(number, for_scheduling=True, ):
    exams_created = 0
    created_exam_ids = []
    
    
    if timezone.localtime(timezone.now()).weekday() == 6:  # Sunday is represented by 6
        print("❌ No exams created on Sundays.")
        return exams_created, created_exam_ids
    for i in range(number):
        try:
            exam_type, _ = ExamType.objects.get_or_create(name='Ibivanze')
            questions = Question.objects.order_by('?')[:20]
            if questions.count() < 20:
                continue

            last_exam = Exam.objects.filter(for_scheduling=True).order_by('-created_at').first()
            next_hour = (last_exam.schedule_hour.hour + 1 if last_exam and last_exam.schedule_hour else 8) % 24
            next_hour = next_hour if next_hour >= 8 and next_hour <= 15 else 8

            exam_schedule_hour = time(next_hour, 0)

            exam = Exam.objects.create(
                exam_type=exam_type,
                schedule_hour=exam_schedule_hour,
                duration=20,
                for_scheduling=for_scheduling,
                is_active=False,
            )
            exam.questions.set(questions)
            created_exam_ids.append(exam.id)
            exams_created += 1

        except Exception as e:
            print(f"Error: {e}")
    notify_admin(f"✅done creating {exams_created} exams")

    return exams_created, created_exam_ids

def auto_schedule_recent_exams():
    scheduled_exams_count = 0
    recent_exams = Exam.objects.filter(for_scheduling=True).order_by('-created_at')[:8]
    today = timezone.localtime(timezone.now()).date()
    message = ''
    
    if today.weekday() == 6:  # Sunday is represented by 6
        message = "❌ No exams to schedule on Sundays."
        print(message)
        return scheduled_exams_count, message

    for exam in recent_exams:
        scheduled_time = timezone.make_aware(
            datetime.combine(today, time(hour=exam.schedule_hour.hour, minute=20))
        )

        ScheduledExam.objects.update_or_create(
            exam=exam,
            defaults={'scheduled_datetime': scheduled_time}
        )
        scheduled_exams_count += 1
        message += f"🏁 Exam '{exam.schedule_hour}' scheduled successfully!\n"
        
    return scheduled_exams_count, message

import re

def validate_phone_number(phone_number):
    """
    Validate a phone number to ensure it is in the correct format.
    
    Args:
        phone_number (str): The phone number to validate.
        
    Returns:
        bool: True if the phone number is valid, False otherwise.
    """
    # Remove any non-digit characters
    cleaned_number = re.sub(r'\D', '', phone_number)
    
    # if cleaned_number.startswith('+250') or cleaned_number.startswith('07'):   
    return len(cleaned_number) == 10 and cleaned_number.startswith('07') or len(cleaned_number) == 12 and cleaned_number.startswith('+250')
    
    # else:
    #     # For other countries, allow only valid E.164 format: starts with '+' and 10-15 digits
    #     return bool(re.fullmatch(r'\+[1-9]\d{9,14}', phone_number))