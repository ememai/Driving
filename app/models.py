 # Install this with `pip install phonenumbers`
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator

import random
from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.core.exceptions import ValidationError
from django.db import models

from django.core.mail import send_mail
from datetime import date, timedelta

import phonenumbers
from django.contrib import messages
from django.utils import timezone

#

class UserProfileManager(BaseUserManager):
    """Custom manager to allow login with either email or phone."""

    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        if not email and not phone_number:
            raise ValueError("Either an email or phone number is required.")

        email = self.normalize_email(email) if email else None
        phone_number = phone_number if phone_number else None  # Ensure None, not ""
    
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, phone_number, password, **extra_fields)


class UserProfile(AbstractUser):
    
    GENDER_CHOICES = [
        ('male','Gabo'),
        ('female', 'Gore')
    ]
    
    username = None  # Remove default username field
    name = models.CharField(max_length=25, unique=True)
    email = models.EmailField(unique=True, blank=True, null=True)  
    phone_number = models.CharField(max_length=15,default=None, unique=True, null=True, blank=True)     
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='images/', default='images/avatar.png',null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    # is_subscribed = models.BooleanField(default=False)
    subscription_end_date = models.DateField(null=True, blank=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'phone_number'  # Default authentication field
    REQUIRED_FIELDS = ['email']  # Email is optional, but preferred

    objects = UserProfileManager()

    def save(self, *args, **kwargs):
        """Normalize phone number before saving to ensure consistency."""
        if self.phone_number:

            # if self.phone_number == '':
            #     self.phone_number = None
            # else:
            self.phone_number = self.normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)


    def clean(self):
        """Ensure phone number is in the correct format before saving."""
        if not self.email and not self.phone_number:
            raise ValidationError("Telefone cg Imeyili hitampo kimwe wuzuze neza.")

        if self.phone_number:
            self.phone_number = self.normalize_phone_number(self.phone_number)

            # Validate phone number format
            try:
                parsed_number = phonenumbers.parse(self.phone_number, "RW")
                if not phonenumbers.is_valid_number(parsed_number):
                    raise ValidationError("Telefone nyarwanda yujujwe nabi (+250).")
            except phonenumbers.NumberParseException:
                raise ValidationError("Telefone nyarwanda yujujwe nabi.")

        else:
            self.phone_number = None
    def normalize_phone_number(self, phone_number):
        """Ensures phone numbers are always stored in the format: +2507XXXXXXXX."""
        try:
            parsed_number = phonenumbers.parse(phone_number, "RW")
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return phone_number  # If invalid, return as-is


    @property
    def is_subscribed(self):
        if not hasattr(self, 'subscription'):
            return False
        return (
            self.subscription.expires_at and 
            self.subscription.expires_at >= timezone.now().date() and
            self.subscription.active_subscription
        )
    
    @property
    def has_ended_subscription(self):
        if not hasattr(self, 'subscription'):
            return False
        return self.subscription.expires_at and self.subscription.expires_at < timezone.now().date()

    def send_otp_email(self):
        """Generates and sends an OTP via email."""
        if not self.email:
            return
        self.otp_code = str(random.randint(100000, 999999))
        self.save()
        send_mail(
            'OTP Code yawe',
            f"Koresha iyi code y'isuzuma👉 {self.otp_code}",
            'ememaiid@gmail.com',
            [self.email],
            fail_silently=False,
        )

    def verify_otp(self, otp):
        return self.otp_code == otp

    def __str__(self):
        return self.email if self.email else self.phone_number



#instances should be first created
class Plan(models.Model):
    PLAN_CHOICES = [
        ('Daily', "Ry'umunsi"),
        ('Weekly', "Ry'icyumweru"),
        ('Monthly', "Ry'ukwezi"),
        ('Super', 'Rihoraho'),
    ]
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default="Daily", null=True)

    def __str__(self):
        return self.plan
    


class Subscription(models.Model):    

    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    price = models.IntegerField(default=500)
    duration_days = models.IntegerField(default=1, null=True)
    phone_number = models.CharField(max_length=13, default="25078")
    transaction_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    active_subscription = models.BooleanField(default=False)
    started_at = models.DateField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)

    def activate(self, duration_days):
        #  """Activate the subscription for the given duration."""
        self.started_at = timezone.now()  # Fixed from 'start_date'
        self.expires_at = timezone.now() + timezone.timedelta(days=duration_days)
        self.active_subscription = True  # Changed from is_active
        self.save()

    def deactivate(self):
        #  """Deactivate the subscription."""
        self.active_subscription = False
        self.save()

    
    def __str__(self):
        return f"{self.user.name} - {'Active' if self.active_subscription else 'Inactive'}"


