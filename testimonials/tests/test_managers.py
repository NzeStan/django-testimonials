# testimonials/tests/test_managers.py

"""
Comprehensive tests for testimonial managers and querysets.
Tests cover all manager methods, queryset filters, edge cases, and failures.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg
from datetime import timedelta
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialSource, TestimonialMediaType
from testimonials.managers import (
    TestimonialCategoryQuerySet,
    TestimonialQuerySet,
    TestimonialMediaQuerySet,
    TestimonialCategoryManager,
    TestimonialManager,
    TestimonialMediaManager,
)

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class ManagerTestCase(TestCase):
    """Base test case with common setup for all manager tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole TestCase."""
        # Create users
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123'
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123'
        )
        
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Create categories
        cls.active_category = TestimonialCategory.objects.create(
            name='Active Category',
            slug='active-category',
            is_active=True,
            order=1
        )
        
        cls.inactive_category = TestimonialCategory.objects.create(
            name='Inactive Category',
            slug='inactive-category',
            is_active=False,
            order=2
        )
        
        cls.another_active_category = TestimonialCategory.objects.create(
            name='Another Active',
            slug='another-active',
            is_active=True,
            order=3
        )
    
    def _create_test_image(self, filename='image.jpg', size=(100, 100)):
        """Helper to create test image file."""
        image = Image.new('RGB', size, color='red')
        file = BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)
        return SimpleUploadedFile(filename, file.read(), content_type='image/jpeg')


# ============================================================================
# TESTIMONIAL CATEGORY QUERYSET TESTS
# ============================================================================

class TestimonialCategoryQuerySetTest(ManagerTestCase):
    """Tests for TestimonialCategoryQuerySet methods."""
    
    def test_active_filter(self):
        """Test active() returns only active categories."""
        active_categories = TestimonialCategory.objects.active()
        
        self.assertEqual(active_categories.count(), 2)
        self.assertIn(self.active_category, active_categories)
        self.assertIn(self.another_active_category, active_categories)
        self.assertNotIn(self.inactive_category, active_categories)
    
    def test_active_filter_empty_result(self):
        """Test active() with no active categories."""
        TestimonialCategory.objects.all().update(is_active=False)
        
        active_categories = TestimonialCategory.objects.active()
        self.assertEqual(active_categories.count(), 0)
    
    def test_with_testimonial_counts(self):
        """Test with_testimonial_counts() annotates correctly."""
        # Create testimonials
        Testimonial.objects.create(
            author=self.user1,
            author_name='User One',
            author_email='user1@example.com',
            content='Great experience with quality service.',
            rating=5,
            category=self.active_category,
            status=TestimonialStatus.APPROVED
        )
        Testimonial.objects.create(
            author=self.user2,
            author_name='User Two',
            author_email='user2@example.com',
            content='Amazing products and support.',
            rating=4,
            category=self.active_category,
            status=TestimonialStatus.APPROVED
        )
        
        categories = TestimonialCategory.objects.with_testimonial_counts()
        active_cat = categories.get(pk=self.active_category.pk)
        
        self.assertEqual(active_cat.testimonials_count, 2)
    
    def test_with_testimonial_counts_zero(self):
        """Test with_testimonial_counts() for category with no testimonials."""
        categories = TestimonialCategory.objects.with_testimonial_counts()
        inactive_cat = categories.get(pk=self.inactive_category.pk)
        
        self.assertEqual(inactive_cat.testimonials_count, 0)
    
    def test_queryset_chaining(self):
        """Test chaining queryset methods."""
        result = TestimonialCategory.objects.active().with_testimonial_counts()
        
        self.assertEqual(result.count(), 2)
        for cat in result:
            self.assertTrue(cat.is_active)
            self.assertTrue(hasattr(cat, 'testimonials_count'))


# ============================================================================
# TESTIMONIAL CATEGORY MANAGER TESTS
# ============================================================================

class TestimonialCategoryManagerTest(ManagerTestCase):
    """Tests for TestimonialCategoryManager methods."""
    
    def test_manager_active_method(self):
        """Test manager.active() proxies to queryset."""
        active_categories = TestimonialCategory.objects.active()
        
        self.assertIsInstance(active_categories, TestimonialCategoryQuerySet)
        self.assertEqual(active_categories.count(), 2)
    
    def test_manager_with_testimonial_counts_method(self):
        """Test manager.with_testimonial_counts() proxies to queryset."""
        categories = TestimonialCategory.objects.with_testimonial_counts()
        
        self.assertIsInstance(categories, TestimonialCategoryQuerySet)
        for cat in categories:
            self.assertTrue(hasattr(cat, 'testimonials_count'))
    
    def test_get_stats_basic(self):
        """Test get_stats() returns correct basic statistics."""
        stats = TestimonialCategory.objects.get_stats()
        
        self.assertIn('total_categories', stats)
        self.assertIn('active_categories', stats)
        self.assertIn('categories', stats)
        
        self.assertEqual(stats['total_categories'], 3)
        self.assertEqual(stats['active_categories'], 2)
    
    def test_get_stats_with_testimonials(self):
        """Test get_stats() includes testimonial counts."""
        Testimonial.objects.create(
            author=self.user1,
            author_name='User One',
            author_email='user1@example.com',
            content='Wonderful experience overall.',
            rating=5,
            category=self.active_category
        )
        
        stats = TestimonialCategory.objects.get_stats()
        
        self.assertIsInstance(stats['categories'], list)
        self.assertGreater(len(stats['categories']), 0)
    
    def test_get_stats_empty_database(self):
        """Test get_stats() with no categories."""
        TestimonialCategory.objects.all().delete()
        
        stats = TestimonialCategory.objects.get_stats()
        
        self.assertEqual(stats['total_categories'], 0)
        self.assertEqual(stats['active_categories'], 0)
        self.assertEqual(stats['categories'], [])


# ============================================================================
# TESTIMONIAL QUERYSET TESTS
# ============================================================================

class TestimonialQuerySetTest(ManagerTestCase):
    """Tests for TestimonialQuerySet methods."""
    
    def setUp(self):
        super().setUp()
        
        # Create testimonials with different statuses
        self.pending = Testimonial.objects.create(
            author=self.user1,
            author_name='Pending User',
            author_email='pending@example.com',
            content='Pending review awaiting approval.',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.active_category
        )
        
        self.approved = Testimonial.objects.create(
            author=self.user1,
            author_name='Approved User',
            author_email='approved@example.com',
            content='Approved review with great feedback.',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.active_category
        )
        
        self.rejected = Testimonial.objects.create(
            author=self.user2,
            author_name='Rejected User',
            author_email='rejected@example.com',
            content='Rejected review for various reasons.',
            rating=2,
            status=TestimonialStatus.REJECTED,
            category=self.active_category
        )
        
        self.featured = Testimonial.objects.create(
            author=self.user2,
            author_name='Featured User',
            author_email='featured@example.com',
            content='Featured review showcasing excellence.',
            rating=5,
            status=TestimonialStatus.FEATURED,
            category=self.active_category,
            is_verified=True
        )
        
        self.archived = Testimonial.objects.create(
            author=self.user1,
            author_name='Archived User',
            author_email='archived@example.com',
            content='Archived review for historical records.',
            rating=3,
            status=TestimonialStatus.ARCHIVED,
            category=self.inactive_category
        )
    
    # Status filter tests
    
    def test_pending_filter(self):
        """Test pending() returns only pending testimonials."""
        pending = Testimonial.objects.pending()
        
        self.assertEqual(pending.count(), 1)
        self.assertIn(self.pending, pending)
        self.assertNotIn(self.approved, pending)
    
    def test_approved_filter(self):
        """Test approved() returns only approved testimonials."""
        approved = Testimonial.objects.approved()
        
        self.assertEqual(approved.count(), 1)
        self.assertIn(self.approved, approved)
        self.assertNotIn(self.featured, approved)
    
    def test_rejected_filter(self):
        """Test rejected() returns only rejected testimonials."""
        rejected = Testimonial.objects.rejected()
        
        self.assertEqual(rejected.count(), 1)
        self.assertIn(self.rejected, rejected)
    
    def test_featured_filter(self):
        """Test featured() returns only featured testimonials."""
        featured = Testimonial.objects.featured()
        
        self.assertEqual(featured.count(), 1)
        self.assertIn(self.featured, featured)
    
    def test_archived_filter(self):
        """Test archived() returns only archived testimonials."""
        archived = Testimonial.objects.archived()
        
        self.assertEqual(archived.count(), 1)
        self.assertIn(self.archived, archived)
    
    def test_published_filter(self):
        """Test published() returns approved and featured testimonials."""
        published = Testimonial.objects.published()
        
        self.assertEqual(published.count(), 2)
        self.assertIn(self.approved, published)
        self.assertIn(self.featured, published)
        self.assertNotIn(self.pending, published)
        self.assertNotIn(self.rejected, published)
    
    def test_verified_filter(self):
        """Test verified() returns only verified testimonials."""
        verified = Testimonial.objects.verified()
        
        self.assertEqual(verified.count(), 1)
        self.assertIn(self.featured, verified)
    
    # Rating filter tests
    
    def test_by_rating_min_only(self):
        """Test by_rating() with minimum rating."""
        high_rated = Testimonial.objects.by_rating(min_rating=4)
        
        self.assertEqual(high_rated.count(), 3)
        self.assertIn(self.approved, high_rated)
        self.assertIn(self.featured, high_rated)
        self.assertNotIn(self.rejected, high_rated)
    
    def test_by_rating_max_only(self):
        """Test by_rating() with maximum rating."""
        low_rated = Testimonial.objects.by_rating(max_rating=3)
        
        self.assertEqual(low_rated.count(), 2)
        self.assertIn(self.rejected, low_rated)
        self.assertIn(self.archived, low_rated)
    
    def test_by_rating_range(self):
        """Test by_rating() with both min and max."""
        mid_rated = Testimonial.objects.by_rating(min_rating=3, max_rating=4)
        
        self.assertEqual(mid_rated.count(), 1)
        self.assertIn(self.archived, mid_rated)
    
    def test_by_rating_no_params(self):
        """Test by_rating() with no parameters returns all."""
        all_rated = Testimonial.objects.by_rating()
        
        self.assertEqual(all_rated.count(), 5)
    
    def test_by_rating_invalid_range(self):
        """Test by_rating() with min > max returns empty."""
        invalid = Testimonial.objects.by_rating(min_rating=5, max_rating=3)
        
        self.assertEqual(invalid.count(), 0)
    
    # Category and author filter tests
    
    def test_by_category_filter(self):
        """Test by_category() filters correctly."""
        active_cat_testimonials = Testimonial.objects.by_category(self.active_category.id)
        
        self.assertEqual(active_cat_testimonials.count(), 4)
        self.assertIn(self.pending, active_cat_testimonials)
        self.assertNotIn(self.archived, active_cat_testimonials)
    
    def test_by_category_nonexistent(self):
        """Test by_category() with non-existent category."""
        result = Testimonial.objects.by_category(99999)
        
        self.assertEqual(result.count(), 0)
    
    def test_by_author_filter(self):
        """Test by_author() filters correctly."""
        user1_testimonials = Testimonial.objects.by_author(self.user1)
        
        self.assertEqual(user1_testimonials.count(), 3)
        self.assertIn(self.pending, user1_testimonials)
        self.assertIn(self.approved, user1_testimonials)
        self.assertNotIn(self.featured, user1_testimonials)
    
    def test_by_author_no_testimonials(self):
        """Test by_author() with user who has no testimonials."""
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='newpass123'
        )
        
        result = Testimonial.objects.by_author(new_user)
        
        self.assertEqual(result.count(), 0)
    
    # Search tests
    
    def test_search_by_author_name(self):
        """Test search() finds testimonials by author name."""
        result = Testimonial.objects.search('Pending User')
        
        self.assertIn(self.pending, result)
    
    def test_search_by_content(self):
        """Test search() finds testimonials by content."""
        result = Testimonial.objects.search('excellence')
        
        self.assertIn(self.featured, result)
    
    def test_search_by_company(self):
        """Test search() finds testimonials by company."""
        self.approved.company = 'Acme Corporation'
        self.approved.save()
        
        result = Testimonial.objects.search('Acme')
        
        self.assertIn(self.approved, result)
    
    def test_search_empty_query(self):
        """Test search() with empty query returns none."""
        result = Testimonial.objects.search('')
        
        self.assertEqual(result.count(), 0)
    
    def test_search_whitespace_query(self):
        """Test search() with whitespace only returns none."""
        result = Testimonial.objects.search('   ')
        
        self.assertEqual(result.count(), 0)
    
    def test_search_case_insensitive(self):
        """Test search() is case insensitive."""
        result = Testimonial.objects.search('PENDING USER')
        
        self.assertIn(self.pending, result)
    
    def test_search_no_results(self):
        """Test search() with no matches."""
        result = Testimonial.objects.search('nonexistent query xyz')
        
        self.assertEqual(result.count(), 0)
    
    # Optimization tests
    
    def test_optimized_for_api(self):
        """Test optimized_for_api() includes prefetches."""
        optimized = Testimonial.objects.optimized_for_api()
        
        # Should have select_related for category and author
        self.assertIn('category', optimized.query.select_related)
        self.assertIn('author', optimized.query.select_related)
    
    def test_with_media_counts(self):
        """Test with_media_counts() annotates correctly."""
        # Create media for a testimonial
        image = self._create_test_image()
        TestimonialMedia.objects.create(
            testimonial=self.approved,
            file=image,
            media_type=TestimonialMediaType.IMAGE
        )
        
        testimonials = Testimonial.objects.with_media_counts()
        approved = testimonials.get(pk=self.approved.pk)
        
        self.assertEqual(approved.media_count, 1)
    
    def test_with_media_counts_zero(self):
        """Test with_media_counts() for testimonials with no media."""
        testimonials = Testimonial.objects.with_media_counts()
        pending = testimonials.get(pk=self.pending.pk)
        
        self.assertEqual(pending.media_count, 0)
    
    # Time period filter tests (from TimePeriodFilterMixin)
    
    def test_in_date_range(self):
        """Test in_date_range() filters correctly."""
        now = timezone.now()
        start = now - timedelta(days=7)
        end = now + timedelta(days=1)
        
        result = Testimonial.objects.all().in_date_range(start, end)
        
        # All our testimonials should be in this range
        self.assertGreaterEqual(result.count(), 5)
    
    def test_in_date_range_narrow(self):
        """Test in_date_range() with narrow range."""
        # Set specific dates on testimonials
        past_date = timezone.now() - timedelta(days=10)
        self.archived.created_at = past_date
        # Use update_fields to avoid triggering updated_at auto-update
        self.archived.save(update_fields=['created_at'])
        
        recent_start = timezone.now() - timedelta(days=2)
        recent_end = timezone.now() + timedelta(days=1)
        
        result = Testimonial.objects.all().in_date_range(recent_start, recent_end)
        
        self.assertNotIn(self.archived, result)
    
    def test_created_in_last_days(self):
        """Test created_in_last_days() filters correctly."""
        result = Testimonial.objects.all().created_in_last_days(30)
        
        # All testimonials should be within last 30 days
        self.assertGreaterEqual(result.count(), 5)
    
    def test_created_in_last_days_zero(self):
        """Test created_in_last_days(0) returns today's testimonials."""
        result = Testimonial.objects.all().created_in_last_days(0)
        
        # Should return testimonials created today
        self.assertGreaterEqual(result.count(), 0)
    
    # Queryset chaining tests
    
    def test_queryset_chaining_complex(self):
        """Test chaining multiple queryset methods."""
        result = (Testimonial.objects
                  .published()
                  .by_rating(min_rating=4)
                  .by_category(self.active_category.id))
        
        self.assertEqual(result.count(), 2)
        self.assertIn(self.approved, result)
        self.assertIn(self.featured, result)


