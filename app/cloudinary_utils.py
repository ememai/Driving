import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CloudinaryMediaHandler:
    """Utility class for optimized Cloudinary media handling"""

    @staticmethod
    def get_optimized_url(public_id, transformation_preset='thumbnail', secure=True):
        """
        Generate an optimized Cloudinary URL with transformations.

        Args:
            public_id: Cloudinary public ID
            transformation_preset: Key from CLOUDINARY_TRANSFORMATIONS
            secure: Use HTTPS

        Returns:
            Optimized Cloudinary URL
        """
        if not public_id:
            return None

        transformations = settings.CLOUDINARY_TRANSFORMATIONS.get(
            transformation_preset,
            {}
        )

        url, _ = cloudinary_url(
            public_id,
            secure=secure,
            **transformations,
            **settings.CLOUDINARY_CDN_SETTINGS,
        )
        return url

    @staticmethod
    def upload_file(file_obj, resource_type='auto', folder='driving-school'):
        """
        Upload a file to Cloudinary with optimization.

        Args:
            file_obj: Django UploadedFile object
            resource_type: 'image', 'video', 'raw', or 'auto'
            folder: Cloudinary folder path

        Returns:
            dict with upload result or None on failure
        """
        try:
            upload_settings = settings.CLOUDINARY_UPLOAD_SETTINGS.copy()
            upload_settings['folder'] = folder
            upload_settings['resource_type'] = resource_type

            result = cloudinary.uploader.upload(
                file_obj,
                **upload_settings
            )
            logger.info(f"File uploaded to Cloudinary: {result.get('public_id')}")
            return result
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}")
            return None

    @staticmethod
    def delete_file(public_id, resource_type='image'):
        """
        Delete a file from Cloudinary.

        Args:
            public_id: Cloudinary public ID
            resource_type: 'image', 'video', or 'raw'

        Returns:
            bool: True if successful
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type
            )
            logger.info(f"File deleted from Cloudinary: {public_id}")
            return result.get('result') == 'ok'
        except Exception as e:
            logger.error(f"Cloudinary delete failed: {str(e)}")
            return False

    @staticmethod
    def get_responsive_image_srcset(public_id, widths=None):
        """
        Generate responsive image srcset for different screen sizes.

        Args:
            public_id: Cloudinary public ID
            widths: List of widths to generate

        Returns:
            dict with srcset and sizes attributes
        """
        if widths is None:
            widths = [300, 600, 900]

        srcset_list = []
        for width in widths:
            url, _ = cloudinary_url(
                public_id,
                width=width,
                crop='scale',
                quality='auto',
                fetch_format='auto',
                secure=True,
            )
            srcset_list.append(f"{url} {width}w")

        return {
            'srcset': ', '.join(srcset_list),
            'sizes': '(max-width: 600px) 100vw, (max-width: 900px) 80vw, 60vw',
        }
