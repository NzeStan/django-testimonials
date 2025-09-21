from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TestimonialsSettings:
    """
    Settings class for the testimonials app. This class provides default settings
    and allows for customization through Django settings.
    """

    @property
    def USE_UUID(self):
        """
        Use UUID as primary key for Testimonial models instead of auto-incrementing IDs.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_USE_UUID", False)

    @property
    def MAX_RATING(self):
        """
        Maximum rating value for testimonials.
        Default is 5.
        """
        return getattr(settings, "TESTIMONIALS_MAX_RATING", 5)

    @property
    def REQUIRE_APPROVAL(self):
        """
        Whether testimonials require approval before being published.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_REQUIRE_APPROVAL", True)

    @property
    def ALLOW_ANONYMOUS(self):
        """
        Whether anonymous testimonials are allowed.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_ALLOW_ANONYMOUS", False)

    @property
    def USER_MODEL(self):
        """
        User model to use for testimonial authors.
        Default is settings.AUTH_USER_MODEL.
        """
        return getattr(settings, "TESTIMONIALS_USER_MODEL", settings.AUTH_USER_MODEL)

    @property
    def MODERATION_ROLES(self):
        """
        List of roles that can moderate testimonials.
        Default is empty list (only superusers).
        """
        return getattr(settings, "TESTIMONIALS_MODERATION_ROLES", [])

    @property
    def ENABLE_CATEGORIES(self):
        """
        Whether to enable categorization of testimonials.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_ENABLE_CATEGORIES", True)

    @property
    def ENABLE_MEDIA(self):
        """
        Whether to enable media attachments for testimonials.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_ENABLE_MEDIA", True)

    @property
    def MEDIA_UPLOAD_PATH(self):
        """
        Path to upload testimonial media.
        Default is 'media_testimonials/media/'.
        """
        return getattr(settings, "TESTIMONIALS_MEDIA_UPLOAD_PATH", "media_testimonials/media/")

    @property
    def NOTIFICATION_EMAIL(self):
        """
        Email address to send testimonial notifications to.
        Default is None.
        """
        return getattr(settings, "TESTIMONIALS_NOTIFICATION_EMAIL", None)
    
    @property
    def PAGINATION_SIZE(self):
        """
        Default pagination size for testimonial listings.
        Default is 10.
        """
        return getattr(settings, "TESTIMONIALS_PAGINATION_SIZE", 10)
    
    @property
    def CUSTOM_MODEL(self):
        """
        Custom model to use instead of the default Testimonial model.
        Default is None.
        """
        return getattr(settings, "TESTIMONIALS_CUSTOM_MODEL", None)
    
    @property
    def TESTIMONIAL_STATUSES(self):
        """
        Custom statuses for testimonials.
        Default is None (use the default statuses).
        """
        return getattr(settings, "TESTIMONIALS_CUSTOM_STATUSES", None)
    
    @property
    def ENABLE_DASHBOARD(self):
        """
        Expose dashboard endpoint.
        Default is False.
        """
        return getattr(settings, 'TESTIMONIALS_ENABLE_DASHBOARD', False)

    
    @property
    def USE_CELERY(self):
        """
        Whether to use Celery for background tasks (email notifications, media processing).
        Requires Celery to be installed and configured.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_USE_CELERY", False)
    
    @property
    def USE_REDIS_CACHE(self):
        """
        Whether to use Redis for caching queries and data.
        Requires Redis to be installed and configured.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_USE_REDIS_CACHE", False)
    
    @property
    def CELERY_BROKER_URL(self):
        """
        Celery broker URL for testimonials tasks.
        Default uses Django's CELERY_BROKER_URL or 'redis://localhost:6379/0'.
        """
        return getattr(
            settings, 
            "TESTIMONIALS_CELERY_BROKER_URL",
            getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0")
        )
    
    @property
    def REDIS_CACHE_URL(self):
        """
        Redis cache URL for testimonials caching.
        Default uses Django's CACHES['default'] or 'redis://localhost:6379/1'.
        """
        return getattr(
            settings,
            "TESTIMONIALS_REDIS_CACHE_URL",
            "redis://localhost:6379/1"
        )
    
    @property
    def CACHE_TIMEOUT(self):
        """
        Default cache timeout in seconds.
        Default is 900 seconds (15 minutes).
        """
        return getattr(settings, "TESTIMONIALS_CACHE_TIMEOUT", 900)
    
    @property
    def CACHE_KEY_PREFIX(self):
        """
        Prefix for all cache keys.
        Default is 'testimonials'.
        """
        return getattr(settings, "TESTIMONIALS_CACHE_KEY_PREFIX", "testimonials")
    
    @property
    def ENABLE_THUMBNAILS(self):
        """
        Whether to automatically generate thumbnails for image uploads.
        Requires Pillow and either Celery (for async) or synchronous processing.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_ENABLE_THUMBNAILS", True)
    
    @property
    def THUMBNAIL_SIZES(self):
        """
        Thumbnail sizes to generate for images.
        Format: {'size_name': (width, height)}
        Default creates small, medium thumbnails.
        """
        return getattr(settings, "TESTIMONIALS_THUMBNAIL_SIZES", {
            'small': (150, 150),
            'medium': (300, 300),
        })
    
    @property
    def MAX_FILE_SIZE(self):
        """
        Maximum file size for media uploads in bytes.
        Default is 10MB.
        """
        return getattr(settings, "TESTIMONIALS_MAX_FILE_SIZE", 10 * 1024 * 1024)
    
    @property
    def ALLOWED_FILE_EXTENSIONS(self):
        """
        Allowed file extensions for media uploads.
        Default includes common image, video, audio, and document formats.
        """
        return getattr(settings, "TESTIMONIALS_ALLOWED_FILE_EXTENSIONS", [
            # Images
            'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
            # Videos
            'mp4', 'webm', 'mov', 'avi', 'mkv',
            # Audio
            'mp3', 'wav', 'ogg', 'aac', 'flac',
            # Documents
            'pdf', 'doc', 'docx', 'txt', 'rtf'
        ])
    
    @property
    def EMAIL_RATE_LIMIT(self):
        """
        Rate limit for email notifications (emails per minute).
        Default is 60 emails per minute.
        """
        return getattr(settings, "TESTIMONIALS_EMAIL_RATE_LIMIT", 60)
    
    @property
    def BULK_OPERATION_BATCH_SIZE(self):
        """
        Batch size for bulk operations (approve, reject, etc.).
        Default is 100.
        """
        return getattr(settings, "TESTIMONIALS_BULK_OPERATION_BATCH_SIZE", 100)
    
    @property
    def SEARCH_MIN_LENGTH(self):
        """
        Minimum search query length for full-text search.
        Default is 3 characters.
        """
        return getattr(settings, "TESTIMONIALS_SEARCH_MIN_LENGTH", 3)
    
    @property
    def SEARCH_RESULTS_LIMIT(self):
        """
        Maximum number of search results to return.
        Default is 1000.
        """
        return getattr(settings, "TESTIMONIALS_SEARCH_RESULTS_LIMIT", 1000)


app_settings = TestimonialsSettings()