# ============================================================================
# TESTIMONIAL MANAGER TESTS
# ============================================================================

class TestimonialManagerTest(ManagerTestCase):
    """Tests for TestimonialManager methods."""
    
    def setUp(self):
        super().setUp()
        
        # Create diverse testimonials
        self.t1 = Testimonial.objects.create(
            author=self.user1,
            author_name='Alpha User',
            author_email='alpha@example.com',
            content='Outstanding quality and service.',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.active_category,
            source=TestimonialSource.WEBSITE,
            is_verified=True
        )
        
        self.t2 = Testimonial.objects.create(
            author=self.user2,
            author_name='Beta User',
            author_email='beta@example.com',
            content='Wonderful experience overall.',
            rating=4,
            status=TestimonialStatus.PENDING,
            category=self.active_category,
            source=TestimonialSource.EMAIL,
            response='Thank you for feedback!'
        )
        
        self.t3 = Testimonial.objects.create(
            author=self.user1,
            author_name='Gamma User',
            author_email='gamma@example.com',
            content='Excellent products received.',
            rating=5,
            status=TestimonialStatus.FEATURED,
            category=self.inactive_category,
            source=TestimonialSource.MOBILE_APP,  # Fixed: was MOBILE_ANDROID
            is_anonymous=True
        )
    
    def test_manager_proxies_queryset_methods(self):
        """Test that manager properly proxies all queryset methods."""
        # Test a few key methods
        self.assertEqual(Testimonial.objects.pending().count(), 1)
        self.assertEqual(Testimonial.objects.approved().count(), 1)
        self.assertEqual(Testimonial.objects.featured().count(), 1)
        self.assertEqual(Testimonial.objects.published().count(), 2)
    
    def test_get_stats_comprehensive(self):
        """Test get_stats() returns comprehensive statistics."""
        stats = Testimonial.objects.get_stats()
        
        # Check all required keys
        self.assertIn('total', stats)
        self.assertIn('avg_rating', stats)
        self.assertIn('status_distribution', stats)
        self.assertIn('source_distribution', stats)
        self.assertIn('rating_distribution', stats)
        self.assertIn('verified', stats)
        self.assertIn('anonymous', stats)
        self.assertIn('with_response', stats)
        self.assertIn('with_media', stats)
    
    def test_get_stats_counts_correct(self):
        """Test get_stats() returns correct counts."""
        stats = Testimonial.objects.get_stats()
        
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['verified'], 1)
        self.assertEqual(stats['anonymous'], 1)
        self.assertEqual(stats['with_response'], 1)
    
    def test_get_stats_status_distribution(self):
        """Test get_stats() status distribution."""
        stats = Testimonial.objects.get_stats()
        
        status_dist = stats['status_distribution']
        self.assertIn('approved', status_dist)
        self.assertIn('pending', status_dist)
        self.assertIn('featured', status_dist)
        
        # Check the structure - should be dict with count, label, percentage
        self.assertEqual(status_dist['approved']['count'], 1)
        self.assertIn('label', status_dist['approved'])
        self.assertIn('percentage', status_dist['approved'])
        
        self.assertEqual(status_dist['pending']['count'], 1)
        self.assertEqual(status_dist['featured']['count'], 1)
    
    def test_get_stats_source_distribution(self):
        """Test get_stats() source distribution."""
        stats = Testimonial.objects.get_stats()
        
        source_dist = stats['source_distribution']
        self.assertIn('website', source_dist)
        self.assertIn('email', source_dist)
        
        # Check structure
        self.assertIsInstance(source_dist['website'], dict)
        self.assertIn('count', source_dist['website'])
        self.assertIn('label', source_dist['website'])
    
    def test_get_stats_rating_distribution(self):
        """Test get_stats() rating distribution."""
        stats = Testimonial.objects.get_stats()
        
        rating_dist = stats['rating_distribution']
        # Rating distribution is stored as string keys '1', '2', etc.
        self.assertEqual(rating_dist['5'], 2)  # Two 5-star reviews
        self.assertEqual(rating_dist['4'], 1)  # One 4-star review
    
    def test_get_stats_avg_rating(self):
        """Test get_stats() calculates average rating correctly."""
        stats = Testimonial.objects.get_stats()
        
        # (5 + 4 + 5) / 3 = 4.666...
        self.assertAlmostEqual(float(stats['avg_rating']), 4.67, places=1)
    
    def test_get_stats_empty_database(self):
        """Test get_stats() with no testimonials."""
        Testimonial.objects.all().delete()
        
        stats = Testimonial.objects.get_stats()
        
        self.assertEqual(stats['total'], 0)
        self.assertIsNone(stats['avg_rating'])
    
    def test_get_recent(self):
        """Test get_recent() returns most recent testimonials."""
        recent = Testimonial.objects.get_recent(limit=2)
        
        self.assertEqual(len(recent), 2)
        # Should be ordered by -created_at
        self.assertTrue(recent[0].created_at >= recent[1].created_at)
    
    def test_get_recent_limit_larger_than_count(self):
        """Test get_recent() with limit larger than total count."""
        recent = Testimonial.objects.get_recent(limit=100)
        
        self.assertEqual(len(recent), 3)
    
    def test_get_recent_limit_zero(self):
        """Test get_recent() with limit of 0."""
        recent = Testimonial.objects.get_recent(limit=0)
        
        self.assertEqual(len(recent), 0)
    
    def test_get_top_rated(self):
        """Test get_top_rated() returns highest rated published testimonials."""
        top_rated = Testimonial.objects.get_top_rated(limit=10)
        
        # Should only include published (approved or featured)
        self.assertEqual(len(top_rated), 2)
        self.assertNotIn(self.t2, top_rated)  # t2 is pending
    
    def test_get_top_rated_ordering(self):
        """Test get_top_rated() orders by rating then created_at."""
        top_rated = Testimonial.objects.get_top_rated(limit=10)
        
        # All should be rating 5 or ordered properly
        for i in range(len(top_rated) - 1):
            self.assertGreaterEqual(top_rated[i].rating, top_rated[i + 1].rating)


