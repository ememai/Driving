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

def notify_admin(message):
    whatsapp_num = '0785287885'
    try:                    # Clean and format number (ensure starts with +)
        whatsapp_num = ''.join(filter(str.isdigit, user.whatsapp_number))
        if whatsapp_num.startswith('0'):
            whatsapp_num = '+250' + whatsapp_num[1:]  # Convert 078... to +25078...
        elif not whatsapp_num.startswith('250'):
            whatsapp_num = '+250' + whatsapp_num  # Add Rwanda code if missing
        else:
            whatsapp_num = '+' + whatsapp_num  # Add + prefix

        # URL-encode the message
        encoded_message = requests.utils.quote(message)
        
        # Build CallMeBot URL
        url = f"{CALLMEBOT_BASE_URL}?phone={whatsapp_num}&text={encoded_message}&apikey={CALLMEBOT_API_KEY}"
        
        # Send request
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ WhatsApp sent to {whatsapp_num}")
        else:
            print(f"❌ CallMeBot error: {response.text}")

    except Exception as e:
        print(f"🚨 WhatsApp failed for {user.whatsapp_number}: {str(e)}")


def job_auto_schedule_exams():
    connections.close_all()
    print("🕛 Running daily auto-schedule...")
    try:
        auto_create_exams()
        notify_admin(f"✅{exams_created} Exams Created successfully!")
        auto_schedule_recent_exams()
        notify_admin(f"✅{exams_created} Recent exams scheduled.")
    except Exception as e:
        notify_admin(e)
    print("✅ Recent exams scheduled.")


# def job_notify_new_published_exams():
#     close_old_connections()  # Close old connections to avoid issues
#     print("📬 Checking for newly published exams...")

#     now = timezone.now()
#     one_hour_ago = now - timezone.timedelta(minutes=60)

#     newly_published = ScheduledExam.objects.filter(
#         scheduled_datetime__gte=one_hour_ago,
#         scheduled_datetime__lte=now
#     )

#     for scheduled in newly_published:
#         exam = scheduled.exam
#         exam_url = f"{settings.BASE_URL}{reverse('exam_detail', args=[exam.id])}"
#         scheduled_time = scheduled.scheduled_datetime.astimezone(ZoneInfo('Africa/Kigali')).strftime('%H:%M')
#         now_year = str(now.year)[-3:]
#         today_date = now.strftime('%d-%m-') + now_year
#         users = UserProfile.objects.all()
        
#         for user in users:
#             if user.email:
#                 try:
#                     send_mail(
#                         subject=f"📢 {scheduled_time}  Exam Published",
                        
#                         message = textwrap.dedent(f'''\
#                                     📅 Kuwa {today_date}

#                                     ⏰ Ikizamini cya Saa {scheduled_time} cyagezeho.
#                                     📝 Gikore uciye aha: {exam_url}

#                                     📞 Ukeneye ubufasha: 0785287885
#                                     '''),
#                         from_email=settings.DEFAULT_FROM_EMAIL,
#                         recipient_list=[user.email],
#                         fail_silently=False,
#                     )
#                     print(f"✅ Email sent for {exam} to {user.email}")
#                 except OperationalError as e:
#                     print(f"❌ Database error when sending email: {e}")
#                     connections.close_all()  # Attempt to close all connections and retry
#                     continue

import requests
from django.conf import settings

# def job_notify_new_published_exams():
#     close_old_connections()
#     print("📬 Checking for newly published exams...")

#     now = timezone.now()
#     one_hour_ago = now - timezone.timedelta(minutes=60)

#     newly_published = ScheduledExam.objects.filter(
#         scheduled_datetime__gte=one_hour_ago,
#         scheduled_datetime__lte=now
#     )

#     # GreenAPI credentials (from your screenshot)
#     GREEN_API_URL = "https://7105.api.greenapi.com"  # Your apiUrl
#     INSTANCE_ID = "7105229020"                      # Your idInstance
#     API_TOKEN = "c554e7fe36214785890aded373a3c08625e3460ecce249d283"               # Replace with actual token (hide in production)

