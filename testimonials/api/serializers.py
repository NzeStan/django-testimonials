# testimonials/api/serializers.py - REFACTORED

"""
Refactored serializers using mixins to eliminate duplication.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus, TestimonialSource, TestimonialMediaType
from ..conf import app_settings
from ..utils import log_testimonial_action

# Import mixins
from ..mixins import (
    FileValidationMixin,
    AnonymousUserValidationMixin,
    ChoiceFieldDisplayMixin
)


class TestimonialMediaSerializer(
    FileValidationMixin,
    ChoiceFieldDisplayMixin,
    serializers.ModelSerializer
):
    """
    Serializer for testimonial media files (secure + validated).
    """

    media_type_display = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    thumbnails = serializers.SerializerMethodField()

    class Meta:
        model = TestimonialMedia
        fields = [
            'id',
            'testimonial',
            'file',
            'file_url',
            'media_type',
            'media_type_display',
            'title',
            'description',
            'is_primary',
            'order',
            'thumbnails',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'file_url',
            'media_type_display',
            'thumbnails',
            'created_at',
            'updated_at',
        ]

    # --------------------
    # Display helpers
    # --------------------

    def get_media_type_display(self, obj):
        return self.get_display_value(obj, 'media_type')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

    def get_thumbnails(self, obj):
        if obj.media_type != TestimonialMediaType.IMAGE:
            return None

        request = self.context.get('request')
        thumbnails = {}

        for size in ['small', 'medium', 'large']:
            thumbnail = getattr(obj, f'{size}_thumbnail', None)
            if thumbnail and hasattr(thumbnail, 'url'):
                thumbnails[size] = (
                    request.build_absolute_uri(thumbnail.url)
                    if request else thumbnail.url
                )

        return thumbnails or None

    # --------------------
    # File validation
    # --------------------

    def validate_file(self, file_obj):
        return self.validate_uploaded_file(
            file_obj,
            app_settings.ALLOWED_FILE_EXTENSIONS,
            app_settings.MAX_FILE_SIZE
        )

    # --------------------
    # Security validation
    # --------------------

    def validate(self, data):
        testimonial = data.get('testimonial')
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            raise serializers.ValidationError({
                'testimonial': _("Authentication required to add media.")
            })

        if user.is_staff or user.is_superuser:
            return data

        if testimonial.author != user:
            raise serializers.ValidationError({
                'testimonial': _("You can only add media to your own testimonials.")
            })

        return data


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


class TestimonialUserSerializer(ChoiceFieldDisplayMixin, serializers.ModelSerializer):
    """
    🔒 SECURED: Serializer for regular users - LIMITED FIELDS ONLY.
    Users can ONLY edit their own basic info, NOT admin fields.
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
    
    # Display fields
    status_display = serializers.SerializerMethodField()
    source_display = serializers.SerializerMethodField()
    author_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Testimonial
        fields = [
            # User can READ these
            'id', 'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'category_id', 'source', 'source_display', 
            'status', 'status_display',  # Read-only for users
            'is_anonymous',  # Read-only after creation
            'is_verified',  # Read-only (admin sets this)
            'media', 'slug', 'website', 'social_media',
            'response',  # Read-only (admin responses)
            'created_at', 'updated_at', 'approved_at', 'author_display', 'display_order'
        ]
        
        # 🔒 CRITICAL: These fields are READ-ONLY for regular users
        read_only_fields = [
            'id', 'status', 'status_display', 'source', 'source_display', 
            'media', 'slug', 'created_at', 'updated_at', 'approved_at', 
            'is_verified', 'author_display',
            'is_anonymous',  # 🔒 Can't change after creation
            'response','display_order'  # 🔒 Admin-only field
        ]
    
    def get_status_display(self, obj) -> str:
        return self.get_display_value(obj, 'status')
    
    def get_source_display(self, obj) -> str:
        return self.get_display_value(obj, 'source')
    
    def get_author_display(self, obj) -> str:
        return obj.author_display
    
    def update(self, instance, validated_data):
        """
        🔒 SECURED UPDATE: Users can ONLY update their basic info.
        Admin fields are BLOCKED even if submitted.
        """
        # Get the request user
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        
        # 🔒 CRITICAL: Remove any admin-only fields from validated_data
        # This prevents users from sneaking these fields into the request
        admin_only_fields = [
            'status', 'is_verified', 'is_anonymous', 'response',
            'response_at', 'response_by', 'approved_at', 'approved_by',
            'rejection_reason', 'display_order', 'source'
        ]
        
        for field in admin_only_fields:
            validated_data.pop(field, None)
        
        # 🔒 CRITICAL: Users can ONLY edit their OWN testimonials
        if user and user.is_authenticated:
            if instance.author != user and not (user.is_staff or user.is_superuser):
                raise serializers.ValidationError(
                    _("You can only edit your own testimonials.")
                )
        
        # Perform the update with cleaned data
        return super().update(instance, validated_data)

