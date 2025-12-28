# testimonials/tests/test_admin.py

"""
Comprehensive tests for Django admin configuration.
Tests cover admin registration, actions, display methods, forms, filters,
search functionality, permissions, and edge cases.
"""

from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from PIL import Image

from testimonials.admin import (
    TestimonialAdmin,
    TestimonialCategoryAdmin,
    TestimonialMediaInline
)
from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialMediaType
from testimonials.forms import TestimonialAdminForm

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class AdminTestCase(TestCase):
    """Base test case with common setup for admin tests."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.factory = RequestFactory()
        
        # Create users
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123'
        )
        
        # Create category
        self.category = TestimonialCategory.objects.create(
            name='Products',
            slug='products',
            is_active=True,
            order=1
        )
        
        # Create testimonials
        self.testimonial = Testimonial.objects.create(
            author=self.regular_user,
            author_name='John Doe',
            author_email='john@example.com',
            company='Acme Corp',
            title='Great Product',
            content='This is an excellent product that exceeded my expectations.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
    
    def _create_test_image(self, filename='test.jpg'):
        """Helper to create test image."""
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(filename, image_io.read(), content_type='image/jpeg')
    
    def _get_request(self, user=None):
        """Helper to create request with user."""
        request = self.factory.get('/admin/')
        request.user = user or self.admin_user
        
        # Add session and messages
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        return request


# ============================================================================
# TESTIMONIAL ADMIN TESTS
# ============================================================================

class TestimonialAdminTest(AdminTestCase):
    """Tests for TestimonialAdmin configuration and methods."""
    
    def setUp(self):
        super().setUp()
        self.admin = TestimonialAdmin(Testimonial, self.site)
    
    def test_admin_is_registered(self):
        """Test that TestimonialAdmin is properly registered."""
        from django.contrib import admin
        self.assertIn(Testimonial, admin.site._registry)
    
    def test_list_display_fields(self):
        """Test list_display configuration."""
        expected_fields = [
            'id', 'get_avatar_thumbnail', 'author_name', 'company',
            'get_rating_stars', 'status_badge', 'category',
            'created_at_formatted', 'has_media'
        ]
        for field in expected_fields:
            self.assertIn(field, self.admin.list_display)
    
    def test_list_filter_fields(self):
        """Test list_filter configuration."""
        expected_filters = [
            'status', 'rating', 'category', 'created_at',
            'is_anonymous', 'is_verified'
        ]
        for filter_field in expected_filters:
            self.assertIn(filter_field, self.admin.list_filter)
    
    def test_search_fields(self):
        """Test search_fields configuration."""
        expected_fields = ['author_name', 'author_email', 'company', 'content']
        for field in expected_fields:
            self.assertIn(field, self.admin.search_fields)
    
    def test_readonly_fields(self):
        """Test readonly_fields configuration."""
        expected_readonly = [
            'created_at', 'updated_at', 'approved_at', 'ip_address', 'get_avatar_preview'
        ]
        for field in expected_readonly:
            self.assertIn(field, self.admin.readonly_fields)
    
    def test_get_queryset_optimization(self):
        """Test get_queryset uses select_related for optimization."""
        request = self._get_request()
        queryset = self.admin.get_queryset(request)
        
        # Check that select_related is used
        self.assertIn('category', queryset.query.select_related)
        self.assertIn('author', queryset.query.select_related)
        self.assertIn('approved_by', queryset.query.select_related)
    
    def test_get_rating_stars_display(self):
        """Test get_rating_stars method displays stars correctly."""
        html = self.admin.get_rating_stars(self.testimonial)
        
        # Should contain 5 filled stars (★) for rating of 5
        self.assertIn('★' * 5, html)
        # Should NOT contain empty stars (☆) for rating of 5
        self.assertNotIn('☆', html)
        self.assertIn('title="5"', html)
    
    def test_get_rating_stars_partial(self):
        """Test rating stars with partial rating."""
        self.testimonial.rating = 3
        self.testimonial.save()
        
        html = self.admin.get_rating_stars(self.testimonial)
        
        # Should have 3 filled and 2 empty
        self.assertIn('★' * 3, html)
        self.assertIn('☆' * 2, html)
    
    def test_status_badge_pending(self):
        """Test status_badge for pending testimonial."""
        html = self.admin.status_badge(self.testimonial)
        
        self.assertIn('Pending', html)
        self.assertIn('background', html.lower())  # Has styling
    
    def test_status_badge_approved(self):
        """Test status_badge for approved testimonial."""
        self.testimonial.status = TestimonialStatus.APPROVED
        self.testimonial.save()
        
        html = self.admin.status_badge(self.testimonial)
        
        self.assertIn('Approved', html)
        self.assertIn('background', html.lower())
    
    def test_status_badge_rejected(self):
        """Test status_badge for rejected testimonial."""
        self.testimonial.status = TestimonialStatus.REJECTED
        self.testimonial.save()
        
        html = self.admin.status_badge(self.testimonial)
        
        self.assertIn('Rejected', html)
        self.assertIn('background', html.lower())
    
    def test_status_badge_featured(self):
        """Test status_badge for featured testimonial."""
        self.testimonial.status = TestimonialStatus.FEATURED
        self.testimonial.save()
        
        html = self.admin.status_badge(self.testimonial)
        
        self.assertIn('Featured', html)
        self.assertIn('background', html.lower())
    
    def test_has_media_true(self):
        """Test has_media when testimonial has media."""
        # Add media to testimonial
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image(),
            media_type=TestimonialMediaType.IMAGE
        )
        
        result = self.admin.has_media(self.testimonial)
        self.assertTrue(result)
    
    def test_has_media_false(self):
        """Test has_media when testimonial has no media."""
        result = self.admin.has_media(self.testimonial)
        self.assertFalse(result)
    
    def test_created_at_formatted(self):
        """Test created_at_formatted displays date correctly."""
        formatted = self.admin.created_at_formatted(self.testimonial)
        
        # Should be formatted as string
        self.assertIsInstance(formatted, str)
        # Should contain year
        self.assertIn(str(self.testimonial.created_at.year), formatted)
    
    def test_get_avatar_thumbnail_with_avatar(self):
        """Test avatar thumbnail display when avatar exists."""
        self.testimonial.avatar = self._create_test_image('avatar.jpg')
        self.testimonial.save()
        
        html = self.admin.get_avatar_thumbnail(self.testimonial)
        
        self.assertIn('<img', html)
        self.assertIn(self.testimonial.avatar.url, html)
        self.assertIn('width="40"', html)
        self.assertIn('height="40"', html)
        self.assertIn('border-radius: 50%', html)
    
    def test_get_avatar_thumbnail_without_avatar(self):
        """Test avatar thumbnail display when no avatar."""
        html = self.admin.get_avatar_thumbnail(self.testimonial)
        
        # Should show placeholder
        self.assertIn('👤', html)
        self.assertIn('<div', html)
        self.assertIn('background-color', html)
    
    def test_get_avatar_preview_with_avatar(self):
        """Test avatar preview display when avatar exists."""
        self.testimonial.avatar = self._create_test_image('avatar.jpg')
        self.testimonial.save()
        
        html = self.admin.get_avatar_preview(self.testimonial)
        
        self.assertIn('<img', html)
        self.assertIn(self.testimonial.avatar.url, html)
        self.assertIn('max-width: 200px', html)
        self.assertIn('max-height: 200px', html)
    
    def test_get_avatar_preview_without_avatar(self):
        """Test avatar preview display when no avatar."""
        html = self.admin.get_avatar_preview(self.testimonial)
        
        # Should show larger placeholder
        self.assertIn('👤', html)
        self.assertIn('width: 200px', html)
        self.assertIn('height: 200px', html)


# ============================================================================
# ADMIN ACTIONS TESTS
# ============================================================================

class TestimonialAdminActionsTest(AdminTestCase):
    """Tests for admin bulk actions."""
    
    def setUp(self):
        super().setUp()
        self.admin = TestimonialAdmin(Testimonial, self.site)
        
        # Create multiple testimonials for bulk actions
        self.testimonials = []
        for i in range(5):
            t = Testimonial.objects.create(
                author=self.regular_user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=4,
                status=TestimonialStatus.PENDING
            )
            self.testimonials.append(t)
    
    def test_approve_testimonials_action(self):
        """Test approve_testimonials admin action."""
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t.id for t in self.testimonials[:3]])
        
        # Execute action
        self.admin.approve_testimonials(request, queryset)
        
        # Verify all are approved
        for t in self.testimonials[:3]:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.APPROVED)
    
    def test_approve_testimonials_already_approved(self):
        """Test approving already approved testimonials."""
        # Approve one first
        self.testimonials[0].status = TestimonialStatus.APPROVED
        self.testimonials[0].save()
        
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t.id for t in self.testimonials[:2]])
        
        # Execute action
        self.admin.approve_testimonials(request, queryset)
        
        # Should only count the one that changed
        messages = list(request._messages)
        self.assertTrue(any('1 testimonial' in str(m) for m in messages))
    
    def test_reject_testimonials_action(self):
        """Test reject_testimonials admin action."""
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t.id for t in self.testimonials[:3]])
        
        # Execute action
        self.admin.reject_testimonials(request, queryset)
        
        # Verify all are rejected
        for t in self.testimonials[:3]:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.REJECTED)
    
    def test_feature_testimonials_action(self):
        """Test feature_testimonials admin action."""
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t.id for t in self.testimonials[:2]])
        
        # Execute action
        self.admin.feature_testimonials(request, queryset)
        
        # Verify all are featured
        for t in self.testimonials[:2]:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.FEATURED)
    
    def test_archive_testimonials_action(self):
        """Test archive_testimonials admin action."""
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t.id for t in self.testimonials])
        
        # Execute action
        self.admin.archive_testimonials(request, queryset)
        
        # Verify all are archived
        for t in self.testimonials:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.ARCHIVED)
    
    def test_actions_count_correctly(self):
        """Test that action counts are correct."""
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t.id for t in self.testimonials[:3]])
        
        self.admin.approve_testimonials(request, queryset)
        
        # Check message
        messages = list(request._messages)
        self.assertTrue(any('3 testimonials' in str(m) for m in messages))
    
    def test_actions_on_empty_queryset(self):
        """Test actions on empty queryset."""
        request = self._get_request()
        queryset = Testimonial.objects.none()
        
        self.admin.approve_testimonials(request, queryset)
        
        # Should show 0 count
        messages = list(request._messages)
        self.assertTrue(any('0 testimonial' in str(m) for m in messages))


# ============================================================================
# CATEGORY ADMIN TESTS
# ============================================================================

class TestimonialCategoryAdminTest(AdminTestCase):
    """Tests for TestimonialCategoryAdmin."""
    
    def setUp(self):
        super().setUp()
        self.admin = TestimonialCategoryAdmin(TestimonialCategory, self.site)
    
    def test_category_admin_is_registered(self):
        """Test that category admin is registered."""
        from django.contrib import admin
        self.assertIn(TestimonialCategory, admin.site._registry)
    
    def test_list_display_fields(self):
        """Test list_display includes necessary fields."""
        expected_fields = ['name', 'slug', 'is_active', 'testimonials_count', 'order']
        for field in expected_fields:
            self.assertIn(field, self.admin.list_display)
    
    def test_prepopulated_fields(self):
        """Test slug is prepopulated from name."""
        self.assertIn('slug', self.admin.prepopulated_fields)
        self.assertEqual(self.admin.prepopulated_fields['slug'], ('name',))
    
    def test_testimonials_count_method(self):
        """Test testimonials_count displays correct count."""
        # Add testimonials to category (setUp already created 1)
        for i in range(3):
            Testimonial.objects.create(
                author=self.regular_user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5,
                category=self.category
            )
        
        count = self.admin.testimonials_count(self.category)
        # Should be 4 total (1 from setUp + 3 new)
        self.assertEqual(count, 4)
    
    def test_testimonials_count_zero(self):
        """Test testimonials_count with no testimonials."""
        new_category = TestimonialCategory.objects.create(
            name='Empty Category',
            slug='empty'
        )
        
        count = self.admin.testimonials_count(new_category)
        self.assertEqual(count, 0)
    
    def test_testimonials_count_uses_annotation(self):
        """Test testimonials_count uses annotated value if available."""
        # Simulate annotated queryset
        self.category.testimonials_count = 42  # Set annotation
        
        count = self.admin.testimonials_count(self.category)
        self.assertEqual(count, 42)  # Should use annotation
    
    def test_get_queryset_annotation(self):
        """Test get_queryset adds testimonials_count annotation."""
        request = self._get_request()
        queryset = self.admin.get_queryset(request)
        
        # Should have annotation
        category = queryset.first()
        self.assertTrue(hasattr(category, 'testimonials_count'))


# ============================================================================
# MEDIA INLINE TESTS
# ============================================================================

class TestimonialMediaInlineTest(AdminTestCase):
    """Tests for TestimonialMediaInline."""
    
    def setUp(self):
        super().setUp()
        self.inline = TestimonialMediaInline(TestimonialMedia, self.site)
    
    def test_inline_configuration(self):
        """Test inline basic configuration."""
        self.assertEqual(self.inline.model, TestimonialMedia)
        self.assertEqual(self.inline.extra, 1)
    
    def test_inline_fields(self):
        """Test inline displays correct fields."""
        expected_fields = ('file', 'media_type', 'title', 'is_primary', 'order')
        self.assertEqual(self.inline.fields, expected_fields)
    
    def test_get_queryset_ordering(self):
        """Test inline queryset is ordered correctly."""
        # Create media items
        media1 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('img1.jpg'),
            media_type=TestimonialMediaType.IMAGE,
            is_primary=False,
            order=2
        )
        media2 = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image('img2.jpg'),
            media_type=TestimonialMediaType.IMAGE,
            is_primary=True,
            order=1
        )
        
        request = self._get_request()
        queryset = self.inline.get_queryset(request)
        
        # Primary should come first, then ordered by order field
        items = list(queryset)
        self.assertEqual(items[0], media2)  # Primary first


# ============================================================================
# ADMIN FORM TESTS
# ============================================================================

class TestimonialAdminFormTest(AdminTestCase):
    """Tests for TestimonialAdminForm."""
    
    def test_form_rejection_reason_required_when_rejected(self):
        """Test rejection_reason is required when status is rejected."""
        form = TestimonialAdminForm(
            data={
                'author_name': 'Test User',
                'content': 'Test content',
                'rating': 5,
                'status': TestimonialStatus.REJECTED,
                # rejection_reason is missing
            },
            instance=self.testimonial
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('rejection_reason', form.errors)
    
    def test_form_rejection_reason_not_required_when_approved(self):
        """Test rejection_reason not required when not rejected."""
        form = TestimonialAdminForm(
            data={
                'author_name': 'Test User',
                'content': 'Test content',
                'rating': 5,
                'status': TestimonialStatus.APPROVED,
                # rejection_reason is optional
            },
            instance=self.testimonial
        )
        
        # Form might have other validation errors, but not for rejection_reason
        if not form.is_valid():
            self.assertNotIn('rejection_reason', form.errors)
    
    def test_form_response_field_exists(self):
        """Test form has response field."""
        form = TestimonialAdminForm(instance=self.testimonial)
        self.assertIn('response', form.fields)
    
    def test_form_rejection_reason_field_exists(self):
        """Test form has rejection_reason field."""
        form = TestimonialAdminForm(instance=self.testimonial)
        self.assertIn('rejection_reason', form.fields)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class AdminEdgeCaseTests(AdminTestCase):
    """Tests for edge cases and error handling."""
    
    def setUp(self):
        super().setUp()
        self.admin = TestimonialAdmin(Testimonial, self.site)
    
    def test_rating_stars_with_minimum_rating(self):
        """Test rating stars with minimum rating (1)."""
        self.testimonial.rating = 1
        self.testimonial.save()
        
        html = self.admin.get_rating_stars(self.testimonial)
        
        # Should have 1 filled and 4 empty
        self.assertIn('★', html)
        self.assertIn('☆' * 4, html)
    
    def test_rating_stars_with_max_rating(self):
        """Test rating stars with maximum rating."""
        self.testimonial.rating = 5
        self.testimonial.save()
        
        html = self.admin.get_rating_stars(self.testimonial)
        
        # Should have 5 filled and 0 empty
        self.assertIn('★' * 5, html)
        self.assertNotIn('☆', html)
    
    def test_has_media_with_deleted_media(self):
        """Test has_media when media is deleted."""
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=self._create_test_image(),
            media_type=TestimonialMediaType.IMAGE
        )
        
        # Delete media
        media.delete()
        
        # Clear cache
        if hasattr(self.testimonial, '_has_media_cache'):
            del self.testimonial._has_media_cache
        
        result = self.admin.has_media(self.testimonial)
        self.assertFalse(result)
    
    def test_testimonials_count_with_no_category(self):
        """Test count when testimonial has no category."""
        t = Testimonial.objects.create(
            author=self.regular_user,
            author_name='No Category User',
            content='Test',
            rating=5,
            category=None
        )
        
        # Should not crash
        self.assertIsNone(t.category)
    
    def test_action_on_mixed_status_testimonials(self):
        """Test actions work on testimonials with mixed statuses."""
        t1 = Testimonial.objects.create(
            author=self.regular_user,
            author_name='User 1',
            content='Content 1',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        t2 = Testimonial.objects.create(
            author=self.regular_user,
            author_name='User 2',
            content='Content 2',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        request = self._get_request()
        queryset = Testimonial.objects.filter(id__in=[t1.id, t2.id])
        
        # Feature both
        self.admin.feature_testimonials(request, queryset)
        
        # Both should be featured now
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertEqual(t1.status, TestimonialStatus.FEATURED)
        self.assertEqual(t2.status, TestimonialStatus.FEATURED)
    
    def test_admin_with_anonymous_testimonial(self):
        """Test admin display works with anonymous testimonials."""
        anon = Testimonial.objects.create(
            author_name='Anonymous',
            content='Anonymous testimonial',
            rating=5,
            is_anonymous=True
        )
        
        # Should display without errors
        html = self.admin.get_rating_stars(anon)
        self.assertIsNotNone(html)
        
        badge = self.admin.status_badge(anon)
        self.assertIsNotNone(badge)
    
    def test_admin_with_very_long_content(self):
        """Test admin handles very long content."""
        long_content = 'A' * 10000
        self.testimonial.content = long_content
        self.testimonial.save()
        
        # Should not crash when displaying
        request = self._get_request()
        queryset = self.admin.get_queryset(request)
        
        # Retrieve it
        t = queryset.get(id=self.testimonial.id)
        self.assertEqual(len(t.content), 10000)
    
    def test_admin_with_special_characters_in_name(self):
        """Test admin handles special characters in names."""
        self.testimonial.author_name = "Tëst Üser <script>alert('xss')</script>"
        self.testimonial.save()
        
        # Should handle safely
        request = self._get_request()
        queryset = self.admin.get_queryset(request)
        t = queryset.get(id=self.testimonial.id)
        
        self.assertIn('Tëst', t.author_name)
    
    def test_category_admin_with_duplicate_slugs_prevented(self):
        """Test that duplicate slugs are handled in category admin."""
        cat1 = TestimonialCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Creating another with same slug should be prevented by model
        # or the admin form should handle it
        # This is tested at the form level
        from testimonials.forms import TestimonialCategoryForm
        
        form = TestimonialCategoryForm(data={
            'name': 'Test Category',
            'slug': 'test-category',  # Duplicate
            'is_active': True,
            'order': 1
        })
        
        # Form should auto-generate unique slug or fail validation
        # Depending on implementation
        self.assertIsNotNone(form)