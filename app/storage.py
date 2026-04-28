import os
import logging
from django.core.files.storage import FileSystemStorage
from django.conf import settings

logger = logging.getLogger(__name__)

class PersistentMediaStorage(FileSystemStorage):
    """
    Custom storage backend that ensures files are saved to the persistent volume.
    Handles file uploads with proper error handling and logging.
    """

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = settings.MEDIA_ROOT
        if base_url is None:
            base_url = settings.MEDIA_URL

        # Ensure the directory exists
        os.makedirs(location, exist_ok=True)

        super().__init__(location=location, base_url=base_url)
        logger.info(f"PersistentMediaStorage initialized at {location}")

    def _save(self, name, content):
        """
        Override _save to ensure file is properly written to disk.
        """
        try:
            # Call parent save
            saved_name = super()._save(name, content)

            # Verify file was actually saved
            full_path = self.path(saved_name)
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                logger.info(f"File saved successfully: {saved_name} ({file_size} bytes)")
                return saved_name
            else:
                logger.error(f"File save failed - file not found at {full_path}")
                raise IOError(f"File was not saved to {full_path}")

        except Exception as e:
            logger.error(f"Error saving file {name}: {str(e)}")
            raise

    def delete(self, name):
        """
        Override delete with logging.
        """
        try:
            super().delete(name)
            logger.info(f"File deleted: {name}")
        except Exception as e:
            logger.error(f"Error deleting file {name}: {str(e)}")
            raise
