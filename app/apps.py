from django.apps import AppConfig
from django.conf import settings


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def ready(self):
        from . import signals
        # Scheduler disabled for now - causes startup hang
        # TODO: Re-enable with proper threading in background
