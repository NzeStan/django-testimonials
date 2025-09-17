from django.utils.translation import gettext_lazy as _


class TestimonialStatus:
    """
    Constants for testimonial statuses.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FEATURED = "featured"
    ARCHIVED = "archived"
    
    CHOICES = (
        (PENDING, _("Pending")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
        (FEATURED, _("Featured")),
        (ARCHIVED, _("Archived")),
    )
    
    DEFAULT = PENDING


class TestimonialSource:
    """
    Constants for testimonial sources.
    """
    WEBSITE = "website"
    MOBILE_APP = "mobile_app"
    EMAIL = "email"
    THIRD_PARTY = "third_party"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"
    
    CHOICES = (
        (WEBSITE, _("Website")),
        (MOBILE_APP, _("Mobile App")),
        (EMAIL, _("Email")),
        (THIRD_PARTY, _("Third Party")),
        (SOCIAL_MEDIA, _("Social Media")),
        (OTHER, _("Other")),
    )
    
    DEFAULT = WEBSITE


class TestimonialMediaType:
    """
    Constants for testimonial media types.
    """
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    
    CHOICES = (
        (IMAGE, _("Image")),
        (VIDEO, _("Video")),
        (AUDIO, _("Audio")),
        (DOCUMENT, _("Document")),
    )