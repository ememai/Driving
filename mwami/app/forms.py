from django import forms

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import *

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()
from django import forms
from django.contrib.auth.hashers import make_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import UserProfile

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, max_length=50, min_length=8, required=True, label="Password")

    password2 = forms.CharField(widget=forms.PasswordInput, max_length=50, min_length=8, required=True, label="Confirm Password")

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={"placeholder": "Enter phone number (e.g., 788123456)"}),
    )

    
    class Meta:
        model = UserProfile
        fields = ['email', 'phone_number']

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone_number = cleaned_data.get("phone_number")

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")


        if not email and not phone_number:
            raise forms.ValidationError("You must provide either an email or phone number.")

        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError("Enter a valid email address.")

            if UserProfile.objects.filter(email=email).exists():
                raise forms.ValidationError("This email is already registered.")

        if phone_number:
            # Normalize phone number (prepend +250 if not already included)
            if not phone_number.startswith('+250'):
                phone_number = '+250' + phone_number.strip()

            # Validate phone number format
            try:
                parsed_number = phonenumbers.parse(phone_number, None)
                if not phonenumbers.is_valid_number(parsed_number):
                    raise forms.ValidationError("Invalid phone number format")
            except phonenumbers.phonenumberutil.NumberParseException:
                raise forms.ValidationError("Invalid phone number format")
            
            # Strip country code (+250) to check the last digits
            stripped_number = phone_number[4:]  # Remove '+250'

            # Check if phone number exists based on the last digits (without country code)
            if UserProfile.objects.filter(phone_number__endswith=stripped_number).exists():
                raise forms.ValidationError(f"A user with this phone number already exists.")


        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        
        

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # Hash the password properly
        if commit:
            user.save()
        return user
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")

        if phone:
            # Remove spaces, dashes, and ensure it starts with +250
            phone = phone.replace(" ", "").replace("-", "")
            if not phone.startswith("+250"):
                phone = "+250" + phone.lstrip("0")  # Remove leading zero and add +250

            # Validate with `phonenumbers` library
            try:
                parsed_number = phonenumbers.parse(phone, "RW")
                if not phonenumbers.is_valid_number(parsed_number):
                    raise forms.ValidationError("Invalid Rwandan phone number.")
            except phonenumbers.phonenumberutil.NumberParseException:
                raise forms.ValidationError("Invalid phone number format.")

        return phone


class LoginForm(forms.Form):
    username = forms.CharField(label="Email or Phone")
    password = forms.CharField(widget=forms.PasswordInput, label="Enter your password",
    max_length=50,
    min_length=8,
    required=True)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")

        if not username:
            raise forms.ValidationError("Email or Phone number is required.")

        return cleaned_data
