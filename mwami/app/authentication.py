from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrPhoneBackend(ModelBackend):
    """
    Custom authentication backend to allow login with email or phone number.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username) if '@' in username else User.objects.get(phone_number=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user

        return None
