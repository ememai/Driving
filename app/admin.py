from django.contrib import admin
from .models import *
from .forms import *

from django.urls import reverse
from django.utils.html import format_html
from django.contrib.admin import AdminSite
# Register your models here.
# class:
#   pass
#       class ExamAdmin(admin.ModelAdmin):
#         list_display = ('name', 'date_created')
#         search_fields = ('name',)

#       class RoadSignAdmin(admin.ModelAdmin):
#         list_display = ('name', 'description')
#         search_fields = ('name',)

#       class ChoiceAdmin(admin.ModelAdmin):
#         list_display = ('question', 'choice_text', 'is_correct')
#         search_fields = ('choice_text',)

#       class QuestionAdmin(admin.ModelAdmin):
#         list_display = ('text', 'exam')
#         search_fields = ('text',)

#       class UserProfileAdmin(admin.ModelAdmin):
#         list_display = ('user', 'bio')
#         search_fields = ('user__username',)

#       class UserExamAdmin(admin.ModelAdmin):
#         list_display = ('user', 'exam', 'score')
#         search_fields = ('user__username', 'exam__name')

#       class PaymentAdmin(admin.ModelAdmin):
#         list_display = ('user', 'amount', 'date')
#         search_fields = ('user__username',)

#       class SubscriptionAdmin(admin.ModelAdmin):
#         list_display = ('user', 'start_date', 'end_date')
#         search_fields = ('user__username',)

#       class ContactMessageAdmin(admin.ModelAdmin):
#         list_display = ('name', 'email', 'message')
#         search_fields = ('name', 'email')


#       admin.site.register(Exam)
#       admin.site.register(RoadSign)
#       admin.site.register(Choice)
#       admin.site.register(Question)
#       admin.site.register(UserProfile)
#       admin.site.register(UserExam)
#       admin.site.register(Payment)
#       admin.site.register(Subscription)
#       admin.site.register(ContactMessage)
#       admin.site.register(Plan)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('name','email', 'phone_number',  'otp_verified')
    search_fields = ('name','email', 'phone_number')
    list_filter = [('otp_verified')]

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ('definition', 'type')
    search_fields = ('definition', 'type')

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('text', 'image_choice')
    search_fields = ('text',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm
    list_display = ('question_text', 'correct_choice')
    filter_horizontal = ('sign', 'choices')
 
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    form = ExamForm
    list_display = ('title', 'created_at', 'updated_at')
    filter_horizontal = ('questions',)

@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'score', 'completed_at')
    search_fields = ('user__email', 'exam__title')

# @admin.register(UserExamAnswer)
# class UserExamAnswerAdmin(admin.ModelAdmin):
#     list_display = ('user_exam', 'question', 'selected_choice')
#     search_fields = ('user_exam__user__email', 'question__question_text')

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('plan',)
    search_fields = ('plan',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'price', 'active_subscription', 'expires_at')
    search_fields = ('user__email', 'plan__plan')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    search_fields = ('user__email', 'transaction_id')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email')

# admin.py

@admin.action(description='Activate selected subscriptions')
def activate_subscriptions(modeladmin, request, queryset):
    queryset.update(active_subscription=True)


@admin.register(ScheduledExam)
class ScheduledExamAdmin(admin.ModelAdmin):
    list_display = ('exam', 'scheduled_datetime', 'is_published')
    list_filter = ('is_published',)
    ordering = ('scheduled_datetime',)
    actions = ['publish_exam']

    def publish_exam(self, request, queryset):
        for scheduled_exam in queryset:
            scheduled_exam.publish()
    publish_exam.short_description = "Publish Scheduled Exams"

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp', 'details')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'timestamp', 'is_read')
    list_filter = ('is_read',)

