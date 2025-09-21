from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import F, Q, Index
import string
from phonenumber_field.modelfields import PhoneNumberField

from ..managers import (
    TestimonialManager, 
    TestimonialCategoryManager, 
    TestimonialMediaManager
)
from ..constants import (
    TestimonialStatus, 
    TestimonialSource, 
    TestimonialMediaType
)
from ..validators import (
    validate_rating, 
    validate_testimonial_content, 
    validate_file_size
)
from ..utils import (
    get_unique_slug,
    generate_upload_path,
    get_file_type,
    validate_file_size,
    invalidate_testimonial_cache
)
from ..conf import app_settings
from .base import BaseModel


class TestimonialCategory(BaseModel):
    """
    Optimized categories for testimonials with enhanced performance.
    """
    __test__ = False
    name = models.CharField(
        max_length=100, 
        verbose_name=_("Name"),
        db_index=True  # Index for faster filtering and sorting
    )
    slug = models.SlugField(
        max_length=120, 
        unique=True, 
        verbose_name=_("Slug"),
        db_index=True  # Index for faster slug-based queries
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Description")
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Is active"),
        db_index=True  # Index for active category filtering
    )
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name=_("Order"),
        db_index=True  # Index for ordering
    )
    
    objects = TestimonialCategoryManager()
    
    class Meta:
        verbose_name = _("Testimonial Category")
        verbose_name_plural = _("Testimonial Categories")
        ordering = ['order', 'name']
        indexes = [
            Index(fields=['is_active', 'order']),  # Compound index for common queries
            Index(fields=['name']),
            Index(fields=['slug']),
        ]
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Optimize string operations
        if self.name:
            self.name = string.capwords(self.name.strip())

        # Generate unique slug efficiently
        if not self.slug:
            self.slug = get_unique_slug(self, 'name', max_length=120)
        
        # Use update_fields for better performance when possible
        if self.pk and 'update_fields' not in kwargs:
            kwargs['update_fields'] = ['name', 'slug', 'description', 'is_active', 'order', 'updated_at']
        
        super().save(*args, **kwargs)
        
        # Invalidate cache after save
        if app_settings.USE_REDIS_CACHE:
            invalidate_testimonial_cache(category_id=self.pk)
    
    def delete(self, *args, **kwargs):
        category_id = self.pk
        super().delete(*args, **kwargs)
        
        # Invalidate cache after deletion
        if app_settings.USE_REDIS_CACHE:
            invalidate_testimonial_cache(category_id=category_id)


