from django.apps import AppConfig
from django.conf import settings


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    if settings.DEBUG:
        def ready(self):
            from . import scheduler
            scheduler.start()
