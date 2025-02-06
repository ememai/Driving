from django.contrib import admin
from .models import *
# Register your models here.

class ExamAdmin(admin.ModelAdmin):
  list_display = ('name', 'date_created')
  search_fields = ('name',)

class RoadSignAdmin(admin.ModelAdmin):
  list_display = ('name', 'description')
  search_fields = ('name',)

class ChoiceAdmin(admin.ModelAdmin):
  list_display = ('question', 'choice_text', 'is_correct')
  search_fields = ('choice_text',)

class QuestionAdmin(admin.ModelAdmin):
  list_display = ('text', 'exam')
  search_fields = ('text',)

class UserProfileAdmin(admin.ModelAdmin):
  list_display = ('user', 'bio')
  search_fields = ('user__username',)

class UserExamAdmin(admin.ModelAdmin):
  list_display = ('user', 'exam', 'score')
  search_fields = ('user__username', 'exam__name')

class PaymentAdmin(admin.ModelAdmin):
  list_display = ('user', 'amount', 'date')
  search_fields = ('user__username',)

class SubscriptionAdmin(admin.ModelAdmin):
  list_display = ('user', 'start_date', 'end_date')
  search_fields = ('user__username',)

class ContactMessageAdmin(admin.ModelAdmin):
  list_display = ('name', 'email', 'message')
  search_fields = ('name', 'email')


admin.site.register(Exam)
admin.site.register(RoadSign)
admin.site.register(Choice)
admin.site.register(Question)
admin.site.register(UserProfile)
admin.site.register(UserExam)
admin.site.register(Payment)
admin.site.register(Subscription)
admin.site.register(ContactMessage)
admin.site.register(Plan)
