from django.contrib import admin, messages
from .models import *
from .forms import *
from django.shortcuts import redirect

from django.urls import reverse
from django.utils.html import format_html
from django.contrib.admin import AdminSite
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# Register your models here.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'otp_verified', 'is_subscribed', 'subscription_end_date')
    search_fields = ('name', 'email', 'phone_number')
    list_filter = ('otp_verified',)


@admin.register(SignType)
class SignTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    form = RoadSignAdminForm

    class Media:
        js = ('admin/js/roadsign_admin.js',)
        css = {'all': ('admin/css/roadsign_admin.css',)}

    list_display = ('name','definition', 'image_preview', 'type', 'uploaded_at', 'date_updated')
    search_fields = ('definition', 'type__name')
    list_filter = ('type', 'is_active')
    readonly_fields = ('image_preview', 'uploaded_at', 'date_updated')

    def get_fieldsets(self, request, obj=None):
        if obj:  # Change form
            fieldsets = (
                ('Image Management', {
                    'fields': ('name','image_preview', 'image_choice', 'existing_image', 'sign_image')
                }),
                ('Dates', {
                    'classes': ('collapse',),
                    'fields': ('uploaded_at', 'date_updated')
                }),
                (None, {
                    'fields': ('definition', 'type', 'is_active')
                }),
            )
        else:  # Add form
            fieldsets = (
                ('Image Management', {
                    'fields': ('image_choice', 'existing_image', 'sign_image', 'name')
                }),
                (None, {
                    'fields': ('definition', 'type', 'is_active')
                }),
            )
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # Editing existing instance
            return readonly_fields + ('image_choice', 'existing_image')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if form.cleaned_data['image_choice'] == form.USE_EXISTING:
            existing_image_name = form.cleaned_data['existing_image']
            obj.sign_image = existing_image_name
        super().save_model(request, obj, form, change)

    def image_preview(self, obj):
        return obj.image_preview()
    image_preview.short_description = 'Preview'
    image_preview.allow_tags = True


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm
    list_display = ('question_preview', 'display_choices', 'correct_choice_display', 'order')
    list_editable = ('order',)
    list_filter = ('correct_choice',)

    class Media:
        css = {
            'all': ('admin/css/admin_custom_styles.css',)
        }
        js = ('admin/js/custom_admin.js',)

    fieldsets = (
        (None, {
            'fields': ('question_text', 'question_sign')
        }),
        ('Choice 1', {
            'fields': ('choice1_text', 'choice1_sign'),
        }),
        ('Choice 2', {
            'fields': ('choice2_text', 'choice2_sign'),
        }),
        ('Choice 3', {
            'fields': ('choice3_text', 'choice3_sign'),
        }),
        ('Choice 4', {
            'fields': ('choice4_text', 'choice4_sign'),
        }),
        (None, {
            'fields': ('order', 'correct_choice')
        }),
    )

    def question_preview(self, obj):
        """Display a preview of the question text."""
        image_url = obj.question_sign.sign_image.url if obj.question_sign else ""
        return format_html(f'{obj.question_text[:100]}<br><img src="{image_url}" height="50"/>')
    question_preview.short_description = 'Question'

    def display_choices(self, obj):
        """Display all choices in the admin list view."""
        choices = []
        for i in range(1, 5):
            text = getattr(obj, f'choice{i}_text')
            sign = getattr(obj, f'choice{i}_sign')

            if text:
                choices.append(f"{i}: {text}")
            elif sign:
                choices.append(f"{i}: <img src='{sign.sign_image.url}' height='50' />")
        return format_html("<br>".join(choices))
    display_choices.short_description = 'Choices'

    def correct_choice_display(self, obj):
        """Highlight the correct choice."""
        correct_num = obj.correct_choice
        text = getattr(obj, f'choice{correct_num}_text')
        sign = getattr(obj, f'choice{correct_num}_sign')

        if text:
            return f"✓ {text}"
        elif sign:
            return format_html(f"✓ <img src='{sign.sign_image.url}' height='50' />")
        return "-"
    correct_choice_display.short_description = 'Correct Answer'

@admin.register(ExamTypes)
class Admin(admin.ModelAdmin):
    list_display = ['name',]
    


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    form = ExamForm
    list_display = ('exam_type', 'question_count', 'created_at', 'updated_at')
    search_fields = ('exam_type',)
    filter_horizontal = ('questions',)

    def question_count(self, obj):
        return obj.questions.count()


@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'score','started_at', 'completed_at')
    search_fields = ('user__email', 'exam__exam_type')
    list_filter = ('completed_at',)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('plan',)
    search_fields = ('plan',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'price', 'active_subscription', 'expires_at')
    search_fields = ('user__email', 'plan__plan')
    ordering = ('expires_at',)


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
    list_display = ('exam', 'scheduled_datetime','updated_datetime', 'is_published')
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

