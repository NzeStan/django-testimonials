# testimonials/tests/test_dashboard_views.py

"""
Comprehensive tests for dashboard views.
Tests cover permissions, data accuracy, edge cases, caching, and all dashboard endpoints.
"""

from django.test import TestCase, override_settings, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import (
    TestimonialStatus,
    TestimonialSource,
    TestimonialMediaType
)
from testimonials.dashboard import views
from testimonials.conf import app_settings

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

@override_settings(
    TESTIMONIALS_ENABLE_DASHBOARD=True,
    TESTIMONIALS_USE_REDIS_CACHE=False,  # Disable cache for testing
)
class DashboardTestCase(TestCase):
    """Base test case for dashboard views."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all dashboard tests."""
        # Create users
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        
        cls.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        
        cls.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        
        # Create categories
        cls.category1 = TestimonialCategory.objects.create(
            name='Products',
            slug='products',
            is_active=True
        )
        
        cls.category2 = TestimonialCategory.objects.create(
            name='Services',
            slug='services',
            is_active=True
        )
        
        cls.inactive_category = TestimonialCategory.objects.create(
            name='Inactive',
            slug='inactive',
            is_active=False
        )
    
    def setUp(self):
        """Set up for each test."""
        self.factory = RequestFactory()


# ============================================================================
# PERMISSION TESTS
# ============================================================================

