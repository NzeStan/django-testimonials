from django.db import models
from django.db.models import Avg, Count, Q, Prefetch, F, Case, When, IntegerField
from django.utils import timezone
from django.core.cache import cache
from .constants import TestimonialStatus
from .utils import get_cache_key, cache_get_or_set, get_search_query
from .conf import app_settings


class TestimonialQuerySet(models.QuerySet):
    """
    Optimized QuerySet for Testimonial model with advanced filtering and caching.
    """
    
    def pending(self):
        """Get pending testimonials with optimized query."""
        return self.filter(status=TestimonialStatus.PENDING)
    
    def approved(self):
        """Get approved testimonials with optimized query."""
        return self.filter(status=TestimonialStatus.APPROVED)
    
    def rejected(self):
        """Get rejected testimonials with optimized query."""
        return self.filter(status=TestimonialStatus.REJECTED)
    
    def featured(self):
        """Get featured testimonials with optimized query and caching."""
        def get_featured():
            return list(self.filter(status=TestimonialStatus.FEATURED)
                       .select_related('category', 'author')
                       .prefetch_related('media')
                       .order_by('-display_order', '-created_at'))
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('featured_testimonials')
            return cache_get_or_set(cache_key, get_featured, timeout=app_settings.CACHE_TIMEOUT)
        
        return get_featured()
    
    def archived(self):
        """Get archived testimonials with optimized query."""
        return self.filter(status=TestimonialStatus.ARCHIVED)
    
    def published(self):
        """Get all published testimonials (approved or featured) with optimization."""
        return self.filter(
            Q(status=TestimonialStatus.APPROVED) | Q(status=TestimonialStatus.FEATURED)
        ).select_related('category', 'author').prefetch_related('media')
    
    def created_by(self, user):
        """Get testimonials created by a specific user with caching."""
        if not user or not user.is_authenticated:
            return self.none()
        
        def get_user_testimonials():
            return list(self.filter(author=user)
                       .select_related('category')
                       .prefetch_related('media')
                       .order_by('-created_at'))
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('user_testimonials', user.id)
            return cache_get_or_set(cache_key, get_user_testimonials, 
                                  timeout=app_settings.CACHE_TIMEOUT // 2)
        
        return get_user_testimonials()
    
    def with_rating(self, min_rating=None, max_rating=None):
        """Get testimonials with a specific rating range using database indexes."""
        queryset = self
        if min_rating is not None:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating is not None:
            queryset = queryset.filter(rating__lte=max_rating)
        return queryset
    
    def with_category(self, category_slug=None, category_id=None):
        """Get testimonials with a specific category with optimized joins."""
        if category_slug:
            return self.filter(category__slug=category_slug).select_related('category')
        if category_id:
            return self.filter(category_id=category_id).select_related('category')
        return self
    
    def with_date_range(self, start_date=None, end_date=None):
        """Get testimonials within a specific date range using indexes."""
        queryset = self
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        return queryset
    
    def search(self, query):
        """Optimized full-text search with minimum length validation."""
        cleaned_query = get_search_query(query)
        if not cleaned_query:
            return self.none()
        
        # Use database-specific full-text search if available
        if hasattr(self.model, 'search_vector'):
            # PostgreSQL full-text search
            return self.filter(search_vector=cleaned_query)
        
        # Fallback to icontains search with optimization
        return (
            self.filter(
                Q(content__icontains=cleaned_query) |
                Q(author_name__icontains=cleaned_query) |
                Q(company__icontains=cleaned_query) |
                Q(title__icontains=cleaned_query)
            )
            .select_related('category', 'author')
            .distinct()
            [:app_settings.SEARCH_RESULTS_LIMIT]
        )
    
    def with_media(self):
        """Get testimonials that have media attachments."""
        return self.filter(media__isnull=False).distinct()
    
    def without_media(self):
        """Get testimonials without media attachments."""
        return self.filter(media__isnull=True)
    
    def with_response(self):
        """Get testimonials that have responses."""
        return self.exclude(response='').exclude(response__isnull=True)
    
    def without_response(self):
        """Get testimonials without responses."""
        return self.filter(Q(response='') | Q(response__isnull=True))
    
    def recent(self, days=30):
        """Get recent testimonials within specified days."""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)
    
    def high_rated(self, min_rating=4):
        """Get high-rated testimonials."""
        return self.with_rating(min_rating=min_rating)
    
    def verified_only(self):
        """Get only verified testimonials."""
        return self.filter(is_verified=True)
    
    def anonymous_only(self):
        """Get only anonymous testimonials."""
        return self.filter(is_anonymous=True)
    
    def non_anonymous_only(self):
        """Get only non-anonymous testimonials."""
        return self.filter(is_anonymous=False)
    
    def optimized_for_api(self):
        """
        Optimized queryset for API responses with all necessary relations preloaded.
        """
        return self.select_related(
            'category', 'author', 'approved_by', 'response_by'
        ).prefetch_related(
            Prefetch(
                'media',
                queryset=self.model.media.related.related_model.objects.order_by(
                    '-is_primary', 'order', '-created_at'
                )
            )
        )
    
    def optimized_for_admin(self):
        """
        Optimized queryset for admin interface with minimal data loading.
        """
        return self.select_related('category', 'author').only(
            'id', 'author_name', 'company', 'rating', 'status', 'created_at',
            'category__name', 'author__username', 'is_verified', 'is_anonymous'
        )
    
    def get_stats(self):
        """
        Get comprehensive testimonial statistics with caching.
        """
        def compute_stats():
            # Use aggregation for better performance
            basic_stats = self.aggregate(
                total=Count('id'),
                average_rating=Avg('rating'),
                total_featured=Count(Case(
                    When(status=TestimonialStatus.FEATURED, then=1),
                    output_field=IntegerField()
                )),
                total_pending=Count(Case(
                    When(status=TestimonialStatus.PENDING, then=1),
                    output_field=IntegerField()
                )),
                total_approved=Count(Case(
                    When(status=TestimonialStatus.APPROVED, then=1),
                    output_field=IntegerField()
                )),
                total_rejected=Count(Case(
                    When(status=TestimonialStatus.REJECTED, then=1),
                    output_field=IntegerField()
                )),
                total_archived=Count(Case(
                    When(status=TestimonialStatus.ARCHIVED, then=1),
                    output_field=IntegerField()
                )),
                total_with_media=Count(Case(
                    When(media__isnull=False, then=1),
                    output_field=IntegerField(),
                    distinct=True
                )),
                total_verified=Count(Case(
                    When(is_verified=True, then=1),
                    output_field=IntegerField()
                )),
                total_anonymous=Count(Case(
                    When(is_anonymous=True, then=1),
                    output_field=IntegerField()
                )),
            )
            
            # Rating distribution
            rating_distribution = {}
            for i in range(1, app_settings.MAX_RATING + 1):
                rating_distribution[i] = self.filter(rating=i).count()
            
            # Recent activity (last 30 days)
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_count = self.filter(created_at__gte=thirty_days_ago).count()
            
            return {
                **basic_stats,
                'by_rating': rating_distribution,
                'recent_30_days': recent_count,
                'average_rating': round(basic_stats['average_rating'] or 0, 2),
                'generated_at': timezone.now().isoformat(),
            }
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('stats')
            return cache_get_or_set(cache_key, compute_stats, 
                                  timeout=app_settings.CACHE_TIMEOUT * 2)
        
        return compute_stats()


