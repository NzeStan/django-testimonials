# testimonials/mixins/validation_mixins.py

"""
Centralized validation mixins to eliminate duplication across serializers and forms.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class FileValidationMixin:
    """
    Reusable file validation logic for serializers.
    Eliminates duplication between serializers and model validators.
    """
    
    @staticmethod
    def validate_file_extension(file_obj, allowed_extensions):
        """
        Validate file extension against allowed extensions list.
        
        Args:
            file_obj: File object to validate
            allowed_extensions: List of allowed extensions
            
        Raises:
            serializers.ValidationError: If extension not allowed
        """
        if not file_obj:
            raise serializers.ValidationError(_("File is required."))
        
        filename = file_obj.name
        if '.' not in filename:
            raise serializers.ValidationError(_("File must have an extension."))
        
        ext = filename.split('.')[-1].lower().strip()
        allowed_extensions_lower = [e.lower().strip() for e in allowed_extensions]
        
        if ext not in allowed_extensions_lower:
            raise serializers.ValidationError(
                _("File type '.%(ext)s' is not allowed. Allowed types: %(types)s") % {
                    'ext': ext,
                    'types': ', '.join(allowed_extensions)
                }
            )
        
        return ext
    
    @staticmethod
    def validate_file_size(file_obj, max_size):
        """
        Validate file size against maximum size.
        
        Args:
            file_obj: File object to validate
            max_size: Maximum file size in bytes
            
        Raises:
            serializers.ValidationError: If file too large
        """
        if file_obj.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            current_size_mb = file_obj.size / (1024 * 1024)
            raise serializers.ValidationError(
                _("File is too large (%(current).1f MB). Maximum size is %(max).1f MB.") % {
                    'current': current_size_mb,
                    'max': max_size_mb
                }
            )
    
    def validate_uploaded_file(self, file_obj, allowed_extensions, max_size):
        """
        Complete file validation combining extension and size checks.
        
        Args:
            file_obj: File object to validate
            allowed_extensions: List of allowed extensions
            max_size: Maximum file size in bytes
            
        Returns:
            Validated file object
        """
        self.validate_file_extension(file_obj, allowed_extensions)
        self.validate_file_size(file_obj, max_size)
        return file_obj


class AnonymousUserValidationMixin:
    """
    Handles anonymous user submission validation logic.
    Centralizes the complex logic from serializers.
    """
    
    @staticmethod
    def ensure_anonymous_display_name(data):
        """
        Ensure anonymous users have a display name.
        
        Args:
            data: Validated data dict
            
        Returns:
            Updated data dict
        """
        name = (data.get('author_name') or "").strip()
        if not name:
            data['author_name'] = _("Anonymous")
        return data
    
    @staticmethod
    def prefill_author_from_user(data, user):
        """
        Prefill author information from authenticated user.
        
        Args:
            data: Validated data dict
            user: Authenticated user object
            
        Returns:
            Updated data dict
        """
        if not user or not user.is_authenticated:
            return data
        
        # Set author FK
        if not data.get('author'):
            data['author'] = user
        
        # Prefill author name
        author_name = (data.get('author_name') or "").strip()
        if not author_name:
            if hasattr(user, 'get_full_name') and user.get_full_name().strip():
                data['author_name'] = user.get_full_name().strip()
            else:
                username = getattr(user, 'username', None)
                data['author_name'] = (username or f"User {getattr(user, 'id', '')}").strip()
        
        # Prefill email
        if not data.get('author_email') and getattr(user, 'email', None):
            data['author_email'] = user.email
        
        return data
    
    @staticmethod
    def validate_anonymous_policy(is_anonymous, allow_anonymous):
        """
        Validate if anonymous testimonials are allowed by policy.
        
        Args:
            is_anonymous: Whether submission is anonymous
            allow_anonymous: Whether policy allows anonymous
            
        Raises:
            ValidationError: If policy violated (compatible with forms and serializers)
        """
        if is_anonymous and not allow_anonymous:
            # Use Django's ValidationError which works in both contexts
            from django.core.exceptions import ValidationError
            raise ValidationError(
                _("Anonymous testimonials are not allowed."),
                code='anonymous_not_allowed'
            )


class ChoiceFieldDisplayMixin:
    """
    Automatically adds display methods for Django choice fields.
    Eliminates repetitive get_X_display methods in serializers.
    """
    
    def get_display_value(self, obj, field_name):
        """
        Generic method to get display value for any choice field.
        
        Args:
            obj: Model instance
            field_name: Name of the field
            
        Returns:
            Display value or field value as fallback
        """
        get_display = getattr(obj, f'get_{field_name}_display', None)
        return get_display() if get_display else getattr(obj, field_name, '')