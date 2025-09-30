from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus, TestimonialSource
from ..conf import app_settings
from ..utils import log_testimonial_action
import phonenumbers
from phonenumbers import NumberParseException

class TestimonialMediaSerializer(serializers.ModelSerializer):
    """Serializer for TestimonialMedia model."""
    
    media_type_display = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TestimonialMedia
        fields = [
            'id', 'file', 'testimonial', 'file_url', 'media_type', 'media_type_display', 
            'title', 'description', 'is_primary', 'order', 'created_at'
        ]
        # FIXED: Remove media_type from read_only_fields to allow auto-detection
        read_only_fields = ['id', 'created_at', 'media_type_display', 'file_url']
    
    def get_media_type_display(self, obj) -> str:
        """Get the display value for media_type."""
        return obj.get_media_type_display()
    
    def get_file_url(self, obj) -> str:
        """Get the URL for the file."""
        if obj.file:
            return obj.file.url
        return None
    
    def create(self, validated_data):
        """
        Create media with auto-detected media type.
        """
        # Let the model's save method handle media_type detection
        # Don't set media_type here - let it be auto-detected from the file
        media = super().create(validated_data)
        return media




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
    
    def get_testimonials_count(self, obj)-> int:
        """Get the count of published testimonials in this category."""
        return obj.testimonials.filter(
            status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
        ).count()