class TestimonialManager(models.Manager):
    """
    Optimized manager for the Testimonial model with performance enhancements.
    """
    
    def get_queryset(self):
        """Return the optimized queryset."""
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
        """Get featured testimonials with caching."""
        return self.get_queryset().featured()
    
    def archived(self):
        """Get archived testimonials."""
        return self.get_queryset().archived()
    
    def published(self):
        """Get all published testimonials with optimization."""
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
    
    def recent(self, days=30):
        """Get recent testimonials."""
        return self.get_queryset().recent(days)
    
    def high_rated(self, min_rating=4):
        """Get high-rated testimonials."""
        return self.get_queryset().high_rated(min_rating)
    
    def get_stats(self):
        """Get testimonial statistics."""
        return self.get_queryset().get_stats()
    
    def create_testimonial(self, **kwargs):
        """
        Create a new testimonial with appropriate status based on settings.
        """
        # Set default status based on settings
        if 'status' not in kwargs:
            if app_settings.REQUIRE_APPROVAL:
                kwargs['status'] = TestimonialStatus.PENDING
            else:
                kwargs['status'] = TestimonialStatus.APPROVED
        
        return self.create(**kwargs)
    
    def bulk_update_status(self, testimonial_ids, status, user=None, **extra_fields):
        """
        Bulk update testimonial status with optimized database operations.
        
        Args:
            testimonial_ids: List of testimonial IDs
            status: New status
            user: User performing the action
            **extra_fields: Additional fields to update
        """
        update_fields = {'status': status, **extra_fields}
        
        if status == TestimonialStatus.APPROVED and user:
            update_fields.update({
                'approved_at': timezone.now(),
                'approved_by': user
            })
        
        # Use bulk_update for better performance
        testimonials = list(self.filter(id__in=testimonial_ids))
        
        for testimonial in testimonials:
            for field, value in update_fields.items():
                setattr(testimonial, field, value)
        
        self.bulk_update(testimonials, update_fields.keys(), batch_size=100)
        
        return len(testimonials)


