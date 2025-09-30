from django.db import models
from django.db.models import Avg, Count, Q, Prefetch, Case, When, IntegerField, Max, Min, When
from django.utils import timezone
from django.core.cache import cache
from .constants import TestimonialStatus, TestimonialSource, TestimonialMediaType
from .utils import get_cache_key, cache_get_or_set, get_search_query
from .conf import app_settings
from datetime import timedelta
from django.db.models.functions import (
    TruncMonth,
    TruncWeek,
)
import os

            

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
        # Get the related model class for media
        media_model = self.model._meta.get_field('media').related_model
        
        return self.select_related(
            'category', 'author', 'approved_by', 'response_by'
        ).prefetch_related(
            Prefetch(
                'media',
                queryset=media_model.objects.order_by(
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
        Get comprehensive testimonial statistics with detailed analytics.
        """
        def compute_stats():
            
            # Basic aggregate stats
            basic_stats = self.aggregate(
                total=Count('id'),
                average_rating=Avg('rating'),
                min_rating=Min('rating'),
                max_rating=Max('rating'),
                
                # Status breakdown
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
                
                # Media and verification stats
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
                
                # Author-related stats
                total_with_authors=Count(Case(
                    When(author__isnull=False, then=1),
                    output_field=IntegerField()
                )),
                total_with_companies=Count(Case(
                    When(company__isnull=False, company__gt='', then=1),
                    output_field=IntegerField()
                )),
                total_with_locations=Count(Case(
                    When(location__isnull=False, location__gt='', then=1),
                    output_field=IntegerField()
                )),
                total_with_avatars=Count(Case(
                    When(avatar__isnull=False, avatar__gt='', then=1),
                    output_field=IntegerField()
                )),
                total_with_titles=Count(Case(
                    When(author_title__isnull=False, author_title__gt='', then=1),
                    output_field=IntegerField()
                )),
                
                # Response stats
                total_with_responses=Count(Case(
                    When(response__isnull=False, response__gt='', then=1),
                    output_field=IntegerField()
                )),
                
                # Website and social media
                total_with_websites=Count(Case(
                    When(website__isnull=False, website__gt='', then=1),
                    output_field=IntegerField()
                )),
                total_with_social_media=Count(Case(
                    When(social_media__isnull=False, then=1),
                    output_field=IntegerField()
                )),
            )
            
            # Rating distribution
            rating_distribution = {}
            for i in range(1, app_settings.MAX_RATING + 1):
                rating_distribution[str(i)] = self.filter(rating=i).count()
            
            # Status distribution (more detailed)
            status_distribution = {}
            for status_code, status_label in TestimonialStatus.choices:
                status_distribution[status_code] = self.filter(status=status_code).count()
            
            # Source distribution
            source_distribution = {}
            for source_code, source_label in TestimonialSource.choices:
                source_distribution[source_code] = self.filter(source=source_code).count()
            
            # Category distribution
            category_stats = list(
                self.values('category__name', 'category__id')
                .annotate(
                    count=Count('id'),
                    approved=Count(
                        'id',
                        filter=Q(status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED])
                    ),
                    avg_rating=Avg('rating'),
                    # FIXED: Proper verified count
                    verified_count=Count('id', filter=Q(is_verified=True))
                )
                .order_by('-count')
            )
            
            # Time-based analytics
            now = timezone.now()
            time_periods = {
                'last_24_hours': now - timedelta(hours=24),
                'last_7_days': now - timedelta(days=7),
                'last_30_days': now - timedelta(days=30),
                'last_90_days': now - timedelta(days=90),
                'last_6_months': now - timedelta(days=180),
                'last_year': now - timedelta(days=365),
            }
            
            time_based_stats = {}
            for period_name, start_date in time_periods.items():
                period_data = self.filter(created_at__gte=start_date).aggregate(
                    total=Count('id'),
                    approved=Count(Case(
                        When(status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED], then=1),
                        output_field=IntegerField()
                    )),
                    avg_rating=Avg('rating'),
                    with_media=Count(Case(
                        When(media__isnull=False, then=1),
                        output_field=IntegerField(),
                        distinct=True
                    ))
                )
                time_based_stats[period_name] = period_data
            
            # Monthly trend (last 12 months)
            monthly_trends = list(
                self.filter(created_at__gte=now - timedelta(days=365))
                .annotate(month=TruncMonth('created_at'))
                .values('month')
                .annotate(
                    total=Count('id'),
                    approved=Count(Case(
                        When(status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED], then=1),
                        output_field=IntegerField()
                    )),
                    avg_rating=Avg('rating'),
                    verified=Count(Case(
                        When(is_verified=True, then=1),
                        output_field=IntegerField()
                    ))
                )
                .order_by('month')
            )
            
            # Weekly trend (last 8 weeks)
            weekly_trends = list(
                self.filter(created_at__gte=now - timedelta(weeks=8))
                .annotate(week=TruncWeek('created_at'))
                .values('week')
                .annotate(
                    total=Count('id'),
                    approved=Count(Case(
                        When(status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED], then=1),
                        output_field=IntegerField()
                    )),
                    avg_rating=Avg('rating')
                )
                .order_by('week')
            )
            
            # Top companies by testimonial count
            top_companies = list(
                self.filter(company__isnull=False, company__gt='')
                .values('company')
                .annotate(
                    count=Count('id'),
                    avg_rating=Avg('rating'),
                    # FIXED: Count individual verified testimonials, not test truthiness
                    verified_count=Count('id', filter=Q(is_verified=True))
                )
                .order_by('-count')[:10]
            )
            
            # Top locations by testimonial count
            top_locations = list(
                self.filter(location__isnull=False, location__gt='')
                .values('location')
                .annotate(
                    count=Count('id'),
                    avg_rating=Avg('rating')
                )
                .order_by('-count')[:10]
            )
            
            # Author title distribution
            author_title_stats = list(
                self.filter(author_title__isnull=False, author_title__gt='')
                .values('author_title')
                .annotate(
                    count=Count('id'),
                    avg_rating=Avg('rating')
                )
                .order_by('-count')
            )
            
            # Media type breakdown
            from .models import TestimonialMedia
            media_stats = list(
                TestimonialMedia.objects.filter(testimonial__in=self)
                .values('media_type')
                .annotate(count=Count('id'))
                .order_by('-count')
            )
            
            # Response rate and time analysis
            approved_testimonials = self.filter(
                status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
            )
            response_stats = {
                'total_responses': self.filter(response__isnull=False, response__gt='').count(),
                'response_rate': 0,
                'avg_response_time_hours': None
            }
            
            if approved_testimonials.exists():
                total_approved = approved_testimonials.count()
                total_responded = approved_testimonials.filter(
                    response__isnull=False, response__gt=''
                ).count()
                response_stats['response_rate'] = round(
                    (total_responded / total_approved) * 100, 2
                ) if total_approved > 0 else 0
                
                # Calculate average response time
                responded_testimonials = approved_testimonials.filter(
                    response_at__isnull=False,
                    approved_at__isnull=False
                )
                if responded_testimonials.exists():
                    response_times = []
                    for testimonial in responded_testimonials:
                        time_diff = testimonial.response_at - testimonial.approved_at
                        response_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
                    
                    if response_times:
                        response_stats['avg_response_time_hours'] = round(
                            sum(response_times) / len(response_times), 2
                        )
            
            # Quality metrics
            quality_metrics = {
                'high_rating_percentage': round(
                    (self.filter(rating__gte=4).count() / max(basic_stats['total'], 1)) * 100, 2
                ),
                'verified_percentage': round(
                    (basic_stats['total_verified'] / max(basic_stats['total'], 1)) * 100, 2
                ),
                'approval_rate': round(
                    ((basic_stats['total_approved'] + basic_stats['total_featured']) / 
                    max(basic_stats['total'], 1)) * 100, 2
                ),
                'rejection_rate': round(
                    (basic_stats['total_rejected'] / max(basic_stats['total'], 1)) * 100, 2
                ),
                'media_attachment_rate': round(
                    (basic_stats['total_with_media'] / max(basic_stats['total'], 1)) * 100, 2
                ),
            }
            
            # Geographic diversity (unique locations)
            geographic_stats = {
                'unique_locations': self.filter(
                    location__isnull=False, location__gt=''
                ).values('location').distinct().count(),
                'unique_companies': self.filter(
                    company__isnull=False, company__gt=''
                ).values('company').distinct().count(),
            }
            
            # User engagement stats
            user_stats = {
                'registered_users': self.filter(author__isnull=False).values('author').distinct().count(),
                'guest_submissions': self.filter(author__isnull=True).count(),
                'repeat_users': self.filter(author__isnull=False)
                    .values('author')
                    .annotate(count=Count('id'))
                    .filter(count__gt=1)
                    .count(),
            }
            
            return {
                # Basic stats
                **basic_stats,
                'average_rating': round(basic_stats['average_rating'] or 0, 2),
                
                # Distributions
                'by_rating': rating_distribution,
                'by_status': status_distribution,
                'by_source': source_distribution,
                'by_category': category_stats,
                'by_author_title': author_title_stats,
                'by_media_type': media_stats,
                
                # Time-based analytics
                'time_based': time_based_stats,
                'monthly_trends': monthly_trends,
                'weekly_trends': weekly_trends,
                
                # Geographic and company data
                'top_companies': top_companies,
                'top_locations': top_locations,
                'geographic_stats': geographic_stats,
                
                # Quality and engagement metrics
                'quality_metrics': quality_metrics,
                'response_stats': response_stats,
                'user_stats': user_stats,
                
                # Meta information
                'generated_at': timezone.now().isoformat(),
                'total_categories': len(category_stats),
                'data_completeness': {
                    'with_companies_percentage': round(
                        (basic_stats['total_with_companies'] / max(basic_stats['total'], 1)) * 100, 2
                    ),
                    'with_locations_percentage': round(
                        (basic_stats['total_with_locations'] / max(basic_stats['total'], 1)) * 100, 2
                    ),
                    'with_avatars_percentage': round(
                        (basic_stats['total_with_avatars'] / max(basic_stats['total'], 1)) * 100, 2
                    ),
                    'with_websites_percentage': round(
                        (basic_stats['total_with_websites'] / max(basic_stats['total'], 1)) * 100, 2
                    ),
                }
            }
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('comprehensive_stats')
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
    
    # ADD MISSING METHODS FROM QUERYSET
    def optimized_for_api(self):
        """Optimized queryset for API responses with all necessary relations preloaded."""
        return self.get_queryset().optimized_for_api()
    
    def optimized_for_admin(self):
        """Optimized queryset for admin interface with minimal data loading."""
        return self.get_queryset().optimized_for_admin()
    
    def with_media(self):
        """Get testimonials that have media attachments."""
        return self.get_queryset().with_media()
    
    def without_media(self):
        """Get testimonials without media attachments."""
        return self.get_queryset().without_media()
    
    def with_response(self):
        """Get testimonials that have responses."""
        return self.get_queryset().with_response()
    
    def without_response(self):
        """Get testimonials without responses."""
        return self.get_queryset().without_response()
    
    def verified_only(self):
        """Get only verified testimonials."""
        return self.get_queryset().verified_only()
    
    def anonymous_only(self):
        """Get only anonymous testimonials."""
        return self.get_queryset().anonymous_only()
    
    def non_anonymous_only(self):
        """Get only non-anonymous testimonials."""
        return self.get_queryset().non_anonymous_only()
    
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
        """
        if published_only:
            testimonials_count = Count(
                Case(
                    When(
                        testimonials__status__in=[
                            TestimonialStatus.APPROVED,
                            TestimonialStatus.FEATURED
                        ],
                        then=1
                    ),
                    output_field=IntegerField()
                )
            )
        else:
            testimonials_count = Count('testimonials')
        
        return self.annotate(
            testimonials_count=testimonials_count
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
    
    # ADD MISSING METHOD FROM QUERYSET
    def optimized_for_api(self):
        """Optimized queryset for API responses."""
        return self.get_queryset().optimized_for_api()
    

    def get_media_stats(self):
        """
        Get comprehensive media statistics with detailed analytics and caching.
        """
        def compute_media_stats():
            
            
            # Basic media aggregate stats
            basic_stats = self.aggregate(
                total_media=Count('id'),
                
                # Media type breakdown
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
                
                # Primary media stats
                total_primary=Count(Case(
                    When(is_primary=True, then=1),
                    output_field=IntegerField()
                )),
                
                # Content availability
                total_with_titles=Count(Case(
                    When(title__isnull=False, title__gt='', then=1),
                    output_field=IntegerField()
                )),
                total_with_descriptions=Count(Case(
                    When(description__isnull=False, description__gt='', then=1),
                    output_field=IntegerField()
                )),
                total_with_extra_data=Count(Case(
                    When(extra_data__isnull=False, then=1),
                    output_field=IntegerField()
                )),
            )
            
            # Detailed media type distribution
            media_type_distribution = {}
            for media_code, media_label in TestimonialMediaType.choices:
                count = self.filter(media_type=media_code).count()
                media_type_distribution[media_code] = {
                    'count': count,
                    'label': media_label,
                    'percentage': round((count / max(basic_stats['total_media'], 1)) * 100, 2)
                }
            
            # File size analysis (requires iterating through files)
            size_stats = {
                'total_size_bytes': 0,
                'average_size_bytes': 0,
                'min_size_bytes': 0,
                'max_size_bytes': 0,
                'total_size_mb': 0,
                'average_size_mb': 0,
                'by_media_type': {}
            }
            
            media_files = self.filter(file__isnull=False).select_related('testimonial')
            file_sizes = []
            size_by_type = {}
            
            for media in media_files:
                try:
                    if media.file and hasattr(media.file, 'size'):
                        file_size = media.file.size
                    elif media.file and hasattr(media.file, 'path') and os.path.exists(media.file.path):
                        file_size = os.path.getsize(media.file.path)
                    else:
                        continue
                    
                    file_sizes.append(file_size)
                    
                    # Track by media type
                    if media.media_type not in size_by_type:
                        size_by_type[media.media_type] = []
                    size_by_type[media.media_type].append(file_size)
                    
                except (OSError, ValueError, AttributeError):
                    continue
            
            if file_sizes:
                total_size = sum(file_sizes)
                size_stats.update({
                    'total_size_bytes': total_size,
                    'average_size_bytes': round(total_size / len(file_sizes), 2),
                    'min_size_bytes': min(file_sizes),
                    'max_size_bytes': max(file_sizes),
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'average_size_mb': round((total_size / len(file_sizes)) / (1024 * 1024), 2),
                    'median_size_bytes': sorted(file_sizes)[len(file_sizes) // 2] if file_sizes else 0
                })
                
                # Size statistics by media type
                for media_type, sizes in size_by_type.items():
                    if sizes:
                        type_total = sum(sizes)
                        size_stats['by_media_type'][media_type] = {
                            'count': len(sizes),
                            'total_size_bytes': type_total,
                            'average_size_bytes': round(type_total / len(sizes), 2),
                            'min_size_bytes': min(sizes),
                            'max_size_bytes': max(sizes),
                            'total_size_mb': round(type_total / (1024 * 1024), 2),
                            'average_size_mb': round((type_total / len(sizes)) / (1024 * 1024), 2),
                            'percentage_of_total_size': round((type_total / total_size) * 100, 2) if total_size > 0 else 0
                        }
            
            # File extension analysis
            extension_stats = {}
            for media in media_files:
                try:
                    if media.file and hasattr(media.file, 'name'):
                        filename = media.file.name
                        extension = os.path.splitext(filename)[1].lower()
                        if extension:
                            if extension not in extension_stats:
                                extension_stats[extension] = {
                                    'count': 0,
                                    'media_types': set(),
                                    'total_size_bytes': 0
                                }
                            extension_stats[extension]['count'] += 1
                            extension_stats[extension]['media_types'].add(media.media_type)
                            
                            # Add file size if available
                            try:
                                if hasattr(media.file, 'size'):
                                    extension_stats[extension]['total_size_bytes'] += media.file.size
                                elif hasattr(media.file, 'path') and os.path.exists(media.file.path):
                                    extension_stats[extension]['total_size_bytes'] += os.path.getsize(media.file.path)
                            except (OSError, ValueError, AttributeError):
                                pass
                except (AttributeError, ValueError):
                    continue
            
            # Convert sets to lists for JSON serialization
            for ext, data in extension_stats.items():
                data['media_types'] = list(data['media_types'])
                data['size_mb'] = round(data['total_size_bytes'] / (1024 * 1024), 2)
            
            # Time-based media upload analytics
            now = timezone.now()
            time_periods = {
                'last_24_hours': now - timedelta(hours=24),
                'last_7_days': now - timedelta(days=7),
                'last_30_days': now - timedelta(days=30),
                'last_90_days': now - timedelta(days=90),
                'last_year': now - timedelta(days=365),
            }
            
            time_based_stats = {}
            for period_name, start_date in time_periods.items():
                period_media = self.filter(created_at__gte=start_date)
                period_stats = period_media.aggregate(
                    total=Count('id'),
                    images=Count(Case(
                        When(media_type=TestimonialMediaType.IMAGE, then=1),
                        output_field=IntegerField()
                    )),
                    videos=Count(Case(
                        When(media_type=TestimonialMediaType.VIDEO, then=1),
                        output_field=IntegerField()
                    )),
                    primary_media=Count(Case(
                        When(is_primary=True, then=1),
                        output_field=IntegerField()
                    ))
                )
                
                # Calculate size for this period
                period_sizes = []
                for media in period_media:
                    try:
                        if media.file and hasattr(media.file, 'size'):
                            period_sizes.append(media.file.size)
                        elif media.file and hasattr(media.file, 'path') and os.path.exists(media.file.path):
                            period_sizes.append(os.path.getsize(media.file.path))
                    except (OSError, ValueError, AttributeError):
                        continue
                
                period_stats['total_size_mb'] = round(sum(period_sizes) / (1024 * 1024), 2) if period_sizes else 0
                time_based_stats[period_name] = period_stats
            
            # Monthly upload trends (last 12 months)
            monthly_trends = list(
                self.filter(created_at__gte=now - timedelta(days=365))
                .annotate(month=TruncMonth('created_at'))
                .values('month')
                .annotate(
                    total=Count('id'),
                    images=Count(Case(
                        When(media_type=TestimonialMediaType.IMAGE, then=1),
                        output_field=IntegerField()
                    )),
                    videos=Count(Case(
                        When(media_type=TestimonialMediaType.VIDEO, then=1),
                        output_field=IntegerField()
                    )),
                    primary=Count(Case(
                        When(is_primary=True, then=1),
                        output_field=IntegerField()
                    ))
                )
                .order_by('month')
            )
            
            # Media per testimonial analysis
            testimonial_media_stats = list(
                self.values('testimonial_id')
                .annotate(
                    media_count=Count('id'),
                    has_primary=Count(Case(
                        When(is_primary=True, then=1),
                        output_field=IntegerField()
                    )),
                    media_types_count=Count('media_type', distinct=True)
                )
                .values('media_count', 'has_primary', 'media_types_count')
            )
            
            # Calculate media per testimonial distribution
            media_per_testimonial = {}
            for stat in testimonial_media_stats:
                count = stat['media_count']
                if count not in media_per_testimonial:
                    media_per_testimonial[count] = 0
                media_per_testimonial[count] += 1
            
            # Top testimonials by media count
            top_testimonials_by_media = list(
                self.values('testimonial_id', 'testimonial__title', 'testimonial__author_name')
                .annotate(media_count=Count('id'))
                .order_by('-media_count')[:10]
            )
            
            # Primary media analysis
            primary_media_stats = {
                'testimonials_with_primary': self.filter(is_primary=True)
                    .values('testimonial_id').distinct().count(),
                'testimonials_without_primary': self.exclude(
                    testimonial_id__in=self.filter(is_primary=True).values('testimonial_id')
                ).values('testimonial_id').distinct().count(),
                'multiple_primary_issues': 0  # Will be calculated below
            }
            
            # Check for testimonials with multiple primary media (data integrity issue)
            testimonials_with_multiple_primary = (
                self.filter(is_primary=True)
                .values('testimonial_id')
                .annotate(primary_count=Count('id'))
                .filter(primary_count__gt=1)
            )
            primary_media_stats['multiple_primary_issues'] = testimonials_with_multiple_primary.count()
            
            # Content completeness analysis
            content_completeness = {
                'with_titles_percentage': round(
                    (basic_stats['total_with_titles'] / max(basic_stats['total_media'], 1)) * 100, 2
                ),
                'with_descriptions_percentage': round(
                    (basic_stats['total_with_descriptions'] / max(basic_stats['total_media'], 1)) * 100, 2
                ),
                'with_extra_data_percentage': round(
                    (basic_stats['total_with_extra_data'] / max(basic_stats['total_media'], 1)) * 100, 2
                ),
                'primary_media_percentage': round(
                    (basic_stats['total_primary'] / max(basic_stats['total_media'], 1)) * 100, 2
                ),
            }
            
            # Quality metrics
            quality_metrics = {
                'average_media_per_testimonial': round(
                    basic_stats['total_media'] / max(
                        self.values('testimonial_id').distinct().count(), 1
                    ), 2
                ),
                'testimonials_with_media_count': self.values('testimonial_id').distinct().count(),
                'orphaned_media_count': 0,  # Media without valid testimonials
                'large_files_count': len([s for s in file_sizes if s >= 10 * 1024 * 1024]),   # ≥ 10 MB
                'medium_files_count': len([s for s in file_sizes if 100 * 1024 <= s < 10 * 1024 * 1024]),  # 100 KB – <10 MB
                'small_files_count': len([s for s in file_sizes if s < 100 * 1024]),          # < 100 KB
            }
            
            # Storage efficiency metrics
            storage_metrics = {
                'average_file_size_mb': size_stats.get('average_size_mb', 0),
                'largest_file_mb': round(size_stats.get('max_size_bytes', 0) / (1024 * 1024), 2),
                'smallest_file_mb': round(size_stats.get('min_size_bytes', 0) / (1024 * 1024), 2),
                'total_storage_used_gb': round(size_stats.get('total_size_bytes', 0) / (1024 * 1024 * 1024), 2),
                'estimated_monthly_growth_mb': 0  # Will be calculated from trends
            }
            
            # Calculate estimated monthly growth
            if len(monthly_trends) >= 2:
                recent_months = monthly_trends[-3:]  # Last 3 months
                if recent_months:
                    # This is a simplified calculation - in reality you'd want to calculate actual file sizes
                    avg_monthly_uploads = sum(month['total'] for month in recent_months) / len(recent_months)
                    avg_file_size_mb = size_stats.get('average_size_mb', 0)
                    storage_metrics['estimated_monthly_growth_mb'] = round(
                        avg_monthly_uploads * avg_file_size_mb, 2
                    )
            
            return {
                # Basic statistics
                **basic_stats,
                
                # Detailed breakdowns
                'media_type_distribution': media_type_distribution,
                'extension_stats': dict(sorted(extension_stats.items(), 
                                            key=lambda x: x[1]['count'], reverse=True)),
                
                # Size and storage analytics
                'size_stats': size_stats,
                'storage_metrics': storage_metrics,
                
                # Time-based analytics
                'time_based_stats': time_based_stats,
                'monthly_trends': monthly_trends,
                
                # Relationship analytics
                'media_per_testimonial_distribution': dict(sorted(media_per_testimonial.items())),
                'top_testimonials_by_media': top_testimonials_by_media,
                'primary_media_stats': primary_media_stats,
                
                # Quality and completeness
                'content_completeness': content_completeness,
                'quality_metrics': quality_metrics,
                
                # Meta information
                'generated_at': timezone.now().isoformat(),
                'total_file_extensions': len(extension_stats),
                'data_integrity': {
                    'files_with_size_info': len(file_sizes),
                    'files_without_size_info': basic_stats['total_media'] - len(file_sizes),
                    'multiple_primary_media_issues': primary_media_stats['multiple_primary_issues']
                }
            }
        
        if app_settings.USE_REDIS_CACHE:
            cache_key = get_cache_key('comprehensive_media_stats')
            return cache_get_or_set(cache_key, compute_media_stats, 
                                timeout=app_settings.CACHE_TIMEOUT * 3)  # Longer cache due to file operations
        
        return compute_media_stats()