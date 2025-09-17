from django.db import models
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .constants import TestimonialStatus


class TestimonialQuerySet(models.QuerySet):
    """
    Custom QuerySet for Testimonial model.
    """
    
    def pending(self):
        """Get pending testimonials."""
        return self.filter(status=TestimonialStatus.PENDING)
    
    def approved(self):
        """Get approved testimonials."""
        return self.filter(status=TestimonialStatus.APPROVED)
    
    def rejected(self):
        """Get rejected testimonials."""
        return self.filter(status=TestimonialStatus.REJECTED)
    
    def featured(self):
        """Get featured testimonials."""
        return self.filter(status=TestimonialStatus.FEATURED)
    
    def archived(self):
        """Get archived testimonials."""
        return self.filter(status=TestimonialStatus.ARCHIVED)
    
    def published(self):
        """Get all published testimonials (approved or featured)."""
        return self.filter(
            Q(status=TestimonialStatus.APPROVED) | Q(status=TestimonialStatus.FEATURED)
        )
    
    def created_by(self, user):
        """Get testimonials created by a specific user."""
        if user and user.is_authenticated:
            return self.filter(author=user)
        return self.none()
    
    def with_rating(self, min_rating=None, max_rating=None):
        """Get testimonials with a specific rating range."""
        queryset = self
        if min_rating is not None:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating is not None:
            queryset = queryset.filter(rating__lte=max_rating)
        return queryset
    
    def with_category(self, category_slug=None, category_id=None):
        """Get testimonials with a specific category."""
        if category_slug:
            return self.filter(category__slug=category_slug)
        if category_id:
            return self.filter(category_id=category_id)
        return self
    
    def with_date_range(self, start_date=None, end_date=None):
        """Get testimonials within a specific date range."""
        queryset = self
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        return queryset
    
    def search(self, query):
        """Search testimonials by content, author name, or company."""
        if not query:
            return self
        q = query.strip()
        return (
            self.filter(
                Q(content__icontains=q) |
                Q(author_name__icontains=q) |
                Q(company__icontains=q)
            )
            .distinct()
        )
    
    def get_stats(self):
        return {
            'total': self.count(),
            'average_rating': self.aggregate(Avg('rating'))['rating__avg'] or 0,
            'total_featured': self.featured().count(),
            'total_pending': self.pending().count(),
            'total_approved': self.approved().count(),
            'total_rejected': self.rejected().count(),
            'total_archived': self.archived().count(),
            'by_rating': {i: self.filter(rating=i).count() for i in range(1, 6)},
        }


class TestimonialManager(models.Manager):
    """
    Custom manager for the Testimonial model.
    """
    
    def get_queryset(self):
        """Return the custom queryset."""
        return TestimonialQuerySet(self.model, using=self._db)
    
    def pending(self):
        """Get pending testimonials."""
        return self.get_queryset().pending()
    
    def approved(self):
        """Get approved testimonials."""
        return self.get_queryset().approved()
    
    def rejected(self):
        """Get rejected testimonials."""
        return self.get_queryset().rejected()
    
    def featured(self):
        """Get featured testimonials."""
        return self.get_queryset().featured()
    
    def archived(self):
        """Get archived testimonials."""
        return self.get_queryset().archived()
    
    def published(self):
        """Get all published testimonials (approved or featured)."""
        return self.get_queryset().published()
    
    def created_by(self, user):
        """Get testimonials created by a specific user."""
        return self.get_queryset().created_by(user)
    
    def with_rating(self, min_rating=None, max_rating=None):
        """Get testimonials with a specific rating range."""
        return self.get_queryset().with_rating(min_rating, max_rating)
    
    def with_category(self, category_slug=None, category_id=None):
        """Get testimonials with a specific category."""
        return self.get_queryset().with_category(category_slug, category_id)
    
    def with_date_range(self, start_date=None, end_date=None):
        """Get testimonials within a specific date range."""
        return self.get_queryset().with_date_range(start_date, end_date)
    
    def search(self, query):
        """Search testimonials by content, author name, or company."""
        return self.get_queryset().search(query)
    
    def get_stats(self):
        """Get testimonial statistics."""
        return self.get_queryset().get_stats()
    
    def create_testimonial(self, **kwargs):
        """
        Create a new testimonial with appropriate status based on settings.
        
        If testimonials require approval, the status will be set to pending.
        Otherwise, it will be set to approved.
        """
        from .conf import app_settings
        
        # Set default status based on settings
        if 'status' not in kwargs:
            if app_settings.REQUIRE_APPROVAL:
                kwargs['status'] = TestimonialStatus.PENDING
            else:
                kwargs['status'] = TestimonialStatus.APPROVED
        
        return self.create(**kwargs)


class TestimonialCategoryManager(models.Manager):
    """
    Manager for the TestimonialCategory model.
    """
    
    def active(self):
        """Get active categories."""
        return self.filter(is_active=True)
    
    def with_testimonials_count(self):
        """Get categories with the count of published testimonials."""
        return self.annotate(
            testimonials_count=Count(
                'testimonials',
                filter=Q(
                    testimonials__status__in=[
                        TestimonialStatus.APPROVED,
                        TestimonialStatus.FEATURED
                    ]
                )
            )
        )


class TestimonialMediaManager(models.Manager):
    """
    Manager for the TestimonialMedia model.
    """
    
    def for_testimonial(self, testimonial):
        """Get media for a specific testimonial."""
        if hasattr(testimonial, 'id'):
            return self.filter(testimonial_id=testimonial.id)
        return self.filter(testimonial_id=testimonial)
    
    def images(self):
        """Get image media items."""
        from .constants import TestimonialMediaType
        return self.filter(media_type=TestimonialMediaType.IMAGE)
    
    def videos(self):
        """Get video media items."""
        from .constants import TestimonialMediaType
        return self.filter(media_type=TestimonialMediaType.VIDEO)
    
    def audios(self):
        """Get audio media items."""
        from .constants import TestimonialMediaType
        return self.filter(media_type=TestimonialMediaType.AUDIO)
    
    def documents(self):
        """Get document media items."""
        from .constants import TestimonialMediaType
        return self.filter(media_type=TestimonialMediaType.DOCUMENT)