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

# GreenAPI Configuration
GREEN_API_URL = "https://7105.api.greenapi.com"
INSTANCE_ID = "7105229020"
API_TOKEN = "c554e7fe36214785890aded373a3c08625e3460ecce249d283"

def notify_admin(message):
    """Send admin notifications via GreenAPI"""
    admin_number = "250785287885"  # Your admin number in E.164 format without +
    try:
        response = requests.post(
            f"{GREEN_API_URL}/waInstance{INSTANCE_ID}/sendMessage/{API_TOKEN}",
            json={
                "chatId": f"{admin_number}@c.us",
                "message": message
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Admin notification sent")
        else:
            print(f"❌ GreenAPI admin error: {response.text}")
    except Exception as e:
        print(f"🚨 Admin notification failed: {str(e)}")

def job_auto_schedule_exams():
    connections.close_all()
    print("🕛 Running daily auto-schedule...")
    try:
        auto_create_exams()
        notify_admin(f"✅  Exams Created successfully!")
        auto_schedule_recent_exams()
        notify_admin(f"✅ Recent exams scheduled.")
    except Exception as e:
        notify_admin(f"❌ Error in auto-scheduling: {str(e)}")
        print(f"❌ Error: {str(e)}")

def job_notify_new_published_exams():
    close_old_connections()
    print("📬 Checking for newly published exams...")

    now = timezone.now()
    one_hour_ago = now - timezone.timedelta(minutes=60)

    newly_published = ScheduledExam.objects.filter(
        scheduled_datetime__gte=one_hour_ago,
        scheduled_datetime__lte=now
    )

    for scheduled in newly_published:
        exam = scheduled.exam
        exam_url = f"{settings.BASE_URL}{reverse('exam_detail', args=[exam.id])}"
        scheduled_time = scheduled.scheduled_datetime.astimezone(ZoneInfo('Africa/Kigali')).strftime('%H:%M')
        today_date = now.strftime('%d-%m-') + str(now.year)[-3:]

        users = UserProfile.objects.filter( Q(whatsapp_consent=True) | 
            Q(email__isnull=False))
        
        message = textwrap.dedent(f'''\
            📅 Kuwa {today_date}

            ⏰ Ikizamini cya Saa {scheduled_time} cyagezeho.
            📝 Gikore uciye aha: {exam_url}

            📞 Ukeneye ubufasha: 0785287885
            ''')
        notify_admin(message)

        for user in users:
            # # 1. WhatsApp via GreenAPI
            # if user.whatsapp_number:
            #     try:
            #         # Clean and validate number
            #         whatsapp_num = ''.join(filter(str.isdigit, user.whatsapp_number))
                    
            #         # Convert to international format
            #         if whatsapp_num.startswith('0'):
            #             whatsapp_num = '250' + whatsapp_num[1:]
            #         elif not whatsapp_num.startswith('250'):
            #             whatsapp_num = '250' + whatsapp_num
                    
            #         # Validate length
            #         if len(whatsapp_num) != 12:
            #             raise ValueError(f"Invalid Rwanda number length: {whatsapp_num}")

            #         response = requests.post(
            #             f"{GREEN_API_URL}/waInstance{INSTANCE_ID}/sendMessage/{API_TOKEN}",
            #             json={
            #                 "chatId": f"{whatsapp_num}@c.us",
            #                 "message": message
            #             },
            #             timeout=10
            #         )
                    
            #         if response.status_code == 200:
            #             print(f"✅ WhatsApp sent to {whatsapp_num}")
            #         else:
            #             print(f"❌ GreenAPI error: {response.text}")

            #     except Exception as e:
            #         print(f"🚨 WhatsApp failed for {user.whatsapp_number}: {str(e)}")

            # # 2. Email fallback
            if user.email:
                try:
                    send_mail(
                        subject=f"📢 {scheduled_time} Exam Published",
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    print(f"📧 Email sent to {user.email}")
                except Exception as e:
                    print(f"❌ Email failed: {e}")

def start():
    scheduler = BackgroundScheduler(timezone=ZoneInfo("Africa/Kigali"))    
    # 1. Run exam scheduling every day at 00:00
    scheduler.add_job(job_auto_schedule_exams, CronTrigger(hour=16, minute=2, second=00), id="auto_schedule_exams")

    # 2. Run email notifications every hour between 07:00 and 17:00
    scheduler.add_job(job_notify_new_published_exams, CronTrigger(minute='2', second='00', hour='7-17'),id="notify_emails")
    
    scheduler.start()
