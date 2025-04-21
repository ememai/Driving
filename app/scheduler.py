from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from .models import *
from .utils import *
from zoneinfo import ZoneInfo
from django.db.utils import OperationalError
import textwrap
from django.db import close_old_connections, connections
import requests
from django.db.models import Q
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import logging
from django.utils.timezone import localtime, now, make_aware, datetime


# Configure logging
logger = logging.getLogger(__name__)

# GreenAPI Configuration
GREEN_API_URL = "https://7105.api.greenapi.com"
INSTANCE_ID = "7105229020"
API_TOKEN = "c554e7fe36214785890aded373a3c08625e3460ecce249d283"

# Configure requests session with retries
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
session.mount('https://', HTTPAdapter(max_retries=retries))

def notify_admin(message):
    """Send admin notifications via GreenAPI with improved error handling"""
    admin_number = "250785287885"  # E.164 format
    
    if not validate_greenapi_credentials():
        logger.error("Cannot send admin notification - GreenAPI credentials invalid")
        return

    try:
        response = session.post(
            f"{GREEN_API_URL}/waInstance{INSTANCE_ID}/sendMessage/{API_TOKEN}",
            json={
                "chatId": f"{admin_number}@c.us",
                "message": message
            },
            timeout=30  # Increased timeout
        )
        
        if response.status_code == 200:
            logger.info("✅ Admin notification sent")
        else:
            logger.error(f"❌ GreenAPI admin error (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        logger.error(f"🚨 Admin notification failed: {str(e)}", exc_info=True)


def job_auto_schedule_exams():
    connections.close_all()
    print("🕛 Running daily auto-schedule...")
    try:        
        # auto_create_exams(11)  
        exams_created, _ = auto_create_exams(11)      
        notify_admin(f"{timezone.now().strftime('%d-%m-%Y %H:%M')} ✅ {exams_created}Exams Created successfully!")
        auto_schedule_recent_exams()
        
        notify_admin(f"✅ {timezone.now().strftime('%d-%m-%Y %H:%M')} Recent exams scheduled.")
    
    except Exception as e:
        notify_admin(f"❌ Error in auto-scheduling: {str(e)}")
        print(f"❌ Error: {str(e)}")


def validate_greenapi_credentials():
    """Validate GreenAPI credentials before use"""
    try:
        response = session.get(
            f"{GREEN_API_URL}/waInstance{INSTANCE_ID}/getStateInstance/{API_TOKEN}",
            timeout=15
        )
        if response.status_code == 200:
            return True
        logger.error(f"GreenAPI credentials validation failed: {response.text}")
        return False
    except Exception as e:
        logger.error(f"GreenAPI connection test failed: {str(e)}")
        return False

def process_whatsapp_number(number):
    """Clean and validate WhatsApp number"""
    cleaned = ''.join(filter(str.isdigit, number))
    
    if not cleaned:
        raise ValueError("Empty phone number")
        
    # Convert to international format
    if cleaned.startswith('0'):
        cleaned = '250' + cleaned[1:]
    elif not cleaned.startswith('250'):
        cleaned = '250' + cleaned
    
    if len(cleaned) != 12:
        raise ValueError(f"Invalid Rwanda number length: {cleaned}")
    
    return cleaned

def send_whatsapp_message(phone_number, message):
    """Send WhatsApp message with robust error handling"""
    try:
        whatsapp_num = process_whatsapp_number(phone_number)
        
        response = session.post(
            f"{GREEN_API_URL}/waInstance{INSTANCE_ID}/sendMessage/{API_TOKEN}",
            json={
                "chatId": f"{whatsapp_num}@c.us",
                "message": message
            },
            timeout=30  # Increased timeout
        )
        
        if response.status_code == 200:
            logger.info(f"✅ WhatsApp sent to {whatsapp_num}")
            return True
        else:
            logger.error(f"❌ GreenAPI error (HTTP {response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"🚨 WhatsApp failed for {phone_number}: {str(e)}", exc_info=True)
        return False

def job_notify_new_published_exams():
    close_old_connections()
    logger.info("📬 Checking for newly published exams...")

    now = timezone.now()
    one_hour_ago = now - timezone.timedelta(minutes=60)

    newly_published = ScheduledExam.objects.filter(
        scheduled_datetime__gte=one_hour_ago,
        scheduled_datetime__lte=now
    ).select_related('exam')

    if not newly_published.exists():
        logger.info("No newly published exams found")
        return

    for scheduled in newly_published:
        exam = scheduled.exam
        exam_url = f"{settings.BASE_URL}{reverse('exam_detail', args=[exam.id])}"
        scheduled_time = scheduled.scheduled_datetime.astimezone(ZoneInfo('Africa/Kigali')).strftime('%H:%M')
        today_date = now.strftime('%d-%m-') + str(now.year)[-3:]

        users = UserProfile.objects.filter(is_superuser=True)
        
        message = textwrap.dedent(f'''\

            ⏰ Ikizamini cya Saa {scheduled_time} cyagezeho.
            📝 Gikore uciye aha: {exam_url}

            📞 Ukeneye ubufasha: 0785287885
            📅 {today_date}
            ''')

        for user in users:
            # WhatsApp notification
            if user.whatsapp_number:
                send_whatsapp_message(user.whatsapp_number, message)

            # Email fallback
            if user.email:
                try:
                    send_mail(
                        subject=f"📢 {scheduled_time} Exam Published",
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    logger.info(f"📧 Email sent to {user.email}")
                except Exception as e:
                    logger.error(f"❌ Email failed for {user.email}: {str(e)}", exc_info=True)

def start():
    try:
        scheduler = BackgroundScheduler(timezone=ZoneInfo("Africa/Kigali"))    
        
        # 1. Run exam scheduling every day at 00:00
        scheduler.add_job(
            job_auto_schedule_exams,
            CronTrigger(hour=0, minute=0, second=50), 
            id="auto_schedule_exams"
        )

        # 2. Run email notifications every hour between 07:00 and 17:00
        scheduler.add_job(
            job_notify_new_published_exams,
            CronTrigger(minute='00', hour='7-17'),
            id="notify_emails"
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
        raise