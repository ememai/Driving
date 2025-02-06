 # Install this with `pip install phonenumbers`
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
import random
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.core.mail import send_mail
from datetime import date
import phonenumbers

class UserProfileManager(BaseUserManager):
    """Custom manager to allow login with either email or phone."""

    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        if not email and not phone_number:
            raise ValueError("Either an email or phone number is required.")

        email = self.normalize_email(email) if email else None
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, phone_number, password, **extra_fields)


class UserProfile(AbstractUser):
    username = None  # Remove default username field
    email = models.EmailField(unique=True, blank=True, null=True)  
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)  
    profile_picture = models.ImageField(upload_to='images/', null=True, blank=True)
    active = models.BooleanField(default=False)
    subscription_end_date = models.DateField(null=True, blank=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)

    USERNAME_FIELD = 'phone_number'  # Default authentication field
    REQUIRED_FIELDS = ['email']  # Email is optional, but preferred

    objects = UserProfileManager()

    def clean(self):
        """
        Ensures that at least one of email or phone number is provided.
        Also validates phone number format.
        """
        if not self.email and not self.phone_number:
            raise ValidationError("Either an email or phone number is required.")

        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number, None)
                
                if not phonenumbers.is_valid_number(parsed_number):
                    raise ValidationError("Invalid phone number format")
            except:
                raise ValidationError("Invalid phone number format")

    @property
    def is_subscribed(self):
        return self.subscription_end_date and self.subscription_end_date >= date.today()

    def send_otp_email(self):
        """Generates and sends an OTP via email."""
        if not self.email:
            return
        self.otp_code = str(random.randint(100000, 999999))
        self.save()
        send_mail(
            'Your OTP Code',
            f'Your OTP code is {self.otp_code}',
            'no-reply@example.com',
            [self.email],
            fail_silently=False,
        )

    def verify_otp(self, otp):
        return self.otp_code == otp

    def __str__(self):
        return self.email if self.email else self.phone_number




class RoadSign(models.Model):
    sign_image = models.FileField(upload_to='images/')
    definition = models.CharField(max_length=100)
    type = models.CharField(max_length=50, null=True, blank=True)  # Fixed field name to lowercase

    def __str__(self):
        return self.definition


class Choice(models.Model):
    text = models.CharField(max_length=1000, null=True, blank=True)
    image_choice = models.OneToOneField(RoadSign, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.text or f"Ishusho: '{self.image_choice.definition}'"


class QuestionManager(models.Manager):
    def get_questions_with_index(self):
        return [(index + 1, question) for index, question in enumerate(self.all())]


class Question(models.Model):
    question_text = models.TextField()
    sign = models.ManyToManyField(RoadSign, related_name='questions', blank=True)
    choices = models.ManyToManyField(Choice, related_name='questions')
    correct_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='correct_for_questions')

    objects = QuestionManager()

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class UserExam(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exam')

    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"


class UserExamAnswer(models.Model):
    user_exam = models.ForeignKey(UserExam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user_exam.user.username} - {self.question.question_text[:50]}"

class Plan(models.Model):
    PLAN_CHOICES = [
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
        ('Super', 'Super'),
    ]
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default="Daily", null=True)

    def __str__(self):
        return self.plan
    


class Subscription(models.Model):
    

    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    price = models.IntegerField(default=500)
    duration_days = models.IntegerField(default=1)
    phone_number = models.CharField(max_length=13, default=25078)
    transaction_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    active = models.BooleanField(default=False)
    started_at = models.DateField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)

    def activate(self, duration_days=30):
        # """Activate the subscription for a given duration."""
        self.start_date = now()
        self.end_date = now() + timedelta(days=duration_days)
        self.is_active = True
        self.save()

    def deactivate(self):
        #  """Deactivate the subscription."""
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.user.username} - {'Active' if self.active else 'Inactive'}"


class Payment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, choices=[('Success', 'Success'), ('Failed', 'Failed')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"
