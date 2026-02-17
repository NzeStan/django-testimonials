from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta

from ..models import Testimonial, TestimonialCategory, TestimonialMedia
from ..constants import TestimonialStatus, TestimonialSource, TestimonialMediaType
from ..conf import app_settings
from ..services import TestimonialCacheService


@staff_member_required
def dashboard_overview(request):
    """
    Main dashboard overview with key metrics and charts.
    Uses short timeout for volatile dashboard data.
    """
    
    def get_dashboard_data():
        now = timezone.now()
        
        # Basic counts
        total_testimonials = Testimonial.objects.count()
        pending_count = Testimonial.objects.filter(status=TestimonialStatus.PENDING).count()
        approved_count = Testimonial.objects.filter(status=TestimonialStatus.APPROVED).count()
        featured_count = Testimonial.objects.filter(status=TestimonialStatus.FEATURED).count()
        rejected_count = Testimonial.objects.filter(status=TestimonialStatus.REJECTED).count()
        
        # Time-based metrics
        today_count = Testimonial.objects.filter(created_at__date=now.date()).count()
        this_week = Testimonial.objects.filter(created_at__gte=now - timedelta(days=7)).count()
        this_month = Testimonial.objects.filter(created_at__gte=now - timedelta(days=30)).count()
        
        # Average rating
        avg_rating = Testimonial.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Recent testimonials
        recent_testimonials = Testimonial.objects.select_related(
            'category', 'author'
        ).order_by('-created_at')[:10]
        
        # Pending testimonials
        pending_testimonials = Testimonial.objects.filter(
            status=TestimonialStatus.PENDING
        ).select_related('category', 'author').order_by('-created_at')[:10]
        
        # Status distribution
        status_distribution = []
        for status_code, status_label in TestimonialStatus.choices:
            count = Testimonial.objects.filter(status=status_code).count()
            status_distribution.append({
                'label': status_label,
                'count': count,
                'percentage': round((count / max(total_testimonials, 1)) * 100, 1)
            })
        
        # Source distribution
        source_distribution = []
        for source_code, source_label in TestimonialSource.choices:
            count = Testimonial.objects.filter(source=source_code).count()
            source_distribution.append({
                'label': source_label,
                'count': count,
                'percentage': round((count / max(total_testimonials, 1)) * 100, 1)
            })
        
        # Rating distribution
        rating_distribution = []
        for rating in range(1, app_settings.MAX_RATING + 1):
            count = Testimonial.objects.filter(rating=rating).count()
            rating_distribution.append({
                'rating': rating,
                'count': count,
                'percentage': round((count / max(total_testimonials, 1)) * 100, 1)
            })
        
        # Top categories
        top_categories = TestimonialCategory.objects.annotate(
            total=Count('testimonials'),
            approved=Count('testimonials', filter=Q(testimonials__status__in=[
                TestimonialStatus.APPROVED, TestimonialStatus.FEATURED
            ])),
            avg_rating=Avg('testimonials__rating')
        ).order_by('-total')[:5]
        
        # Media statistics
        total_media = TestimonialMedia.objects.count()
        media_by_type = []
        for media_type, label in TestimonialMediaType.choices:
            count = TestimonialMedia.objects.filter(media_type=media_type).count()
            media_by_type.append({
                'type': label,
                'count': count,
                'percentage': round((count / max(total_media, 1)) * 100, 1)
            })
        
        # Last 30 days trend
        daily_trend = []
        for i in range(30, -1, -1):
            date = (now - timedelta(days=i)).date()
            count = Testimonial.objects.filter(created_at__date=date).count()
            daily_trend.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        return {
            'total_testimonials': total_testimonials,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'featured_count': featured_count,
            'rejected_count': rejected_count,
            'today_count': today_count,
            'this_week': this_week,
            'this_month': this_month,
            'avg_rating': round(avg_rating, 2),
            'recent_testimonials': recent_testimonials,
            'pending_testimonials': pending_testimonials,
            'status_distribution': status_distribution,
            'source_distribution': source_distribution,
            'rating_distribution': rating_distribution,
            'top_categories': top_categories,
            'total_media': total_media,
            'media_by_type': media_by_type,
            'daily_trend': daily_trend,
        }
    
    # Use semantic helper method for dashboard data (volatile)
    if app_settings.USE_CACHE:
        data = TestimonialCacheService.get_or_set(
            TestimonialCacheService.get_key('DASHBOARD_OVERVIEW'),
            get_dashboard_data,
            timeout_type='volatile' 
        )
    else:
        data = get_dashboard_data()
    
    context = {
        'title': _('Testimonials Dashboard'),
        **data
    }
    
    return render(request, 'testimonials/dashboard/overview.html', context)