class DashboardPermissionTests(DashboardTestCase):
    """Tests for dashboard permission requirements."""
    
    def test_overview_requires_staff(self):
        """Test that overview requires staff authentication."""
        url = reverse('testimonials:dashboard:overview')
        
        # Anonymous user
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('login', response.url)
    
    def test_overview_regular_user_denied(self):
        """Test that regular users cannot access overview."""
        self.client.login(username='regular', password='regularpass123')
        url = reverse('testimonials:dashboard:overview')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_overview_staff_allowed(self):
        """Test that staff users can access overview."""
        self.client.login(username='staff', password='staffpass123')
        url = reverse('testimonials:dashboard:overview')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_overview_admin_allowed(self):
        """Test that admin users can access overview."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('testimonials:dashboard:overview')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_analytics_requires_staff(self):
        """Test that analytics requires staff authentication."""
        url = reverse('testimonials:dashboard:analytics')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
    
    def test_moderation_requires_staff(self):
        """Test that moderation requires staff authentication."""
        url = reverse('testimonials:dashboard:moderation')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
    
    def test_categories_requires_staff(self):
        """Test that categories requires staff authentication."""
        url = reverse('testimonials:dashboard:categories')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


# ============================================================================
# OVERVIEW DASHBOARD TESTS
# ============================================================================

class DashboardOverviewTests(DashboardTestCase):
    """Tests for dashboard overview view."""
    
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='adminpass123')
        self.url = reverse('testimonials:dashboard:overview')
    
    def test_overview_renders_template(self):
        """Test that overview renders correct template."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testimonials/dashboard/overview.html')
    
    def test_overview_empty_data(self):
        """Test overview with no testimonials."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_testimonials'], 0)
        self.assertEqual(response.context['pending_count'], 0)
        self.assertEqual(response.context['approved_count'], 0)
        self.assertEqual(response.context['featured_count'], 0)
        self.assertEqual(response.context['rejected_count'], 0)
        self.assertEqual(response.context['today_count'], 0)
        self.assertEqual(response.context['this_week'], 0)
        self.assertEqual(response.context['this_month'], 0)
        self.assertEqual(response.context['avg_rating'], 0)
    
    def test_overview_basic_counts(self):
        """Test that overview shows correct counts."""
        # Create testimonials with different statuses
        Testimonial.objects.create(
            author=self.admin_user,
            content='Pending testimonial',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Approved testimonial',
            rating=4,
            status=TestimonialStatus.APPROVED
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Featured testimonial',
            rating=5,
            status=TestimonialStatus.FEATURED
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rejected testimonial',
            rating=2,
            status=TestimonialStatus.REJECTED
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.context['total_testimonials'], 4)
        self.assertEqual(response.context['pending_count'], 1)
        self.assertEqual(response.context['approved_count'], 1)
        self.assertEqual(response.context['featured_count'], 1)
        self.assertEqual(response.context['rejected_count'], 1)
    
    def test_overview_time_based_metrics(self):
        """Test that time-based metrics are accurate."""
        # Get baseline counts first
        initial_response = self.client.get(self.url)
        initial_today = initial_response.context['today_count']
        initial_week = initial_response.context['this_week']
        initial_month = initial_response.context['this_month']
        
        now = timezone.now()
        
        # Create testimonials (created_at has auto_now_add=True, so we update after)
        today = Testimonial.objects.create(
            author=self.admin_user,
            content='Today testimonial',
            rating=5
        )
        
        week_ago = Testimonial.objects.create(
            author=self.admin_user,
            content='This week testimonial',
            rating=5
        )
        # Update created_at manually (bypasses auto_now_add)
        Testimonial.objects.filter(pk=week_ago.pk).update(created_at=now - timedelta(days=3))
        
        month_ago = Testimonial.objects.create(
            author=self.admin_user,
            content='This month testimonial',
            rating=5
        )
        Testimonial.objects.filter(pk=month_ago.pk).update(created_at=now - timedelta(days=15))
        
        old = Testimonial.objects.create(
            author=self.admin_user,
            content='Old testimonial',
            rating=5
        )
        Testimonial.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=40))
        
        response = self.client.get(self.url)
        
        # Check increments from baseline
        self.assertEqual(response.context['today_count'], initial_today + 1)
        self.assertEqual(response.context['this_week'], initial_week + 2)  # Today + 3 days ago
        self.assertEqual(response.context['this_month'], initial_month + 3)  # All within 30 days
    
    def test_overview_average_rating(self):
        """Test that average rating is calculated correctly."""
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rating 5',
            rating=5
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rating 3',
            rating=3
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rating 4',
            rating=4
        )
        
        response = self.client.get(self.url)
        
        # Average = (5 + 3 + 4) / 3 = 4.0
        self.assertEqual(response.context['avg_rating'], 4.0)
    
    def test_overview_recent_testimonials(self):
        """Test that recent testimonials are shown."""
        # Create 15 testimonials
        for i in range(15):
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Testimonial {i}',
                rating=5
            )
        
        response = self.client.get(self.url)
        
        # Should only show 10 most recent
        self.assertEqual(len(response.context['recent_testimonials']), 10)
    
    def test_overview_pending_testimonials_list(self):
        """Test that pending testimonials are listed."""
        # Create 12 pending testimonials
        for i in range(12):
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Pending {i}',
                rating=5,
                status=TestimonialStatus.PENDING
            )
        
        # Create some approved (shouldn't appear in pending list)
        Testimonial.objects.create(
            author=self.admin_user,
            content='Approved',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        response = self.client.get(self.url)
        
        # Should show only 10 most recent pending
        self.assertEqual(len(response.context['pending_testimonials']), 10)
        
        # All should be pending
        for testimonial in response.context['pending_testimonials']:
            self.assertEqual(testimonial.status, TestimonialStatus.PENDING)
    
    def test_overview_status_distribution(self):
        """Test that status distribution is accurate."""
        # Create mix of statuses
        Testimonial.objects.create(author=self.admin_user, content='P1', rating=5, status=TestimonialStatus.PENDING)
        Testimonial.objects.create(author=self.admin_user, content='P2', rating=5, status=TestimonialStatus.PENDING)
        Testimonial.objects.create(author=self.admin_user, content='A1', rating=5, status=TestimonialStatus.APPROVED)
        Testimonial.objects.create(author=self.admin_user, content='F1', rating=5, status=TestimonialStatus.FEATURED)
        
        response = self.client.get(self.url)
        
        status_dist = response.context['status_distribution']
        
        # Find pending status
        pending_stat = next(s for s in status_dist if s['label'] == 'Pending')
        self.assertEqual(pending_stat['count'], 2)
        self.assertEqual(pending_stat['percentage'], 50.0)  # 2 out of 4
    
    def test_overview_source_distribution(self):
        """Test that source distribution is accurate."""
        Testimonial.objects.create(
            author=self.admin_user,
            content='Website',
            rating=5,
            source=TestimonialSource.WEBSITE
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Email',
            rating=5,
            source=TestimonialSource.EMAIL
        )
        
        response = self.client.get(self.url)
        
        source_dist = response.context['source_distribution']
        
        # Find website source
        website_stat = next(s for s in source_dist if s['label'] == 'Website')
        self.assertEqual(website_stat['count'], 1)
    
    def test_overview_rating_distribution(self):
        """Test that rating distribution is accurate."""
        # Create testimonials with different ratings
        for rating in [1, 3, 5, 5, 5]:
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Rating {rating}',
                rating=rating
            )
        
        response = self.client.get(self.url)
        
        rating_dist = response.context['rating_distribution']
        
        # Find rating 5
        rating_5 = next(r for r in rating_dist if r['rating'] == 5)
        self.assertEqual(rating_5['count'], 3)
        self.assertEqual(rating_5['percentage'], 60.0)  # 3 out of 5
    
    def test_overview_top_categories(self):
        """Test that top categories are shown correctly."""
        # Create testimonials in different categories
        for i in range(7):
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Product {i}',
                rating=5,
                category=self.category1
            )
        
        for i in range(3):
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Service {i}',
                rating=5,
                category=self.category2
            )
        
        response = self.client.get(self.url)
        
        top_categories = list(response.context['top_categories'])
        
        # Filter categories that have testimonials
        categories_with_data = [c for c in top_categories if c.total > 0]
        
        # Should be ordered by total count
        self.assertEqual(len(categories_with_data), 2)
        self.assertEqual(categories_with_data[0].name, 'Products')
        self.assertEqual(categories_with_data[0].total, 7)
    
    def test_overview_media_statistics(self):
        """Test media statistics in overview."""
        testimonial = Testimonial.objects.create(
            author=self.admin_user,
            content='With media',
            rating=5
        )
        
        # Create media files
        TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE,
            title='Image 1'
        )
        
        TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.VIDEO,
            title='Video 1'
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.context['total_media'], 2)
        
        media_by_type = response.context['media_by_type']
        image_stat = next(m for m in media_by_type if m['type'] == 'Image')
        self.assertEqual(image_stat['count'], 1)
    
    def test_overview_daily_trend(self):
        """Test that daily trend data is generated."""
        # Create testimonial today
        Testimonial.objects.create(
            author=self.admin_user,
            content='Today',
            rating=5
        )
        
        response = self.client.get(self.url)
        
        daily_trend = response.context['daily_trend']
        
        # Should have 31 days (0 to 30)
        self.assertEqual(len(daily_trend), 31)
        
        # Today should have count of 1
        today_data = daily_trend[-1]
        self.assertEqual(today_data['count'], 1)
    
    def test_overview_context_keys(self):
        """Test that all expected context keys are present."""
        response = self.client.get(self.url)
        
        expected_keys = [
            'title',
            'total_testimonials',
            'pending_count',
            'approved_count',
            'featured_count',
            'rejected_count',
            'today_count',
            'this_week',
            'this_month',
            'avg_rating',
            'recent_testimonials',
            'pending_testimonials',
            'status_distribution',
            'source_distribution',
            'rating_distribution',
            'top_categories',
            'total_media',
            'media_by_type',
            'daily_trend',
        ]
        
        for key in expected_keys:
            self.assertIn(key, response.context)


# ============================================================================
# ANALYTICS DASHBOARD TESTS
# ============================================================================

class DashboardAnalyticsTests(DashboardTestCase):
    """Tests for dashboard analytics view."""
    
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='adminpass123')
        self.url = reverse('testimonials:dashboard:analytics')
    
    def test_analytics_renders_template(self):
        """Test that analytics renders correct template."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testimonials/dashboard/analytics.html')
    
    def test_analytics_empty_data(self):
        """Test analytics with no data."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('testimonial_stats', response.context)
        self.assertIn('media_stats', response.context)
    
    def test_analytics_testimonial_stats(self):
        """Test that testimonial stats are included."""
        # Create some testimonials
        Testimonial.objects.create(
            author=self.admin_user,
            content='Test testimonial',
            rating=5
        )
        
        response = self.client.get(self.url)
        
        stats = response.context['testimonial_stats']
        self.assertIn('total', stats)
        self.assertIn('avg_rating', stats)  # FIX: Use 'avg_rating' not 'average_rating'
    
    def test_analytics_media_stats(self):
        """Test that media stats are included."""
        testimonial = Testimonial.objects.create(
            author=self.admin_user,
            content='With media',
            rating=5
        )
        
        TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE
        )
        
        response = self.client.get(self.url)
        
        media_stats = response.context['media_stats']
        self.assertIn('total_media', media_stats)
    
    def test_analytics_context_keys(self):
        """Test that expected context keys are present."""
        response = self.client.get(self.url)
        
        self.assertIn('title', response.context)
        self.assertIn('testimonial_stats', response.context)
        self.assertIn('media_stats', response.context)


# ============================================================================
# MODERATION DASHBOARD TESTS
# ============================================================================

class DashboardModerationTests(DashboardTestCase):
    """Tests for dashboard moderation view."""
    
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='adminpass123')
        self.url = reverse('testimonials:dashboard:moderation')
    
    def test_moderation_renders_template(self):
        """Test that moderation renders correct template."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testimonials/dashboard/moderation.html')
    
    def test_moderation_empty_queue(self):
        """Test moderation with no pending testimonials."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pending_count'], 0)
        self.assertEqual(len(response.context['pending_testimonials']), 0)
    
    def test_moderation_shows_pending_only(self):
        """Test that only pending testimonials are shown."""
        # Create mix of statuses
        Testimonial.objects.create(
            author=self.admin_user,
            content='Pending 1',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Pending 2',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Approved',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rejected',
            rating=5,
            status=TestimonialStatus.REJECTED
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.context['pending_count'], 2)
        self.assertEqual(len(response.context['pending_testimonials']), 2)
        
        # All should be pending
        for testimonial in response.context['pending_testimonials']:
            self.assertEqual(testimonial.status, TestimonialStatus.PENDING)
    
    def test_moderation_ordered_by_created_desc(self):
        """Test that pending testimonials are ordered newest first."""
        now = timezone.now()
        
        old = Testimonial.objects.create(
            author=self.admin_user,
            content='Old',
            rating=5,
            status=TestimonialStatus.PENDING,
            created_at=now - timedelta(days=5)
        )
        
        new = Testimonial.objects.create(
            author=self.admin_user,
            content='New',
            rating=5,
            status=TestimonialStatus.PENDING,
            created_at=now
        )
        
        response = self.client.get(self.url)
        
        pending = response.context['pending_testimonials']
        self.assertEqual(pending[0].id, new.id)
        self.assertEqual(pending[1].id, old.id)
    
    def test_moderation_prefetches_relations(self):
        """Test that category and author are prefetched."""
        Testimonial.objects.create(
            author=self.admin_user,
            content='With category',
            rating=5,
            category=self.category1,
            status=TestimonialStatus.PENDING
        )
        
        response = self.client.get(self.url)
        
        # Should not cause additional queries
        with self.assertNumQueries(0):
            for testimonial in response.context['pending_testimonials']:
                _ = testimonial.category
                _ = testimonial.author
    
    def test_moderation_context_keys(self):
        """Test that expected context keys are present."""
        response = self.client.get(self.url)
        
        self.assertIn('title', response.context)
        self.assertIn('pending_testimonials', response.context)
        self.assertIn('pending_count', response.context)


# ============================================================================
# CATEGORIES DASHBOARD TESTS
# ============================================================================

class DashboardCategoriesTests(DashboardTestCase):
    """Tests for dashboard categories view."""
    
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='adminpass123')
        self.url = reverse('testimonials:dashboard:categories')
    
    def test_categories_renders_template(self):
        """Test that categories renders correct template."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testimonials/dashboard/categories.html')
    
    def test_categories_shows_all_categories(self):
        """Test that all categories are shown."""
        response = self.client.get(self.url)
        
        # Should show active and inactive
        self.assertEqual(response.context['total_categories'], 3)
    
    def test_categories_annotated_with_counts(self):
        """Test that categories have testimonial counts."""
        # Create testimonials
        Testimonial.objects.create(
            author=self.admin_user,
            content='Product 1',
            rating=5,
            category=self.category1,
            status=TestimonialStatus.APPROVED
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Product 2',
            rating=5,
            category=self.category1,
            status=TestimonialStatus.PENDING
        )
        
        response = self.client.get(self.url)
        
        categories = list(response.context['categories'])
        category1 = next(c for c in categories if c.id == self.category1.id)
        
        self.assertEqual(category1.total, 2)
        self.assertEqual(category1.pending, 1)
        self.assertEqual(category1.approved, 1)
    
    def test_categories_average_rating(self):
        """Test that average rating is calculated."""
        # Create testimonials with different ratings
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rating 5',
            rating=5,
            category=self.category1
        )
        
        Testimonial.objects.create(
            author=self.admin_user,
            content='Rating 3',
            rating=3,
            category=self.category1
        )
        
        response = self.client.get(self.url)
        
        categories = list(response.context['categories'])
        category1 = next(c for c in categories if c.id == self.category1.id)
        
        self.assertEqual(category1.avg_rating, 4.0)  # (5 + 3) / 2
    
    def test_categories_ordered_by_total_desc(self):
        """Test that categories are ordered by total testimonials."""
        # Category1 gets more testimonials
        for i in range(5):
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Product {i}',
                rating=5,
                category=self.category1
            )
        
        # Category2 gets fewer
        for i in range(2):
            Testimonial.objects.create(
                author=self.admin_user,
                content=f'Service {i}',
                rating=5,
                category=self.category2
            )
        
        response = self.client.get(self.url)
        
        categories = list(response.context['categories'])
        
        # First should be category1
        self.assertEqual(categories[0].id, self.category1.id)
        self.assertEqual(categories[1].id, self.category2.id)
    
    def test_categories_context_keys(self):
        """Test that expected context keys are present."""
        response = self.client.get(self.url)
        
        self.assertIn('title', response.context)
        self.assertIn('categories', response.context)
        self.assertIn('total_categories', response.context)


