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
from .utils import notify_admin
import logging
from django.utils.timezone import localtime, now, make_aware, datetime


# Configure logging
logger = logging.getLogger(__name__)


def job_auto_schedule_exams():
    connections.close_all()
    print("🕛 Running daily auto-schedule...")
    try:
        exams_created, _ = auto_create_exams(8)      
        notify_admin(f"{localtime().strftime('%d-%m-%Y %H:%M')} ✅ {exams_created} Exams Created successfully!")
        scheduled_exams_count, message = auto_schedule_recent_exams()
        
        notify_admin(f"✅ {localtime().strftime('%d-%m-%Y %H:%M')} {scheduled_exams_count} {message}")
    
    except Exception as e:
        notify_admin(f"❌ Error in auto-scheduling: {str(e)}")
        print(f"❌ Error: {str(e)}")


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
            f"{settings.WHATSAPP_API_URL}/waInstance{settings.INSTANCE_ID}/sendMessage/{settings.API_TOKEN}",
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
            logger.error(f"❌ whats_api error (HTTP {response.status_code}): {response.text}")
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
        scheduled_time = scheduled.scheduled_datetime.astimezone(ZoneInfo('Africa/Kigali')).strftime('%H:00')
        # today_date = now.strftime('%d-%m-') + str(now.year)[-3:]
        today_date = now.strftime('%d-%m-%Y')

        users = UserProfile.objects.filter(Q(is_superuser=True) |
            Q(email__isnull=False), whatsapp_consent=True) # Notify admins and users with email   
        message = textwrap.dedent(f'''\

            ⏰ Ikizamini cya Saa {scheduled_time} cyageze ku rubuga.
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
            CronTrigger(hour=0, minute=0, second=0),
            id="auto_schedule_exams"
        )

        
        scheduler.add_job(
            job_notify_new_published_exams,
            CronTrigger(minute='20', hour='8-15', second=00),
            id="notify_emails"
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
        raise
    