class TestimonialCategoryQuerySet(models.QuerySet):
    """
    Optimized QuerySet for TestimonialCategory model.
    """
    
    def active(self):
        """Get active categories."""
        return self.filter(is_active=True)
    
    def with_testimonials_count(self, published_only=True):
        """
        Get categories with the count of testimonials with optimized aggregation.
        
        Args:
            published_only: If True, count only published testimonials
        """
        if published_only:
            filter_condition = Q(
                testimonials__status__in=[
                    TestimonialStatus.APPROVED,
                    TestimonialStatus.FEATURED
                ]
            )
        else:
            filter_condition = Q()
        
        return self.annotate(
            testimonials_count=Count(
                'testimonials',
                filter=filter_condition
            )
        ).order_by('order', 'name')
    
    def with_stats(self):
        """Get categories with comprehensive statistics."""
        return self.annotate(
            total_testimonials=Count('testimonials'),
            published_testimonials=Count(
                'testimonials',
                filter=Q(testimonials__status__in=[
                    TestimonialStatus.APPROVED,
                    TestimonialStatus.FEATURED
                ])
            ),
            pending_testimonials=Count(
                'testimonials',
                filter=Q(testimonials__status=TestimonialStatus.PENDING)
            ),
            average_rating=Avg('testimonials__rating'),
            latest_testimonial=models.Max('testimonials__created_at')
        )


class TestimonialCategoryManager(models.Manager):
    """
    Optimized manager for the TestimonialCategory model.
    """
    
    def get_queryset(self):
        """Return the optimized queryset."""
        return TestimonialCategoryQuerySet(self.model, using=self._db)
    
    def active(self):
        """Get active categories with caching."""
        def get_active_categories():
            return list(self.get_queryset().active().order_by('order', 'name'))
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('active_categories')
            return cache_get_or_set(cache_key, get_active_categories)
        
        return get_active_categories()
    
    def with_testimonials_count(self, published_only=True):
        """Get categories with testimonial counts."""
        def get_categories_with_counts():
            return list(self.get_queryset().with_testimonials_count(published_only))
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('categories_with_counts', published_only)
            return cache_get_or_set(cache_key, get_categories_with_counts)
        
        return get_categories_with_counts()
    
    def get_category_stats(self, category_id):
        """Get statistics for a specific category."""
        def compute_category_stats():
            try:
                category = self.with_stats().get(id=category_id)
                return {
                    'id': category.id,
                    'name': category.name,
                    'total_testimonials': category.total_testimonials,
                    'published_testimonials': category.published_testimonials,
                    'pending_testimonials': category.pending_testimonials,
                    'average_rating': round(category.average_rating or 0, 2),
                    'latest_testimonial': category.latest_testimonial,
                }
            except self.model.DoesNotExist:
                return None
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('category_stats', category_id)
            return cache_get_or_set(cache_key, compute_category_stats)
        
        return compute_category_stats()


class TestimonialMediaQuerySet(models.QuerySet):
    """
    Optimized QuerySet for TestimonialMedia model.
    """
    
    def for_testimonial(self, testimonial):
        """Get media for a specific testimonial with optimization."""
        testimonial_id = testimonial.id if hasattr(testimonial, 'id') else testimonial
        return self.filter(testimonial_id=testimonial_id).order_by('-is_primary', 'order', '-created_at')
    
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
    
    def primary_only(self):
        """Get only primary media items."""
        return self.filter(is_primary=True)
    
    def optimized_for_api(self):
        """Optimized queryset for API responses."""
        return self.select_related('testimonial').order_by('-is_primary', 'order', '-created_at')


class TestimonialMediaManager(models.Manager):
    """
    Optimized manager for the TestimonialMedia model.
    """
    
    def get_queryset(self):
        """Return the optimized queryset."""
        return TestimonialMediaQuerySet(self.model, using=self._db)
    
    def for_testimonial(self, testimonial):
        """Get media for a specific testimonial."""
        return self.get_queryset().for_testimonial(testimonial)
    
    def images(self):
        """Get image media items."""
        return self.get_queryset().images()
    
    def videos(self):
        """Get video media items."""
        return self.get_queryset().videos()
    
    def audios(self):
        """Get audio media items."""
        return self.get_queryset().audios()
    
    def documents(self):
        """Get document media items."""
        return self.get_queryset().documents()
    
    def primary_only(self):
        """Get only primary media items."""
        return self.get_queryset().primary_only()
    
    def get_media_stats(self):
        """Get media statistics with caching."""
        def compute_media_stats():
            from .constants import TestimonialMediaType
            
            stats = self.aggregate(
                total_media=Count('id'),
                total_images=Count(Case(
                    When(media_type=TestimonialMediaType.IMAGE, then=1),
                    output_field=IntegerField()
                )),
                total_videos=Count(Case(
                    When(media_type=TestimonialMediaType.VIDEO, then=1),
                    output_field=IntegerField()
                )),
                total_audios=Count(Case(
                    When(media_type=TestimonialMediaType.AUDIO, then=1),
                    output_field=IntegerField()
                )),
                total_documents=Count(Case(
                    When(media_type=TestimonialMediaType.DOCUMENT, then=1),
                    output_field=IntegerField()
                )),
                total_primary=Count(Case(
                    When(is_primary=True, then=1),
                    output_field=IntegerField()
                )),
            )
            
            return {
                **stats,
                'generated_at': timezone.now().isoformat(),
            }
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('media_stats')
            return cache_get_or_set(cache_key, compute_media_stats)
        
        return compute_media_stats()