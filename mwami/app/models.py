from django.db import models
from django.contrib.auth.models import User
from datetime import date
# Create your models here.    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    subscription_end_date = models.DateField(null=True, blank=True)

    @property
    def is_subscribed(self):
        return self.subscription_end_date and self.subscription_end_date >= date.today()
        
class RoadSign(models.Model):
    name = models.CharField(max_length=50)
    image = models.FileField(upload_to='images/', blank=True)

    def __str__(self):
        return self.name

class Question(models.Model):
    title = models.TextField()
    sign = models.ManyToManyField(to=RoadSign, related_name='sign', blank=True)
    choice1 = models.CharField(max_length=1000)
    choice2 = models.CharField(max_length=1000)
    choice3 = models.CharField(max_length=1000)
    choice4 = models.CharField(max_length=1000)
    CORRECT = [
        ('A',choice1),
        ('B',choice2),
        ('C',choice3),
        ('D',choice4),
    ]
    correct_choice = models.CharField(max_length=500,   choices = CORRECT)

    def __str__(self):
        return self.title

class Exam(models.Model):
    TYPE = [
        ('Ibimenyetso', 'Ibimenyetso'),
        ('Ibyapa', 'Ibyapa'),
        ('Bivanze', 'Bivanze'),
        ('Ibindi', 'Ibindi'),

    ]
    title = models.CharField(max_length=500, choices=TYPE, blank=True)
    questions = models.ManyToManyField(to=Question, related_name='questions')
    created_at = models.DateTimeField(auto_now_add=True)
   # duration = models.DurationField()

    def __str__(self):
        return self.title

class UserExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exam')  # Enforce unique user-exam combination

    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"

class UserExamAnswer(models.Model):
    user_exam = models.ForeignKey(UserExam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.CharField(max_length=1, null=True, blank=True)

    def __str__(self):
        return f"{self.user_exam.user.username} - {self.question.title}"

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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

