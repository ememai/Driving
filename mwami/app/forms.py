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
    password = forms.CharField(widget=forms.PasswordInput, max_length=50, min_length=8, required=True)
    
    class Meta:
        model = UserProfile
        fields = ['email', 'phone_number', 'password']

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone_number = cleaned_data.get("phone_number")

        if not email and not phone_number:
            raise forms.ValidationError("You must provide either an email or phone number.")

        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError("Enter a valid email address.")

            if UserProfile.objects.filter(email=email).exists():
                raise forms.ValidationError("This email is already registered.")

        if phone_number and UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data["password"])  # Hash the password
        if commit:
            user.save()
        return user

# class RegisterForm(forms.ModelForm):
#     password = forms.CharField(widget=forms.PasswordInput,  max_length=50,
#     min_length=8,
#     required=True)
    
#     class Meta:
#         model = UserProfile
#         fields = ['email', 'phone_number', 'password']

#     def clean(self):
#         cleaned_data = super().clean()
#         email = cleaned_data.get("email")
#         phone_number = cleaned_data.get("phone_number")

#         if not email and not phone_number:
#             raise forms.ValidationError("You must provide either an email or phone number.")

#         return cleaned_data

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



class SubscriptionForm(forms.Form):
    plan_choices = [
        ('monthly', 'Monthly - $10'),
        ('yearly', 'Yearly - $100'),
    ]
    plan = forms.ChoiceField(choices=plan_choices, widget=forms.RadioSelect)
