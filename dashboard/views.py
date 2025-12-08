
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from app.models import *
from app.views import *
from app.authentication import *
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import *
import time
import logging
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from app.decorators import redirect_authenticated_users  # Make sure this exists

logger = logging.getLogger(__name__)

# A helper test so that only staff (admin) users can access these views.
def staff_required(user):
    return user.is_staff

from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

class StaffLoginView(View):
    """
    Secure staff login page with multiple security layers
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page = 'staff_login'
    
    @method_decorator(redirect_authenticated_users)
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        # Security headers
        request.META['HTTP_X_FRAME_OPTIONS'] = 'DENY'
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = StaffLoginForm()
        return self.render_response(form)
    
    def post(self, request):
        form = StaffLoginForm(request.POST, request=request)
        
        # Artificial delay to prevent timing attacks
        start_time = time.time()
        
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            
            # Check rate limiting first
            rate_ok, rate_message = self.rate_limit_check(request, username)
            if not rate_ok:
                messages.error(request, rate_message)
                self.log_login_attempt(request, username, "RATE_LIMITED")
                return self.render_response(form)
            
            # Normalize phone number if needed
            if "@" not in username:  
                username = EmailOrPhoneBackend().normalize_phone_number(username)

            # Fetch user by email or phone number
            user = User.objects.filter(
                Q(phone_number=username) | Q(email=username)
            ).first()
            
            if user:
                # Ensure phone_number is set to None if empty
                if user.phone_number == "":
                    user.phone_number = None
                    user.save(update_fields=["phone_number"])
                
                # Enhanced staff verification
                if user.is_staff or user.is_superuser:
                    return self.handle_staff_authentication(request, user, username, password, form, start_time)
                else:
                    messages.error(request, "This account does not have staff privileges.")
                    self.increment_rate_limit(request, username)
                    self.log_login_attempt(request, username, "FAILED_NO_PRIVILEGES")
            else:
                # User doesn't exist - still log the attempt
                self.increment_rate_limit(request, username)
                self.log_login_attempt(request, username, "FAILED_NOT_EXIST")
                messages.error(request, "Staff account does not exist.")
                
            # Add delay to prevent timing attacks
            self.add_security_delay(start_time)
                
        # Handle form validation errors
        self.handle_form_errors(form)
        return self.render_response(form)
    
    def handle_staff_authentication(self, request, user, username, password, form, start_time):
        """Handle staff authentication with security checks"""
        # Check if staff account is active
        if not user.is_active:
            messages.error(request, "Staff account is deactivated.")
            self.increment_rate_limit(request, username)
            self.log_login_attempt(request, username, "FAILED_INACTIVE")
            return self.render_response(form)
        
        # Check for suspicious login patterns
        if self.is_suspicious_login(request, user):
            messages.error(request, "Suspicious login attempt detected.")
            self.increment_rate_limit(request, username)
            self.log_login_attempt(request, username, "FAILED_SUSPICIOUS")
            return self.render_response(form)
        
        # Authenticate with password
        authenticated_user = authenticate(request, username=username, password=password)
        
        if authenticated_user:
            return self.handle_successful_login(request, authenticated_user, username)
        else:
            # Failed authentication
            self.handle_failed_login(request, username, user)
            messages.error(request, "Invalid credentials.")
            self.add_security_delay(start_time)
            return self.render_response(form)
    
    def handle_successful_login(self, request, user, username):
        """Handle successful login"""
        login(request, user)
        
        # Clear rate limiting on success
        self.clear_rate_limits(request, username)
        
        # Log successful login
        self.log_login_attempt(request, username, "SUCCESS")
        
        # Update last login info
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Store last login IP for future comparison
        cache.set(f"last_login_ip_{user.id}", self.get_client_ip(request), 86400)
        
        # Redirect to appropriate admin page
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        
        messages.success(request, "Staff login successful! Welcome back.")
        return redirect("home")
    
    def handle_failed_login(self, request, username, user):
        """Handle failed login attempts with security measures"""
        # Increment failed attempts counter
        self.increment_rate_limit(request, username)
        
        # Log the attempt
        self.log_login_attempt(request, username, "FAILED_PASSWORD")
        
        # Optional: Lock account after too many attempts
        attempts = cache.get(f"staff_login_attempts_{username}", 0)
        if attempts >= 5 and user:
            user.is_active = False
            user.save()
            # Send security alert email would go here
    
    def handle_form_errors(self, form):
        """Handle form validation errors"""
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")
    
    def add_security_delay(self, start_time):
        """Add delay to prevent timing attacks"""
        elapsed = time.time() - start_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
    
    def render_response(self, form):
        """Render the response with form and context"""
        context = {
            "form": form,
            "page": self.page
        }
        return render(self.request, "admin/staff_login.html", context)
    
    # Security Helper Methods
    
    def rate_limit_check(self, request, username):
        """Custom rate limiting without external dependencies"""
        client_ip = self.get_client_ip(request)
        
        # Username-based rate limiting (5 attempts per 15 minutes)
        username_key = f"staff_login_attempts_{username}"
        username_attempts = cache.get(username_key, 0)
        
        # IP-based rate limiting (10 attempts per 15 minutes)
        ip_key = f"staff_login_ip_{client_ip}"
        ip_attempts = cache.get(ip_key, 0)
        
        if username_attempts >= 5:
            return False, "Too many login attempts for this username. Please try again in 15 minutes."
        
        if ip_attempts >= 10:
            return False, "Too many login attempts from your network. Please try again in 15 minutes."
        
        return True, None
    
    def increment_rate_limit(self, request, username):
        """Increment rate limiting counters"""
        client_ip = self.get_client_ip(request)
        
        username_key = f"staff_login_attempts_{username}"
        ip_key = f"staff_login_ip_{client_ip}"
        
        # Increment counters with 15-minute expiration
        cache.set(username_key, cache.get(username_key, 0) + 1, 900)  # 15 minutes
        cache.set(ip_key, cache.get(ip_key, 0) + 1, 900)  # 15 minutes
    
    def clear_rate_limits(self, request, username):
        """Clear rate limits on successful login"""
        client_ip = self.get_client_ip(request)
        cache.delete(f"staff_login_attempts_{username}")
        cache.delete(f"staff_login_ip_{client_ip}")
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FRAME_OPTIONS')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_login_attempt(self, request, username, status):
        """Log login attempts for security monitoring"""
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        logger.info(f"Staff login attempt - Username: {username}, IP: {client_ip}, Status: {status}")
    
    def is_suspicious_login(self, request, user):
        """Detect suspicious login patterns"""
        client_ip = self.get_client_ip(request)
        
        # Check if login from new IP (basic check)
        last_ip_key = f"last_login_ip_{user.id}"
        last_ip = cache.get(last_ip_key)
        
        if last_ip and last_ip != client_ip:
            # IP changed - could be suspicious
            suspicious_key = f"suspicious_ip_{user.id}_{client_ip}"
            if cache.get(suspicious_key):
                return True
        
        # Check login time patterns (unusual hours)
        current_hour = timezone.now().hour
        if current_hour < 6 or current_hour > 22:  # Outside business hours
            unusual_key = f"unusual_hours_{user.id}"
            unusual_count = cache.get(unusual_key, 0) + 1
            cache.set(unusual_key, unusual_count, 3600)  # 1 hour
            return unusual_count > 2
        
        return False


@login_required(login_url="staff_login")
@user_passes_test(staff_required)
def admin_dashboard(request):
    """
    Displays tables for Payments, Subscriptions, Users, and Scheduled Exams.
    """
    payments = Payment.objects.all()
    subscriptions = Subscription.objects.all()
    users = UserProfile.objects.all()
    scheduled_exams = ScheduledExam.objects.all()
    
    context = {
        'payments': payments,
        'subscriptions': subscriptions,
        'users': users,
        'scheduled_exams': scheduled_exams,
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
@user_passes_test(staff_required)
def schedule_exam(request):
    """
    Displays and processes the form to schedule a new exam.
    """
    if request.method == 'POST':
        form = ScheduledExamForm(request.POST)
        if form.is_valid():
            scheduled_exam = form.save()
            messages.success(request, f"Exam scheduled successfully for {scheduled_exam.scheduled_datetime}.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ScheduledExamForm()
    context = {
        'form': form,
    }
    return render(request, 'dashboard/schedule_exam.html', context)

@login_required
@user_passes_test(staff_required)
def scheduled_exam_update(request, pk):
    """
    Displays and processes the form to update an existing scheduled exam.
    """
    scheduled_exam = get_object_or_404(ScheduledExam, pk=pk)
    if request.method == 'POST':
        form = ScheduledExamForm(request.POST, instance=scheduled_exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Scheduled exam updated successfully.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ScheduledExamForm(instance=scheduled_exam)
    context = {'form': form, 'scheduled_exam': scheduled_exam}
    return render(request, 'dashboard/schedule_exam_update.html', context)

@login_required
@user_passes_test(staff_required)
def scheduled_exam_delete(request, pk):
    """
    Confirms and then deletes the selected scheduled exam.
    """
    scheduled_exam = get_object_or_404(ScheduledExam, pk=pk)
    if request.method == 'POST':
        scheduled_exam.delete()
        messages.success(request, "Scheduled exam deleted successfully.")
        return redirect('admin_dashboard')
    context = {'scheduled_exam': scheduled_exam}
    return render(request, 'dashboard/schedule_exam_delete.html', context)
