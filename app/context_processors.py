# app/context_processors.py
from django.utils import timezone
from .models import *
from .utils import *

def unverified_subscription_context(request):
    subscription = get_unverified_subscription(request.user)
    return {'unverified_subscription': subscription}

def exams_slider_context(request):
    now = timezone.localtime(timezone.now())
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    return {
        'exams_scheduled': ScheduledExam.objects.filter(
            scheduled_datetime__range=(start_of_day, end_of_day)
        ),
        # 'current_time': now
    }