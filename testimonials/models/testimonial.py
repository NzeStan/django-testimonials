from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import  Q, Index
import string
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone

from ..managers import (
    TestimonialManager, 
    TestimonialCategoryManager, 
    TestimonialMediaManager
)
from ..constants import (
    TestimonialStatus, 
    TestimonialSource, 
    TestimonialMediaType,
    AuthorTitle
)
from ..validators import (
    validate_rating, 
    validate_testimonial_content, 
    create_file_size_validator,
    create_avatar_size_validator,
    image_dimension_validator,
)
from ..utils import (
    get_unique_slug,
    generate_upload_path,
    get_file_type,
    invalidate_testimonial_cache,
    
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
        db_index=True,  # Index for faster filtering and sorting
        help_text=_("Name of the testimonial category (e.g., Products, Services, Events).")
    )
    slug = models.SlugField(
        max_length=120, 
        unique=True, 
        verbose_name=_("Slug"),
        db_index=True,  # Index for faster slug-based queries
        help_text=_("Unique identifier for the category, used in URLs.")
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Description"),
        help_text=_("Optional description providing more details about this category.")
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Is Active"),
        db_index=True,  # Index for active category filtering
        help_text=_("If checked, this category is active and can be assigned to testimonials.")
    )
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name=_("Order"),
        db_index=True,  # Index for ordering
        help_text=_("Controls the display order of categories. "
                    "Lower numbers appear first.")
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
        db_index=True,  # Index for user-based queries
        help_text=_("Registered user who submitted the testimonial. "
                    "Optional if testimonial is provided by a guest.")
    )
    author_name = models.CharField(
        max_length=255,
        verbose_name=_("Author Name"),
        blank=True,
        db_index=True,  # Index for author name searches
        help_text=_("Full name of the testimonial author if not linked to a user account.")
    )
    author_email = models.EmailField(
        blank=True,
        verbose_name=_("Author Email"),
        db_index=True,  # Index for email-based queries
        help_text=_("Email address of the testimonial author. "
                    "Useful for verification or follow-up communication.")
    )
    author_phone = PhoneNumberField(
        region=app_settings.DEFAULT_PHONE_REGION,
        blank=True,
        verbose_name=_("Author Phone"),
        help_text=_("Optional phone number of the testimonial author.")
    )
    author_title = models.CharField(
        max_length=255,
        choices=AuthorTitle.choices,
        blank=True,
        verbose_name=_("Author Title"),
        help_text=_("Professional title or role of the testimonial author.")
    )
    company = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Company"),
        db_index=True,  # Index for company-based searches
        help_text=_("Company or organization associated with the author, if applicable.")
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Location"),
        help_text=_("Geographical location of the testimonial author.")
    )
    avatar = models.ImageField(
        upload_to=generate_upload_path,
        blank=True,
        null=True,
        validators=[create_avatar_size_validator(), image_dimension_validator],
        verbose_name=_("Avatar"),
        help_text=_("Profile picture of the testimonial author.")
    )
    
    # Testimonial content with optimized text fields
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Title"),
        db_index=True,  # Index for title searches
        help_text=_("Short descriptive title for the testimonial.")
    )
    content = models.TextField(
        validators=[validate_testimonial_content],
        verbose_name=_("Content"),
        help_text=_("Full testimonial text provided by the author.")
        # Full-text search index would be added at database level
    )
    rating = models.PositiveSmallIntegerField(
        validators=[validate_rating],
        verbose_name=_("Rating"),
        db_index=True,
        help_text=_("Rating score given by the author, "
                    "from %(min)d to %(max)d stars.") % {
            'min': app_settings.MIN_RATING,
            'max': app_settings.MAX_RATING
        }
    )
    
    # Categorization and metadata with optimized relationships
    category = models.ForeignKey(
        'TestimonialCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        verbose_name=_("Category"),
        db_index=True,  # Index for category filtering
        help_text=_("Category under which this testimonial is grouped.")
    )
    source = models.CharField(
        max_length=30,
        choices=TestimonialSource.choices,
        default=TestimonialSource.WEBSITE,
        verbose_name=_("Source"),
        db_index=True,  # Index for source filtering
        help_text=_("Origin of the testimonial (e.g., Website, Mobile Apple, Email ).")
    )
    status = models.CharField(
        max_length=30,
        choices=TestimonialStatus.choices,
        default=TestimonialStatus.PENDING,
        verbose_name=_("Status"),
        db_index=True,  # Critical index for status filtering
        help_text=_("Moderation status of the testimonial.")
    )
    
    # Flags and options with optimized boolean fields
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name=_("Is Anonymous"),
        db_index=True,  # Index for anonymous filtering
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Is Verified"),
        db_index=True,  # Index for verified filtering
        help_text=_("Indicates whether this testimonial has been verified by an admin.")
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        db_index=True,  # Index for ordering
        help_text=_("Controls the order in which testimonials are displayed. "
                    "Lower numbers appear first.")
    )
    
    # Additional fields with optimized indexes
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name=_("Slug"),
        db_index=True,  # Index for slug-based queries
        help_text=_("Unique slug used for testimonial URLs.")
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_("IP Address"),
        help_text=_("IP address from which the testimonial was submitted.")
    )
    website = models.URLField(
        blank=True,
        verbose_name=_("Website"),
        help_text=_("Optional website link provided by the testimonial author.")
    )
    social_media = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Social Media"),
        help_text=_("Links to the author’s social media profiles (JSON format).")
    )
    
    # Moderation fields with optimized relationships
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Approved At"),
        db_index=True,  # Index for approval date queries
        help_text=_("Date and time when the testimonial was approved.")
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_testimonials',
        verbose_name=_("Approved By"),
        help_text=_("Admin user who approved this testimonial.")
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Rejection Reason"),
        help_text=_("Reason provided for rejecting the testimonial, if applicable.")
    )
    
    # Response field with optimized structure
    response = models.TextField(
        blank=True,
        verbose_name=_("Response"),
        help_text=_("Official response from the admin or company to this testimonial.")
    )
    response_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Response At"),
        help_text=_("Date and time when a response was made.")
    )
    response_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonial_responses',
        verbose_name=_("Response By"),
        help_text=_("Admin user who responded to the testimonial.")
    )

    # Extra fields for customization
    extra_data = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Extra Data"),
        help_text=_(
        "Optional JSON field for storing additional metadata related to the testimonial. "
        "Use this for custom attributes or integration-specific information."
    )
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
        """
        Anonymity is a DISPLAY concern only.
        Do NOT null author FK or wipe contact info here.
        Ensure author_name is never empty when anonymous (DB constraint).
        """
        if self.is_anonymous:
            if not (self.author_name or "").strip():
                self.author_name = _("Anonymous")
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
        db_index=True,  # Index for testimonial-based queries
        help_text=_("The testimonial this media file is attached to. "
                    "Deleting the testimonial will also delete its media files.")
    )
    file = models.FileField(
        upload_to=generate_upload_path,
        validators=[create_file_size_validator(file_type="media file")],  # Uses MAX_FILE_SIZE
        verbose_name=_("File"),
        help_text=_("Upload the media file.")
    )
    media_type = models.CharField(
        max_length=20,
        choices=TestimonialMediaType.choices,
        default=TestimonialMediaType.IMAGE,
        verbose_name=_("Media Type"),
        db_index=True,  # Index for media type filtering
        help_text=_("Type of media (e.g., image, video, document).")
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Title"),
        help_text=_("Optional short title for the media file.")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optional description or caption for the media file.")
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_("Is Primary"),
        db_index=True,  # Index for primary media queries
        help_text=_("Mark this as the primary or featured media for the testimonial.")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        db_index=True,  # Index for ordering
        help_text=_("Display order of the media files. "
                    "Lower numbers are shown first.")
    )
    
    # Extra data for thumbnails, metadata, etc.
    extra_data = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Extra Data"),
        help_text=_("Optional JSON field for storing additional metadata, "
                    "such as thumbnails, dimensions, or custom attributes.")
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
        """Validate media file and auto-detect type."""
        super().clean()
        
        if self.file and not self.media_type:
            # Auto-detect media type if not specified
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
            TestimonialMedia.objects.filter(
                testimonial_id=self.testimonial_id
            ).exclude(pk=self.pk).update(is_primary=False)

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