#     for scheduled in newly_published:
#         exam = scheduled.exam
#         exam_url = f"{settings.BASE_URL}{reverse('exam_detail', args=[exam.id])}"
#         scheduled_time = scheduled.scheduled_datetime.astimezone(ZoneInfo('Africa/Kigali')).strftime('%H:%M')
#         today_date = now.strftime('%d-%m-') + str(now.year)[-3:]

#         users = UserProfile.objects.filter(
#                     Q(whatsapp_consent=True) | 
#                     Q(email__isnull=False)
#                 )  # Only users who opted in
        
#         for user in users:
#             # WhatsApp message content (in Kinyarwanda)
#             message = textwrap.dedent(f'''\
#                                     📅 Kuwa {today_date}

#                                      ⏰ Ikizamini cya Saa {scheduled_time} cyagezeho.
#                                      📝 Gikore uciye aha: {exam_url}

#                                      📞 Ukeneye ubufasha: 0785287885
#                                      ''')

#             # 1. Send WhatsApp via GreenAPI
#             if user.whatsapp_number:  # Ensure number exists
#                 try:
#     # Clean and validate WhatsApp number
#                     whatsapp_num = ''.join(filter(str.isdigit, user.whatsapp_number))  # Remove all non-digits
                    
#                     # Ensure number starts with country code (250 for Rwanda)
#                     if whatsapp_num.startswith('0'):
#                         whatsapp_num = '250' + whatsapp_num[1:]  # Convert 078... to 25078...
#                     elif not whatsapp_num.startswith('250'):
#                         whatsapp_num = '250' + whatsapp_num  # Add Rwanda code if missing
                    
#                     formatted_number = whatsapp_num + "@c.us"
                    
#                     # Validate length (Rwanda numbers should be 12 digits with country code)
#                     if len(whatsapp_num) != 12:
#                         raise ValueError(f"Invalid Rwanda number length: {whatsapp_num}")

#                     response = requests.post(
#                         f"{GREEN_API_URL}/waInstance{INSTANCE_ID}/sendMessage/{API_TOKEN}",
#                         json={
#                             "chatId": formatted_number,
#                             "message": message
#                         },
#                         timeout=10
#                     )
                    
#                     if response.status_code == 200:
#                         print(f"✅ WhatsApp sent to {formatted_number}")
#                     else:
#                         print(f"❌ GreenAPI error: {response.text}")

#                 except ValueError as e:
#                     print(f"⚠️ Invalid number format for {user.whatsapp_number}: {str(e)}")
#                 except Exception as e:
#                     print(f"🚨 WhatsApp failed for {user.whatsapp_number}: {str(e)}")

#             # 2. Email fallback (existing code)
#             if user.email:
#                 try:
#                     send_mail(
#                         subject=f"📢 {scheduled_time} Exam Published",
#                         message=message,
#                         from_email=settings.DEFAULT_FROM_EMAIL,
#                         recipient_list=[user.email],
#                         fail_silently=False,
#                     )
#                     print(f"📧 Email sent to {user.email}")
#                 except Exception as e:
#                     print(f"❌ Email failed: {e}")

def job_notify_new_published_exams():
    close_old_connections()
    print("📬 Checking for newly published exams...")

    # CallMeBot Configuration
    CALLMEBOT_API_KEY = "3324518"  # Your provided API key
    CALLMEBOT_BASE_URL = "https://api.callmebot.com/whatsapp.php"

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

        users = UserProfile.objects.filter(
            Q(whatsapp_consent=True) | 
            Q(email__isnull=False)
        )
        
        message = textwrap.dedent(f'''\
                📅 Kuwa {today_date}

                ⏰ Ikizamini cya Saa {scheduled_time} cyagezeho.
                📝 Gikore uciye aha: {exam_url}

                📞 Ukeneye ubufasha: 0785287885
                ''')
        
        
        notify_admin(message)
        for user in users:
            # Message content (in Kinyarwanda)
            

            # 1. Send WhatsApp via CallMeBot
            # if user.whatsapp_number and user.whatsapp_consent:
                

            # 2. Email fallback
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
    scheduler.add_job(job_auto_schedule_exams, CronTrigger(hour=15, minute=2, second=0), id="auto_schedule_exams")

    # 2. Run email notifications every hour between 07:00 and 17:00
    scheduler.add_job(job_notify_new_published_exams, CronTrigger(minute='32', second='00', hour='7-17'), id="notify_emails")
    
    scheduler.start()
