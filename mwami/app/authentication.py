from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import phonenumbers  # Ensure you have `phonenumbers` installed: pip install phonenumbers

User = get_user_model()

class EmailOrPhoneBackend(ModelBackend):
    """
    Custom authentication backend to allow login with email or phone number.
    Supports normalized phone numbers.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:  # Prevent NoneType error
            return None
        
        # Check if username is an email or phone number
        lookup_field = "email" if "@" in username else "phone_number"

        # Normalize phone number if it's not an email
        if lookup_field == "phone_number":
            username = self.normalize_phone_number(username)  


        try:
            user = User.objects.get(**{lookup_field: username})
        except User.DoesNotExist:
            return None

        if user and user.check_password(password):
            return user

        return None

    def normalize_phone_number(self, phone_number):
        """
        Ensures the phone number is in the format: +2507XXXXXXXX
        """
        try:
            parsed_number = phonenumbers.parse(phone_number, "RW")  # "RW" is the country code for Rwanda
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return phone_number  # If invalid, return as-is