class Payment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, choices=[('Success', 'Success'), ('Failed', 'Failed')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.status}"


class RoadSign(models.Model):
    sign_image = models.FileField(upload_to='images/')
    definition = models.CharField(max_length=100)
    type = models.CharField(max_length=50, null=True, blank=True)  # Fixed field name to lowercase

    def __str__(self):
        return self.definition


class Choice(models.Model):
    text = models.CharField(max_length=1000, null=True, blank=True)
    image_choice = models.OneToOneField(RoadSign, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.text or f"Ishusho: '{self.image_choice.definition}'"


class QuestionManager(models.Manager):
    def get_questions_with_index(self):
        return [(index + 1, question) for index, question in enumerate(self.all())]


class Question(models.Model):
    question_text = models.TextField()
    sign = models.ManyToManyField(RoadSign, related_name='road_sign_questions', blank=True)
    choices = models.ManyToManyField(Choice, related_name='choice_questions')
    correct_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='correct_for_questions')
    order = models.PositiveIntegerField(help_text="Order of the question in the exam")


    objects = QuestionManager()

    # def clean(self):
    #     if self.choices.count() > 4:
    #         raise ValidationError("Exam must have max of 4 choices")

    def __str__(self):
        return f"{self.id}. {self.question_text[:50]}"


class Exam(models.Model):
    TYPE_CHOICES = [
        ('Ibimenyetso', 'Ibimenyetso'),
        ('Ibyapa', 'Ibyapa'),
        ('Bivanze', 'Bivanze'),
        ('Ibindi', 'Ibindi'),
    ]
    title = models.CharField(max_length=500, choices=TYPE_CHOICES, blank=True)
    questions = models.ManyToManyField(Question, related_name='exams')
    duration = models.PositiveIntegerField(default=20,help_text="Duration of the exam in minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=False)
    # max_attempts = models.PositiveIntegerField(default=1)


    # def remaining_attempts(self, user):
    #     attempts = UserExam.objects.filter(user=user, exam=self).count()
    #     return self.max_attempts - attempts

    def __str__(self):
        return self.title


class UserExam(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exam')
    
    
    def save(self, *args, **kwargs):
        if not self.user.is_subscribed:
            raise ValidationError(
                "Umukoresha ntabwo yishyuye kugirango akore ijazo."
            )
        if self.completed_at and self.completed_at < timezone.now() - timedelta(hours=24):
            raise ValidationError(
                "You cannot modify exams older than 24 hours"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"


class UserExamAnswer(models.Model):
    user_exam = models.ForeignKey(UserExam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user_exam.user.username} - {self.question.question_text[:50]}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"



class ScheduledExam(models.Model):
    exam = models.ForeignKey("Exam", on_delete=models.CASCADE)  # Ensure CASCADE to avoid null exams
    scheduled_datetime = models.DateTimeField(help_text="Date & time when the exam should be published")
    is_published = models.BooleanField(default=False)


    def publish(self):
        """Marks the exam as published"""
        if not self.is_published and self.scheduled_datetime <= timezone.now():
            self.is_published = True
            self.exam.is_active = True  # Activate the exam
            self.exam.save()
            self.save()

            # Send email to all users (or you can send it to specific ones)
            self.send_notification()
            
            print(f"Exam '{self.exam.title}' has been published!")
            
    def save(self, *args, **kwargs):
        """Auto-publish if scheduled time has passed (Kigali time)"""
        now = timezone.localtime(timezone.now())
        scheduled_time = timezone.localtime(self.scheduled_datetime)
        
        if scheduled_time <= now:
            self.is_published = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Scheduled: {self.exam.title} at {self.scheduled_datetime}"

            # Notify all subscribed users
    def send_notification(self):
        """Send an email notification to all users when the exam goes live"""
        subject = f"New Exam is Live: {self.exam.title}"
        message = f"The exam titled '{self.exam.title}' is now live! You can take it now."
        
        # Here, you would fetch the users who should receive the notification
        # Assuming you have a way to fetch them from the `UserProfile` model:
        users = UserProfile.objects.all()  # You can filter by specific users if needed
        for user in users:
            if user.email:  # Ensure the user has an email
                send_mail(
                    subject,
                    message,
                    'noreply@yourdomain.com',  # This can be your business email
                    [user.email],
                    fail_silently=False,
                )
            
            print(f"Exam '{self.exam.title}' has been published and users have been notified!")

    def __str__(self):
        return f"Scheduled: {self.exam.title} at {self.scheduled_datetime}"

class UserActivity(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=255)
    details = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.activity_type} by {self.user.username} on {self.timestamp}"

class Notification(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}"

