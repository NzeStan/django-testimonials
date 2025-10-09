# testimonials/api/serializers.py - REFACTORED

"""
Refactored serializers using mixins to eliminate duplication.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus, TestimonialSource
from ..conf import app_settings
from ..utils import log_testimonial_action

# Import mixins
from ..mixins import (
    FileValidationMixin,
    AnonymousUserValidationMixin,
    ChoiceFieldDisplayMixin
)


class TestimonialMediaSerializer(FileValidationMixin, ChoiceFieldDisplayMixin, serializers.ModelSerializer):
    """
    Refactored serializer for TestimonialMedia with centralized validation.
    """
    
    media_type_display = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TestimonialMedia
        fields = [
            'id', 'file', 'testimonial', 'file_url', 'media_type', 'media_type_display', 
            'title', 'description', 'is_primary', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'media_type_display', 'file_url']
    
    def get_media_type_display(self, obj) -> str:
        """Get display value for media_type using mixin."""
        return self.get_display_value(obj, 'media_type')
    
    def get_file_url(self, obj) -> str:
        """Get the URL for the file."""
        return obj.file.url if obj.file else None
    
    def validate_file(self, file_obj):
        """
        Validate file using centralized mixin method.
        Much cleaner than 50+ lines of duplicate code!
        """
        return self.validate_uploaded_file(
            file_obj,
            app_settings.ALLOWED_FILE_EXTENSIONS,
            app_settings.MAX_FILE_SIZE
        )
    
    def create(self, validated_data):
        """Create media with auto-detected media type."""
        return super().create(validated_data)


class TestimonialCategorySerializer(serializers.ModelSerializer):
    """Serializer for TestimonialCategory model."""
    
    testimonials_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TestimonialCategory
        fields = [
            'id', 'name', 'slug', 'description', 'is_active', 
            'order', 'testimonials_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'testimonials_count', 'slug', 'created_at', 'updated_at']
    
    def get_testimonials_count(self, obj) -> int:
        """Get count of published testimonials."""
        return obj.testimonials.filter(
            status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
        ).count()


class TestimonialSerializer(ChoiceFieldDisplayMixin, serializers.ModelSerializer):
    """
    Refactored serializer for Testimonial with display mixins.
    """
    
    category = TestimonialCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TestimonialCategory.objects.filter(is_active=True),
        source='category',
        required=False,
        allow_null=True,
        write_only=True
    )
    
    media = TestimonialMediaSerializer(many=True, read_only=True)
    
    # Use mixin for display fields - no more repetition!
    status_display = serializers.SerializerMethodField()
    source_display = serializers.SerializerMethodField()
    author_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Testimonial
        fields = [
            'id', 'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'category_id', 'source', 'source_display', 'status',
            'status_display', 'is_anonymous', 'is_verified', 'media',
            'display_order', 'slug', 'website', 'social_media', 'response',
            'created_at', 'updated_at', 'approved_at', 'author_display',
        ]
        read_only_fields = [
            'id', 'status_display', 'source_display', 'media', 'slug',
            'created_at', 'updated_at', 'approved_at', 'is_verified',
            'author_display',
        ]
    
    # Clean display methods using mixin
    def get_status_display(self, obj) -> str:
        return self.get_display_value(obj, 'status')
    
    def get_source_display(self, obj) -> str:
        return self.get_display_value(obj, 'source')
    
    def get_author_display(self, obj) -> str:
        return obj.author_display


class TestimonialDetailSerializer(TestimonialSerializer):
    """
    Extended serializer with more details for single object retrieval.
    """
    
    class Meta(TestimonialSerializer.Meta):
        fields = TestimonialSerializer.Meta.fields + [
            'ip_address', 'rejection_reason', 'response_at', 'response_by',
        ]
        read_only_fields = TestimonialSerializer.Meta.read_only_fields + [
            'ip_address', 'rejection_reason', 'response_at', 'response_by',
        ]


class TestimonialCreateSerializer(AnonymousUserValidationMixin, serializers.ModelSerializer):
    """
    Refactored serializer for creating testimonials.
    Uses AnonymousUserValidationMixin for cleaner validation logic.
    """
    
    class Meta:
        model = Testimonial
        fields = [
            'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'source', 'is_anonymous', 'website', 'social_media',
        ]
    
    def validate(self, data):
        """
        Cleaner validation using extracted methods from mixin.
        Much more readable than 80+ lines of nested conditions!
        """
        data = self._set_authentication_defaults(data)
        data = self._handle_submission_type(data)
        return data
    
    def _set_authentication_defaults(self, data):
        """Set defaults based on authentication state."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_authenticated = bool(user and user.is_authenticated)
        
        # Force anonymous for guests
        if not is_authenticated:
            data['is_anonymous'] = True
        
        # Set default status and source
        if 'status' not in data:
            data['status'] = (
                TestimonialStatus.PENDING if app_settings.REQUIRE_APPROVAL
                else TestimonialStatus.APPROVED
            )
        if 'source' not in data:
            data['source'] = TestimonialSource.WEBSITE
        
        return data
    
    def _handle_submission_type(self, data):
        """Handle anonymous vs authenticated submissions."""
        is_anonymous = bool(data.get('is_anonymous', False))
        
        # Validate policy using mixin
        self.validate_anonymous_policy(is_anonymous, app_settings.ALLOW_ANONYMOUS)
        
        if is_anonymous:
            # Use mixin method for anonymous handling
            data = self.ensure_anonymous_display_name(data)
        else:
            # Use mixin method for authenticated handling
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            data = self.prefill_author_from_user(data, user)
        
        return data
    
    def create(self, validated_data):
        """Create testimonial with logging."""
        request = self.context.get('request')
        
        # Add IP if available
        if request and request.META.get('REMOTE_ADDR'):
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
        
        # Attach author if authenticated
        if request and request.user.is_authenticated:
            validated_data.setdefault('author', request.user)
        
        testimonial = super().create(validated_data)
        
        user = request.user if request and request.user.is_authenticated else None
        log_testimonial_action(testimonial, "create", user)
        
        return testimonial


class TestimonialAdminActionSerializer(serializers.Serializer):
    """Serializer for admin actions on testimonials."""
    
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'feature', 'archive'],
        required=True
    )
    testimonial_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Optional reason for rejection")
    )
    
    def validate_testimonial_ids(self, value):
        """Validate that testimonials exist."""
        if not value:
            raise serializers.ValidationError(_("At least one testimonial ID required."))
        
        # Check if testimonials exist
        existing_count = Testimonial.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError(
                _("Some testimonial IDs do not exist.")
            )
        
        return value
    
    def validate(self, data):
        """Validate that reason is provided for rejection."""
        if data.get('action') == 'reject' and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': _("Reason is required when rejecting testimonials.")
            })
        return data