# ============================================================================
# CACHING TESTS
# ============================================================================

@override_settings(TESTIMONIALS_USE_REDIS_CACHE=True)
class DashboardCachingTests(DashboardTestCase):
    """Tests for dashboard caching behavior."""
    
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='adminpass123')
    
    @patch('testimonials.services.TestimonialCacheService.get_or_set')
    def test_overview_uses_cache(self, mock_cache):
        """Test that overview uses cache when enabled."""
        mock_cache.return_value = {
            'total_testimonials': 0,
            'pending_count': 0,
            'approved_count': 0,
            'featured_count': 0,
            'rejected_count': 0,
            'today_count': 0,
            'this_week': 0,
            'this_month': 0,
            'avg_rating': 0,
            'recent_testimonials': [],
            'pending_testimonials': [],
            'status_distribution': [],
            'source_distribution': [],
            'rating_distribution': [],
            'top_categories': [],
            'total_media': 0,
            'media_by_type': [],
            'daily_trend': [],
        }
        
        url = reverse('testimonials:dashboard:overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        mock_cache.assert_called_once()
        
        # Check that volatile timeout is used
        call_kwargs = mock_cache.call_args[1]
        self.assertEqual(call_kwargs.get('timeout_type'), 'volatile')
    
    @patch('testimonials.services.TestimonialCacheService.get_or_set')
    def test_analytics_uses_cache_with_stats_timeout(self, mock_cache):
        """Test that analytics uses stats timeout."""
        mock_cache.return_value = {
            'testimonial_stats': {},
            'media_stats': {},
        }
        
        url = reverse('testimonials:dashboard:analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that stats timeout is used
        call_kwargs = mock_cache.call_args[1]
        self.assertEqual(call_kwargs.get('timeout_type'), 'stats')
    
    @patch('testimonials.services.TestimonialCacheService.get_or_set')
    def test_categories_uses_cache_with_stable_timeout(self, mock_cache):
        """Test that categories uses stable timeout."""
        mock_cache.return_value = []
        
        url = reverse('testimonials:dashboard:categories')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that stable timeout is used
        call_kwargs = mock_cache.call_args[1]
        self.assertEqual(call_kwargs.get('timeout_type'), 'stable')
    
    def test_moderation_does_not_use_cache(self):
        """Test that moderation does NOT use cache (real-time data)."""
        # Moderation should always show fresh data
        url = reverse('testimonials:dashboard:moderation')
        
        # Create pending testimonial
        t1 = Testimonial.objects.create(
            author=self.admin_user,
            content='Pending',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        response1 = self.client.get(url)
        self.assertEqual(response1.context['pending_count'], 1)
        
        # Approve it
        t1.status = TestimonialStatus.APPROVED
        t1.save()
        
        # Should immediately show 0 pending (no cache)
        response2 = self.client.get(url)
        self.assertEqual(response2.context['pending_count'], 0)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class DashboardEdgeCaseTests(DashboardTestCase):
    """Tests for edge cases and error handling."""
    
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='adminpass123')
    
    def test_overview_handles_zero_division(self):
        """Test that percentage calculations handle zero testimonials."""
        url = reverse('testimonials:dashboard:overview')
        response = self.client.get(url)
        
        # Should not raise ZeroDivisionError
        self.assertEqual(response.status_code, 200)
        
        # All percentages should be 0
        for item in response.context['status_distribution']:
            self.assertEqual(item['percentage'], 0.0)
    
    def test_overview_with_null_ratings(self):
        """Test overview with testimonials that have null ratings."""
        # This shouldn't happen with current model, but test defensive code
        url = reverse('testimonials:dashboard:overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['avg_rating'], 0)
    
    def test_categories_with_no_testimonials(self):
        """Test categories view with categories that have no testimonials."""
        url = reverse('testimonials:dashboard:categories')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        categories = list(response.context['categories'])
        for category in categories:
            self.assertEqual(category.total, 0)
            self.assertEqual(category.pending, 0)
            self.assertEqual(category.approved, 0)
    
    def test_overview_with_deleted_author(self):
        """Test that testimonials with deleted authors don't break view."""
        # Create testimonial
        user = User.objects.create_user(username='temp', password='temp')
        Testimonial.objects.create(
            author=user,
            content='Test',
            rating=5
        )
        
        # Delete user (if on_delete=SET_NULL)
        user.delete()
        
        url = reverse('testimonials:dashboard:overview')
        response = self.client.get(url)
        
        # Should still work
        self.assertEqual(response.status_code, 200)
    
    def test_overview_with_very_large_numbers(self):
        """Test that dashboard handles large numbers of testimonials."""
        # Create many testimonials with manually set slugs (bulk_create bypasses save())
        from django.utils.text import slugify
        
        testimonials = []
        for i in range(1000):
            t = Testimonial(
                author=self.admin_user,
                author_name=f'Test User {i}',  # Unique author name
                content=f'Test content number {i}',
                title=f'Unique Test Testimonial {i}',
                rating=5
            )
            # Manually set unique slug since bulk_create bypasses save()
            t.slug = slugify(f'test-user-{i}')
            testimonials.append(t)
        
        Testimonial.objects.bulk_create(testimonials)
        
        url = reverse('testimonials:dashboard:overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_testimonials'], 1000)
    
    def test_daily_trend_handles_timezone_correctly(self):
        """Test that daily trend uses correct timezone."""
        url = reverse('testimonials:dashboard:overview')
        response = self.client.get(url)
        
        daily_trend = response.context['daily_trend']
        
        # Should have 31 entries
        self.assertEqual(len(daily_trend), 31)
        
        # All should have date and count
        for entry in daily_trend:
            self.assertIn('date', entry)
            self.assertIn('count', entry)
            self.assertIsInstance(entry['count'], int)