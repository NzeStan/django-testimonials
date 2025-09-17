import logging
import uuid
import os
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from .conf import app_settings
from .exceptions import TestimonialMediaError

# Set up logging
logger = logging.getLogger("testimonials")


def get_unique_slug(model_instance, slug_field, max_length=50):
    """
    Generate a unique slug for a model instance.

    Args:
        model_instance: The model instance to generate a slug for
        slug_field: The field name to use for creating the slug
        max_length: Maximum length of the slug
    """
    slug_source = getattr(model_instance, slug_field, "")
    if not slug_source:
        # fallback if source field empty
        slug_source = f"{getattr(model_instance, 'author_name', 'testimonial')}-{timezone.now().timestamp()}"

    slug = slugify(slug_source)[:max_length]
    unique_slug = slug

    model_class = model_instance.__class__
    extension = 1

    # exclude self on updates
    qs = model_class.objects.exclude(pk=model_instance.pk)

    while qs.filter(slug=unique_slug).exists():
        extension_str = f"-{extension}"
        unique_slug = f"{slug[:max_length - len(extension_str)]}{extension_str}"
        extension += 1

    return unique_slug


def validate_rating(value, max_rating=None):
    """
    Validate a rating value.
    
    Args:
        value: The rating value to validate
        max_rating: The maximum allowed rating value
        
    Raises:
        ValidationError: If the rating is invalid
    """
    if max_rating is None:
        max_rating = app_settings.MAX_RATING
        
    if not isinstance(value, (int, float)):
        raise ValidationError(_("Rating must be a number"))
    
    if value < 1 or value > max_rating:
        raise ValidationError(_(f"Rating must be between 1 and {max_rating}"))


def generate_upload_path(instance, filename):
    """
    Generate a unique upload path for testimonial media files.
    
    Args:
        instance: The model instance the file is attached to
        filename: The original filename
        
    Returns:
        A unique file path
    """
    # Get file extension
    ext = filename.split('.')[-1].lower()
    
    # Generate a UUID filename
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # Get the testimonial ID
    testimonial_id = getattr(instance, "testimonial_id", None)
    if testimonial_id:
        # If attached to a testimonial, use its ID in the path
        return os.path.join(app_settings.MEDIA_UPLOAD_PATH, str(testimonial_id), unique_filename)
    else:
        # Otherwise, use a generic path
        return os.path.join(app_settings.MEDIA_UPLOAD_PATH, "misc", unique_filename)


def get_file_type(file_obj):
    """
    Determine the type of a file based on its extension.
    
    Args:
        file_obj: A file-like object or path
        
    Returns:
        The media type as a string
    """
    from .constants import TestimonialMediaType

    if hasattr(file_obj, "name"):
        filename = file_obj.name
    else:
        filename = str(file_obj)
    
    ext = filename.split('.')[-1].lower()
    
    # Define file types by extension
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
    video_extensions = ['mp4', 'webm', 'mov', 'avi']
    audio_extensions = ['mp3', 'wav', 'ogg']
    document_extensions = ['pdf', 'doc', 'docx', 'txt']
    
    if ext in image_extensions:
        return TestimonialMediaType.IMAGE
    elif ext in video_extensions:
        return TestimonialMediaType.VIDEO
    elif ext in audio_extensions:
        return TestimonialMediaType.AUDIO
    elif ext in document_extensions:
        return TestimonialMediaType.DOCUMENT
    else:
        # Default to generic document type
        logger.warning(f"Unknown file extension for testimonial media: {ext}")
        return TestimonialMediaType.DOCUMENT


def log_testimonial_action(testimonial, action, user=None, notes=None):
    """
    Log a testimonial action for auditing purposes.
    
    Args:
        testimonial: The testimonial instance
        action: The action being performed
        user: The user performing the action
        notes: Any additional notes
    """
    user_str = f"User: {user}" if user else "System"
    testimonial_id = getattr(testimonial, "id", "unknown")
    
    logger.info(
        f"Testimonial Action: {action} | "
        f"Testimonial ID: {testimonial_id} | "
        f"{user_str} | "
        f"Notes: {notes or 'None'}"
    )