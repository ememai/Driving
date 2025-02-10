from django.utils import timezone
from app.models import Subscription
from django.core.mail import send_mail


def check_subscription_expiry():
    expired_subscriptions = Subscription.objects.filter(
        expires_at__lte=timezone.now().date(),
        active=True
    )
    
    for sub in expired_subscriptions:
        sub.active = False
        sub.save()
        # Send expiration notification
        send_mail(
            'Subscription Expired',
            'Your subscription has expired. Renew to continue services.',
            'noreply@rwandadrivers.com',
            [sub.user.email],
            fail_silently=False,
        )