class TestimonialAdminSerializer(ChoiceFieldDisplayMixin, serializers.ModelSerializer):
    """
    🔓 ADMIN SERIALIZER: Full access to all fields including admin-only ones.
    Only used when request.user.is_staff = True.
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
    
    # Display fields
    status_display = serializers.SerializerMethodField()
    source_display = serializers.SerializerMethodField()
    author_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Testimonial
        fields = [
            # All fields - admins have full access
            'id', 'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'category_id', 'source', 'source_display', 
            'status', 'status_display',
            'is_anonymous', 'is_verified', 'display_order',
            'media', 'slug', 'website', 'social_media',
            'response', 'response_at', 'response_by',  # Admin can edit
            'approved_at', 'approved_by', 'rejection_reason',
            'created_at', 'updated_at', 'author_display',
        ]
        
        # Minimal read-only fields for admins
        read_only_fields = [
            'id', 'status_display', 'source_display', 'media', 'slug',
            'created_at', 'updated_at', 'author_display',
        ]
    
    def get_status_display(self, obj) -> str:
        return self.get_display_value(obj, 'status')
    
    def get_source_display(self, obj) -> str:
        return self.get_display_value(obj, 'source')
    
    def get_author_display(self, obj) -> str:
        return obj.author_display

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


class TestimonialUserDetailSerializer(TestimonialUserSerializer):
    """
    🔒 SECURED: Detail serializer for users.
    Shows slightly more fields than list, but NO sensitive admin data.
    """
    
    class Meta(TestimonialUserSerializer.Meta):
        # Add response_at (when company responded) - but NOT response_by (who responded)
        fields = TestimonialUserSerializer.Meta.fields + [
            'response_at',  # Users can see WHEN response was added
        ]
        
        read_only_fields = TestimonialUserSerializer.Meta.read_only_fields + [
            'response_at',
        ]

class TestimonialAdminDetailSerializer(TestimonialAdminSerializer):
    """
    🔓 ADMIN DETAIL SERIALIZER: Shows EVERYTHING including sensitive data.
    Used for detail/retrieve views when user is admin.
    """
    
    class Meta(TestimonialAdminSerializer.Meta):
        # Add sensitive fields that should ONLY appear in detail view
        fields = TestimonialAdminSerializer.Meta.fields + [
            'ip_address',  # 🔒 Sensitive - only for admins in detail view
            'extra_data',  # 🔒 Internal metadata
        ]
        
        read_only_fields = TestimonialAdminSerializer.Meta.read_only_fields + [
            'ip_address',
        ]



class TestimonialCreateSerializer(AnonymousUserValidationMixin, serializers.ModelSerializer):
    """
    Serializer for creating testimonials.
    Sets is_anonymous at creation time only.
    """
    
    # ✅ FIX: Add explicit category validation
    category = serializers.PrimaryKeyRelatedField(
        queryset=TestimonialCategory.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Testimonial
        fields = [
            'id',  # ✅ FIX: Include id in response after creation
            'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'source', 'is_anonymous', 'website', 'social_media',
        ]
        read_only_fields = ['id']  # ✅ FIX: Make id read-only
    
    def validate_category(self, value):
        """
        ✅ FIX: Explicitly validate that category is active.
        """
        if value and not value.is_active:
            raise serializers.ValidationError(
                _("Cannot use inactive category. Please select an active category.")
            )
        return value
    
    def validate(self, data):
        """Cleaner validation using extracted methods from mixin."""
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
            data = self.ensure_anonymous_display_name(data)
        else:
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
    """
    ✅ FIXED: Serializer for admin actions on testimonials.
    Now properly validates rejection reason requirement.
    """
    
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
        help_text=_("Reason for rejection (required when rejecting)")
    )
    
    def validate_testimonial_ids(self, value):
        """Validate that testimonials exist."""
        if not value:
            raise serializers.ValidationError(_("At least one testimonial ID required."))
        
        from ..models import Testimonial
        existing_count = Testimonial.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError(
                _("Some testimonial IDs do not exist.")
            )
        
        return value
    
    def validate(self, data):
        """
        ✅ FIX: Make reason required for rejection action.
        """
        action = data.get('action')
        reason = data.get('reason', '').strip()
        
        if action == 'reject' and not reason:
            raise serializers.ValidationError({
                'reason': _("Reason is required when rejecting testimonials.")
            })
        
        return data