class Testimonial(BaseModel):
    """
    Highly optimized main testimonial model with performance enhancements.
    """
    __test__ = False
    
    # Author information with optimized field types
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        verbose_name=_("User"),
        db_index=True  # Index for user-based queries
    )
    author_name = models.CharField(
        max_length=255,
        verbose_name=_("Author Name"),
        blank=True,
        db_index=True  # Index for author name searches
    )
    author_email = models.EmailField(
        blank=True,
        verbose_name=_("Author Email"),
        db_index=True  # Index for email-based queries
    )
    author_phone = PhoneNumberField(
        blank=True,
        verbose_name=_("Author Phone"),
    )
    author_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Author Title")
    )
    company = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Company"),
        db_index=True  # Index for company-based searches
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Location")
    )
    avatar = models.ImageField(
        upload_to=generate_upload_path,
        blank=True,
        null=True,
        verbose_name=_("Avatar")
    )
    
    # Testimonial content with optimized text fields
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Title"),
        db_index=True  # Index for title searches
    )
    content = models.TextField(
        validators=[validate_testimonial_content],
        verbose_name=_("Content")
        # Full-text search index would be added at database level
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(app_settings.MAX_RATING),
            validate_rating
        ],
        verbose_name=_("Rating"),
        db_index=True  # Index for rating-based filtering
    )
    
    # Categorization and metadata with optimized relationships
    category = models.ForeignKey(
        'TestimonialCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        verbose_name=_("Category"),
        db_index=True  # Index for category filtering
    )
    source = models.CharField(
        max_length=30,
        choices=TestimonialSource.CHOICES,
        default=TestimonialSource.DEFAULT,
        verbose_name=_("Source"),
        db_index=True  # Index for source filtering
    )
    status = models.CharField(
        max_length=30,
        choices=TestimonialStatus.CHOICES,
        default=TestimonialStatus.DEFAULT,
        verbose_name=_("Status"),
        db_index=True  # Critical index for status filtering
    )
    
    # Flags and options with optimized boolean fields
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name=_("Is Anonymous"),
        db_index=True  # Index for anonymous filtering
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Is Verified"),
        db_index=True  # Index for verified filtering
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        db_index=True  # Index for ordering
    )
    
    # Additional fields with optimized indexes
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name=_("Slug"),
        db_index=True  # Index for slug-based queries
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_("IP Address")
    )
    website = models.URLField(
        blank=True,
        verbose_name=_("Website")
    )
    social_media = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Social Media")
    )
    
    # Moderation fields with optimized relationships
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Approved At"),
        db_index=True  # Index for approval date queries
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_testimonials',
        verbose_name=_("Approved By")
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Rejection Reason")
    )
    
    # Response field with optimized structure
    response = models.TextField(
        blank=True,
        verbose_name=_("Response")
    )
    response_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Response At")
    )
    response_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonial_responses',
        verbose_name=_("Response By")
    )
    
    # Extra fields for customization
    extra_data = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Extra Data")
    )
    
    # Optimized manager
    objects = TestimonialManager()
    
    class Meta:
        verbose_name = _("Testimonial")
        verbose_name_plural = _("Testimonials")
        ordering = ['-display_order', '-created_at']
        
        # Comprehensive indexing strategy for optimal performance
        indexes = [
            # Single field indexes for common queries
            Index(fields=['status']),
            Index(fields=['rating']),
            Index(fields=['author_name']),
            Index(fields=['created_at']),
            Index(fields=['approved_at']),
            Index(fields=['display_order']),
            Index(fields=['is_anonymous']),
            Index(fields=['is_verified']),
            
            # Compound indexes for complex queries
            Index(fields=['status', 'created_at']),  # Published testimonials by date
            Index(fields=['status', 'rating']),     # Published high-rated testimonials
            Index(fields=['status', 'display_order']), # Published testimonials by order
            Index(fields=['category', 'status']),   # Category testimonials by status
            Index(fields=['author', 'status']),     # User testimonials by status
            Index(fields=['rating', 'created_at']), # High-rated recent testimonials
            Index(fields=['is_verified', 'status']), # Verified published testimonials
            
            # Partial indexes would be created at database level for:
            # - WHERE status IN ('approved', 'featured') for published testimonials
            # - WHERE is_anonymous = False for non-anonymous testimonials
        ]
        
        # Database constraints for data integrity
        constraints = [
            models.CheckConstraint(
                check=Q(rating__gte=1) & Q(rating__lte=app_settings.MAX_RATING),
                name='testimonial_rating_range'
            ),
            models.CheckConstraint(
                check=~(Q(is_anonymous=True) & Q(author_name='') & Q(author_email='')),
                name='testimonial_author_info_required'
            ),
        ]
    
    def __str__(self):
        return f"{self.author_name}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        # Optimize field processing
        self._normalize_text_fields()
        self._handle_anonymity()
        self._prefill_author_data()
        self._generate_slug()
        
        # Use update_fields for better performance when possible
        if self.pk and 'update_fields' not in kwargs and hasattr(self, '_state'):
            # Only update changed fields
            changed_fields = self._get_changed_fields()
            if changed_fields:
                kwargs['update_fields'] = changed_fields + ['updated_at']
        
        super().save(*args, **kwargs)
        
        # Invalidate cache after save
        if app_settings.USE_REDIS_CACHE:
            invalidate_testimonial_cache(
                testimonial_id=self.pk,
                category_id=self.category_id,
                user_id=self.author_id
            )
    
    def delete(self, *args, **kwargs):
        # Store IDs for cache invalidation
        testimonial_id = self.pk
        category_id = self.category_id
        user_id = self.author_id
        
        super().delete(*args, **kwargs)
        
        # Invalidate cache after deletion
        if app_settings.USE_REDIS_CACHE:
            invalidate_testimonial_cache(
                testimonial_id=testimonial_id,
                category_id=category_id,
                user_id=user_id
            )
    
    def _normalize_text_fields(self):
        """Optimize text field normalization."""
        if self.author_name:
            self.author_name = string.capwords(self.author_name.strip())
        if self.author_title:
            self.author_title = string.capwords(self.author_title.strip())
        if self.company:
            self.company = self.company.strip()
    
    def _handle_anonymity(self):
        """Handle anonymous testimonial logic efficiently."""
        if self.is_anonymous:
            self.author_name = _("Anonymous")
            self.author_email = ""
            self.author_phone = ""
            self.author = None
            self.avatar = None
    
    def _prefill_author_data(self):
        """Prefill author data efficiently."""
        if self.author and not self.is_anonymous:
            if not self.author_name:
                if hasattr(self.author, "get_full_name") and self.author.get_full_name():
                    self.author_name = self.author.get_full_name()
                else:
                    self.author_name = self.author.username
            if not self.author_email and getattr(self.author, "email", None):
                self.author_email = self.author.email
    
    def _generate_slug(self):
        """Generate slug efficiently."""
        if not self.slug:
            slug_source_field = 'author_name' if self.author_name else 'title'
            self.slug = get_unique_slug(self, slug_source_field, max_length=255)
    
    def _get_changed_fields(self):
        """Get list of changed fields for optimized updates."""
        if not self.pk:
            return None
        
        try:
            original = self.__class__.objects.get(pk=self.pk)
            changed_fields = []
            
            for field in self._meta.fields:
                if field.name in ['created_at', 'updated_at']:
                    continue
                
                current_value = getattr(self, field.name)
                original_value = getattr(original, field.name)
                
                if current_value != original_value:
                    changed_fields.append(field.name)
            
            return changed_fields
        except self.__class__.DoesNotExist:
            return None
    
    # Optimized properties with caching
    @property
    def is_published(self):
        """Check if the testimonial is published (approved or featured)."""
        return self.status in [TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
    
    @property
    def has_media(self):
        """Check if the testimonial has any media attached (cached)."""
        if not hasattr(self, '_has_media_cache'):
            self._has_media_cache = self.media.exists()
        return self._has_media_cache
    
    @property
    def author_display(self):
        """Get the author display name, respecting anonymity."""
        return _("Anonymous") if self.is_anonymous else self.author_name
    
    # Optimized action methods
    def approve(self, user=None):
        """
        Approve the testimonial with optimized update.
        """
        from django.utils import timezone
        
        self.status = TestimonialStatus.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save(update_fields=['status', 'approved_at', 'approved_by', 'updated_at'])
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "approve", user)
    
    def reject(self, reason=None, user=None):
        """
        Reject the testimonial with optimized update.
        """
        update_fields = ['status', 'updated_at']
        
        self.status = TestimonialStatus.REJECTED
        if reason:
            self.rejection_reason = reason
            update_fields.append('rejection_reason')
        
        self.save(update_fields=update_fields)
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "reject", user, notes=reason)
    
    def feature(self, user=None):
        """
        Feature the testimonial with optimized update.
        """
        self.status = TestimonialStatus.FEATURED
        self.save(update_fields=['status', 'updated_at'])
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "feature", user)
    
    def archive(self, user=None):
        """
        Archive the testimonial with optimized update.
        """
        self.status = TestimonialStatus.ARCHIVED
        self.save(update_fields=['status', 'updated_at'])
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "archive", user)
    
    def add_response(self, response_text, user=None):
        """
        Add a response to the testimonial with optimized update.
        """
        from django.utils import timezone
        
        self.response = response_text
        self.response_at = timezone.now()
        self.response_by = user
        self.save(update_fields=['response', 'response_at', 'response_by', 'updated_at'])
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "add_response", user)
    
    def add_media(self, file_obj, title=None, description=None):
        """
        Add media to the testimonial with optimized creation.
        """
        media_type = get_file_type(file_obj)
        
        return TestimonialMedia.objects.create(
            testimonial=self,
            file=file_obj,
            media_type=media_type,
            title=title or "",
            description=description or ""
        )


