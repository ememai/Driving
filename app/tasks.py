"""
Celery tasks for background job processing
Handles email sending, notifications, and other async operations
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Subscription, UserProfile, ScheduledExam, Notification, Exam
from .utils import auto_schedule_recent_exams
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================================================
# EMAIL TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, subject, message, recipient_list, from_email=None):
    """
    Send email asynchronously
    
    Args:
        subject: Email subject
        message: Email body
        recipient_list: List of recipient email addresses
        from_email: Sender email (uses DEFAULT_FROM_EMAIL if not provided)
    """
    try:
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        logger.info(f"Email sent to {recipient_list}")
        return f"Email sent successfully to {len(recipient_list)} recipients"
    except Exception as exc:
        logger.error(f"Failed to send email: {str(exc)}")
        self.retry(exc=exc)


@shared_task
def send_otp_email_task(user_id, email, otp_code):
    """Send OTP email to user"""
    try:
        subject = "OTP Code yawe"
        message = f"Koresha iyi code y'isuzuma👉 {otp_code}"
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email: {str(e)}")
        return False


@shared_task
def send_subscription_confirmation_task(user_id):
    """Send subscription confirmation email"""
    try:
        user = User.objects.get(id=user_id)
        subject = "Ifatabuguzi Ryatangira"
        message = f"Mwamukirayo {user.name}, ifatabuguzi ryacu ryatangira. Mukomeze musomera neza!"
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email] if user.email else [],
            fail_silently=False,
        )
        logger.info(f"Subscription confirmation sent to {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")


# ============================================================================
# SUBSCRIPTION TASKS
# ============================================================================

@shared_task
def check_subscription_expiry():
    """
    Check for expiring subscriptions and send renewal reminders
    Runs daily at midnight
    """
    try:
        # Find subscriptions expiring in the next 3 days
        now = timezone.now()
        expiring_soon = Subscription.objects.filter(
            expires_at__lte=now + timezone.timedelta(days=3),
            expires_at__gte=now
        ).select_related('user')
        
        for sub in expiring_soon:
            if sub.user.email:
                subject = "Ifatabuguzi Irangira"
                message = f"Mwami {sub.user.name}, ifatabuguzi ryacu irangira mu minsi {(sub.expires_at - now).days}. Musubiremo muri hano niba urundi kubona ubwiyunge."
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[sub.user.email],
                    fail_silently=False,
                )
        
        logger.info(f"Subscription expiry check completed. {expiring_soon.count()} users notified.")
        return f"Checked {expiring_soon.count()} expiring subscriptions"
    except Exception as e:
        logger.error(f"Error checking subscription expiry: {str(e)}")
        return f"Error: {str(e)}"


# ============================================================================
# NOTIFICATION TASKS
# ============================================================================

@shared_task
def send_scheduled_exams_notification():
    """
    Send notifications about upcoming scheduled exams
    Runs every 2 hours
    """
    try:
        now = timezone.now()
        upcoming_exams = ScheduledExam.objects.filter(
            scheduled_datetime__gte=now,
            scheduled_datetime__lte=now + timezone.timedelta(hours=3),
            exam__is_active=True
        ).select_related('exam', 'exam__exam_type')
        
        if upcoming_exams.exists():
            users = User.objects.filter(is_active=True)
            
            for exam_schedule in upcoming_exams:
                subject = f"Ikizamini Kizaba Mumahoro: {exam_schedule.exam.exam_type.name}"
                message = f"Ikizamini cy'ibivanze kizaba mu gihe cyo mu irangamuntu {exam_schedule.scheduled_datetime.strftime('%H:%M')}. Witeguye?"
                
                for user in users.filter(email__isnull=False):
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
        
        logger.info(f"Exam notifications sent for {upcoming_exams.count()} scheduled exams")
        return f"Notified users about {upcoming_exams.count()} upcoming exams"
    except Exception as e:
        logger.error(f"Error sending exam notifications: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def send_notification_task(user_id, message, notification_type='info'):
    """Send in-app notification to user"""
    try:
        user = User.objects.get(id=user_id)
        Notification.objects.create(
            user=user,
            message=message
        )
        logger.info(f"Notification sent to user {user_id}")
        return True
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for notification")
        return False


# ============================================================================
# EXAM TASKS
# ============================================================================

@shared_task
def auto_schedule_recent_exams_task():
    """
    Auto schedule the most recent exams daily
    """
    try:
        auto_schedule_recent_exams()
        logger.info("✅ Exams scheduled successfully")
        return "Exams scheduled successfully"
    except Exception as e:
        logger.error(f"Error auto-scheduling exams: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def cleanup_old_data():
    """
    Cleanup old exam data and logs
    Runs weekly on Sunday at 2 AM
    """
    try:
        from django.db.models import Q
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # Archive/delete old user activity logs
        from .models import UserActivity
        deleted_count = UserActivity.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old activity records")
        return f"Cleaned up {deleted_count} old records"
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return f"Error: {str(e)}"


# ============================================================================
# Example management command that was previously in tasks.py
# ============================================================================

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Auto schedules the most recent exams daily'

    def handle(self, *args, **kwargs):
        auto_schedule_recent_exams()
        self.stdout.write(self.style.SUCCESS('✅ Exams scheduled successfully.'))
