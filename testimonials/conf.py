# testimonials/conf.py

from django.conf import settings


class AppSettings:
    """
    Settings configuration for the django-testimonials package.
    All settings can be overridden in Django's settings.py with the TESTIMONIALS_ prefix.
    """

    # ====== UUID & PRIMARY KEY SETTINGS ======
    
    @property
    def USE_UUID(self):
        """
        Use UUID as primary key for Testimonial models instead of auto-incrementing IDs.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_USE_UUID", False)

    # ====== RATING SETTINGS ======

    @property
    def MAX_RATING(self):
        """
        Maximum rating value for testimonials.
        Default is 5.
        """
        return getattr(settings, "TESTIMONIALS_MAX_RATING", 5)
    
    @property
    def MIN_RATING(self):
        """
        Minimum rating value.
        Default is 1.
        """
        return getattr(settings, "TESTIMONIALS_MIN_RATING", 1)

    # ====== CONTENT LENGTH SETTINGS ======
    
    @property
    def MIN_TESTIMONIAL_LENGTH(self):
        """
        Minimum length for testimonial content in characters.
        Default is 10 characters.
        """
        return getattr(settings, "TESTIMONIALS_MIN_CONTENT_LENGTH", 10)

    @property
    def MAX_TESTIMONIAL_LENGTH(self):
        """
        Maximum length for testimonial content in characters.
        Default is 5000 characters.
        """
        return getattr(settings, "TESTIMONIALS_MAX_CONTENT_LENGTH", 5000)
    
    # ====== CONTENT VALIDATION SETTINGS ======
    
    @property
    def VALIDATE_CONTENT_QUALITY(self):
        """
        Whether to validate content quality (no spam, etc.).
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_VALIDATE_CONTENT_QUALITY", True)

    @property
    def FORBIDDEN_WORDS(self):
        """
        List of forbidden words in testimonial content.
        These words will trigger validation errors if found in testimonial content.
        Default includes common spam and test keywords.
        
        You can override this in settings.py:
        TESTIMONIALS_FORBIDDEN_WORDS = ['spam', 'fake', 'your_custom_words']
        """
        return getattr(settings, "TESTIMONIALS_FORBIDDEN_WORDS", [
            # Spam keywords
            'spam', 'scam', 'fraud', 'phishing', 'viagra', 'cialis',
            'pharmacy', 'pills', 'lottery', 'winner', 'congratulations',
            'click here', 'buy now', 'limited time', 'act now',
            
            # Testing keywords
            'test', 'testing', 'test123', 'asdf', 'qwerty',
            'lorem ipsum', 'dummy', 'sample',
            
            # Fake/bot indicators
            'fake', 'bot', 'automated', 'script', 'generated',
            
            # Offensive placeholder (add more as needed)
            'xxx', 'adult content',
            
            # SEO spam
            'seo', 'backlink', 'link building', 'guest post',
        ])

    # ====== FILE UPLOAD SETTINGS ======

    @property
    def MAX_FILE_SIZE(self):
        """
        Maximum file size for media uploads in bytes.
        Default is 10MB (10 * 1024 * 1024).
        """
        return getattr(settings, "TESTIMONIALS_MAX_FILE_SIZE", 10 * 1024 * 1024)

    @property
    def MAX_AVATAR_SIZE(self):
        """
        Maximum avatar size in bytes.
        Default is 5MB (5 * 1024 * 1024).
        """
        return getattr(settings, "TESTIMONIALS_MAX_AVATAR_SIZE", 5 * 1024 * 1024)

    @property  
    def MAX_IMAGE_WIDTH(self):
        """
        Maximum image width in pixels.
        Default is 2000.
        """
        return getattr(settings, "TESTIMONIALS_MAX_IMAGE_WIDTH", 2000)

    @property
    def MAX_IMAGE_HEIGHT(self):
        """
        Maximum image height in pixels.
        Default is 2000.
        """
        return getattr(settings, "TESTIMONIALS_MAX_IMAGE_HEIGHT", 2000)

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

    # ====== MODERATION & APPROVAL SETTINGS ======

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
        Whether to allow anonymous testimonials.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_ALLOW_ANONYMOUS", True)

    @property
    def USER_MODEL(self):
        """
        User model to use for testimonial authors.
        Default is settings.AUTH_USER_MODEL.
        
        This setting allows you to use a custom user model throughout the testimonials app.
        """
        return getattr(settings, "TESTIMONIALS_USER_MODEL", settings.AUTH_USER_MODEL)

    @property
    def MODERATION_ROLES(self):
        """
        List of group names that can moderate testimonials.
        Users in these groups will have permission to approve, reject, and feature testimonials.
        Default is empty list (only superusers and staff).
        
        Example:
        TESTIMONIALS_MODERATION_ROLES = ['Content Manager', 'Moderator']
        """
        return getattr(settings, "TESTIMONIALS_MODERATION_ROLES", [])

    # ====== FEATURE TOGGLES ======

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
    def ENABLE_DASHBOARD(self):
        """
        Enable the testimonials dashboard with analytics and insights.
        When enabled, adds a dedicated admin dashboard at /testimonials/dashboard/
        Default is False.
        """
        return getattr(settings, 'TESTIMONIALS_ENABLE_DASHBOARD', False)

    # ====== NOTIFICATION SETTINGS ======

    @property
    def NOTIFICATION_EMAIL(self):
        """
        Email address to send testimonial notifications to.
        This is used for admin notifications about new testimonials.
        Default is None.
        """
        return getattr(settings, "TESTIMONIALS_NOTIFICATION_EMAIL", None)

    @property
    def EMAIL_RATE_LIMIT(self):
        """
        Rate limit for email notifications (emails per minute).
        Default is 60 emails per minute.
        """
        return getattr(settings, "TESTIMONIALS_EMAIL_RATE_LIMIT", 60)
    
    # ====== EMAIL NOTIFICATION CONTROLS ======
    
    @property
    def SEND_EMAIL_NOTIFICATIONS(self):
        """
        Whether to send email notifications for testimonial actions.
        This includes approved, rejected, and response emails.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS", False)
    
    @property
    def SEND_ADMIN_NOTIFICATIONS(self):
        """
        Whether to send email notifications to admins for new testimonials.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_SEND_ADMIN_NOTIFICATIONS", False)
    
    @property
    def EMAIL_FROM_NAME(self):
        """
        Name to use in the 'From' field of testimonial emails.
        Default is the SITE_NAME or 'Testimonials'.
        """
        return getattr(
            settings, 
            "TESTIMONIALS_EMAIL_FROM_NAME",
            getattr(settings, "SITE_NAME", "Testimonials")
        )
    
    @property
    def USE_HTML_EMAILS(self):
        """
        Whether to use HTML email templates instead of plain text.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_USE_HTML_EMAILS", True)

    # ====== PAGINATION & DISPLAY SETTINGS ======
    
    @property
    def PAGINATION_SIZE(self):
        """
        Default pagination size for testimonial listings.
        Default is 10.
        """
        return getattr(settings, "TESTIMONIALS_PAGINATION_SIZE", 10)

    # ====== SEARCH SETTINGS ======
    
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
    
    # ====== LOCALIZATION SETTINGS ======
    
    @property
    def DEFAULT_PHONE_REGION(self):
        """
        Default region for phone number validation.
        This is passed to PhoneNumberField(region=...).
        Default is "NG" (Nigeria).
        """
        return getattr(settings, "TESTIMONIALS_DEFAULT_PHONE_REGION", "NG")

    # ====== CELERY & ASYNC SETTINGS ======
    
    @property
    def USE_CELERY(self):
        """
        Whether to use Celery for background tasks (email notifications, media processing).
        Requires Celery to be installed and configured.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_USE_CELERY", False)
    
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

    # ====== REDIS & CACHE SETTINGS ======
    
    @property
    def USE_REDIS_CACHE(self):
        """
        Whether to use Redis for caching queries and data.
        Requires Redis to be installed and configured.
        Default is False.
        """
        return getattr(settings, "TESTIMONIALS_USE_REDIS_CACHE", False)
    
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

    # ====== THUMBNAIL SETTINGS ======

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
        Default creates small, medium, and large thumbnails.
        """
        return getattr(settings, "TESTIMONIALS_THUMBNAIL_SIZES", {
            'small': (150, 150),
            'medium': (300, 300),
            'large': (600, 600),
        })


# Create a single instance to be imported throughout the app
app_settings = AppSettings()