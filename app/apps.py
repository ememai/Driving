from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def ready(self):
        from . import signals
        import threading
        
        # Start scheduler in background thread to prevent blocking startup
        def start_scheduler():
            try:
                from . import scheduler
                scheduler.start()
            except Exception as e:
                logger.error(f"Scheduler failed to start: {e}", exc_info=True)
        
        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()
