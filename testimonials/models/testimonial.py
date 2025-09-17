from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
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
    validate_file_size,
    validate_file_extension
)
from ..utils import (
    get_unique_slug,
    generate_upload_path,
    get_file_type
)
from ..conf import app_settings
from .base import BaseModel


class TestimonialCategory(BaseModel):
    """
    Categories for testimonials.
    """
    __test__ = False
    name = models.CharField(
        max_length=100, 
        verbose_name=_("Name")
    )
    slug = models.SlugField(
        max_length=120, 
        unique=True, 
        verbose_name=_("Slug")
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Description")
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Is active")
    )
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name=_("Order")
    )
    
    objects = TestimonialCategoryManager()
    
    class Meta:
        verbose_name = _("Testimonial Category")
        verbose_name_plural = _("Testimonial Categories")
        ordering = ['order', 'name']
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.name:
            self.name = string.capwords(self.name.strip())

        # if slug already set, use it as base; else derive from 'name'
        slug_source_field = 'slug' if self.slug else 'name'
        self.slug = get_unique_slug(self, slug_source_field, max_length=120)
        super().save(*args, **kwargs)


class Testimonial(BaseModel):
    """
    Main testimonial model.
    """
    __test__ = False
    # Author information
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        verbose_name=_("User")
    )
    author_name = models.CharField(
        max_length=255,
        verbose_name=_("Author Name"),
        blank=True
    )
    author_email = models.EmailField(
        blank=True,
        verbose_name=_("Author Email")
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
        verbose_name=_("Company")
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
    
    # Testimonial content
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Title")
    )
    content = models.TextField(
        validators=[validate_testimonial_content],
        verbose_name=_("Content")
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(app_settings.MAX_RATING),
            validate_rating
        ],
        verbose_name=_("Rating")
    )
    
    # Categorization and metadata
    category = models.ForeignKey(
        'TestimonialCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        verbose_name=_("Category")
    )
    source = models.CharField(
        max_length=30,
        choices=TestimonialSource.CHOICES,
        default=TestimonialSource.DEFAULT,
        verbose_name=_("Source")
    )
    status = models.CharField(
        max_length=30,
        choices=TestimonialStatus.CHOICES,
        default=TestimonialStatus.DEFAULT,
        verbose_name=_("Status")
    )
    
    # Flags and options
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name=_("Is Anonymous")
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Is Verified")
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order")
    )
    
    # Additional fields
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name=_("Slug")
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
    social_media = models.URLField(
        blank=True,
        verbose_name=_("Social Media")
    )
    
    # Moderation fields
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Approved At")
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
    
    # Response field (for replies to testimonials)
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
        verbose_name=_("Extra Data")
    )
    
    # Manager
    objects = TestimonialManager()
    
    class Meta:
        verbose_name = _("Testimonial")
        verbose_name_plural = _("Testimonials")
        ordering = ['-display_order', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['rating']),
            models.Index(fields=['author_name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.author_name}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        # Normalize names/titles first
        if self.author_name:
            self.author_name = string.capwords(self.author_name.strip())
        if self.author_title:
            self.author_title = string.capwords(self.author_title.strip())

        # Prefill from user if present & not anonymous
        if self.author and not self.is_anonymous:
            if not self.author_name:
                if hasattr(self.author, "get_full_name") and self.author.get_full_name():
                    self.author_name = self.author.get_full_name()
                else:
                    self.author_name = self.author.username
            if not self.author_email and getattr(self.author, "email", None):
                self.author_email = self.author.email

        # Handle anonymity overrides
        if self.is_anonymous:
            self.author_name = _("Anonymous")
            self.author_email = ""
            self.author_phone = ""
            self.author = None
            self.avatar = None

        # Always enforce unique slug. If provided, base = slug; else base = author_name
        slug_source_field = 'slug' if self.slug else 'author_name'
        self.slug = get_unique_slug(self, slug_source_field, max_length=255)

        super().save(*args, **kwargs)

        
    @property
    def is_published(self):
        """Check if the testimonial is published (approved or featured)."""
        return self.status in [TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
    
    @property
    def has_media(self):
        """Check if the testimonial has any media attached."""
        return self.media.exists()
    
    @property
    def author_display(self):
        """Get the author display name, respecting anonymity."""
        if self.is_anonymous:
            return _("Anonymous")
        return self.author_name
    
    def approve(self, user=None):
        """
        Approve the testimonial.
        
        Args:
            user: The user approving the testimonial
        """
        from django.utils import timezone
        
        self.status = TestimonialStatus.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "approve", user)
    
    def reject(self, reason=None, user=None):
        """
        Reject the testimonial.
        
        Args:
            reason: The reason for rejection
            user: The user rejecting the testimonial
        """
        self.status = TestimonialStatus.REJECTED
        if reason:
            self.rejection_reason = reason
        self.save()
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "reject", user, notes=reason)
    
    def feature(self, user=None):
        """
        Feature the testimonial.
        
        Args:
            user: The user featuring the testimonial
        """
        self.status = TestimonialStatus.FEATURED
        self.save()
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "feature", user)
    
    def archive(self, user=None):
        """
        Archive the testimonial.
        
        Args:
            user: The user archiving the testimonial
        """
        self.status = TestimonialStatus.ARCHIVED
        self.save()
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "archive", user)
    
    def add_response(self, response_text, user=None):
        """
        Add a response to the testimonial.
        
        Args:
            response_text: The response text
            user: The user adding the response
        """
        from django.utils import timezone
        
        self.response = response_text
        self.response_at = timezone.now()
        self.response_by = user
        self.save()
        
        # Log the action
        from ..utils import log_testimonial_action
        log_testimonial_action(self, "add_response", user)
    
    def add_media(self, file_obj, title=None, description=None):
        """
        Add media to the testimonial.
        
        Args:
            file_obj: The file object
            title: Optional title for the media
            description: Optional description for the media
            
        Returns:
            The created TestimonialMedia instance
        """
        from ..utils import get_file_type
        
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
    Media files attached to testimonials (images, videos, etc.).
    """
    __test__ = False
    testimonial = models.ForeignKey(
        'Testimonial',
        on_delete=models.CASCADE,
        related_name='media',
        verbose_name=_("Testimonial")
    )
    file = models.FileField(
        upload_to=generate_upload_path,
        validators=[
            validate_file_size,
            validate_file_extension
        ],
        verbose_name=_("File")
    )
    media_type = models.CharField(
        max_length=20,
        choices=TestimonialMediaType.CHOICES,
        verbose_name=_("Media Type")
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
        verbose_name=_("Is Primary")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    
    objects = TestimonialMediaManager()
    
    class Meta:
        verbose_name = _("Testimonial Media")
        verbose_name_plural = _("Testimonial Media")
        ordering = ['-is_primary', 'order', '-created_at']
    
    def __str__(self):
        return f"{self.get_media_type_display()} - {self.title or self.pk}"
    
    def save(self, *args, **kwargs):
        # Auto-detect media type if not specified
        if not self.media_type:
            self.media_type = get_file_type(self.file)

        # Preserve original casing for title/description; just trim
        if self.title is not None:
            self.title = self.title.strip()
        if self.description is not None:
            self.description = self.description.strip()

        # If marked as primary, unset primary on siblings
        if self.is_primary and self.testimonial_id:
            TestimonialMedia.objects.filter(
                testimonial_id=self.testimonial_id
            ).exclude(pk=self.pk).update(is_primary=False)

        super().save(*args, **kwargs)
