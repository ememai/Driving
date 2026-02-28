"""
Celery configuration for Kigali Driving School
This module sets up Celery for handling background tasks asynchronously.
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mwami.settings')

app = Celery('mwami')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'check-subscription-expiry': {
        'task': 'app.tasks.check_subscription_expiry',
        'schedule': crontab(hour=0, minute=0),  # Run at midnight daily
    },
    'send-scheduled-exams-notification': {
        'task': 'app.tasks.send_scheduled_exams_notification',
        'schedule': crontab(hour='*/2'),  # Run every 2 hours
    },
    'cleanup-old-exam-data': {
        'task': 'app.tasks.cleanup_old_data',
        'schedule': crontab(day_of_week=0, hour=2),  # Run weekly on Sunday at 2 AM
    },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