@staff_member_required
def dashboard_analytics(request):
    """
    Advanced analytics view with detailed insights.
    Uses stats timeout for analytics data.
    """

    def get_analytics_data():
        now = timezone.now()

        # Basic stats
        total = Testimonial.objects.count()
        avg_rating = Testimonial.objects.aggregate(avg=Avg('rating'))['avg'] or 0

        # Status and feature counts
        approved_count = Testimonial.objects.filter(
            status__in=[TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]
        ).count()
        verified_count = Testimonial.objects.filter(is_verified=True).count()
        with_response_count = Testimonial.objects.exclude(
            response=''
        ).exclude(response__isnull=True).count()
        with_media_count = Testimonial.objects.filter(
            media__isnull=False
        ).distinct().count()
        high_rating_count = Testimonial.objects.filter(rating__gte=4).count()

        safe_total = max(total, 1)

        # Quality metrics
        quality_metrics = {
            'verified_percentage': round((verified_count / safe_total) * 100, 1),
            'high_rating_percentage': round((high_rating_count / safe_total) * 100, 1),
            'approval_rate': round((approved_count / safe_total) * 100, 1),
            'media_attachment_rate': round((with_media_count / safe_total) * 100, 1),
        }

        # Response stats
        response_stats = {
            'response_rate': round((with_response_count / safe_total) * 100, 1),
        }

        # Time-based analytics
        time_based = {
            'last_24_hours': {
                'total': Testimonial.objects.filter(
                    created_at__gte=now - timedelta(hours=24)
                ).count()
            },
            'last_7_days': {
                'total': Testimonial.objects.filter(
                    created_at__gte=now - timedelta(days=7)
                ).count()
            },
            'last_30_days': {
                'total': Testimonial.objects.filter(
                    created_at__gte=now - timedelta(days=30)
                ).count()
            },
            'last_year': {
                'total': Testimonial.objects.filter(
                    created_at__gte=now - timedelta(days=365)
                ).count()
            },
        }

        # Top companies
        top_companies = list(
            Testimonial.objects.exclude(company='').values('company').annotate(
                count=Count('id'),
                verified_count=Count('id', filter=Q(is_verified=True)),
                avg_rating=Avg('rating'),
            ).order_by('-count')[:10]
        )

        testimonial_stats = {
            'total': total,
            'average_rating': round(avg_rating, 1),
            'total_verified': verified_count,
            'quality_metrics': quality_metrics,
            'response_stats': response_stats,
            'time_based': time_based,
            'top_companies': top_companies,
        }

        # Media stats
        total_media = TestimonialMedia.objects.count()
        total_images = TestimonialMedia.objects.filter(
            media_type=TestimonialMediaType.IMAGE
        ).count()
        total_videos = TestimonialMedia.objects.filter(
            media_type=TestimonialMediaType.VIDEO
        ).count()

        # File size stats (approximate via DB if possible, otherwise defaults)
        safe_media_total = max(total_media, 1)
        media_stats = {
            'total_media': total_media,
            'total_images': total_images,
            'total_videos': total_videos,
            'size_stats': {
                'total_size_mb': 0,
                'average_size_mb': 0,
            },
        }

        return {
            'testimonial_stats': testimonial_stats,
            'media_stats': media_stats,
        }

    if app_settings.USE_CACHE:
        data = TestimonialCacheService.get_or_set(
            TestimonialCacheService.get_key('DASHBOARD_ANALYTICS'),
            get_analytics_data,
            timeout_type='stats'
        )
    else:
        data = get_analytics_data()

    context = {
        'title': _('Analytics'),
        **data
    }

    return render(request, 'testimonials/dashboard/analytics.html', context)


@staff_member_required
def dashboard_moderation(request):
    """
    Moderation queue view for quick testimonial review.
    No caching for real-time moderation data.
    """
    
    pending = Testimonial.objects.filter(
        status=TestimonialStatus.PENDING
    ).select_related('category', 'author').order_by('-created_at')
    
    context = {
        'title': _('Moderation Queue'),
        'pending_testimonials': pending,
        'pending_count': pending.count(),
    }
    
    return render(request, 'testimonials/dashboard/moderation.html', context)


@staff_member_required
def dashboard_categories(request):
    """
    Category management and statistics.
    Uses stable timeout for category data.
    """
    
    def get_categories_data():
        return TestimonialCategory.objects.annotate(
            total=Count('testimonials'),
            pending=Count('testimonials', filter=Q(testimonials__status=TestimonialStatus.PENDING)),
            approved=Count('testimonials', filter=Q(testimonials__status__in=[
                TestimonialStatus.APPROVED, TestimonialStatus.FEATURED
            ])),
            avg_rating=Avg('testimonials__rating')
        ).order_by('-total')
    
    if app_settings.USE_CACHE:
        categories = TestimonialCacheService.get_or_set(
            TestimonialCacheService.get_key('CATEGORY_STATS', id='dashboard'),
            get_categories_data,
            timeout_type='stable' 
        )
    else:
        categories = get_categories_data()
    
    context = {
        'title': _('Categories'),
        'categories': categories,
        'total_categories': len(categories) if hasattr(categories, '__len__') else categories.count(),
    }
    
    return render(request, 'testimonials/dashboard/categories.html', context)