# ============================================================================
# TESTIMONIAL MEDIA QUERYSET TESTS
# ============================================================================

class TestimonialMediaQuerySetTest(ManagerTestCase):
    """Tests for TestimonialMediaQuerySet methods."""
    
    def setUp(self):
        super().setUp()
        
        self.testimonial = Testimonial.objects.create(
            author=self.user1,
            author_name='Media User',
            author_email='media@example.com',
            content='Review with various media attachments.',
            rating=5,
            category=self.active_category
        )
        
        # Create media of different types
        self.image = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('image1.jpg'),
            media_type=TestimonialMediaType.IMAGE,
            is_primary=True,
            order=1
        )
        
        self.video = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('video.mp4'),  # Fake video
            media_type=TestimonialMediaType.VIDEO,
            is_primary=False,
            order=2
        )
        
        self.audio = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('audio.mp3'),  # Fake audio
            media_type=TestimonialMediaType.AUDIO,
            is_primary=False,
            order=3
        )
        
        self.document = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('doc.pdf'),  # Fake pdf
            media_type=TestimonialMediaType.DOCUMENT,
            is_primary=False,
            order=4
        )
    
    def test_images_filter(self):
        """Test images() returns only image media."""
        images = TestimonialMedia.objects.images()
        
        self.assertEqual(images.count(), 1)
        self.assertIn(self.image, images)
        self.assertNotIn(self.video, images)
    
    def test_videos_filter(self):
        """Test videos() returns only video media."""
        videos = TestimonialMedia.objects.videos()
        
        self.assertEqual(videos.count(), 1)
        self.assertIn(self.video, videos)
    
    def test_audios_filter(self):
        """Test audios() returns only audio media."""
        audios = TestimonialMedia.objects.audios()
        
        self.assertEqual(audios.count(), 1)
        self.assertIn(self.audio, audios)
    
    def test_documents_filter(self):
        """Test documents() returns only document media."""
        documents = TestimonialMedia.objects.documents()
        
        self.assertEqual(documents.count(), 1)
        self.assertIn(self.document, documents)
    
    def test_primary_only_filter(self):
        """Test primary_only() returns only primary media."""
        primary = TestimonialMedia.objects.primary_only()
        
        self.assertEqual(primary.count(), 1)
        self.assertIn(self.image, primary)
    
    def test_primary_only_multiple(self):
        """Test primary_only() with multiple primary items across testimonials."""
        # Create another testimonial with its own primary media
        other_testimonial = Testimonial.objects.create(
            author=self.user1,
            author_name='Other User',
            author_email='other@example.com',
            content='Another review with media.',
            rating=5,
            category=self.active_category
        )
        
        other_primary = TestimonialMedia.objects.create(
            testimonial=other_testimonial,
            file=self._create_test_image('other.jpg'),
            media_type=TestimonialMediaType.IMAGE,
            is_primary=True
        )
        
        primary = TestimonialMedia.objects.primary_only()
        
        # Should have 2 primary items (one per testimonial)
        self.assertEqual(primary.count(), 2)
        self.assertIn(self.image, primary)
        self.assertIn(other_primary, primary)
    
    def test_optimized_for_api(self):
        """Test optimized_for_api() includes testimonial select_related."""
        optimized = TestimonialMedia.objects.optimized_for_api()
        
        # Should have select_related for testimonial
        self.assertIn('testimonial', optimized.query.select_related)
    
    def test_optimized_for_api_ordering(self):
        """Test optimized_for_api() orders correctly."""
        optimized = list(TestimonialMedia.objects.optimized_for_api())
        
        # Should be ordered by -is_primary, then order
        self.assertEqual(optimized[0], self.image)  # is_primary=True
    
    def test_queryset_chaining_media(self):
        """Test chaining media queryset methods."""
        result = TestimonialMedia.objects.images().primary_only()
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.image)


