# yourapp/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import UserActivity

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        activity_type="Login",
        details=f"User {user.username} logged in."
    )
