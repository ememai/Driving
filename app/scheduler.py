from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from .models import *
from .utils import auto_schedule_recent_exams
from zoneinfo import ZoneInfo
from django.db import close_old_connections, connections
from django.db.utils import OperationalError
import textwrap


def job_auto_schedule_exams():
    connections.close_all()
    print("🕛 Running daily auto-schedule...")
    auto_schedule_recent_exams()
    print("✅ Recent exams scheduled.")


def job_notify_new_published_exams():
    close_old_connections()  # Close old connections to avoid issues
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
        now_year = str(now.year)[-3:]
        today_date = now.strftime('%d-%m-') + now_year
        users = UserProfile.objects.all()
        
        for user in users:
            if user.email:
                try:
                    send_mail(
                        subject=f"📢 {scheduled_time}  Exam Published",
                        
                        message = textwrap.dedent(f'''\
                                    📅 Kuwa {today_date}

                                    ⏰ Ikizamini cya Saa {scheduled_time} cyagezeho.
                                    📝 Gikore uciye aha: {exam_url}

                                    📞 Ukeneye ubufasha: 0785287885
                                    '''),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    print(f"✅ Email sent for {exam} to {user.email}")
                except OperationalError as e:
                    print(f"❌ Database error when sending email: {e}")
                    connections.close_all()  # Attempt to close all connections and retry
                    continue

def start():
    scheduler = BackgroundScheduler(timezone=ZoneInfo("Africa/Kigali"))    
    # 1. Run exam scheduling every day at 00:00
    scheduler.add_job(job_auto_schedule_exams, CronTrigger(hour=0, minute=0), id="auto_schedule_exams")

    # 2. Run email notifications every hour between 07:00 and 17:00
    scheduler.add_job(job_notify_new_published_exams, CronTrigger(minute='0', hour='7-17'), id="notify_emails")
    
    scheduler.start()
