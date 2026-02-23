from django.apps import AppConfig
from django.conf import settings


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def ready(self):
        from . import signals  # Import signals to register receivers
        if settings.DEBUG:
            from . import scheduler
            scheduler.start()
