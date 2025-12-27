from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .conf import app_settings
from decimal import Decimal, InvalidOperation
import re


def validate_rating(value):
    """
    Validator for testimonial ratings.
    
    Ensures the rating is between configured min and max values.
    """
    min_rating = app_settings.MIN_RATING
    max_rating = app_settings.MAX_RATING
    
    if not isinstance(value, (int, float)):
        raise ValidationError(_("Rating must be a number."))
    
    # Convert to int if it's a whole number float
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    elif isinstance(value, float):
        raise ValidationError(_("Rating must be a whole number."))
    
    if value < min_rating:
        raise ValidationError(
            _("Rating must be at least %(min_rating)d.") % {'min_rating': min_rating}
        )
        
    if value > max_rating:
        raise ValidationError(
            _("Rating cannot exceed %(max_rating)d.") % {'max_rating': max_rating}
        )
        
    return value

def validate_phone_number(value):
    """
    Basic phone number validation.
    Uses django-phonenumber-field if available, otherwise basic validation.
    """
    if not value:
        return value
        
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', value)
    
    # Check if it's mostly digits (allow + for international)
    if not re.match(r'^\+?\d{10,15}$', cleaned):
        raise ValidationError(
            _("Phone number must be between 10-15 digits.")
        )
    
    return value


def validate_testimonial_content(value):
    """
    Validate testimonial content for minimum/maximum length and other criteria.
    Configurable via app settings.
    """
    
    # Check minimum length
    min_length = app_settings.MIN_TESTIMONIAL_LENGTH
    if value and len(value.strip()) < min_length:
        raise ValidationError(
            _("Testimonial content must be at least %(min_length)d characters long.") % {
                'min_length': min_length
            }
        )
    
    # Check maximum length
    max_length = app_settings.MAX_TESTIMONIAL_LENGTH
    if value and len(value.strip()) > max_length:
        raise ValidationError(
            _("Testimonial content cannot exceed %(max_length)d characters.") % {
                'max_length': max_length
            }
        )
    
    if app_settings.VALIDATE_CONTENT_QUALITY and value:
        # Check for forbidden words - FIX: Check for whole words, not substrings
        forbidden_words = app_settings.FORBIDDEN_WORDS
        value_lower = value.lower()
        
        for word in forbidden_words:
            # Use word boundaries to match whole words only
            # \b ensures we match "test" but not "test" in "testimonial"
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            if re.search(pattern, value_lower):
                raise ValidationError(
                    _("Testimonial content contains inappropriate language.")
                )
        
        # Check for excessive repetition (basic spam detection)
        words = value.split()
        if len(words) > 5 and len(set(words)) / len(words) < 0.3:  # Less than 30% unique words
            raise ValidationError(
                _("Testimonial content appears to contain excessive repetition.")
            )
    
    return value


def create_file_size_validator(max_size_mb=None, file_type="file"):
    """Factory function to create file size validators with custom limits"""
    # Use app_settings if no custom size provided
    if max_size_mb is None:
        max_size_bytes = app_settings.MAX_FILE_SIZE
        max_size_mb = max_size_bytes / (1024 * 1024)
    else:
        max_size_bytes = max_size_mb * 1024 * 1024
    
    def validator(file):
        if file.size > max_size_bytes:
            current_size_mb = file.size / (1024 * 1024)
            raise ValidationError(
                _("%(file_type)s is too large (%(current)0.1f MB). "
                  "Maximum size is %(max)0.1f MB.") % {
                    'file_type': file_type.title(),
                    'current': current_size_mb,
                    'max': max_size_mb
                }
            )
    return validator

def create_avatar_size_validator():
    """Create validator specifically for avatars using settings"""
    max_size_bytes = getattr(app_settings, 'MAX_AVATAR_SIZE', app_settings.MAX_FILE_SIZE)
    max_size_mb = max_size_bytes / (1024 * 1024)
    
    def validator(file):
        if file.size > max_size_bytes:
            current_size_mb = file.size / (1024 * 1024)
            raise ValidationError(
                _("Avatar is too large (%(current)0.1f MB). "
                  "Maximum size is %(max)0.1f MB.") % {
                    'current': current_size_mb,
                    'max': max_size_mb
                }
            )
    return validator

def image_dimension_validator(image):
    """Validate image dimensions using settings"""
    max_width = getattr(app_settings, 'MAX_IMAGE_WIDTH', 2000)
    max_height = getattr(app_settings, 'MAX_IMAGE_HEIGHT', 2000)
    
    try:
        from PIL import Image
        img = Image.open(image)
        width, height = img.size
        
        if width > max_width or height > max_height:
            raise ValidationError(
                _("Image dimensions too large (%(width)dx%(height)d). "
                  "Maximum allowed is %(max_width)dx%(max_height)d pixels.") % {
                    'width': width,
                    'height': height,
                    'max_width': max_width,
                    'max_height': max_height
                }
            )
    except Exception as e:
        raise ValidationError(_("Invalid image file: %(error)s") % {'error': str(e)})