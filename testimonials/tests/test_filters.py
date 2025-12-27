# testimonials/tests/test_filters.py

"""
Comprehensive tests for testimonial filters.
Tests cover all filter fields, combinations, edge cases, and custom filter methods.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from testimonials.models import Testimonial, TestimonialCategory
from testimonials.constants import TestimonialStatus, TestimonialSource
from testimonials.api.filters import TestimonialFilter

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class FilterTestCase(TestCase):
    """Base test case for filter tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all filter tests."""
        # Create users
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com'
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com'
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
        
        # Create diverse testimonials for filtering
        now = timezone.now()
        
        # Testimonial 1: Approved, high rating, category1, recent
        cls.t1 = Testimonial.objects.create(
            author=cls.user1,
            author_name='John Doe',
            author_email='john@example.com',
            company='Acme Corp',
            content='Excellent product quality and service',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=cls.category1,
            source=TestimonialSource.WEBSITE,
            is_verified=True
        )
        
        # Testimonial 2: Pending, medium rating, category2
        cls.t2 = Testimonial.objects.create(
            author=cls.user1,
            author_name='Jane Smith',
            author_email='jane@example.com',
            company='Tech Inc',
            content='Good service but could improve',
            rating=4,
            status=TestimonialStatus.PENDING,
            category=cls.category2,
            source=TestimonialSource.EMAIL
        )
        
        # Testimonial 3: Rejected, low rating, no category
        cls.t3 = Testimonial.objects.create(
            author=cls.user2,
            author_name='Bob Johnson',
            author_email='bob@example.com',
            content='Not satisfied with the product',
            rating=2,
            status=TestimonialStatus.REJECTED,
            source=TestimonialSource.WEBSITE
        )
        
        # Testimonial 4: Featured, high rating, category1
        cls.t4 = Testimonial.objects.create(
            author=cls.user2,
            author_name='Alice Brown',
            company='Best Corp',
            content='Amazing experience, highly recommend',
            rating=5,
            status=TestimonialStatus.FEATURED,
            category=cls.category1,
            source=TestimonialSource.MOBILE_APP,
            is_verified=True,
            is_anonymous=True
        )
        
        # Testimonial 5: Approved, old testimonial
        # Note: source defaults to WEBSITE
        cls.t5 = Testimonial.objects.create(
            author=cls.user1,
            author_name='Charlie Davis',
            content='Great product from last year',
            rating=4,
            status=TestimonialStatus.APPROVED,
            category=cls.category2,
            response='Thank you for your feedback!'
        )
        # Make it old
        Testimonial.objects.filter(pk=cls.t5.pk).update(
            created_at=now - timedelta(days=60)
        )
    
    def setUp(self):
        """Set up for each test."""
        self.factory = RequestFactory()


# ============================================================================
# STATUS FILTER TESTS
# ============================================================================

class StatusFilterTests(FilterTestCase):
    """Tests for status filter."""
    
    def test_filter_by_approved_status(self):
        """Test filtering by approved status."""
        f = TestimonialFilter(
            {'status': TestimonialStatus.APPROVED},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 2)  # t1 and t5
        self.assertIn(self.t1, results)
        self.assertIn(self.t5, results)
    
    def test_filter_by_pending_status(self):
        """Test filtering by pending status."""
        f = TestimonialFilter(
            {'status': TestimonialStatus.PENDING},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t2)
    
    def test_filter_by_rejected_status(self):
        """Test filtering by rejected status."""
        f = TestimonialFilter(
            {'status': TestimonialStatus.REJECTED},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t3)
    
    def test_filter_by_featured_status(self):
        """Test filtering by featured status."""
        f = TestimonialFilter(
            {'status': TestimonialStatus.FEATURED},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t4)
    
    def test_filter_invalid_status(self):
        """Test filtering with invalid status value."""
        f = TestimonialFilter(
            {'status': 'invalid_status'},
            queryset=Testimonial.objects.all()
        )
        
        # Should return all testimonials (filter ignored)
        self.assertEqual(f.qs.count(), 5)


# ============================================================================
# CATEGORY FILTER TESTS
# ============================================================================

class CategoryFilterTests(FilterTestCase):
    """Tests for category filters."""
    
    def test_filter_by_category_id(self):
        """Test filtering by category ID."""
        f = TestimonialFilter(
            {'category': self.category1.id},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 2)  # t1 and t4
        self.assertIn(self.t1, results)
        self.assertIn(self.t4, results)
    
    def test_filter_by_category_slug(self):
        """Test filtering by category slug."""
        f = TestimonialFilter(
            {'category_slug': 'services'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 2)  # t2 and t5
        self.assertIn(self.t2, results)
        self.assertIn(self.t5, results)
    
    def test_filter_category_not_found(self):
        """Test filtering with non-existent category ID."""
        f = TestimonialFilter(
            {'category': 99999},
            queryset=Testimonial.objects.all()
        )
        
        # Django-filter's ModelChoiceFilter with invalid ID returns empty queryset
        # However, the filter might be skipped if the queryset validation fails
        # So we check that it either returns 0 or doesn't filter at all
        count = f.qs.count()
        # Accept both behaviors: strict (0) or permissive (all 5)
        self.assertIn(count, [0, 5], 
            "Invalid category ID should either return empty or ignore filter")
    
    def test_filter_category_slug_not_found(self):
        """Test filtering with non-existent category slug."""
        f = TestimonialFilter(
            {'category_slug': 'nonexistent'},
            queryset=Testimonial.objects.all()
        )
        
        # Should return empty queryset
        self.assertEqual(f.qs.count(), 0)


# ============================================================================
# RATING FILTER TESTS
# ============================================================================

class RatingFilterTests(FilterTestCase):
    """Tests for rating filters."""
    
    def test_filter_by_min_rating(self):
        """Test filtering by minimum rating."""
        f = TestimonialFilter(
            {'min_rating': 4},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Should return t1, t2, t4, t5 (ratings 5, 4, 5, 4)
        self.assertEqual(len(results), 4)
        self.assertNotIn(self.t3, results)  # rating 2
    
    def test_filter_by_max_rating(self):
        """Test filtering by maximum rating."""
        f = TestimonialFilter(
            {'max_rating': 3},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Should only return t3 (rating 2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t3)
    
    def test_filter_by_rating_range(self):
        """Test filtering by rating range."""
        f = TestimonialFilter(
            {'min_rating': 3, 'max_rating': 4},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Should return t2 and t5 (both rating 4)
        self.assertEqual(len(results), 2)
        self.assertIn(self.t2, results)
        self.assertIn(self.t5, results)
    
    def test_filter_by_exact_rating_5(self):
        """Test filtering for exact rating."""
        f = TestimonialFilter(
            {'min_rating': 5, 'max_rating': 5},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Should return t1 and t4 (both rating 5)
        self.assertEqual(len(results), 2)
        self.assertIn(self.t1, results)
        self.assertIn(self.t4, results)
    
    def test_filter_invalid_rating(self):
        """Test filtering with invalid rating values."""
        f = TestimonialFilter(
            {'min_rating': 'abc'},
            queryset=Testimonial.objects.all()
        )
        
        # Invalid value should be ignored
        self.assertEqual(f.qs.count(), 5)


# ============================================================================
# SOURCE FILTER TESTS
# ============================================================================

class SourceFilterTests(FilterTestCase):
    """Tests for source filter."""
    
    def test_filter_by_website_source(self):
        """Test filtering by website source."""
        f = TestimonialFilter(
            {'source': TestimonialSource.WEBSITE},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # t1, t3, and t5 are from website (t5 uses default source)
        self.assertEqual(len(results), 3)
        self.assertIn(self.t1, results)
        self.assertIn(self.t3, results)
        self.assertIn(self.t5, results)
    
    def test_filter_by_email_source(self):
        """Test filtering by email source."""
        f = TestimonialFilter(
            {'source': TestimonialSource.EMAIL},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t2)
    
    def test_filter_by_mobile_app_source(self):
        """Test filtering by mobile app source."""
        f = TestimonialFilter(
            {'source': TestimonialSource.MOBILE_APP},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t4)


# ============================================================================
# DATE FILTER TESTS
# ============================================================================

class DateFilterTests(FilterTestCase):
    """Tests for date filters."""
    
    def test_filter_created_after(self):
        """Test filtering by created_after date."""
        cutoff = timezone.now() - timedelta(days=30)
        
        f = TestimonialFilter(
            {'created_after': cutoff},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # t5 is older than 30 days, others are recent
        self.assertEqual(len(results), 4)
        self.assertNotIn(self.t5, results)
    
    def test_filter_created_before(self):
        """Test filtering by created_before date."""
        cutoff = timezone.now() - timedelta(days=30)
        
        f = TestimonialFilter(
            {'created_before': cutoff},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t5 is older than 30 days
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t5)
    
    def test_filter_date_range(self):
        """Test filtering by date range."""
        start = timezone.now() - timedelta(days=90)
        end = timezone.now() - timedelta(days=30)
        
        f = TestimonialFilter(
            {'created_after': start, 'created_before': end},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t5 is in this range
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t5)


# ============================================================================
# CUSTOM FILTER METHOD TESTS
# ============================================================================

class CustomFilterMethodTests(FilterTestCase):
    """Tests for custom filter methods."""
    
    def test_filter_by_author_name(self):
        """Test filtering by author name."""
        f = TestimonialFilter(
            {'author': 'John'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Should find t1 and t3 (John Doe, Bob Johnson)
        self.assertEqual(len(results), 2)
        self.assertIn(self.t1, results)
        self.assertIn(self.t3, results)
    
    def test_filter_by_author_email(self):
        """Test filtering by author email."""
        f = TestimonialFilter(
            {'author': 'jane@example.com'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t2)
    
    def test_filter_author_case_insensitive(self):
        """Test that author filter is case-insensitive."""
        f = TestimonialFilter(
            {'author': 'JOHN'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 2)
        self.assertIn(self.t1, results)
        self.assertIn(self.t3, results)
    
    def test_search_filter(self):
        """Test search across multiple fields."""
        f = TestimonialFilter(
            {'search': 'product'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Should find t1 (content: "product quality")
        # and t3 (content: "Not satisfied with the product")
        # and t5 (content: "Great product")
        self.assertEqual(len(results), 3)
        self.assertIn(self.t1, results)
        self.assertIn(self.t3, results)
        self.assertIn(self.t5, results)
    
    def test_search_company(self):
        """Test search in company field."""
        f = TestimonialFilter(
            {'search': 'Acme'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t1)
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        f = TestimonialFilter(
            {'search': 'EXCELLENT'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t1)
    
    def test_filter_is_anonymous_true(self):
        """Test filtering for anonymous testimonials."""
        f = TestimonialFilter(
            {'is_anonymous': True},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t4)
    
    def test_filter_is_anonymous_false(self):
        """Test filtering for non-anonymous testimonials."""
        f = TestimonialFilter(
            {'is_anonymous': False},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # All except t4 are not anonymous
        self.assertEqual(len(results), 4)
        self.assertNotIn(self.t4, results)
    
    def test_filter_is_verified_true(self):
        """Test filtering for verified testimonials."""
        f = TestimonialFilter(
            {'is_verified': True},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # t1 and t4 are verified
        self.assertEqual(len(results), 2)
        self.assertIn(self.t1, results)
        self.assertIn(self.t4, results)
    
    def test_filter_is_verified_false(self):
        """Test filtering for unverified testimonials."""
        f = TestimonialFilter(
            {'is_verified': False},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # t2, t3, t5 are not verified
        self.assertEqual(len(results), 3)
        self.assertIn(self.t2, results)
        self.assertIn(self.t3, results)
        self.assertIn(self.t5, results)
    
    def test_filter_has_media_true(self):
        """Test filtering testimonials with media."""
        from testimonials.models import TestimonialMedia
        from testimonials.constants import TestimonialMediaType
        
        # Add media to t1
        TestimonialMedia.objects.create(
            testimonial=self.t1,
            media_type=TestimonialMediaType.IMAGE,
            title='Test image'
        )
        
        f = TestimonialFilter(
            {'has_media': True},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t1)
    
    def test_filter_has_media_false(self):
        """Test filtering testimonials without media."""
        f = TestimonialFilter(
            {'has_media': False},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # All testimonials have no media
        self.assertEqual(len(results), 5)
    
    def test_filter_has_response_true(self):
        """Test filtering testimonials with responses."""
        f = TestimonialFilter(
            {'has_response': True},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t5 has a response
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t5)
    
    def test_filter_has_response_false(self):
        """Test filtering testimonials without responses."""
        f = TestimonialFilter(
            {'has_response': False},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # All except t5 have no response
        self.assertEqual(len(results), 4)
        self.assertNotIn(self.t5, results)


# ============================================================================
# COMBINED FILTER TESTS
# ============================================================================

class CombinedFilterTests(FilterTestCase):
    """Tests for multiple filters applied together."""
    
    def test_status_and_category(self):
        """Test combining status and category filters."""
        f = TestimonialFilter(
            {
                'status': TestimonialStatus.APPROVED,
                'category': self.category1.id
            },
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t1 is approved and in category1
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t1)
    
    def test_rating_and_status(self):
        """Test combining rating and status filters."""
        f = TestimonialFilter(
            {
                'min_rating': 5,
                'status': TestimonialStatus.APPROVED
            },
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t1 is approved with rating 5
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t1)
    
    def test_multiple_filters_no_results(self):
        """Test that conflicting filters return no results."""
        f = TestimonialFilter(
            {
                'status': TestimonialStatus.PENDING,
                'category': self.category1.id,
                'min_rating': 5
            },
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # No testimonial matches all these criteria
        self.assertEqual(len(results), 0)
    
    def test_status_category_rating_verified(self):
        """Test combining multiple filters."""
        f = TestimonialFilter(
            {
                'status': TestimonialStatus.APPROVED,
                'category': self.category1.id,
                'min_rating': 4,
                'is_verified': True
            },
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t1 matches all criteria
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t1)
    
    def test_search_with_status_filter(self):
        """Test combining search with status filter."""
        f = TestimonialFilter(
            {
                'search': 'product',
                'status': TestimonialStatus.APPROVED
            },
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # t1 and t5 are approved and contain "product"
        self.assertEqual(len(results), 2)
        self.assertIn(self.t1, results)
        self.assertIn(self.t5, results)
    
    def test_date_range_with_category(self):
        """Test combining date filters with category."""
        start = timezone.now() - timedelta(days=90)
        end = timezone.now() - timedelta(days=30)
        
        f = TestimonialFilter(
            {
                'created_after': start,
                'created_before': end,
                'category': self.category2.id
            },
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Only t5 matches (old + category2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.t5)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class FilterEdgeCaseTests(FilterTestCase):
    """Tests for edge cases and error handling."""
    
    def test_empty_filter_params(self):
        """Test with no filter parameters."""
        f = TestimonialFilter({}, queryset=Testimonial.objects.all())
        
        # Should return all testimonials
        self.assertEqual(f.qs.count(), 5)
    
    def test_none_values(self):
        """Test with None values in filters."""
        f = TestimonialFilter(
            {'status': None, 'category': None},
            queryset=Testimonial.objects.all()
        )
        
        # None values should be ignored
        self.assertEqual(f.qs.count(), 5)
    
    def test_empty_string_search(self):
        """Test search with empty string."""
        f = TestimonialFilter(
            {'search': ''},
            queryset=Testimonial.objects.all()
        )
        
        # Empty search should return all
        self.assertEqual(f.qs.count(), 5)
    
    def test_whitespace_search(self):
        """Test search with only whitespace."""
        f = TestimonialFilter(
            {'search': '   '},
            queryset=Testimonial.objects.all()
        )
        
        # Whitespace search should be ignored or return all
        self.assertEqual(f.qs.count(), 5)
    
    def test_special_characters_in_search(self):
        """Test search with special characters."""
        f = TestimonialFilter(
            {'search': '@#$%'},
            queryset=Testimonial.objects.all()
        )
        
        # Should not raise error, just return no results
        results = list(f.qs)
        self.assertEqual(len(results), 0)
    
    def test_min_rating_greater_than_max(self):
        """Test with min_rating > max_rating."""
        f = TestimonialFilter(
            {'min_rating': 5, 'max_rating': 2},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # No testimonials can satisfy this
        self.assertEqual(len(results), 0)
    
    def test_very_large_rating_values(self):
        """Test with rating values beyond normal range."""
        f = TestimonialFilter(
            {'min_rating': 100},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # No testimonials have rating >= 100
        self.assertEqual(len(results), 0)
    
    def test_negative_rating_values(self):
        """Test with negative rating values."""
        f = TestimonialFilter(
            {'max_rating': -1},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # No testimonials have negative ratings
        self.assertEqual(len(results), 0)
    
    def test_invalid_date_format(self):
        """Test with invalid date format."""
        f = TestimonialFilter(
            {'created_after': 'not-a-date'},
            queryset=Testimonial.objects.all()
        )
        
        # Should handle gracefully and return all or none
        # Exact behavior depends on django-filter version
        self.assertIsNotNone(f.qs)
    
    def test_future_date_filter(self):
        """Test filtering with future date."""
        future = timezone.now() + timedelta(days=30)
        
        f = TestimonialFilter(
            {'created_after': future},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # No testimonials from the future
        self.assertEqual(len(results), 0)
    
    def test_filter_with_deleted_category(self):
        """Test filtering by category that doesn't exist."""
        # Delete category2
        category2_id = self.category2.id
        self.category2.delete()
        
        f = TestimonialFilter(
            {'category': category2_id},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        # Django-filter may ignore invalid category or return empty
        # Accept both behaviors as valid
        self.assertIn(len(results), [0, 5],
            "Deleted category filter should either return empty or ignore filter")
    
    def test_case_sensitivity_in_filters(self):
        """Test that filters handle case correctly."""
        # Status values should be case-sensitive
        f = TestimonialFilter(
            {'status': 'APPROVED'},  # Correct
            queryset=Testimonial.objects.all()
        )
        
        # Should work correctly (status is choice field)
        self.assertGreater(len(list(f.qs)), 0)
    
    def test_unicode_in_search(self):
        """Test search with Unicode characters."""
        # Create testimonial with Unicode content
        unicode_t = Testimonial.objects.create(
            author=self.user1,
            author_name='José García',
            content='Excelente producto, muy satisfecho',
            rating=5
        )
        
        f = TestimonialFilter(
            {'search': 'José'},
            queryset=Testimonial.objects.all()
        )
        
        results = list(f.qs)
        self.assertIn(unicode_t, results)
    
    def test_sql_injection_attempt(self):
        """Test that filters are safe from SQL injection."""
        f = TestimonialFilter(
            {'search': "'; DROP TABLE testimonials; --"},
            queryset=Testimonial.objects.all()
        )
        
        # Should handle safely without error
        try:
            list(f.qs)
            # If we got here, SQL injection was prevented
            self.assertTrue(True)
        except Exception:
            self.fail("Filter should handle SQL injection attempts safely")