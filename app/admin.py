from django.contrib import admin, messages
from .models import *
from .forms import *
from django.shortcuts import redirect

from django.urls import reverse, path
from django.utils.html import format_html
from django.utils import timezone
from django.contrib.admin import AdminSite

from django.db.models import Count
from django.utils.timezone import now, make_aware
from datetime import timedelta, datetime
from django.utils.timezone import localtime
# Register your models here.
class SubscriptionInline(admin.StackedInline):  # or TabularInline
    
    model = Subscription
    can_delete = True
    extra = 0
    readonly_fields = ('active_subscription','updated_at', 'expires_at', 'started_at')

  
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    inlines = [SubscriptionInline]
    list_display = ('name', 'contact','is_subscribed','subscription_expires_at','whatsapp_consent','whatsapp_number','date_joined', 'otp_verified')
    search_fields = ('name', 'email', 'phone_number')
    list_filter = ('date_joined',)

    @admin.display(description='Contact')
    def contact(self, obj):
        if obj.phone_number and obj.email:
            return format_html(f"Phone: {obj.phone_number}<br>Email: {obj.email}")
        elif obj.phone_number:
            return f"Phone: {obj.phone_number}"
        elif obj.email:
            return f"Email: {obj.email}"
        return "No contact info"

    @admin.display(description='Subscription Ends')
    def subscription_expires_at(self, obj):
        if hasattr(obj, 'subscription') and obj.subscription.expires_at:
            return localtime(obj.subscription.expires_at).strftime("%d,%m %Y Saa %H:%M")
        return '❌'


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('plan', 'price',  'delta_display')
    list_editable = ('price', )
    search_fields = ('plan',)
    actions = ['activate_subscriptions']
    ordering = ('price',)

    def delta_display(self, obj):
        if obj.delta_hours:
            return f"{obj.delta_hours} hours"
        if obj.delta_days:
            return f"{obj.delta_days} days"
        return "-"
    delta_display.short_description = "Delta"

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    form = SubscriptionForm
    list_display = ('user', 'plan_price', 'otp_summary', 'subscription_timing', 'is_active', 'renew_subscription', 'end_subscription')
    readonly_fields = ('started_at', 'expires_at', 'otp_code', 'otp_created_at', 'otp_verified') 
    
    list_filter = ('super_subscription', 'plan')
    search_fields = ('user__name', 'user__email', 'user__phone_number')
    ordering = ('-otp_created_at', '-updated_at', '-started_at', '-price',)
    
    class Media: 
        css = {'all': ('admin/css/admin_custom_styles.css',)}
    
    fieldsets = (
        (None, {
            "fields": ('user', 'plan', 'updated'),
        }),
        ('Super Subscription', {
            'fields': ('super_subscription', 'price', 'delta_hours', 'delta_days'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if change:
            obj.renew
        super().save_model(request, obj, form, change)
        if not change and not obj.otp_code:
            obj.generate_otp()

    @admin.display(description='Plan')
    def plan_price(self, obj):
        if obj.super_subscription:
            return format_html('<div style="white-space:normal !important; min-width:8rem;">Super</div>')
        if obj.plan is None:
            return "None"
        price_str = f"{obj.plan.price:,} RWF" if obj.plan.price is not None else "-"
        return format_html(
            '<div style="white-space:normal !important; min-width:5rem;">{}<br><span style="color:gray; font-size:90%">{}</span></div>',
            obj.plan.plan,
            price_str,
        )

    @admin.display(description='OTP Info')
    def otp_summary(self, obj):
        if not obj.otp_code:
            return format_html('<div style="white-space:normal !important; min-width:8rem;">—</div>')
        
        created = localtime(obj.otp_created_at).strftime("%d-%m %H:%M") if obj.otp_created_at else "—"
        expires = localtime(obj.otp_expires_at).strftime("%d-%m %H:%M") if obj.otp_expires_at else "—"
        status = format_html('<i class="fas fa-circle" style="color:green;"></i>') if obj.otp_verified else format_html('<i class="fas fa-circle" style="color:orange;"></i>')
        
        return format_html(
            '<div style="white-space:normal !important; min-width:8rem; font-size:90%; line-height:1.4;">'
            '<strong>{} </strong>{}<br>'
            '<span style="color:gray;">Created: {}</span><br>'
            '<span style="color:gray;">Expires: {}</span></div>',
            status,
            obj.otp_code,
            created,
            expires,
        )

    @admin.display(description='Subscription Timing')
    def subscription_timing(self, obj):
        started = localtime(obj.started_at).strftime("%d-%m %H:%M") if obj.started_at else "—"
        updated_at = localtime(obj.updated_at).strftime("%d-%m %H:%M") if obj.updated else "Not updated"
        expires = localtime(obj.expires_at).strftime("%d-%m %H:%M") if obj.expires_at else "—"
        updated_indicator = format_html('<i class="fa-solid fa-thumbs-up"></i>') if obj.updated else format_html('<i class="fa-solid fa-thumbs-down"></i>')
        
        return format_html(
            '<div style="white-space:normal !important; min-width:10rem; font-size:90%; line-height:1.5;">'
            '<span>Started: </span><span style="color:gray;">{}</span><br>'
            'Updated: <span style="color:#007bff;">{}</span><br>'
            'Updated_at: <span style="color:gray;">{}</span><br>'
            'Expires: <span style="color:gray;">{}</span></div>',
            started,
            updated_indicator,
            updated_at,
            expires,
        )

    @admin.display(description='Status')
    def is_active(self, obj):
        if obj.active_subscription:
            return format_html('<div style="text-align: center; width: 100%;">Active</div>')
        elif obj.expires_at and obj.expires_at < timezone.now():
            return format_html('<div style="text-align: center; width: 100%; color: red;">Expired</div>')
        elif obj.otp_code and not obj.otp_verified:
            return format_html('<div style="text-align: center; width: 100%; color: orange;"><i class="fas fa-circle" style="color:orange;"></i></div>')
        else:
            return format_html('<div style="text-align: center; width: 100%; color: gray;">Inactive</div>')

    def renew_subscription(self, obj):
        if not obj.super_subscription and obj.plan:
            return format_html(
                '<a class="btn btn-success d-flex align-items-center" href="{}" onclick="return confirm(\'Are you sure you want to renew subscription for {}?\')"><i class="fas fa-sync-alt mx-1"></i><span> Renew</span></a>',
                f"/admin/app/subscription/{obj.pk}/renew/",
                obj.user.name
            )
        return "-"
    renew_subscription.short_description = 'Renew'

    def end_subscription(self, obj):        
        if obj.user.has_ended_subscription:
            return format_html('<span class="text-red">❌ Ended</span>')
        
        return format_html(
            '<a class="btn btn-danger d-flex align-items-center" href="{}" onclick="return confirm(\'Are you sure you want to end subscription for {}? This action cannot be undone.\')"><i class="fa-solid fa-stop mx-1"></i><span> End</span></a>',
            f"/admin/app/subscription/{obj.pk}/end/",
            obj.user.name
        )
    end_subscription.short_description = 'End'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:subscription_id>/renew/', self.admin_site.admin_view(self.process_renew), name='subscription-renew'),
            path('<int:subscription_id>/end/', self.admin_site.admin_view(self.process_end), name='subscription-end'),
        ]
        return custom_urls + urls

    def process_renew(self, request, subscription_id):
        subscription = self.get_object(request, subscription_id)
        if subscription and subscription.plan:
            subscription.renew
            subscription.price = subscription.plan.price
            delta = subscription.plan.get_delta()
            if delta:
                subscription.updated = True
                subscription.updated_at = timezone.now()
                subscription.save()
                self.message_user(request, f"Subscription for {subscription.user} successfully renewed!", messages.SUCCESS)
            else:
                self.message_user(request, "No valid duration set for plan.", messages.ERROR)
        else:
            self.message_user(request, "Cannot renew: missing plan.", messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def process_end(self, request, subscription_id):
        subscription = self.get_object(request, subscription_id)
        if subscription:
            subscription.updated = False
            subscription.super_subscription = False
            subscription.otp_verified = True
            subscription.delta_hours = 0
            subscription.delta_days = 0
            subscription.expires_at = timezone.now()
            subscription.save()
            self.message_user(request, f"Subscription for {subscription.user} successfully ended!", messages.SUCCESS)
        else:
            self.message_user(request, "Subscription not found.", messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))


    # def save_model(self, request, obj, form, change):
    #     existing = Subscription.objects.filter(user=obj.user).first()

    #     if existing and not change:
    #         # If trying to add a new subscription but one exists, update it instead
    #         existing.plan = obj.plan
    #         existing.super_subscription = obj.super_subscription
    #         existing.price = obj.price
    #         existing.phone_number = obj.phone_number
    #         existing.transaction_id = obj.transaction_id
    #         existing.delta_days = obj.delta_days
    #         existing.delta_hours = obj.delta_hours
    #         existing.updated = True
    #         existing.updated_at = timezone.now()

    #         # Force-save to apply new expiration logic
    #         existing.save()
    #     else:
    #         # New or updated normally
    #         super().save_model(request, obj, form, change)

@admin.register(PaymentConfirm)
class PaymentConfirmAdmin(admin.ModelAdmin):
    list_display = ('user', 'payeer_name', 'phone_number', 'plan', 'time', 'whatsapp_number')
    search_fields = ('user__name', 'payeer_name', 'phone_number')
    list_filter = ('plan', 'time')
    ordering = ('-time',)

@admin.register(SignType)
class SignTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    form = RoadSignAdminForm

    class Media:
        js = ('admin/js/roadsign_admin.js',)
        css = {'all': ('admin/css/roadsign_admin.css',)}

    list_display = ('definition', 'image_preview', 'type', 'uploaded_at', 'date_updated')
    search_fields = ('definition', 'type__name')
    list_filter = ('type', 'is_active')
    readonly_fields = ('image_preview', 'uploaded_at', 'date_updated')

    def get_fieldsets(self, request, obj=None):
        if obj:  # Change form
            fieldsets = (
                ('Image Management', {
                    'fields': ('image_preview', 'image_choice', 'existing_image', 'sign_image')
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
                    'fields': ('image_choice', 'existing_image', 'sign_image')
                }),
                (None, {
                    'fields': ('definition', 'type', 'is_active')
                }),
            )
        return fieldsets

    # def get_readonly_fields(self, request, obj=None):
    #     readonly_fields = super().get_readonly_fields(request, obj)
    #     if obj:  # Editing existing instance
    #         return readonly_fields + ('image_choice', 'existing_image')
    #     return readonly_fields

    
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
    list_display = ('question_preview', 'display_choices', 'correct_choice_display', 'order','question_type')
    list_per_page = 10
    list_editable = ('order','question_type')
    list_filter = ('question_type','correct_choice')
    # list_display_links = ('correct_choice_display',)
    search_fields = ('question_text', 'order', 'question_type__name')
    ordering = ('order',)

    class Media:
        css = {
            'all': ('admin/css/admin_custom_styles.css',)
        }
        js = ('admin/js/custom_admin.js',)
    readonly_fields = (
    'question_image_preview',
    'choice1_image_preview',
    'choice2_image_preview',
    'choice3_image_preview',
    'choice4_image_preview',
        )


    def get_fieldsets(self, request, obj=None):
        if obj:
            return (
                (None, {
                    'fields': ('question_text', 'question_image_preview', 'question_sign')
                }),
                ('Properties', {
                    'fields': ('order', 'correct_choice', 'question_type')
                }),
                ('Choice 1', {
                    'fields': ('choice1_text', 'choice1_image_preview', 'choice1_sign'),
                }),
                ('Choice 2', {
                    'fields': ('choice2_text', 'choice2_image_preview', 'choice2_sign'),
                }),
                ('Choice 3', {
                    'fields': ('choice3_text', 'choice3_image_preview', 'choice3_sign'),
                }),
                ('Choice 4', {
                    'fields': ('choice4_text', 'choice4_image_preview', 'choice4_sign'),
                }),
            )
        else:
            # Add form: no preview
            return (
                (None, {
                    'fields': ('question_text', 'question_sign')
                }),
                ('Properties', {
                    'fields': ('order', 'correct_choice', 'question_type')
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
            )

    def question_image_preview(self, obj):
        if obj.question_sign:
            return format_html('<img src="{}" height="100"/>', obj.question_sign.sign_image.url)
        return "No image"
    question_image_preview.short_description = "Question Image"

    def choice1_image_preview(self, obj):
        if obj.choice1_sign:
            return format_html('<img src="{}" height="100"/>', obj.choice1_sign.sign_image.url)
        return "No image"
    choice1_image_preview.short_description = "Choice 1 Image"

    def choice2_image_preview(self, obj):
        if obj.choice2_sign:
            return format_html('<img src="{}" height="100"/>', obj.choice2_sign.sign_image.url)
        return "No image"
    choice2_image_preview.short_description = "Choice 2 Image"

    def choice3_image_preview(self, obj):
        if obj.choice3_sign:
            return format_html('<img src="{}" height="100"/>', obj.choice3_sign.sign_image.url)
        return "No image"
    choice3_image_preview.short_description = "Choice 3 Image"

    def choice4_image_preview(self, obj):
        if obj.choice4_sign:
            return format_html('<img src="{}" height="100"/>', obj.choice4_sign.sign_image.url)
        return "No image"
    choice4_image_preview.short_description = "Choice 4 Image"



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

@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ['name',]
    search_fields = ['name']
    ordering = ['order']

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('exam_type','schedule_hour', 'total_questions','for_scheduling', 'created_at', 'updated_at')

    ordering = ('-created_at',)
    list_editable = ('for_scheduling',)
    list_filter = ('exam_type', 'for_scheduling', )
    list_per_page = 11
    search_fields = ('exam_type',)
    filter_horizontal = ('questions',)
    # Use different forms for add vs change
    def get_form(self, request, obj=None, **kwargs):
        if obj is None:  # Creating new exam
            return ExamCreationForm
        return super().get_form(request, obj, **kwargs)

    # Customize fieldsets only for creation
    def get_fieldsets(self, request, obj=None):
        if obj:  # Editing existing exam - use default
            return super().get_fieldsets(request, obj)

        # Creation fieldsets
        fieldsets = [
            ('Properties', {
                'fields': ('exam_type','schedule_hour', 'duration', 'is_active', 'for_scheduling')
            })
        ]

        # Add fieldsets for each question type
        question_types = ExamType.objects.annotate(
            num_questions=Count('question')
        ).filter(num_questions__gt=0).order_by('order')

        for q_type in question_types:
            fieldsets.append((
                f'{q_type.name} Questions',
                {
                    'fields': [f'questions_{q_type.id}'],
                    'classes': ('collapse',),
                    'description': f"Select {q_type.name} questions for this exam."
                }
            ))

        return fieldsets

    # Only show our custom fields during creation
    def get_fields(self, request, obj=None):
        if obj:  # Editing existing exam
            return super().get_fields(request, obj)

        fields = ['exam_type','schedule_hour', 'duration', 'is_active', 'for_scheduling']

        question_types = ExamType.objects.annotate(
            num_questions=Count('question')
        ).filter(num_questions__gt=0).order_by('order')

        for q_type in question_types:
            fields.append(f'questions_{q_type.id}')

        return fields

    class Media:
        css = {
            'all': ('admin/css/exam_creation.css',)
        }


@admin.register(TodayExam)
class TodayExamAdmin(admin.ModelAdmin):
    list_display = ('exam__exam_type','exam__schedule_hour', 'exam__for_scheduling', 'exam__created_at', 'exam__updated_at')

    ordering = ('exam__schedule_hour', '-exam__created_at',)
    list_per_page = 11
    form = ScheduleExamForm


    def get_queryset(self, request):
        today = now().date()
        start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        return super().get_queryset(request).filter(
            exam__for_scheduling=True,
            scheduled_datetime__range=(start, end)
        )


@admin.register(UnscheduledExam)
class UnscheduledExamsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'schedule_hour', 'exam_type', 'is_active']
    def get_queryset(self, request):
        return super().get_queryset(request).filter(for_scheduling=False)


@admin.register(UserExam)
class UserExamAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'marks','started_at', 'completed_at')
    search_fields = ('user__email', 'exam__exam_type__name','user__name')
    ordering = ('-completed_at',)
    list_filter = ('completed_at',)
    
    @admin.display(description='Pts')
    def marks(self, obj):
        if obj.score is not None:
            return f"{obj.score} / {obj.exam.total_questions}"
        return "-"
    

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    search_fields = ('user__email', 'transaction_id')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'method','message', 'created_at')
    search_fields = ('name', 'email')

    @admin.display(description='Contact Method')
    def method(self, obj):
        if obj.whatsapp_number:
            return f"Phone: {obj.whatsapp_number}"
        elif obj.email:
            return f"Email: {obj.email}"
        return "Unknown"
@admin.action(description='Activate selected subscriptions')
def activate_subscriptions(modeladmin, request, queryset):
    queryset.update(active_subscription=True)


@admin.register(ScheduledExam)
class ScheduledExamAdmin(admin.ModelAdmin):
    form = ScheduleExamForm
    list_display = ('exam', 'scheduled_datetime','updated_datetime', 'is_published')
    ordering = ('-scheduled_datetime',)
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


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_at')
    prepopulated_fields = {'slug': ('title',)}  # Optional: Auto-fill slug