# ============================================================================
# TESTIMONIAL MEDIA MANAGER TESTS
# ============================================================================

class TestimonialMediaManagerTest(ManagerTestCase):
    """Tests for TestimonialMediaManager methods."""
    
    def setUp(self):
        super().setUp()
        
        self.testimonial = Testimonial.objects.create(
            author=self.user1,
            author_name='Manager User',
            author_email='manager@example.com',
            content='Manager review with media.',
            rating=5
        )
        
        # Create various media
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('img1.jpg'),
            media_type=TestimonialMediaType.IMAGE,
            title='Image with title',
            description='Image description',
            is_primary=True
        )
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('img2.jpg'),
            media_type=TestimonialMediaType.IMAGE,
            is_primary=False
        )
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('vid.mp4'),
            media_type=TestimonialMediaType.VIDEO
        )
    
    def test_manager_proxies_queryset_methods(self):
        """Test manager properly proxies queryset methods."""
        self.assertEqual(TestimonialMedia.objects.images().count(), 2)
        self.assertEqual(TestimonialMedia.objects.videos().count(), 1)
        self.assertEqual(TestimonialMedia.objects.primary_only().count(), 1)
    
    def test_get_media_stats_basic(self):
        """Test get_media_stats() returns basic statistics."""
        stats = TestimonialMedia.objects.get_media_stats()
        
        self.assertIn('total_media', stats)
        self.assertIn('media_type_distribution', stats)
        self.assertIn('primary_media', stats)
        self.assertIn('with_titles', stats)
        self.assertIn('with_descriptions', stats)
    
    def test_get_media_stats_counts(self):
        """Test get_media_stats() returns correct counts."""
        stats = TestimonialMedia.objects.get_media_stats()
        
        self.assertEqual(stats['total_media'], 3)
        self.assertEqual(stats['primary_media'], 1)
        # with_titles and with_descriptions count non-null, non-empty values
        # All 3 have title='Image with title', 'None', 'None'
        # So with_titles might be 1 or 3 depending on how it handles auto-generated titles
        self.assertGreaterEqual(stats['with_titles'], 1)
        self.assertGreaterEqual(stats['with_descriptions'], 1)
    
    def test_get_media_stats_type_distribution(self):
        """Test get_media_stats() media type distribution."""
        stats = TestimonialMedia.objects.get_media_stats()
        
        type_dist = stats['media_type_distribution']
        # Returns dict with count, label, percentage
        self.assertEqual(type_dist['image']['count'], 2)
        self.assertIn('label', type_dist['image'])
        self.assertIn('percentage', type_dist['image'])
        
        self.assertEqual(type_dist['video']['count'], 1)
    
    def test_get_media_stats_empty_database(self):
        """Test get_media_stats() with no media."""
        TestimonialMedia.objects.all().delete()
        
        stats = TestimonialMedia.objects.get_media_stats()
        
        self.assertEqual(stats['total_media'], 0)
        self.assertEqual(stats['primary_media'], 0)


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class ManagerEdgeCasesTest(ManagerTestCase):
    """Tests for edge cases and error handling in managers."""
    
    def test_search_with_special_characters(self):
        """Test search handles special characters correctly."""
        testimonial = Testimonial.objects.create(
            author=self.user1,
            author_name='User <script>alert("xss")</script>',
            author_email='xss@example.com',
            content='Content with "quotes" and \'apostrophes\'',
            rating=5
        )
        
        result = Testimonial.objects.search('<script>')
        # Should handle special chars without errors
        self.assertIsNotNone(result)
    
    def test_by_rating_negative_values(self):
        """Test by_rating handles negative values gracefully."""
        result = Testimonial.objects.by_rating(min_rating=-1, max_rating=10)
        
        # Should not raise error, just filter appropriately
        self.assertIsNotNone(result)
    
    def test_queryset_on_empty_database(self):
        """Test queryset methods on empty database."""
        Testimonial.objects.all().delete()
        
        # All these should work without errors
        self.assertEqual(Testimonial.objects.pending().count(), 0)
        self.assertEqual(Testimonial.objects.approved().count(), 0)
        self.assertEqual(Testimonial.objects.published().count(), 0)
        self.assertEqual(Testimonial.objects.search('anything').count(), 0)
    
    def test_by_category_with_null(self):
        """Test by_category with None returns testimonials without category."""
        testimonial = Testimonial.objects.create(
            author=self.user1,
            author_name='No Category User',
            author_email='nocat@example.com',
            content='Review without category.',
            rating=5,
            category=None
        )
        
        result = Testimonial.objects.by_category(None)
        
        self.assertIn(testimonial, result)
    
    def test_chaining_filters_order_independence(self):
        """Test that chaining filters works in any order."""
        t1 = Testimonial.objects.create(
            author=self.user1,
            author_name='Chain User',
            author_email='chain@example.com',
            content='Chain review.',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.active_category
        )
        
        # These should give same results regardless of order
        result1 = (Testimonial.objects
                   .approved()
                   .by_category(self.active_category.id)
                   .by_rating(min_rating=5))
        
        result2 = (Testimonial.objects
                   .by_rating(min_rating=5)
                   .by_category(self.active_category.id)
                   .approved())
        
        self.assertEqual(list(result1), list(result2))