"""
Tests for the testimonials app managers.
"""

import pytest
from django.utils import timezone
from django.db.models import Avg

from testimonials.models import Testimonial, TestimonialCategory
from testimonials.constants import TestimonialStatus
from testimonials.models import TestimonialMedia as MediaModel


@pytest.mark.django_db
class TestTestimonialManager:
    """Tests for the TestimonialManager."""
    
    def test_pending_method(self, testimonial, pending_testimonial):
        """Test the pending method."""
        pending = Testimonial.objects.pending()
        
        assert pending.count() == 1
        assert pending.first() == pending_testimonial
        assert testimonial not in pending
    
    def test_approved_method(self, testimonial, pending_testimonial):
        """Test the approved method."""
        approved = Testimonial.objects.approved()
        
        assert approved.count() == 1
        assert approved.first() == testimonial
        assert pending_testimonial not in approved
    
    def test_featured_method(self, testimonial, featured_testimonial):
        """Test the featured method."""
        featured = Testimonial.objects.featured()
        
        assert featured.count() == 1
        assert featured.first() == featured_testimonial
        assert testimonial not in featured
    
    def test_published_method(self, testimonial, pending_testimonial, featured_testimonial):
        """Test the published method."""
        published = Testimonial.objects.published()
        
        assert published.count() == 2
        assert testimonial in published
        assert featured_testimonial in published
        assert pending_testimonial not in published
    
    def test_created_by_method(self, user, testimonial, anonymous_testimonial):
        """Test the created_by method."""
        user_testimonials = Testimonial.objects.created_by(user)
        
        assert user_testimonials.count() == 1
        assert testimonial in user_testimonials
        assert anonymous_testimonial not in user_testimonials
    
    def test_with_rating_method(self, testimonial, featured_testimonial, anonymous_testimonial):
        """Test the with_rating method."""
        # Set up testimonials with different ratings
        testimonial.rating = 5
        testimonial.save()
        
        featured_testimonial.rating = 5
        featured_testimonial.save()
        
        anonymous_testimonial.rating = 3
        anonymous_testimonial.save()
        
        # Test min_rating
        high_rated = Testimonial.objects.with_rating(min_rating=4)
        assert high_rated.count() == 2
        assert testimonial in high_rated
        assert featured_testimonial in high_rated
        assert anonymous_testimonial not in high_rated
        
        # Test max_rating
        low_rated = Testimonial.objects.with_rating(max_rating=3)
        assert low_rated.count() == 1
        assert anonymous_testimonial in low_rated
        
        # Test both min and max
        mid_rated = Testimonial.objects.with_rating(min_rating=3, max_rating=4)
        assert mid_rated.count() == 1
        assert anonymous_testimonial in mid_rated
    
    def test_with_category_method(self, category, testimonial):
        """Test the with_category method."""
        # Create a new category
        new_category = TestimonialCategory.objects.create(
            name='Another Category',
            slug='another-category'
        )
        
        # Create testimonial in the new category
        another_testimonial = Testimonial.objects.create(
            author_name='Another User',
            content='This is another testimonial in a different category.',
            rating=4,
            category=new_category,
            status=TestimonialStatus.APPROVED
        )
        
        # Test filtering by category
        category_testimonials = Testimonial.objects.with_category(category_id=category.id)
        assert category_testimonials.count() == 1
        assert testimonial in category_testimonials
        assert another_testimonial not in category_testimonials
        
        # Test filtering by slug
        slug_testimonials = Testimonial.objects.with_category(category_slug=new_category.slug)
        assert slug_testimonials.count() == 1
        assert another_testimonial in slug_testimonials
    
    def test_search_method(self, testimonial, featured_testimonial, anonymous_testimonial):
        """Test the search method."""
        # Set specific content for search testing
        testimonial.content = "Unique content for search test"
        testimonial.save()
        
        featured_testimonial.company = "Searchable Company"
        featured_testimonial.save()
        
        anonymous_testimonial.author_name = "Anonymous Searchable User"
        anonymous_testimonial.save()
        
        # Search by content
        content_search = Testimonial.objects.search("Unique content")
        assert content_search.count() == 1
        assert testimonial in content_search
        
        # Search by company
        company_search = Testimonial.objects.search("Searchable Company")
        assert company_search.count() == 1
        assert featured_testimonial in company_search
        
        # Search by author name
        author_search = Testimonial.objects.search("Searchable User")
        assert author_search.count() == 1
        assert anonymous_testimonial in author_search
    
    def test_get_stats_method(self, testimonial, featured_testimonial, anonymous_testimonial, pending_testimonial):
        """Test the get_stats method."""
        # Set specific ratings
        testimonial.rating = 5
        testimonial.save()
        
        featured_testimonial.rating = 5
        featured_testimonial.save()
        
        anonymous_testimonial.rating = 3
        anonymous_testimonial.save()
        
        pending_testimonial.rating = 4
        pending_testimonial.status = TestimonialStatus.REJECTED
        pending_testimonial.save()
        
        # Get stats
        stats = Testimonial.objects.get_stats()
        
        assert stats['total'] == 4
        assert stats['total_approved'] == 1
        assert stats['total_featured'] == 1
        assert stats['total_rejected'] == 1
        assert stats['total_pending'] == 0  # Changed to rejected above
        
        # Check average rating (should be (5+5+3+4)/4 = 4.25)
        assert stats['average_rating'] == 4.25
        
        # Check rating distribution
        assert stats['by_rating'][3] == 1
        assert stats['by_rating'][4] == 1
        assert stats['by_rating'][5] == 2
    
    def test_create_testimonial_method(self, user, category):
        """Test the create_testimonial method."""
        # Create with default settings (should be pending)
        testimonial = Testimonial.objects.create_testimonial(
            author=user,
            author_name='New User',
            content='This is a new testimonial created with create_testimonial.',
            rating=4,
            category=category
        )
        
        assert testimonial.status == TestimonialStatus.PENDING
        
        # Test with settings override
        from django.test import override_settings
        
        with override_settings(TESTIMONIALS_REQUIRE_APPROVAL=False):
            from testimonials.conf import app_settings
            # Force refresh app_settings
            app_settings.__class__.REQUIRE_APPROVAL.fget.cache_clear()
            
            testimonial2 = Testimonial.objects.create_testimonial(
                author=user,
                author_name='Another User',
                content='This testimonial should be automatically approved.',
                rating=5,
                category=category
            )
            
            assert testimonial2.status == TestimonialStatus.APPROVED


@pytest.mark.django_db
class TestTestimonialCategoryManager:
    """Tests for the TestimonialCategoryManager."""
    
    def test_active_method(self, category):
        """Test the active method."""
        # Create an inactive category
        inactive_category = TestimonialCategory.objects.create(
            name='Inactive Category',
            slug='inactive-category',
            is_active=False
        )
        
        active_categories = TestimonialCategory.objects.active()
        
        assert active_categories.count() == 1
        assert category in active_categories
        assert inactive_category not in active_categories
    
    def test_with_testimonials_count(self, category, testimonial, featured_testimonial):
        """Test the with_testimonials_count method."""
        # Create another category with no testimonials
        empty_category = TestimonialCategory.objects.create(
            name='Empty Category',
            slug='empty-category'
        )
        
        categories = TestimonialCategory.objects.with_testimonials_count()
        
        # Find our test category in the results
        test_category = next(c for c in categories if c.id == category.id)
        empty_category_result = next(c for c in categories if c.id == empty_category.id)
        
        assert test_category.testimonials_count == 2  # testimonial + featured_testimonial
        assert empty_category_result.testimonials_count == 0


@pytest.mark.django_db
class TestTestimonialMediaManager:
    """Tests for the TestimonialMediaManager."""
    
    def test_for_testimonial_method(self, testimonial, testimonial_media):
        """Test the for_testimonial method."""
        media = testimonial.media.all()
        
        assert media.count() == 1
        assert testimonial_media in media
        
        # Test using the manager directly
        media_manager = testimonial_media.__class__.objects.for_testimonial(testimonial)
        assert media_manager.count() == 1
        assert testimonial_media in media_manager
    
    def test_media_type_filters(self, testimonial, test_image):
        """Test the media type filter methods (images, videos, etc.)."""
        from testimonials.constants import TestimonialMediaType
        
        # Create different types of media
        image_media = testimonial.add_media(
            test_image,
            title="Test Image",
            description="An image"
        )
        
        # Update one to be a different type for testing
        video_media = testimonial.add_media(
            test_image,
            title="Test Video",
            description="Actually an image but we'll pretend it's a video"
        )
        video_media.media_type = TestimonialMediaType.VIDEO
        video_media.save()
        
        # Test the type filters
        MediaModel = testimonial_media.__class__
        
        images = MediaModel.objects.images()
        assert images.count() == 1
        assert image_media in images
        
        videos = MediaModel.objects.videos()
        assert videos.count() == 1
        assert video_media in videos