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
        return getattr(settings, "TESTIMONIALS_USER_MODEL", settings.AUTH_USER_MODEL) ##############

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
        return getattr(settings, "TESTIMONIALS_ENABLE_CATEGORIES", True) #############

    @property
    def ENABLE_MEDIA(self):
        """
        Whether to enable media attachments for testimonials.
        Default is True.
        """
        return getattr(settings, "TESTIMONIALS_ENABLE_MEDIA", True) ##############

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
        return getattr(settings, "TESTIMONIALS_CUSTOM_MODEL", None) ##########
    
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


app_settings = TestimonialsSettings()