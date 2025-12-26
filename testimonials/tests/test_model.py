# testimonials/tests/test_models.py

"""
Comprehensive model tests for django-testimonials package.
Tests cover all angles: creation, validation, methods, edge cases, and failures.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from datetime import timedelta
import io

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import (
    TestimonialStatus,
    TestimonialSource,
    TestimonialMediaType,
    AuthorTitle
)

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class TestimonialTestCase(TestCase):
    """Base test case with common setup for all testimonial tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole TestCase (runs once)."""
        # Create test users
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        cls.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        
        cls.moderator = User.objects.create_user(
            username='moderator',
            email='moderator@example.com',
            password='modpass123',
            is_staff=True
        )
        
        # Create test categories
        cls.category1 = TestimonialCategory.objects.create(
            name='Products',
            description='Product testimonials',
            is_active=True,
            order=1
        )
        
        cls.category2 = TestimonialCategory.objects.create(
            name='Services',
            description='Service testimonials',
            is_active=True,
            order=2
        )
        
        cls.inactive_category = TestimonialCategory.objects.create(
            name='Inactive Category',
            description='Not active',
            is_active=False,
            order=3
        )
    
    def setUp(self):
        """Set up data for each test method (runs before each test)."""
        # This runs before each test method
        pass
    
    def create_test_image(self, name='test.jpg', width=100, height=100):
        """Helper to create a test image file."""
        from PIL import Image
        
        # Create a simple image
        image = Image.new('RGB', (width, height), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            name=name,
            content=image_io.read(),
            content_type='image/jpeg'
        )
    
    def create_test_pdf(self, name='test.pdf'):
        """Helper to create a test PDF file."""
        content = b'%PDF-1.4\nTest PDF content'
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type='application/pdf'
        )


# ============================================================================
# TESTIMONIAL CATEGORY TESTS
# ============================================================================

class TestimonialCategoryModelTests(TestimonialTestCase):
    """Tests for TestimonialCategory model."""
    
    def test_create_category_with_valid_data(self):
        """Test creating a category with all valid data."""
        category = TestimonialCategory.objects.create(
            name='Events',
            slug='events',
            description='Event testimonials',
            is_active=True,
            order=5
        )
        
        self.assertEqual(category.name, 'Events')
        self.assertEqual(category.slug, 'events')
        self.assertEqual(category.description, 'Event testimonials')
        self.assertTrue(category.is_active)
        self.assertEqual(category.order, 5)
        self.assertIsNotNone(category.created_at)
        self.assertIsNotNone(category.updated_at)
    
    def test_category_slug_auto_generation(self):
        """Test that slug is auto-generated from name if not provided."""
        category = TestimonialCategory.objects.create(
            name='Customer Support'
        )
        
        self.assertEqual(category.slug, 'customer-support')
    
    def test_category_slug_uniqueness(self):
        """Test that duplicate slugs get unique suffixes."""
        category1 = TestimonialCategory.objects.create(name='Test Category')
        category2 = TestimonialCategory.objects.create(name='Test Category')
        
        self.assertNotEqual(category1.slug, category2.slug)
        self.assertTrue(category2.slug.startswith('test-category'))
    
    def test_category_name_normalization(self):
        """Test that category names are normalized with proper capitalization."""
        category = TestimonialCategory.objects.create(
            name='customer support team'  # lowercase
        )
        
        self.assertEqual(category.name, 'Customer Support Team')
    
    def test_category_name_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped from name."""
        category = TestimonialCategory.objects.create(
            name='  Spaced Name  '
        )
        
        self.assertEqual(category.name, 'Spaced Name')
    
    def test_category_string_representation(self):
        """Test __str__ method returns category name."""
        category = TestimonialCategory.objects.create(name='Test')
        self.assertEqual(str(category), 'Test')
    
    def test_category_default_values(self):
        """Test default values for category fields."""
        category = TestimonialCategory.objects.create(name='Minimal')
        
        self.assertTrue(category.is_active)  # Default True
        self.assertEqual(category.order, 0)  # Default 0
        self.assertEqual(category.description, '')  # Blank
    
    def test_category_ordering(self):
        """Test that categories are ordered by order field, then name."""
        cat_a = TestimonialCategory.objects.create(name='A Category', order=2)
        cat_b = TestimonialCategory.objects.create(name='B Category', order=1)
        cat_c = TestimonialCategory.objects.create(name='C Category', order=1)
        
        # Get only the categories we just created
        categories = list(
            TestimonialCategory.objects.filter(
                pk__in=[cat_a.pk, cat_b.pk, cat_c.pk]
            ).order_by('order', 'name')
        )
        
        # Should be ordered by order (ascending), then name (ascending)
        self.assertEqual(categories[0], cat_b)  # order=1, name=B
        self.assertEqual(categories[1], cat_c)  # order=1, name=C
        self.assertEqual(categories[2], cat_a)  # order=2, name=A
    
    def test_category_active_manager_method(self):
        """Test the active() manager method filters correctly."""
        active_categories = TestimonialCategory.objects.active()
        
        self.assertIn(self.category1, active_categories)
        self.assertIn(self.category2, active_categories)
        self.assertNotIn(self.inactive_category, active_categories)
    
    def test_category_with_testimonial_counts(self):
        """Test with_testimonial_counts() manager method."""
        # Create testimonials
        Testimonial.objects.create(
            author=self.user,
            author_name='Test User',
            content='Test content for category',
            rating=5,
            category=self.category1
        )
        
        categories = TestimonialCategory.objects.with_testimonial_counts()
        category_with_count = categories.get(pk=self.category1.pk)
        
        self.assertEqual(category_with_count.testimonials_count, 1)
    
    def test_category_get_stats(self):
        """Test get_stats() manager method returns correct statistics."""
        stats = TestimonialCategory.objects.get_stats()
        
        self.assertIn('total_categories', stats)
        self.assertIn('active_categories', stats)
        self.assertIn('categories', stats)
        
        # Should have 3 total categories (2 active + 1 inactive)
        self.assertEqual(stats['total_categories'], 3)
        self.assertEqual(stats['active_categories'], 2)
    
    def test_category_deletion_does_not_delete_testimonials(self):
        """Test that deleting a category doesn't delete its testimonials."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Test',
            content='Test content',
            rating=5,
            category=self.category1
        )
        
        self.category1.delete()
        
        # Testimonial should still exist with null category
        testimonial.refresh_from_db()
        self.assertIsNone(testimonial.category)


# ============================================================================
# TESTIMONIAL MODEL TESTS - CREATION & VALIDATION
# ============================================================================

class TestimonialCreationTests(TestimonialTestCase):
    """Tests for Testimonial model creation and validation."""
    
    def test_create_testimonial_with_authenticated_user(self):
        """Test creating a testimonial as an authenticated user."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Great product! Highly recommend.',
            rating=5,
            category=self.category1
        )
        
        self.assertEqual(testimonial.author, self.user)
        # Author name should be prefilled from user
        self.assertEqual(testimonial.author_name, 'Test User')
        self.assertEqual(testimonial.author_email, 'testuser@example.com')
        self.assertEqual(testimonial.content, 'Great product! Highly recommend.')
        self.assertEqual(testimonial.rating, 5)
        self.assertEqual(testimonial.status, TestimonialStatus.PENDING)
        self.assertFalse(testimonial.is_anonymous)
    
    def test_create_testimonial_with_explicit_author_name(self):
        """Test that explicit author_name is not overridden by user data."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Custom Name',
            author_email='custom@example.com',
            content='Test content',
            rating=5
        )
        
        # Should keep the explicit values
        self.assertEqual(testimonial.author_name, 'Custom Name')
        self.assertEqual(testimonial.author_email, 'custom@example.com')
    
    def test_create_anonymous_testimonial(self):
        """Test creating an anonymous testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Anonymous feedback',
            rating=4,
            is_anonymous=True
        )
        
        self.assertTrue(testimonial.is_anonymous)
        self.assertEqual(testimonial.author_name, 'Anonymous')
        # ImageFieldFile is never None, check if it has a name
        self.assertFalse(testimonial.avatar.name)
    
    def test_create_guest_testimonial(self):
        """Test creating a testimonial without a user account."""
        testimonial = Testimonial.objects.create(
            author_name='Guest User',
            author_email='guest@example.com',
            content='Great service!',
            rating=5
        )
        
        self.assertIsNone(testimonial.author)
        self.assertEqual(testimonial.author_name, 'Guest User')
        self.assertEqual(testimonial.author_email, 'guest@example.com')
    
    def test_create_testimonial_with_all_fields(self):
        """Test creating a testimonial with all optional fields."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@company.com',
            author_phone='+2348012345678',
            author_title=AuthorTitle.CEO,
            company='Acme Corp',
            location='Lagos, Nigeria',
            title='Excellent Experience',
            content='This is a detailed testimonial with all fields filled.',
            rating=5,
            category=self.category1,
            source=TestimonialSource.EMAIL,
            website='https://example.com',
            social_media={'twitter': '@johndoe'},
            is_verified=True,
            display_order=10
        )
        
        # Note: author_title gets normalized by string.capwords, so 'CEO' becomes 'Ceo'
        self.assertEqual(testimonial.author_title, 'Ceo')
        self.assertEqual(testimonial.company, 'Acme Corp')
        self.assertEqual(testimonial.location, 'Lagos, Nigeria')
        self.assertEqual(testimonial.title, 'Excellent Experience')
        self.assertEqual(testimonial.source, TestimonialSource.EMAIL)
        self.assertTrue(testimonial.is_verified)
        self.assertEqual(testimonial.display_order, 10)
    
    def test_testimonial_default_values(self):
        """Test default values for testimonial fields."""
        testimonial = Testimonial.objects.create(
            author_name='Test',
            content='Minimal testimonial',
            rating=5
        )
        
        self.assertEqual(testimonial.status, TestimonialStatus.PENDING)
        self.assertEqual(testimonial.source, TestimonialSource.WEBSITE)
        self.assertFalse(testimonial.is_anonymous)
        self.assertFalse(testimonial.is_verified)
        self.assertEqual(testimonial.display_order, 0)
        self.assertEqual(testimonial.social_media, {})
    
    def test_testimonial_slug_auto_generation(self):
        """Test that slug is auto-generated from author_name."""
        testimonial = Testimonial.objects.create(
            author_name='John Doe',
            content='Test content',
            rating=5
        )
        
        self.assertEqual(testimonial.slug, 'john-doe')
    
    def test_testimonial_slug_from_title_if_no_author_name(self):
        """Test slug generation when anonymous."""
        testimonial = Testimonial.objects.create(
            title='Great Product Review',
            content='Excellent product quality and service',
            rating=5,
            is_anonymous=True
        )
        
        # When anonymous, author_name becomes 'Anonymous' and that's used for slug
        self.assertEqual(testimonial.author_name, 'Anonymous')
        self.assertTrue(testimonial.slug.startswith('anonymous'))
    
    def test_testimonial_slug_uses_title_when_no_author_name(self):
        """Test slug generation from title when author_name is truly empty."""
        testimonial = Testimonial.objects.create(
            author_name='',  # Empty string
            title='Excellent Service',
            content='Very satisfied with the service',
            rating=5,
            is_anonymous=False
        )
        
        # With empty author_name (not anonymous), should use title
        self.assertTrue(testimonial.slug.startswith('excellent-service'))
    
    def test_testimonial_slug_uniqueness(self):
        """Test that duplicate slugs get unique suffixes."""
        testimonial1 = Testimonial.objects.create(
            author_name='John Doe',
            content='First testimonial',
            rating=5
        )
        
        testimonial2 = Testimonial.objects.create(
            author_name='John Doe',
            content='Second testimonial',
            rating=4
        )
        
        self.assertNotEqual(testimonial1.slug, testimonial2.slug)
        self.assertTrue(testimonial2.slug.startswith('john-doe'))
    
    def test_author_name_normalization(self):
        """Test that author names are normalized with proper capitalization."""
        testimonial = Testimonial.objects.create(
            author_name='john doe smith',
            content='Test content',
            rating=5
        )
        
        self.assertEqual(testimonial.author_name, 'John Doe Smith')
    
    def test_author_name_strips_whitespace(self):
        """Test that whitespace is stripped from author fields."""
        testimonial = Testimonial.objects.create(
            author_name='  John Doe  ',
            author_title='  ceo  ',
            company='  Test Company  ',
            content='Test content',
            rating=5
        )
        
        self.assertEqual(testimonial.author_name, 'John Doe')
        self.assertEqual(testimonial.author_title, 'Ceo')
        self.assertEqual(testimonial.company, 'Test Company')


# ============================================================================
# TESTIMONIAL MODEL TESTS - VALIDATION
# ============================================================================

class TestimonialValidationTests(TestimonialTestCase):
    """Tests for Testimonial model validation."""
    
    def test_rating_minimum_value(self):
        """Test that rating below minimum is rejected."""
        testimonial = Testimonial(
            author_name='Test',
            content='Test content',
            rating=0  # Below minimum of 1
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('rating', context.exception.message_dict)
    
    def test_rating_maximum_value(self):
        """Test that rating above maximum is rejected."""
        testimonial = Testimonial(
            author_name='Test',
            content='Test content',
            rating=6  # Above default maximum of 5
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('rating', context.exception.message_dict)
    
    def test_rating_valid_range(self):
        """Test that ratings within valid range are accepted."""
        for rating in range(1, 6):  # 1 to 5
            testimonial = Testimonial(
                author_name='John Doe',
                content='This is excellent quality content for validation',
                rating=rating
            )
            testimonial.full_clean()  # Should not raise
    
    def test_content_minimum_length(self):
        """Test that content below minimum length is rejected."""
        testimonial = Testimonial(
            author_name='Test',
            content='Short',  # Less than 10 characters
            rating=5
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('content', context.exception.message_dict)
    
    def test_content_maximum_length(self):
        """Test that content above maximum length is rejected."""
        long_content = 'x' * 5001  # Over default max of 5000
        
        testimonial = Testimonial(
            author_name='Test',
            content=long_content,
            rating=5
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('content', context.exception.message_dict)
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    def test_content_forbidden_words(self):
        """Test that content with forbidden words is rejected."""
        testimonial = Testimonial(
            author_name='Test',
            content='This is spam content that should be rejected.',
            rating=5
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('content', context.exception.message_dict)
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    def test_content_excessive_repetition(self):
        """Test that content with excessive repetition is rejected."""
        # Less than 30% unique words
        testimonial = Testimonial(
            author_name='Test',
            content='word word word word word word word word word word',
            rating=5
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('content', context.exception.message_dict)
    
    def test_email_format_validation(self):
        """Test that invalid email format is rejected."""
        testimonial = Testimonial(
            author_name='Test',
            author_email='invalid-email',
            content='Test content here',
            rating=5
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('author_email', context.exception.message_dict)
    
    def test_url_format_validation(self):
        """Test that invalid URL format is rejected."""
        testimonial = Testimonial(
            author_name='Test',
            content='Test content here',
            rating=5,
            website='not-a-valid-url'
        )
        
        with self.assertRaises(ValidationError) as context:
            testimonial.full_clean()
        
        self.assertIn('website', context.exception.message_dict)


# ============================================================================
# TESTIMONIAL MODEL TESTS - STATUS & WORKFLOW
# ============================================================================

class TestimonialStatusWorkflowTests(TestimonialTestCase):
    """Tests for Testimonial status transitions and workflow."""
    
    def test_approve_testimonial(self):
        """Test approving a pending testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test content for approval',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        testimonial.approve(user=self.admin)
        
        self.assertEqual(testimonial.status, TestimonialStatus.APPROVED)
        self.assertIsNotNone(testimonial.approved_at)
        self.assertEqual(testimonial.approved_by, self.admin)
        self.assertAlmostEqual(
            testimonial.approved_at,
            timezone.now(),
            delta=timedelta(seconds=1)
        )
    
    def test_reject_testimonial(self):
        """Test rejecting a testimonial with a reason."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test content for rejection',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        reason = 'Does not meet quality standards'
        testimonial.reject(reason=reason, user=self.admin)
        
        self.assertEqual(testimonial.status, TestimonialStatus.REJECTED)
        self.assertEqual(testimonial.rejection_reason, reason)
    
    def test_reject_testimonial_without_reason(self):
        """Test rejecting a testimonial without providing a reason."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Quality content here',
            rating=5
        )
        
        testimonial.reject(user=self.admin)
        
        self.assertEqual(testimonial.status, TestimonialStatus.REJECTED)
        # Model sets a default reason if none provided
        self.assertTrue(len(testimonial.rejection_reason) > 0)
    
    def test_feature_testimonial(self):
        """Test featuring an approved testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Outstanding testimonial content',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        testimonial.feature(user=self.admin)
        
        self.assertEqual(testimonial.status, TestimonialStatus.FEATURED)
    
    def test_archive_testimonial(self):
        """Test archiving a testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Old testimonial',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        testimonial.archive(user=self.admin)
        
        self.assertEqual(testimonial.status, TestimonialStatus.ARCHIVED)
    
    def test_add_response(self):
        """Test adding an admin response to a testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Question about product',
            rating=4
        )
        
        response_text = 'Thank you for your feedback!'
        testimonial.add_response(response_text, user=self.admin)
        
        self.assertEqual(testimonial.response, response_text)
        self.assertIsNotNone(testimonial.response_at)
        self.assertEqual(testimonial.response_by, self.admin)


# ============================================================================
# TESTIMONIAL MODEL TESTS - PROPERTIES & METHODS
# ============================================================================

class TestimonialPropertiesTests(TestimonialTestCase):
    """Tests for Testimonial model properties and computed fields."""
    
    def test_is_published_property_approved(self):
        """Test is_published returns True for approved status."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        self.assertTrue(testimonial.is_published)
    
    def test_is_published_property_featured(self):
        """Test is_published returns True for featured status."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5,
            status=TestimonialStatus.FEATURED
        )
        
        self.assertTrue(testimonial.is_published)
    
    def test_is_published_property_pending(self):
        """Test is_published returns False for pending status."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        self.assertFalse(testimonial.is_published)
    
    def test_is_published_property_rejected(self):
        """Test is_published returns False for rejected status."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5,
            status=TestimonialStatus.REJECTED
        )
        
        self.assertFalse(testimonial.is_published)
    
    def test_has_media_property_with_media(self):
        """Test has_media returns True when media exists."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test with media',
            rating=5
        )
        
        # Add media
        image = self.create_test_image()
        testimonial.add_media(image, title='Test Image')
        
        # Refresh from database to get updated media relation
        testimonial.refresh_from_db()
        
        self.assertTrue(testimonial.has_media)
    
    def test_has_media_property_without_media(self):
        """Test has_media returns False when no media exists."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test without media',
            rating=5
        )
        
        self.assertFalse(testimonial.has_media)
    
    def test_author_display_for_named_user(self):
        """Test author_display returns name for non-anonymous user."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test',
            rating=5,
            is_anonymous=False
        )
        
        self.assertEqual(testimonial.author_display, 'John Doe')
    
    def test_author_display_for_anonymous_user(self):
        """Test author_display returns 'Anonymous' for anonymous user."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5,
            is_anonymous=True
        )
        
        self.assertEqual(testimonial.author_display, 'Anonymous')
    
    def test_string_representation(self):
        """Test __str__ method returns author name and content preview."""
        testimonial = Testimonial.objects.create(
            author_name='Test User',
            content='This is a long testimonial that should be truncated',
            rating=5
        )
        
        str_repr = str(testimonial)
        self.assertIn('Test User', str_repr)
        self.assertIn('This is a long testimonial', str_repr)


# ============================================================================
# TESTIMONIAL MODEL TESTS - MEDIA MANAGEMENT
# ============================================================================

class TestimonialMediaManagementTests(TestimonialTestCase):
    """Tests for testimonial media management."""
    
    def test_add_media_to_testimonial(self):
        """Test adding media to a testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test with media',
            rating=5
        )
        
        image = self.create_test_image()
        media = testimonial.add_media(
            file_obj=image,
            title='Test Image',
            description='A test image'
        )
        
        self.assertIsNotNone(media)
        self.assertEqual(media.testimonial, testimonial)
        self.assertEqual(media.title, 'Test Image')
        self.assertEqual(media.description, 'A test image')
        self.assertEqual(media.media_type, TestimonialMediaType.IMAGE)
    
    def test_add_multiple_media_files(self):
        """Test adding multiple media files to one testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test with multiple media',
            rating=5
        )
        
        image1 = self.create_test_image('image1.jpg')
        image2 = self.create_test_image('image2.jpg')
        pdf = self.create_test_pdf('document.pdf')
        
        media1 = testimonial.add_media(image1)
        media2 = testimonial.add_media(image2)
        media3 = testimonial.add_media(pdf)
        
        self.assertEqual(testimonial.media.count(), 3)
        self.assertEqual(media1.media_type, TestimonialMediaType.IMAGE)
        self.assertEqual(media2.media_type, TestimonialMediaType.IMAGE)
        self.assertEqual(media3.media_type, TestimonialMediaType.DOCUMENT)


# ============================================================================
# TESTIMONIAL MODEL TESTS - MANAGER METHODS
# ============================================================================

class TestimonialManagerTests(TestimonialTestCase):
    """Tests for Testimonial model manager methods."""
    
    def setUp(self):
        super().setUp()
        
        # Create testimonials with different statuses
        self.pending = Testimonial.objects.create(
            author=self.user,
            content='Pending testimonial',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        self.approved = Testimonial.objects.create(
            author=self.user,
            content='Approved testimonial',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        self.featured = Testimonial.objects.create(
            author=self.user,
            content='Featured testimonial',
            rating=5,
            status=TestimonialStatus.FEATURED
        )
        
        self.rejected = Testimonial.objects.create(
            author=self.user,
            content='Rejected testimonial',
            rating=2,
            status=TestimonialStatus.REJECTED
        )
        
        self.archived = Testimonial.objects.create(
            author=self.user,
            content='Archived testimonial',
            rating=3,
            status=TestimonialStatus.ARCHIVED
        )
    
    def test_pending_queryset_filter(self):
        """Test pending() manager method."""
        pending = Testimonial.objects.pending()
        
        self.assertIn(self.pending, pending)
        self.assertNotIn(self.approved, pending)
        self.assertNotIn(self.featured, pending)
    
    def test_approved_queryset_filter(self):
        """Test approved() manager method."""
        approved = Testimonial.objects.approved()
        
        self.assertIn(self.approved, approved)
        self.assertNotIn(self.pending, approved)
        self.assertNotIn(self.featured, approved)
    
    def test_featured_queryset_filter(self):
        """Test featured() manager method."""
        featured = Testimonial.objects.featured()
        
        self.assertIn(self.featured, featured)
        self.assertNotIn(self.approved, featured)
        self.assertNotIn(self.pending, featured)
    
    def test_rejected_queryset_filter(self):
        """Test rejected() manager method."""
        rejected = Testimonial.objects.rejected()
        
        self.assertIn(self.rejected, rejected)
        self.assertNotIn(self.approved, rejected)
    
    def test_archived_queryset_filter(self):
        """Test archived() manager method."""
        archived = Testimonial.objects.archived()
        
        self.assertIn(self.archived, archived)
        self.assertNotIn(self.approved, archived)
    
    def test_published_queryset_filter(self):
        """Test published() includes approved and featured only."""
        published = Testimonial.objects.published()
        
        self.assertIn(self.approved, published)
        self.assertIn(self.featured, published)
        self.assertNotIn(self.pending, published)
        self.assertNotIn(self.rejected, published)
        self.assertNotIn(self.archived, published)
    
    def test_verified_queryset_filter(self):
        """Test verified() manager method."""
        verified = Testimonial.objects.create(
            author=self.user,
            content='Verified testimonial',
            rating=5,
            is_verified=True
        )
        
        verified_testimonials = Testimonial.objects.verified()
        
        self.assertIn(verified, verified_testimonials)
        self.assertNotIn(self.approved, verified_testimonials)
    
    def test_by_rating_filter(self):
        """Test by_rating() manager method."""
        # Test minimum rating
        high_rated = Testimonial.objects.by_rating(min_rating=4)
        self.assertIn(self.approved, high_rated)
        self.assertNotIn(self.rejected, high_rated)
        
        # Test maximum rating
        low_rated = Testimonial.objects.by_rating(max_rating=3)
        self.assertIn(self.rejected, low_rated)
        self.assertIn(self.archived, low_rated)
        self.assertNotIn(self.approved, low_rated)
        
        # Test range
        mid_rated = Testimonial.objects.by_rating(min_rating=3, max_rating=4)
        self.assertIn(self.archived, mid_rated)
        self.assertNotIn(self.approved, mid_rated)
        self.assertNotIn(self.rejected, mid_rated)
    
    def test_by_category_filter(self):
        """Test by_category() manager method."""
        categorized = Testimonial.objects.create(
            author=self.user,
            content='Categorized testimonial',
            rating=5,
            category=self.category1
        )
        
        results = Testimonial.objects.by_category(self.category1.id)
        
        self.assertIn(categorized, results)
        self.assertNotIn(self.approved, results)
    
    def test_by_author_filter(self):
        """Test by_author() manager method."""
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com'
        )
        
        other_testimonial = Testimonial.objects.create(
            author=other_user,
            content='Other user testimonial',
            rating=5
        )
        
        user_testimonials = Testimonial.objects.by_author(self.user)
        
        self.assertIn(self.approved, user_testimonials)
        self.assertNotIn(other_testimonial, user_testimonials)
    
    def test_search_queryset_method(self):
        """Test search() manager method."""
        searchable = Testimonial.objects.create(
            author=self.user,
            author_name='Unique Author',
            company='Unique Company',
            content='Contains unique search term',
            rating=5
        )
        
        # Search by author name
        results = Testimonial.objects.search('Unique Author')
        self.assertIn(searchable, results)
        
        # Search by company
        results = Testimonial.objects.search('Unique Company')
        self.assertIn(searchable, results)
        
        # Search by content
        results = Testimonial.objects.search('unique search')
        self.assertIn(searchable, results)
        
        # Search with no results
        results = Testimonial.objects.search('nonexistent')
        self.assertNotIn(searchable, results)
    
    def test_search_with_short_query(self):
        """Test that search with query shorter than minimum returns empty."""
        results = Testimonial.objects.search('ab')  # Less than 3 chars
        self.assertEqual(results.count(), 0)
    
    def test_get_stats_manager_method(self):
        """Test get_stats() returns comprehensive statistics."""
        stats = Testimonial.objects.get_stats()
        
        self.assertIn('total', stats)
        self.assertIn('avg_rating', stats)
        self.assertIn('status_distribution', stats)
        self.assertIn('source_distribution', stats)
        self.assertIn('rating_distribution', stats)
        
        # Check totals
        self.assertEqual(stats['total'], 5)
        
        # Check status distribution
        status_dist = stats['status_distribution']
        self.assertEqual(status_dist[TestimonialStatus.PENDING]['count'], 1)
        self.assertEqual(status_dist[TestimonialStatus.APPROVED]['count'], 1)
        self.assertEqual(status_dist[TestimonialStatus.FEATURED]['count'], 1)
    
    def test_get_recent_manager_method(self):
        """Test get_recent() returns most recent testimonials."""
        recent = Testimonial.objects.get_recent(limit=3)
        
        # Should be ordered by most recent first
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0], self.archived)  # Last created
    
    def test_get_top_rated_manager_method(self):
        """Test get_top_rated() returns highest rated published testimonials."""
        top = Testimonial.objects.get_top_rated(limit=5)
        
        # Should only include published (approved/featured)
        self.assertIn(self.approved, top)
        self.assertIn(self.featured, top)
        self.assertNotIn(self.pending, top)
        self.assertNotIn(self.rejected, top)


# ============================================================================
# TESTIMONIAL MEDIA MODEL TESTS
# ============================================================================

class TestimonialMediaModelTests(TestimonialTestCase):
    """Tests for TestimonialMedia model."""
    
    def setUp(self):
        super().setUp()
        
        self.testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test testimonial with media',
            rating=5
        )
    
    def test_create_image_media(self):
        """Test creating an image media file."""
        image = self.create_test_image()
        
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            media_type=TestimonialMediaType.IMAGE,
            title='Test Image',
            description='A test image file'
        )
        
        self.assertEqual(media.media_type, TestimonialMediaType.IMAGE)
        self.assertEqual(media.title, 'Test Image')
        self.assertEqual(media.description, 'A test image file')
        self.assertFalse(media.is_primary)
        self.assertEqual(media.order, 0)
    
    def test_create_pdf_media(self):
        """Test creating a PDF media file."""
        pdf = self.create_test_pdf()
        
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=pdf,
            media_type=TestimonialMediaType.DOCUMENT
        )
        
        self.assertEqual(media.media_type, TestimonialMediaType.DOCUMENT)
    
    def test_media_auto_detect_type_image(self):
        """Test that media type is auto-detected for images."""
        image = self.create_test_image('photo.png')
        
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image
        )
        
        self.assertEqual(media.media_type, TestimonialMediaType.IMAGE)
    
    def test_media_auto_detect_type_document(self):
        """Test that media type is auto-detected for documents."""
        pdf = self.create_test_pdf('doc.pdf')
        
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=pdf
        )
        
        self.assertEqual(media.media_type, TestimonialMediaType.DOCUMENT)
    
    def test_primary_media_flag(self):
        """Test that only one media can be primary per testimonial."""
        image1 = self.create_test_image('image1.jpg')
        image2 = self.create_test_image('image2.jpg')
        
        media1 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image1,
            is_primary=True
        )
        
        media2 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image2,
            is_primary=True
        )
        
        # Refresh media1 from database
        media1.refresh_from_db()
        
        # Only media2 should be primary now
        self.assertFalse(media1.is_primary)
        self.assertTrue(media2.is_primary)
    
    def test_media_ordering(self):
        """Test media ordering by is_primary, order, and created_at."""
        image1 = self.create_test_image('image1.jpg')
        image2 = self.create_test_image('image2.jpg')
        image3 = self.create_test_image('image3.jpg')
        
        media1 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image1,
            order=2
        )
        
        media2 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image2,
            order=1,
            is_primary=True
        )
        
        media3 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image3,
            order=1
        )
        
        media_list = list(TestimonialMedia.objects.filter(
            testimonial=self.testimonial
        ))
        
        # Primary should come first, then by order
        self.assertEqual(media_list[0], media2)  # is_primary=True
    
    def test_media_string_representation(self):
        """Test __str__ method for media."""
        image = self.create_test_image()
        
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            title='My Image'
        )
        
        str_repr = str(media)
        self.assertIn('Image', str_repr)
        self.assertIn('My Image', str_repr)
    
    def test_media_manager_images_filter(self):
        """Test images() manager method."""
        image = self.create_test_image()
        pdf = self.create_test_pdf()
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            media_type=TestimonialMediaType.IMAGE
        )
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=pdf,
            media_type=TestimonialMediaType.DOCUMENT
        )
        
        images = TestimonialMedia.objects.images()
        self.assertEqual(images.count(), 1)
        self.assertEqual(images.first().media_type, TestimonialMediaType.IMAGE)
    
    def test_media_manager_documents_filter(self):
        """Test documents() manager method."""
        image = self.create_test_image()
        pdf = self.create_test_pdf()
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            media_type=TestimonialMediaType.IMAGE
        )
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=pdf,
            media_type=TestimonialMediaType.DOCUMENT
        )
        
        documents = TestimonialMedia.objects.documents()
        self.assertEqual(documents.count(), 1)
        self.assertEqual(documents.first().media_type, TestimonialMediaType.DOCUMENT)
    
    def test_media_manager_primary_only_filter(self):
        """Test primary_only() manager method."""
        image1 = self.create_test_image('image1.jpg')
        image2 = self.create_test_image('image2.jpg')
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image1,
            is_primary=True
        )
        
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image2,
            is_primary=False
        )
        
        primary = TestimonialMedia.objects.primary_only()
        self.assertEqual(primary.count(), 1)
        self.assertTrue(primary.first().is_primary)


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

class TestimonialEdgeCasesTests(TestimonialTestCase):
    """Tests for edge cases and error handling."""
    
    def test_testimonial_with_empty_strings(self):
        """Test handling of empty strings vs None."""
        testimonial = Testimonial.objects.create(
            author_name='Test',
            author_email='',  # Empty string
            content='Test content',
            rating=5
        )
        
        self.assertEqual(testimonial.author_email, '')
        self.assertIsNotNone(testimonial.author_email)
    
    def test_testimonial_with_unicode_content(self):
        """Test handling of Unicode characters."""
        testimonial = Testimonial.objects.create(
            author_name='用户测试',
            content='这是一个测试内容 with émojis 🎉 and spëcial çhars',
            rating=5
        )
        
        self.assertIn('用户测试', testimonial.author_name)
        self.assertIn('🎉', testimonial.content)
    
    def test_testimonial_with_very_long_slug(self):
        """Test slug generation for very long names."""
        long_name = 'A' * 300
        
        testimonial = Testimonial.objects.create(
            author_name=long_name,
            content='Test content',
            rating=5
        )
        
        # Slug should be truncated to max_length
        self.assertLessEqual(len(testimonial.slug), 255)
    
    def test_concurrent_slug_generation(self):
        """Test that concurrent creates with same name get unique slugs."""
        testimonials = []
        for i in range(5):
            testimonials.append(
                Testimonial.objects.create(
                    author_name='Same Name',
                    content=f'Content {i}',
                    rating=5
                )
            )
        
        slugs = [t.slug for t in testimonials]
        # All slugs should be unique
        self.assertEqual(len(slugs), len(set(slugs)))
    
    def test_testimonial_with_null_json_fields(self):
        """Test handling of null JSON fields."""
        testimonial = Testimonial.objects.create(
            author_name='John Doe',
            content='Quality content here',
            rating=5,
            social_media=None,
            extra_data=None
        )
        
        # Model keeps None for null JSON fields (doesn't auto-convert to {})
        # The default=dict in model only applies when field is not explicitly set
        self.assertIsNone(testimonial.social_media)
        self.assertIsNone(testimonial.extra_data)
    
    def test_testimonial_json_fields_default_behavior(self):
        """Test JSON fields get default dict when not explicitly set."""
        testimonial = Testimonial.objects.create(
            author_name='Jane Doe',
            content='Quality content here',
            rating=5
            # social_media and extra_data not set at all
        )
        
        # When not explicitly set, should get default value (dict)
        self.assertEqual(testimonial.social_media, {})
        self.assertEqual(testimonial.extra_data, {})
    
    def test_delete_testimonial_with_media(self):
        """Test that deleting testimonial cascades to media."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5
        )
        
        image = self.create_test_image()
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            file=image
        )
        
        media_id = media.id
        testimonial.delete()
        
        # Media should also be deleted
        with self.assertRaises(TestimonialMedia.DoesNotExist):
            TestimonialMedia.objects.get(id=media_id)
    
    def test_update_with_invalid_data(self):
        """Test that update with invalid data raises appropriate error."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test content',
            rating=5
        )
        
        # Try to update with invalid rating
        testimonial.rating = 0
        
        with self.assertRaises(ValidationError):
            testimonial.full_clean()


# ============================================================================
# DATABASE CONSTRAINTS TESTS
# ============================================================================

class TestimonialConstraintsTests(TestimonialTestCase):
    """Tests for database constraints."""
    
    def test_rating_range_constraint(self):
        """Test that rating outside range violates database constraint."""
        # This should be caught by validation before hitting DB,
        # but test the constraint directly
        testimonial = Testimonial(
            author_name='Test',
            content='Test content',
            rating=10  # Way above max
        )
        
        with self.assertRaises(ValidationError):
            testimonial.full_clean()
    
    def test_anonymous_author_info_constraint(self):
        """Test constraint that anonymous testimonials need author info."""
        # Create with proper validation bypassed
        testimonial = Testimonial.objects.create(
            author_name='',  # Empty
            author_email='',  # Empty
            content='Test content',
            rating=5,
            is_anonymous=False  # Not anonymous, so this is OK
        )
        
        # But if we make it anonymous with no author info, validation should fail
        testimonial.is_anonymous = True
        testimonial.author_name = ''
        testimonial.author_email = ''
        
        # The model's save method should handle this by setting name to "Anonymous"
        testimonial.save()
        self.assertEqual(testimonial.author_name, 'Anonymous')


# ============================================================================
# PERFORMANCE & OPTIMIZATION TESTS
# ============================================================================

class TestimonialPerformanceTests(TestimonialTestCase):
    """Tests for performance and optimization features."""
    
    def test_optimized_for_api_queryset(self):
        """Test that optimized_for_api() reduces database queries."""
        # Create testimonials with relations
        for i in range(5):
            testimonial = Testimonial.objects.create(
                author=self.user,
                content=f'Quality content number {i}',
                rating=5,
                category=self.category1
            )
            
            # Add media
            image = self.create_test_image(f'image{i}.jpg')
            TestimonialMedia.objects.create(
                testimonial=testimonial,
                file=image
            )
        
        # Test query count with optimized queryset
        # Should be 2 queries: 1 for testimonials (with select_related)
        # + 1 for prefetch_related (media)
        with self.assertNumQueries(2):
            testimonials = list(
                Testimonial.objects.optimized_for_api()[:5]
            )
            
            # Access related objects (should not cause additional queries)
            for t in testimonials:
                _ = t.category
                _ = t.author
                _ = list(t.media.all())
    
    def test_with_media_counts_annotation(self):
        """Test with_media_counts() adds annotation efficiently."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test',
            rating=5
        )
        
        # Add multiple media files
        for i in range(3):
            image = self.create_test_image(f'image{i}.jpg')
            TestimonialMedia.objects.create(
                testimonial=testimonial,
                file=image
            )
        
        # Query with annotation
        result = Testimonial.objects.with_media_counts().get(pk=testimonial.pk)
        
        self.assertEqual(result.media_count, 3)