class TestimonialMedia(BaseModel):
    """
    Optimized media files attached to testimonials.
    """
    __test__ = False
    testimonial = models.ForeignKey(
        'Testimonial',
        on_delete=models.CASCADE,
        related_name='media',
        verbose_name=_("Testimonial"),
        db_index=True  # Index for testimonial-based queries
    )
    file = models.FileField(
        upload_to=generate_upload_path,
        verbose_name=_("File")
    )
    media_type = models.CharField(
        max_length=20,
        choices=TestimonialMediaType.CHOICES,
        verbose_name=_("Media Type"),
        db_index=True  # Index for media type filtering
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Title")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_("Is Primary"),
        db_index=True  # Index for primary media queries
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        db_index=True  # Index for ordering
    )
    
    # Extra data for thumbnails, metadata, etc.
    extra_data = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Extra Data")
    )
    
    objects = TestimonialMediaManager()
    
    class Meta:
        verbose_name = _("Testimonial Media")
        verbose_name_plural = _("Testimonial Media")
        ordering = ['-is_primary', 'order', '-created_at']
        
        indexes = [
            Index(fields=['testimonial', 'is_primary']),  # Primary media for testimonial
            Index(fields=['media_type']),                 # Media type filtering
            Index(fields=['is_primary', 'order']),        # Ordering media
            Index(fields=['testimonial', 'media_type']),  # Testimonial media by type
        ]
    
    def __str__(self):
        return f"{self.get_media_type_display()} - {self.title or self.pk}"
    
    def clean(self):
        """Validate media file."""
        super().clean()
        
        if self.file:
            # Validate file size
            validate_file_size(self.file)
            
            # Validate and set media type
            if not self.media_type:
                self.media_type = get_file_type(self.file)
    
    def save(self, *args, **kwargs):
        # Auto-detect media type if not specified
        if self.file and not self.media_type:
            self.media_type = get_file_type(self.file)

        # Optimize text field processing
        if self.title is not None:
            self.title = self.title.strip()
        if self.description is not None:
            self.description = self.description.strip()

        # Handle primary media efficiently
        if self.is_primary and self.testimonial_id:
            # Use bulk update for better performance
            TestimonialMedia.objects.filter(
                testimonial_id=self.testimonial_id
            ).exclude(pk=self.pk).update(is_primary=False)

        # Use update_fields for better performance when possible
        if self.pk and 'update_fields' not in kwargs:
            kwargs['update_fields'] = ['file', 'media_type', 'title', 'description', 
                                     'is_primary', 'order', 'extra_data', 'updated_at']

        super().save(*args, **kwargs)
        
        # Invalidate cache after save
        if app_settings.USE_REDIS_CACHE:
            invalidate_testimonial_cache(testimonial_id=self.testimonial_id)
    
    def delete(self, *args, **kwargs):
        testimonial_id = self.testimonial_id
        super().delete(*args, **kwargs)
        
        # Invalidate cache after deletion
        if app_settings.USE_REDIS_CACHE:
            invalidate_testimonial_cache(testimonial_id=testimonial_id)