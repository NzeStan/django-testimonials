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
        read_only_fields = ['id', 'created_at', 'media_type_display', 'file_url']
    
    def get_media_type_display(self, obj)-> str:
        """Get the display value for media_type."""
        return obj.get_media_type_display()
    
    def get_file_url(self, obj)-> str:
        """Get the URL for the file."""
        if obj.file:
            return obj.file.url
        return None


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
    
    
    class Meta:
        model = Testimonial
        fields = [
            'id', 'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'category_id', 'source', 'source_display', 'status', 
            'status_display', 'is_anonymous', 'is_verified', 'media',
            'display_order', 'slug', 'website', 'social_media', 'response',
            'created_at', 'updated_at', 'approved_at'
        ]
        read_only_fields = [
            'id', 'status_display', 'source_display', 'media', 'slug',
            'created_at', 'updated_at', 'approved_at', 'is_verified'
        ]
    
    def get_status_display(self, obj)-> str:
        """Get the display value for status."""
        return obj.get_status_display()
    
    def get_source_display(self, obj) -> str:
        """Get the display value for source."""
        return obj.get_source_display()
    
    def validate(self, data):
        """
        Validate the testimonial data.
        
        - Ensure anonymous testimonials are allowed if specified.
        - Set default status based on settings.
        - Set default source if not provided.
        - Handle author information prefilling.
        """
        is_anonymous = data.get('is_anonymous', False)
        request = self.context.get('request')
        
        # Validate anonymous testimonials
        if is_anonymous and not app_settings.ALLOW_ANONYMOUS:
            raise serializers.ValidationError(
                {'is_anonymous': _("Anonymous testimonials are not allowed.")}
            )
        
        # Set default status if not provided
        if 'status' not in data:
            if app_settings.REQUIRE_APPROVAL:
                data['status'] = TestimonialStatus.PENDING
            else:
                data['status'] = TestimonialStatus.APPROVED
        
        # Set default source if not provided
        if 'source' not in data:
            data['source'] = TestimonialSource.DEFAULT
        
        # Handle anonymous testimonials
        if is_anonymous:
            data['author_name'] = _("Anonymous")
            data['author_email'] = ""
            data['author_phone'] = ""
            data['author'] = None
            
            # Clear avatar if present
            if 'avatar' in data:
                data['avatar'] = None
        else:
            # Handle authenticated user data prefilling for non-anonymous testimonials
            author = data.get('author')
            
            # If no author specified but user is authenticated, use current user
            if not author and request and request.user.is_authenticated:
                author = request.user
                data['author'] = author
            
            # Prefill author information if author exists
            if author:
                # Set author name from user if not provided or blank
                if not data.get('author_name') or str(data.get('author_name')).strip() == "":
                    if hasattr(author, 'get_full_name') and author.get_full_name():
                        data['author_name'] = author.get_full_name()
                    else:
                        data['author_name'] = author.username
                
                # Set author email from user if not provided or blank
                if not data.get('author_email') and hasattr(author, 'email') and author.email:
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
            'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category_id', 'is_anonymous', 'website', 'social_media'
        ]
    
    def validate(self, data):
        """
        Validate the testimonial data.
        
        - Ensure anonymous testimonials are allowed if specified.
        - Set default status based on settings.
        - Set default source if not provided.
        - Handle author information prefilling.
        """
        is_anonymous = data.get('is_anonymous', False)
        request = self.context.get('request')
        
        # Validate anonymous testimonials
        if is_anonymous and not app_settings.ALLOW_ANONYMOUS:
            raise serializers.ValidationError(
                {'is_anonymous': _("Anonymous testimonials are not allowed.")}
            )
        
        # Set default status if not provided
        if 'status' not in data:
            if app_settings.REQUIRE_APPROVAL:
                data['status'] = TestimonialStatus.PENDING
            else:
                data['status'] = TestimonialStatus.APPROVED
        
        # Set default source if not provided
        if 'source' not in data:
            data['source'] = TestimonialSource.DEFAULT
        
        # Handle anonymous testimonials
        if is_anonymous:
            data['author_name'] = _("Anonymous")
            data['author_email'] = ""
            data['author_phone'] = ""
            data['author'] = None
            
            # Clear avatar if present
            if 'avatar' in data:
                data['avatar'] = None
        else:
            # Handle authenticated user data prefilling for non-anonymous testimonials
            author = data.get('author')
            
            # If no author specified but user is authenticated, use current user
            if not author and request and request.user.is_authenticated:
                author = request.user
                data['author'] = author
            
            # Prefill author information if author exists
            if author:
                # ALWAYS set author_name to avoid blank field error
                author_name = data.get('author_name', '').strip()
                if not author_name:  # Empty, None, or whitespace only
                    if hasattr(author, 'get_full_name') and author.get_full_name().strip():
                        data['author_name'] = author.get_full_name().strip()
                    elif hasattr(author, 'username') and author.username.strip():
                        data['author_name'] = author.username.strip()
                    else:
                        # Fallback to avoid blank field error since field doesn't allow blank
                        data['author_name'] = f"User {author.id}"
                
                # Set author email from user if not provided or blank
                if not data.get('author_email') and hasattr(author, 'email') and author.email:
                    data['author_email'] = author.email
            
            # NOW check required fields AFTER auto-fill logic
            if not data.get('author_name'):
                raise serializers.ValidationError(
                    {'author_name': _("Author name is required for non-anonymous testimonials.")}
                )
        
        return data
    
    def create(self, validated_data):
        """
        Create a new testimonial.
        
        Sets status based on settings and logs the action.
        """
        request = self.context.get('request')
        
        # Set status based on settings
        if app_settings.REQUIRE_APPROVAL:
            validated_data['status'] = TestimonialStatus.PENDING
        else:
            validated_data['status'] = TestimonialStatus.APPROVED
        
        # Set source to website
        validated_data['source'] = TestimonialSource.WEBSITE
        
        # Add IP address if available
        if request and request.META.get('REMOTE_ADDR'):
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
        
        # Set author if user is authenticated
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        
        # Create the testimonial
        testimonial = super().create(validated_data)
        
        # Log the action
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