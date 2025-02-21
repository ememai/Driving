from django import forms

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import *

class UserProfileRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)

    class Meta:
        model = UserProfile
        fields = ['email', 'username', 'phone_number', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if UserProfile.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Phone number already exists")
        return phone_number

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Email or Phone Number", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class SubscriptionForm(forms.Form):
    plan_choices = [
        ('monthly', 'Monthly - $10'),
        ('yearly', 'Yearly - $100'),
    ]
    plan = forms.ChoiceField(choices=plan_choices, widget=forms.RadioSelect)