class TestimonialSerializer(serializers.ModelSerializer):
    """Serializer for Testimonial model."""
    
    category = TestimonialCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TestimonialCategory.objects.filter(is_active=True),
        source='category',
        required=False,
        allow_null=True,
        write_only=True
    )
    
    media = TestimonialMediaSerializer(many=True, read_only=True)
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
            'created_at', 'updated_at', 'approved_at',
            # NEW:
            'author_display',
        ]
        read_only_fields = [
            'id', 'status_display', 'source_display', 'media', 'slug',
            'created_at', 'updated_at', 'approved_at', 'is_verified',
            # NEW:
            'author_display',
        ]

    def get_author_display(self, obj) -> str:
        return obj.author_display
    
    def get_status_display(self, obj)-> str:
        """Get the display value for status."""
        return obj.get_status_display()
    
    def get_source_display(self, obj) -> str:
        """Get the display value for source."""
        return obj.get_source_display()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        if instance.is_anonymous:
            viewer = getattr(request, 'user', None)
            is_auth   = bool(viewer and viewer.is_authenticated)
            is_staff  = bool(is_auth and (viewer.is_staff or viewer.is_superuser))
            is_mod    = is_staff or bool(is_auth and getattr(viewer, 'groups', None)
                                         and viewer.groups.filter(name__in=app_settings.MODERATION_ROLES).exists())
            is_author = bool(is_auth and instance.author_id == viewer.id)

            if not (is_author or is_mod):
                # Replace user PII with masked display
                data['author_name']  = instance.author_display
                data['author_email'] = ''
                data['author_phone'] = ''
                data['avatar']       = None
                # (optional) Hide website/socials if you consider them PII:
                # data['website']      = ''
                # data['social_media'] = {}

        return data
    
    def validate(self, data):
        """
        Final validation for create/update via the base serializer.
        - Force guests to anonymous.
        - Enforce project policy on anonymous.
        - Set status/source defaults.
        - Ensure a non-empty author_name when anonymous.
        - Prefill author/name/email for authenticated non-anonymous.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_authenticated = bool(user and user.is_authenticated)

        # Force anonymous for guests
        if not is_authenticated:
            data['is_anonymous'] = True

        is_anonymous = bool(data.get('is_anonymous', False))

        # Policy: allow/disallow anonymous
        if is_anonymous and not app_settings.ALLOW_ANONYMOUS:
            raise serializers.ValidationError({
                'is_anonymous': _("Anonymous testimonials are not allowed.")
            })

        # Defaults
        if 'status' not in data:
            data['status'] = (
                TestimonialStatus.PENDING if app_settings.REQUIRE_APPROVAL
                else TestimonialStatus.APPROVED
            )
        if 'source' not in data:
            data['source'] = TestimonialSource.WEBSITE

        # Anonymous path: ensure display name, don't wipe stored PII/FK
        if is_anonymous:
            name = (data.get('author_name') or "").strip()
            if not name:
                data['author_name'] = _("Anonymous")
            # NOTE: do not null author/email/phone; masking is done in representation
            return data

        # Non-anonymous path: prefill from authenticated user
        author = data.get('author')
        if not author and is_authenticated:
            author = user
            data['author'] = author

        if author:
            author_name = (data.get('author_name') or "").strip()
            if not author_name:
                if hasattr(author, 'get_full_name') and author.get_full_name().strip():
                    data['author_name'] = author.get_full_name().strip()
                else:
                    username = getattr(author, 'username', None)
                    data['author_name'] = (username or f"User {getattr(author, 'id', '')}").strip()

            if not data.get('author_email') and getattr(author, 'email', None):
                data['author_email'] = author.email

        return data
    
    def create(self, validated_data):
        """
        Create a new testimonial.
        
        Logs the action and sets the IP address if available.
        """
        request = self.context.get('request')
        
        # Add IP address if available
        if request and request.META.get('REMOTE_ADDR'):
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
        
        # Create the testimonial
        testimonial = super().create(validated_data)
        
        # Log the action
        user = request.user if request and request.user.is_authenticated else None
        log_testimonial_action(testimonial, "create", user)
        
        return testimonial


class TestimonialDetailSerializer(TestimonialSerializer):
    """Extended serializer for Testimonial detail view."""
    
    class Meta(TestimonialSerializer.Meta):
        fields = TestimonialSerializer.Meta.fields + [
            'ip_address', 'rejection_reason', 'extra_data', 
            'response_at', 'approved_by'
        ]
        read_only_fields = TestimonialSerializer.Meta.read_only_fields + [
            'ip_address', 'response_at', 'approved_by'
        ]


class TestimonialCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating testimonials."""
    
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TestimonialCategory.objects.filter(is_active=True),
        source='category',
        required=False,
        allow_null=True,
        write_only=True
    )
    
    class Meta:
        model = Testimonial
        fields = [
            'id',
            'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category_id', 'is_anonymous', 'website', 'social_media'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """
        Creation-specific validation.
        - Force guests to anonymous.
        - Enforce project policy on anonymous.
        - Set status/source defaults.
        - Ensure a non-empty author_name when anonymous.
        - Prefill author/name/email for authenticated non-anonymous.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_authenticated = bool(user and user.is_authenticated)

        # Force anonymous for guests
        if not is_authenticated:
            data['is_anonymous'] = True

        is_anonymous = bool(data.get('is_anonymous', False))

        # Policy: allow/disallow anonymous
        if is_anonymous and not app_settings.ALLOW_ANONYMOUS:
            raise serializers.ValidationError({
                'is_anonymous': _("Anonymous testimonials are not allowed.")
            })

        # Defaults
        if 'status' not in data:
            data['status'] = (
                TestimonialStatus.PENDING if app_settings.REQUIRE_APPROVAL
                else TestimonialStatus.APPROVED
            )
        if 'source' not in data:
            data['source'] = TestimonialSource.WEBSITE

        # Anonymous path: ensure display name, don't wipe stored PII/FK
        if is_anonymous:
            name = (data.get('author_name') or "").strip()
            if not name:
                data['author_name'] = _("Anonymous")
            # NOTE: do not null author/email/phone; masking is done in representation
            return data

        # Non-anonymous path: prefill from authenticated user
        author = data.get('author')
        if not author and is_authenticated:
            author = user
            data['author'] = author

        if author:
            author_name = (data.get('author_name') or "").strip()
            if not author_name:
                if hasattr(author, 'get_full_name') and author.get_full_name().strip():
                    data['author_name'] = author.get_full_name().strip()
                else:
                    username = getattr(author, 'username', None)
                    data['author_name'] = (username or f"User {getattr(author, 'id', '')}").strip()

            if not data.get('author_email') and getattr(author, 'email', None):
                data['author_email'] = author.email

        return data

    def create(self, validated_data):
        request = self.context.get('request')

        # Finalize status/source
        validated_data['status'] = TestimonialStatus.PENDING if app_settings.REQUIRE_APPROVAL else TestimonialStatus.APPROVED
        validated_data['source'] = TestimonialSource.WEBSITE

        # Add IP if available
        if request and request.META.get('REMOTE_ADDR'):
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')

        # Attach author if authenticated (even if anonymous, we KEEP the FK)
        if request and request.user.is_authenticated:
            validated_data.setdefault('author', request.user)

        testimonial = super().create(validated_data)

        user = request.user if request and request.user.is_authenticated else None
        log_testimonial_action(testimonial, "create", user)
        return testimonial


class TestimonialAdminActionSerializer(serializers.Serializer):
    """Serializer for admin actions on testimonials."""
    
    testimonial_ids = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text=_("List of testimonial IDs to perform the action on.")
    )
    
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Reason for rejection (required for reject action).")
    )
    
    response = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Response to add to the testimonial(s).")
    )
    
    def validate(self, data):
        """
        Validate the action data.
        
        Ensures testimonial IDs exist and rejection reason is provided for reject action.
        """
        testimonial_ids = data.get('testimonial_ids', [])
        action = self.context.get('action')
        
        # Check if testimonials exist
        existing_ids = set(str(id) for id in Testimonial.objects.filter(
            pk__in=testimonial_ids
        ).values_list('pk', flat=True))
        
        non_existing_ids = set(testimonial_ids) - existing_ids
        if non_existing_ids:
            raise serializers.ValidationError(
                {'testimonial_ids': _("Some testimonial IDs do not exist: %(ids)s") % 
                 {'ids': ', '.join(non_existing_ids)}}
            )
        
        # Check for rejection reason when rejecting
        if action == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError(
                {'rejection_reason': _("Rejection reason is required when rejecting testimonials.")}
            )
        
        return data