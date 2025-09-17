import re
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .conf import app_settings
from .exceptions import TestimonialValidationError


class NoHTMLValidator:
    """
    Validator that prohibits HTML tags in the input.
    """
    def __init__(self, message=None):
        self.message = message or _("HTML tags are not allowed.")
        self.html_pattern = re.compile(r'<[^>]*>')
        
    def __call__(self, value):
        if value and self.html_pattern.search(value):
            raise ValidationError(self.message)
        return value


class NoURLValidator:
    """
    Validator that prohibits URLs in the input.
    """
    def __init__(self, message=None):
        self.message = message or _("URLs are not allowed.")
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
    def __call__(self, value):
        if value and self.url_pattern.search(value):
            raise ValidationError(self.message)
        return value


class NoEmailValidator:
    """
    Validator that prohibits email addresses in the input.
    """
    def __init__(self, message=None):
        self.message = message or _("Email addresses are not allowed.")
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        
    def __call__(self, value):
        if value and self.email_pattern.search(value):
            raise ValidationError(self.message)
        return value


class NoPhoneValidator:
    """
    Validator that prohibits phone numbers in the input.
    """
    def __init__(self, message=None):
        self.message = message or _("Phone numbers are not allowed.")
        self.phone_pattern = re.compile(r'(\+\d{1,3}[\s.-])?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}')
        
    def __call__(self, value):
        if value and self.phone_pattern.search(value):
            raise ValidationError(self.message)
        return value


class ProfanityValidator:
    """
    Basic validator that checks for common profanity in the input.
    
    Note: This is a very basic implementation. For production use,
    consider using a more comprehensive profanity detection library.
    """
    def __init__(self, message=None, custom_words=None):
        self.message = message or _("This text contains inappropriate language.")
        # Very basic list - in a real implementation, this would be more comprehensive
        self.profanity_list = {
            'profanity1', 'profanity2', 'profanity3'
        }
        
        if custom_words:
            if isinstance(custom_words, (list, tuple, set)):
                self.profanity_list.update(custom_words)
            else:
                raise TestimonialValidationError("custom_words must be a list, tuple, or set")
        
    def __call__(self, value):
        if not value:
            return value
            
        # Convert to lowercase for case-insensitive matching
        value_lower = value.lower()
        
        # Check each word in the value
        words = re.findall(r'\b\w+\b', value_lower)
        for word in words:
            if word in self.profanity_list:
                raise ValidationError(self.message)
                
        return value


def validate_rating(value):
    """
    Validator for testimonial ratings.
    
    Ensures the rating is between 1 and the configured maximum rating.
    """
    max_rating = app_settings.MAX_RATING
    
    if not isinstance(value, (int, float)):
        raise ValidationError(_("Rating must be a number."))
        
    if value < 1:
        raise ValidationError(_("Rating must be at least 1."))
        
    if value > max_rating:
        raise ValidationError(_("Rating cannot exceed {max_rating}.").format(max_rating=max_rating))
        
    return value


def validate_testimonial_content(value):
    """
    Validate testimonial content for minimum length and other criteria.
    """
    if not value:
        raise ValidationError(_("Testimonial content is required."))
        
    # Check minimum length (adjust as needed)
    if len(value) < 10:
        raise ValidationError(_("Testimonial content must be at least 10 characters long."))
        
    return value


def validate_file_size(file_obj, max_size_mb=5):
    """
    Validate that a file doesn't exceed the maximum size.
    
    Args:
        file_obj: The file to validate
        max_size_mb: Maximum size in megabytes
        
    Raises:
        ValidationError: If the file is too large
    """
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    
    if file_obj.size > max_size_bytes:
        raise ValidationError(
            _("File is too large. Maximum size is {max_size} MB.").format(max_size=max_size_mb)
        )
        
    return file_obj


def validate_file_extension(file_obj, allowed_extensions=None):
    """
    Validate that a file has an allowed extension.
    
    Args:
        file_obj: The file to validate
        allowed_extensions: List of allowed extensions (without the dot)
        
    Raises:
        ValidationError: If the file has an invalid extension
    """
    if not allowed_extensions:
        # Default allowed extensions
        allowed_extensions = [
            'jpg', 'jpeg', 'png', 'gif', 'webp',  # Images
            'mp4', 'webm', 'mov',  # Videos
            'mp3', 'wav', 'ogg',  # Audio
            'pdf', 'doc', 'docx', 'txt'  # Documents
        ]
    
    ext = file_obj.name.split('.')[-1].lower()
    
    if ext not in allowed_extensions:
        raise ValidationError(
            _("File type not supported. Allowed types: {extensions}").format(
                extensions=", ".join(allowed_extensions)
            )
        )
        
    return file_obj