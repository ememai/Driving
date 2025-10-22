# dashboard/forms.py
from django import forms
from django.utils import timezone
from app.models import *
from app.authentication import *
import re
from django.core.cache import cache
from datetime import timedelta

class ScheduledExamForm(forms.ModelForm):
    # Use an HTML5 datetime-local widget for a better UI
    scheduled_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Select a future date and time."
    )

    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ScheduledExam
        fields = ['exam', 'scheduled_datetime']
    
    def clean_scheduled_datetime(self):
        scheduled_datetime = self.cleaned_data.get('scheduled_datetime')
        if scheduled_datetime < timezone.now():
            raise forms.ValidationError("Scheduled time cannot be in the past.")
        return scheduled_datetime


class StaffLoginForm(forms.Form):
    username = forms.CharField(
        label="Email or Phone Number",
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your email or phone number...',
            'class': 'form-control',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password...',
            'class': 'form-control',
            'autocomplete': 'current-password'
        }),
        label="Password"
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Basic sanitization
            username = username.strip()
            # Check for suspicious patterns
            if re.search(r'[<>"\']', username):
                raise forms.ValidationError("Invalid characters in username.")
            
            # Rate limiting per username
            cache_key = f"staff_login_attempts_{username}"
            attempts = cache.get(cache_key, 0)
            if attempts >= 5:  # Max 5 attempts per username
                raise forms.ValidationError("Too many login attempts. Please try again in 15 minutes.")
                
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        
        if username and not password:
            raise forms.ValidationError("Password is required for staff login.")
        
        # IP-based rate limiting
        if self.request:
            client_ip = self.get_client_ip()
            ip_cache_key = f"staff_login_ip_{client_ip}"
            ip_attempts = cache.get(ip_cache_key, 0)
            
            if ip_attempts >= 10:  # Max 10 attempts per IP
                raise forms.ValidationError("Too many login attempts from your network. Please try again later.")
        
        return cleaned_data
    
    def get_client_ip(self):
        """Get client IP address for rate limiting"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip