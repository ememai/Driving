# yourapp/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import UserActivity, PaymentConfirm, PaymentAutoConfirmSetting, Subscription, Plan, PaymentConfirmLog
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        activity_type="Login",
        details=f"User {user.username} logged in."
    )


@receiver(post_save, sender=PaymentConfirm)
def auto_confirm_payment(sender, instance, created, **kwargs):
    """
    Automatically confirm payment if:
    1. PaymentAutoConfirmSetting is enabled and within the active period
    2. User has submitted enough confirmations (tracked via logs)

    The PaymentConfirm table has a unique constraint on user, so each update
    still triggers this signal. We log every save instead of relying on one
    record per attempt.
    """
    try:
        # Always create a log entry for this save event
        PaymentConfirmLog.objects.create(user=instance.user, payment_confirm=instance)

        # Check if auto-confirmation setting is active
        setting = PaymentAutoConfirmSetting.objects.filter(is_enabled=True).last()
        if not setting or not setting.is_active:
            logger.debug("Auto-confirm setting not active")
            return

        # Count payment confirm logs from this user within the active period
        confirm_count = PaymentConfirmLog.objects.filter(
            user=instance.user,
            payment_confirm__time__gte=setting.period_start,
            payment_confirm__time__lte=setting.period_end
        ).count()

        logger.info(f"User {instance.user.name} has {confirm_count} payment confirm logs in the active period")

        # Skip auto-approval if user already has an active subscription
        if hasattr(instance.user, 'subscription') and instance.user.subscription.active_subscription:
            logger.info(f"User {instance.user.name} already has an active subscription; skipping auto-approval")
            return

        # If user has enough logs, auto-approve
        if confirm_count >= setting.required_confirms:
            _auto_approve_payment(instance.user, instance.plan, setting)

    except Exception as e:
        logger.error(f"Error in auto_confirm_payment signal: {str(e)}", exc_info=True)


def _auto_approve_payment(user, plan, setting):
    """
    Create/update subscription and generate OTP for automatic payment approval.
    """
    try:
        subscription, created = Subscription.objects.get_or_create(user=user)
        
        # Update subscription with the plan
        subscription.plan = plan
        subscription.generate_otp()
        subscription.save()
        
        # Send notification to admin
        from .utils import notify_admin
        
        message = (
            f"✅ AUTO-CONFIRMED PAYMENT\n\n"
            f"User: {user.name}\n"
            f"Phone: {user.phone_number}\n"
            f"Plan: {plan.plan}\n"
            f"Price: {plan.price}\n"
            f"OTP Code: {subscription.otp_code}\n\n"
            f"User must verify this OTP to activate subscription."
        )
        
        notify_admin(message)
        
        logger.info(f"Payment auto-confirmed for user {user.name}. OTP: {subscription.otp_code}")
        
    except Exception as e:
        logger.error(f"Error in _auto_approve_payment: {str(e)}", exc_info=True)
