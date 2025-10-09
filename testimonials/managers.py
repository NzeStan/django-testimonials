# testimonials/managers.py - REFACTORED

"""
Refactored managers using mixins to eliminate duplication.
Includes the BUG FIX for optimized_for_api().
"""

from django.db import models
from django.db.models import Count, Avg, Q, Prefetch, Case, When, IntegerField
from django.utils import timezone

from .constants import TestimonialStatus, TestimonialSource, TestimonialMediaType
from .conf import app_settings

# Import mixins
from .mixins import (
    StatisticsAggregationMixin,
    TimePeriodFilterMixin,
    BulkOperationMixin
)


# === QUERYSETS ===

class TestimonialCategoryQuerySet(models.QuerySet):
    """QuerySet for TestimonialCategory with common filters."""
    
    def active(self):
        """Get only active categories."""
        return self.filter(is_active=True)
    
    def with_testimonial_counts(self):
        """Annotate with testimonial counts."""
        return self.annotate(
            testimonials_count=Count('testimonials')
        )


class TestimonialQuerySet(TimePeriodFilterMixin, models.QuerySet):
    """
    Optimized QuerySet for Testimonial model.
    Uses TimePeriodFilterMixin to avoid duplication.
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
        """Get published testimonials (approved or featured)."""
        return self.filter(
            status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
        )
    
    def verified(self):
        """Get verified testimonials."""
        return self.filter(is_verified=True)
    
    def by_rating(self, min_rating=None, max_rating=None):
        """Filter by rating range."""
        qs = self
        if min_rating is not None:
            qs = qs.filter(rating__gte=min_rating)
        if max_rating is not None:
            qs = qs.filter(rating__lte=max_rating)
        return qs
    
    def by_category(self, category_id):
        """Filter by category."""
        return self.filter(category_id=category_id)
    
    def by_author(self, user):
        """Filter by author."""
        return self.filter(author=user)
    
    def search(self, query):
        """Full-text search across multiple fields."""
        cleaned_query = get_search_query(query)
        if not cleaned_query:
            return self.none()
        
        return self.filter(
            Q(author_name__icontains=cleaned_query) |
            Q(company__icontains=cleaned_query) |
            Q(content__icontains=cleaned_query) |
            Q(title__icontains=cleaned_query)
        ).distinct()
    
    def optimized_for_api(self):
        """
        Optimized queryset for API responses.
        
        BUG FIX: Import TestimonialMedia to avoid NoneType error.
        """
        # Import here to avoid circular imports
        from .models import TestimonialMedia
        
        return self.select_related(
            'category',
            'author'
        ).prefetch_related(
            Prefetch(
                'media',
                # FIXED: Use TestimonialMedia.objects instead of models.QuerySet()
                queryset=TestimonialMedia.objects.order_by('-is_primary', 'order')
            )
        )
    
    def with_media_counts(self):
        """Annotate with media counts."""
        return self.annotate(media_count=Count('media'))


class TestimonialMediaQuerySet(models.QuerySet):
    """QuerySet for TestimonialMedia with common filters."""
    
    def images(self):
        """Get only image media."""
        return self.filter(media_type=TestimonialMediaType.IMAGE)
    
    def videos(self):
        """Get only video media."""
        return self.filter(media_type=TestimonialMediaType.VIDEO)
    
    def audios(self):
        """Get only audio media."""
        return self.filter(media_type=TestimonialMediaType.AUDIO)
    
    def documents(self):
        """Get only document media."""
        return self.filter(media_type=TestimonialMediaType.DOCUMENT)
    
    def primary_only(self):
        """Get only primary media items."""
        return self.filter(is_primary=True)
    
    def optimized_for_api(self):
        """Optimized queryset for API responses."""
        return self.select_related('testimonial').order_by('-is_primary', 'order')


# === MANAGERS ===

class TestimonialCategoryManager(StatisticsAggregationMixin, models.Manager):
    """
    Refactored manager for TestimonialCategory.
    Uses StatisticsAggregationMixin to eliminate duplication.
    """
    
    def get_queryset(self):
        return TestimonialCategoryQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def with_testimonial_counts(self):
        return self.get_queryset().with_testimonial_counts()
    
    def get_stats(self):
        """
        Get category statistics using mixin methods.
        Much cleaner than before!
        """
        base_stats = self.get_basic_aggregates({
            'total_categories': Count('id'),
            'active_categories': Count(Case(
                When(is_active=True, then=1),
                output_field=IntegerField()
            ))
        })
        
        # Get testimonial distribution per category
        categories_with_counts = list(
            self.with_testimonial_counts().values('id', 'name', 'testimonials_count')
        )
        
        return {
            **base_stats,
            'categories': categories_with_counts,
        }


class TestimonialManager(StatisticsAggregationMixin, BulkOperationMixin, models.Manager):
    """
    Refactored manager for Testimonial model.
    Uses multiple mixins to eliminate duplication.
    """
    
    def get_queryset(self):
        return TestimonialQuerySet(self.model, using=self._db)
    
    # Proxy queryset methods
    def pending(self):
        return self.get_queryset().pending()
    
    def approved(self):
        return self.get_queryset().approved()
    
    def rejected(self):
        return self.get_queryset().rejected()
    
    def featured(self):
        return self.get_queryset().featured()
    
    def archived(self):
        return self.get_queryset().archived()
    
    def published(self):
        return self.get_queryset().published()
    
    def verified(self):
        return self.get_queryset().verified()
    
    def by_rating(self, min_rating=None, max_rating=None):
        return self.get_queryset().by_rating(min_rating, max_rating)
    
    def by_category(self, category_id):
        return self.get_queryset().by_category(category_id)
    
    def by_author(self, user):
        return self.get_queryset().by_author(user)
    
    def search(self, query):
        return self.get_queryset().search(query)
    
    def optimized_for_api(self):
        return self.get_queryset().optimized_for_api()
    
    def with_media_counts(self):
        return self.get_queryset().with_media_counts()
    
    def get_stats(self):
        """
        Get comprehensive testimonial statistics.
        Refactored to use mixin methods - much cleaner!
        """
        # Basic aggregates using mixin
        base_stats = self.get_basic_aggregates({
            'total': Count('id'),
            'avg_rating': Avg('rating'),
        })
        
        # Status distribution using mixin
        status_dist = self.get_choice_distribution('status', TestimonialStatus.choices)
        
        # Source distribution using mixin
        source_dist = self.get_choice_distribution('source', TestimonialSource.choices)
        
        # Conditional counts using mixin
        feature_stats = self.get_conditional_counts({
            'verified': Q(is_verified=True),
            'anonymous': Q(is_anonymous=True),
            'with_response': Q(response__isnull=False) & ~Q(response=''),
            'with_media': Q(media__isnull=False),
        })
        
        # Rating distribution
        rating_dist = {}
        for i in range(1, app_settings.MAX_RATING + 1):
            rating_dist[str(i)] = self.filter(rating=i).count()
        
        return {
            **base_stats,
            'status_distribution': status_dist,
            'source_distribution': source_dist,
            'rating_distribution': rating_dist,
            **feature_stats,
        }
    
    def get_recent(self, limit=10):
        """Get recent testimonials."""
        return self.order_by('-created_at')[:limit]
    
    def get_top_rated(self, limit=10):
        """Get top-rated testimonials."""
        return self.published().order_by('-rating', '-created_at')[:limit]


class TestimonialMediaManager(StatisticsAggregationMixin, models.Manager):
    """
    Refactored manager for TestimonialMedia.
    Uses StatisticsAggregationMixin for cleaner stats.
    """
    
    def get_queryset(self):
        return TestimonialMediaQuerySet(self.model, using=self._db)
    
    # Proxy queryset methods
    def images(self):
        return self.get_queryset().images()
    
    def videos(self):
        return self.get_queryset().videos()
    
    def audios(self):
        return self.get_queryset().audios()
    
    def documents(self):
        return self.get_queryset().documents()
    
    def primary_only(self):
        return self.get_queryset().primary_only()
    
    def optimized_for_api(self):
        return self.get_queryset().optimized_for_api()
    
    def get_media_stats(self):
        """
        Get media statistics using mixin methods.
        Dramatically simplified from the original 100+ lines!
        """
        # Basic stats using mixin
        base_stats = self.get_basic_aggregates({
            'total_media': Count('id'),
        })
        
        # Media type distribution using mixin
        media_type_dist = self.get_choice_distribution('media_type', TestimonialMediaType.choices)
        
        # Boolean field counts using mixin
        primary_stats = self.get_boolean_field_counts('is_primary')
        
        # Null vs filled counts using mixin
        title_stats = self.get_null_vs_filled_counts('title')
        description_stats = self.get_null_vs_filled_counts('description')
        
        return {
            **base_stats,
            'media_type_distribution': media_type_dist,
            'primary_media': primary_stats['true_count'],
            'with_titles': title_stats['filled_count'],
            'with_descriptions': description_stats['filled_count'],
        }