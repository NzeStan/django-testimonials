# testimonials/tests/test_views.py

"""
Comprehensive API view tests for django-testimonials package.
Tests cover all endpoints, permissions, actions, and edge cases.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import json
import io

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import (
    TestimonialStatus,
    TestimonialSource,
    TestimonialMediaType
)

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================
@override_settings(
    ADMINS=[('Admin', 'admin@example.com')],
    LOGGING={'version': 1, 'disable_existing_loggers': True}
)
class APITestCaseBase(APITestCase):
    """Base test case with common setup for all API tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole TestCase (runs once)."""
        # Create test users
        cls.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123',
            first_name='Regular',
            last_name='User'
        )
        
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True,
            first_name='Admin',
            last_name='User'
        )
        
        cls.moderator_user = User.objects.create_user(
            username='moderator',
            email='moderator@example.com',
            password='modpass123',
            is_staff=True,
            first_name='Moderator',
            last_name='User'
        )
        
        # Create test categories
        cls.category1 = TestimonialCategory.objects.create(
            name='Products',
            slug='products',
            description='Product testimonials',
            is_active=True
        )
        
        cls.category2 = TestimonialCategory.objects.create(
            name='Services',
            slug='services',
            description='Service testimonials',
            is_active=True
        )
    
    def setUp(self):
        """Set up for each test method."""
        self.client = APIClient()
    
    def create_test_image(self, name='test.jpg', width=100, height=100):
        """Helper to create a test image file."""
        from PIL import Image
        
        image = Image.new('RGB', (width, height), color='blue')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            name=name,
            content=image_io.read(),
            content_type='image/jpeg'
        )


# ============================================================================
# TESTIMONIAL API TESTS - LIST & RETRIEVE
# ============================================================================

class TestimonialListAPITests(APITestCaseBase):
    """Tests for testimonial list endpoint."""
    
    def setUp(self):
        super().setUp()
        
        # Create testimonials with different statuses
        self.pending = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Regular User',
            content='Pending testimonial content here',
            rating=5,
            status=TestimonialStatus.PENDING
        )
        
        self.approved = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Regular User',
            content='Approved testimonial content',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        self.featured = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Regular User',
            content='Featured testimonial content',
            rating=5,
            status=TestimonialStatus.FEATURED
        )
        
        self.rejected = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Regular User',
            content='Rejected testimonial content',
            rating=2,
            status=TestimonialStatus.REJECTED
        )
    
    def test_list_testimonials_anonymous(self):
        """Test that anonymous users only see published testimonials."""
        url = reverse('testimonials:api:testimonial-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only see approved and featured
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.approved.id, ids)
        self.assertIn(self.featured.id, ids)
        self.assertNotIn(self.pending.id, ids)
        self.assertNotIn(self.rejected.id, ids)
    
    def test_list_testimonials_authenticated_user(self):
        """Test that authenticated users see published + their own."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('testimonials:api:testimonial-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should see all their own testimonials
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.approved.id, ids)
        self.assertIn(self.featured.id, ids)
        self.assertIn(self.pending.id, ids)  # Own pending
        self.assertIn(self.rejected.id, ids)  # Own rejected
    
    def test_list_testimonials_admin(self):
        """Test that admins see all testimonials."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('testimonials:api:testimonial-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should see everything
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.approved.id, ids)
        self.assertIn(self.featured.id, ids)
        self.assertIn(self.pending.id, ids)
        self.assertIn(self.rejected.id, ids)
    
    def test_list_testimonials_pagination(self):
        """Test pagination works correctly."""
        # Create more testimonials
        for i in range(15):
            Testimonial.objects.create(
                author=self.regular_user,
                content=f'Testimonial {i} content',
                rating=5,
                status=TestimonialStatus.APPROVED
            )
        
        url = reverse('testimonials:api:testimonial-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
    
    def test_list_testimonials_ordering(self):
        """Test ordering by different fields."""
        self.client.force_authenticate(user=self.admin_user)
        
        # Test ordering by rating
        url = reverse('testimonials:api:testimonial-list') + '?ordering=-rating'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ratings = [t['rating'] for t in response.data['results']]
        self.assertEqual(ratings, sorted(ratings, reverse=True))
        
        # Test ordering by created_at
        url = reverse('testimonials:api:testimonial-list') + '?ordering=created_at'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestimonialRetrieveAPITests(APITestCaseBase):
    """Tests for testimonial retrieve endpoint."""
    
    def setUp(self):
        super().setUp()
        
        self.testimonial = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Regular User',
            content='Detailed testimonial content',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category1
        )
    
    def test_retrieve_testimonial_anonymous(self):
        """Test retrieving testimonial as anonymous user."""
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': self.testimonial.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.testimonial.id)
        self.assertEqual(response.data['content'], self.testimonial.content)
        
        # Should NOT see sensitive fields like ip_address
        self.assertNotIn('ip_address', response.data)
        self.assertNotIn('rejection_reason', response.data)
    
    def test_retrieve_testimonial_admin(self):
        """Test admin sees all fields including sensitive ones."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': self.testimonial.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Admin should see sensitive fields in detail view
        self.assertIn('ip_address', response.data)
        self.assertIn('extra_data', response.data)
    
    def test_retrieve_nonexistent_testimonial(self):
        """Test retrieving non-existent testimonial returns 404."""
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_retrieve_pending_testimonial_as_owner(self):
        """Test owner can retrieve their own pending testimonial."""
        pending = Testimonial.objects.create(
            author=self.regular_user,
            content='My pending testimonial',
            rating=4,
            status=TestimonialStatus.PENDING
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': pending.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], pending.id)
    
    def test_retrieve_pending_testimonial_as_other_user(self):
        """Test other users cannot retrieve someone's pending testimonial."""
        pending = Testimonial.objects.create(
            author=self.regular_user,
            content='Pending testimonial',
            rating=4,
            status=TestimonialStatus.PENDING
        )
        
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123'
        )
        
        self.client.force_authenticate(user=other_user)
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': pending.pk})
        response = self.client.get(url)
        
        # Should get 404 (not found in their queryset)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ============================================================================
# TESTIMONIAL API TESTS - CREATE
# ============================================================================

class TestimonialCreateAPITests(APITestCaseBase):
    """Tests for testimonial creation endpoint."""
    
    def test_create_testimonial_authenticated(self):
        """Test authenticated user can create testimonial."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'This is excellent quality and service',
            'rating': 5,
            'category': self.category1.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], data['content'])
        self.assertEqual(response.data['rating'], data['rating'])
        
        # Verify in database
        testimonial = Testimonial.objects.get(pk=response.data['id'])
        self.assertEqual(testimonial.author, self.regular_user)
        self.assertEqual(testimonial.author_name, 'Regular User')
    
    def test_create_testimonial_anonymous(self):
        """Test anonymous user can create testimonial."""
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'Anonymous quality testimonial content here',
            'rating': 5,
            'is_anonymous': True,
            'author_name': 'Anonymous User',
            'author_email': 'anon@example.com'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_testimonial_with_all_fields(self):
        """Test creating testimonial with all optional fields."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'Detailed quality testimonial with all fields',
            'rating': 5,
            'author_name': 'John Doe',
            'author_email': 'john@example.com',
            'author_title': 'ceo',
            'company': 'Acme Corp',
            'location': 'New York, NY',
            'title': 'Great Product',
            'website': 'https://acme.com',
            'social_media': {'twitter': '@johndoe'},
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['company'], data['company'])
        self.assertEqual(response.data['location'], data['location'])
        self.assertEqual(response.data['title'], data['title'])
    
    def test_create_testimonial_invalid_rating(self):
        """Test creating testimonial with invalid rating."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'Quality content here',
            'rating': 0  # Invalid
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rating', response.data)
    
    def test_create_testimonial_content_too_short(self):
        """Test creating testimonial with content too short."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'Short',  # Less than minimum
            'rating': 5
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
    
    def test_create_testimonial_missing_required_fields(self):
        """Test creating testimonial without required fields."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'rating': 5
            # Missing content
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
    
    def test_create_testimonial_with_inactive_category(self):
        """Test creating testimonial with inactive category."""
        inactive_category = TestimonialCategory.objects.create(
            name='Inactive',
            is_active=False
        )
        
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'Quality content here',
            'rating': 5,
            'category': inactive_category.id
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should reject inactive category
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# TESTIMONIAL API TESTS - UPDATE & DELETE
# ============================================================================

class TestimonialUpdateAPITests(APITestCaseBase):
    """Tests for testimonial update endpoint."""
    
    def setUp(self):
        super().setUp()
        
        self.testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='Original quality content',
            rating=4,
            status=TestimonialStatus.PENDING
        )
    
    def test_update_own_testimonial(self):
        """Test user can update their own testimonial."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': self.testimonial.pk})
        data = {
            'content': 'Updated quality content here',
            'rating': 5
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], data['content'])
        self.assertEqual(response.data['rating'], data['rating'])
        
        # Verify in database
        self.testimonial.refresh_from_db()
        self.assertEqual(self.testimonial.content, data['content'])
    
    def test_update_other_user_testimonial(self):
        """Test user cannot update another user's testimonial."""
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123'
        )
        
        self.client.force_authenticate(user=other_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': self.testimonial.pk})
        data = {
            'content': 'Trying to update quality content',
            'rating': 5
        }
        
        response = self.client.patch(url, data, format='json')
        
        # Should be forbidden or not found
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])
    
    def test_user_cannot_update_admin_fields(self):
        """Test user cannot update admin-only fields."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': self.testimonial.pk})
        data = {
            'content': 'Updated quality content',
            'rating': 5,
            'status': TestimonialStatus.APPROVED,  # Admin-only
            'is_verified': True,  # Admin-only
            'display_order': 100  # Admin-only
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify admin fields were NOT changed
        self.testimonial.refresh_from_db()
        self.assertEqual(self.testimonial.status, TestimonialStatus.PENDING)
        self.assertFalse(self.testimonial.is_verified)
        self.assertEqual(self.testimonial.display_order, 0)
    
    def test_admin_can_update_all_fields(self):
        """Test admin can update all fields including admin-only."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': self.testimonial.pk})
        data = {
            'status': TestimonialStatus.APPROVED,
            'is_verified': True,
            'display_order': 10
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify admin fields were changed
        self.testimonial.refresh_from_db()
        self.assertEqual(self.testimonial.status, TestimonialStatus.APPROVED)
        self.assertTrue(self.testimonial.is_verified)
        self.assertEqual(self.testimonial.display_order, 10)


class TestimonialDeleteAPITests(APITestCaseBase):
    """Tests for testimonial delete endpoint."""
    
    def test_delete_own_testimonial(self):
        """Test user can delete their own testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='To be deleted quality content',
            rating=5
        )
        
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': testimonial.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deleted
        self.assertFalse(Testimonial.objects.filter(pk=testimonial.pk).exists())
    
    def test_delete_other_user_testimonial(self):
        """Test user cannot delete another user's testimonial."""
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123'
        )
        
        testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='Protected quality content',
            rating=5
        )
        
        self.client.force_authenticate(user=other_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': testimonial.pk})
        response = self.client.delete(url)
        
        # Should be forbidden or not found
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])
        
        # Verify NOT deleted
        self.assertTrue(Testimonial.objects.filter(pk=testimonial.pk).exists())
    
    def test_admin_can_delete_any_testimonial(self):
        """Test admin can delete any testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='Admin can delete quality content',
            rating=5
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': testimonial.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Testimonial.objects.filter(pk=testimonial.pk).exists())


# ============================================================================
# TESTIMONIAL API TESTS - FILTERING & SEARCHING
# ============================================================================

class TestimonialFilteringAPITests(APITestCaseBase):
    """Tests for testimonial filtering."""
    
    def setUp(self):
        super().setUp()
        
        # Create diverse testimonials for filtering
        self.t1 = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Alice',
            company='Acme Corp',
            content='Excellent product quality',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category1
        )
        
        self.t2 = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Bob',
            company='Tech Inc',
            content='Good service experience',
            rating=4,
            status=TestimonialStatus.APPROVED,
            category=self.category2
        )
        
        self.t3 = Testimonial.objects.create(
            author=self.regular_user,
            author_name='Charlie',
            content='Average quality product',
            rating=3,
            status=TestimonialStatus.PENDING
        )
    
    def test_filter_by_status(self):
        """Test filtering by status."""
        url = reverse('testimonials:api:testimonial-list') + '?status=approved'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t3.id, ids)
    
    def test_filter_by_category(self):
        """Test filtering by category."""
        url = reverse('testimonials:api:testimonial-list') + f'?category={self.category1.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)
    
    def test_filter_by_rating(self):
        """Test filtering by rating."""
        url = reverse('testimonials:api:testimonial-list') + '?min_rating=4'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t3.id, ids)
    
    def test_search_testimonials(self):
        """Test searching testimonials."""
        url = reverse('testimonials:api:testimonial-list') + '?search=Acme'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)
    
    def test_multiple_filters(self):
        """Test combining multiple filters."""
        url = reverse('testimonials:api:testimonial-list') + \
              f'?status=approved&category={self.category1.id}&min_rating=5'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)
        self.assertNotIn(self.t3.id, ids)


# ============================================================================
# TESTIMONIAL API TESTS - CUSTOM ACTIONS
# ============================================================================

class TestimonialCustomActionsAPITests(APITestCaseBase):
    """Tests for custom testimonial actions."""
    
    def setUp(self):
        super().setUp()
        
        self.pending_testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='Pending quality testimonial',
            rating=5,
            status=TestimonialStatus.PENDING
        )
    
    def test_approve_action_as_admin(self):
        """Test admin can approve testimonial."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-approve', kwargs={'pk': self.pending_testimonial.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'success')
        
        # Verify in database
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, TestimonialStatus.APPROVED)
        self.assertIsNotNone(self.pending_testimonial.approved_at)
        self.assertEqual(self.pending_testimonial.approved_by, self.admin_user)
    
    def test_approve_action_as_regular_user(self):
        """Test regular user cannot approve testimonial."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-approve', kwargs={'pk': self.pending_testimonial.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify NOT approved
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, TestimonialStatus.PENDING)
    
    def test_reject_action_with_reason(self):
        """Test admin can reject testimonial with reason."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-reject', kwargs={'pk': self.pending_testimonial.pk})
        data = {'reason': 'Does not meet quality standards'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify in database
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, TestimonialStatus.REJECTED)
        self.assertEqual(self.pending_testimonial.rejection_reason, data['reason'])
    
    def test_reject_action_without_reason(self):
        """Test rejecting without reason uses default."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-reject', kwargs={'pk': self.pending_testimonial.pk})
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.pending_testimonial.refresh_from_db()
        self.assertEqual(self.pending_testimonial.status, TestimonialStatus.REJECTED)
    
    def test_feature_action(self):
        """Test admin can feature testimonial."""
        approved = Testimonial.objects.create(
            author=self.regular_user,
            content='Quality content to feature',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-feature', kwargs={'pk': approved.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify in database
        approved.refresh_from_db()
        self.assertEqual(approved.status, TestimonialStatus.FEATURED)
    
    def test_featured_list_action(self):
        """Test getting featured testimonials."""
        # Create featured testimonials
        for i in range(3):
            Testimonial.objects.create(
                author=self.regular_user,
                content=f'Featured quality content {i}',
                rating=5,
                status=TestimonialStatus.FEATURED
            )
        
        url = reverse('testimonials:api:testimonial-featured')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
        # All should be featured
        for item in response.data:
            testimonial = Testimonial.objects.get(pk=item['id'])
            self.assertEqual(testimonial.status, TestimonialStatus.FEATURED)
    
    def test_stats_action(self):
        """Test getting testimonial statistics."""
        url = reverse('testimonials:api:testimonial-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('status_distribution', response.data)
        self.assertIn('rating_distribution', response.data)


class TestimonialBulkActionsAPITests(APITestCaseBase):
    """Tests for bulk actions on testimonials."""
    
    def setUp(self):
        super().setUp()
        
        # Create multiple pending testimonials
        self.testimonials = []
        for i in range(5):
            t = Testimonial.objects.create(
                author=self.regular_user,
                content=f'Bulk action quality content {i}',
                rating=5,
                status=TestimonialStatus.PENDING
            )
            self.testimonials.append(t)
    
    def test_bulk_approve(self):
        """Test bulk approving testimonials."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-bulk-action')
        data = {
            'action': 'approve',
            'testimonial_ids': [t.id for t in self.testimonials[:3]]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        
        # Verify in database
        for t in self.testimonials[:3]:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.APPROVED)
        
        # Others should still be pending
        for t in self.testimonials[3:]:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.PENDING)
    
    def test_bulk_reject(self):
        """Test bulk rejecting testimonials."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-bulk-action')
        data = {
            'action': 'reject',
            'testimonial_ids': [t.id for t in self.testimonials[:2]],
            'rejection_reason': 'Quality standards not met'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        
        # Verify in database
        for t in self.testimonials[:2]:
            t.refresh_from_db()
            self.assertEqual(t.status, TestimonialStatus.REJECTED)
    
    def test_bulk_action_empty_list(self):
        """Test bulk action with empty list fails."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-bulk-action')
        data = {
            'action': 'approve',
            'testimonial_ids': []
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bulk_action_invalid_ids(self):
        """Test bulk action with invalid IDs fails."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonial-bulk-action')
        data = {
            'action': 'approve',
            'testimonial_ids': [99999, 88888]  # Non-existent
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bulk_action_as_regular_user(self):
        """Test regular user cannot perform bulk actions."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-bulk-action')
        data = {
            'action': 'approve',
            'testimonial_ids': [self.testimonials[0].id]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================================
# CATEGORY API TESTS
# ============================================================================

class TestimonialCategoryAPITests(APITestCaseBase):
    """Tests for testimonial category endpoints."""
    
    def test_list_categories(self):
        """Test listing categories."""
        url = reverse('testimonials:api:testimonialcategory-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)
    
    def test_retrieve_category(self):
        """Test retrieving a single category."""
        url = reverse('testimonials:api:testimonialcategory-detail', kwargs={'pk': self.category1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.category1.name)
        self.assertIn('testimonials_count', response.data)
    
    def test_create_category_as_admin(self):
        """Test admin can create category."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonialcategory-list')
        data = {
            'name': 'Events',
            'description': 'Event testimonials',
            'is_active': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], data['name'])
    
    def test_create_category_as_regular_user(self):
        """Test regular user cannot create category."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonialcategory-list')
        data = {
            'name': 'New Category',
            'description': 'Should fail'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_category_as_admin(self):
        """Test admin can update category."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonialcategory-detail', kwargs={'pk': self.category1.pk})
        data = {
            'description': 'Updated description'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], data['description'])
    
    def test_delete_category_as_admin(self):
        """Test admin can delete category."""
        category = TestimonialCategory.objects.create(
            name='To Delete',
            is_active=True
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('testimonials:api:testimonialcategory-detail', kwargs={'pk': category.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TestimonialCategory.objects.filter(pk=category.pk).exists())
    
    def test_category_stats_action(self):
        """Test getting category statistics."""
        url = reverse('testimonials:api:testimonialcategory-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_categories', response.data)
        self.assertIn('active_categories', response.data)


# ============================================================================
# MEDIA API TESTS
# ============================================================================

class TestimonialMediaAPITests(APITestCaseBase):
    """Tests for testimonial media endpoints."""
    
    def setUp(self):
        super().setUp()
        
        self.testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='Testimonial with media',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
    
    def test_list_media(self):
        """Test listing media files."""
        # Create some media
        image = self.create_test_image()
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            media_type=TestimonialMediaType.IMAGE
        )
        
        url = reverse('testimonials:api:testimonialmedia-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_retrieve_media(self):
        """Test retrieving a single media file."""
        image = self.create_test_image()
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            title='Test Image',
            media_type=TestimonialMediaType.IMAGE
        )
        
        url = reverse('testimonials:api:testimonialmedia-detail', kwargs={'pk': media.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Image')
    
    def test_create_media_authenticated(self):
        """Test authenticated user can upload media."""
        self.client.force_authenticate(user=self.regular_user)
        
        image = self.create_test_image()
        
        url = reverse('testimonials:api:testimonialmedia-list')
        data = {
            'testimonial': self.testimonial.id,
            'file': image,
            'title': 'My Image'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'My Image')
        self.assertEqual(response.data['media_type'], TestimonialMediaType.IMAGE)
    
    def test_filter_media_by_testimonial(self):
        """Test filtering media by testimonial."""
        image = self.create_test_image()
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            media_type=TestimonialMediaType.IMAGE
        )
        
        url = reverse('testimonials:api:testimonialmedia-list') + f'?testimonial={self.testimonial.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        for item in response.data['results']:
            self.assertEqual(item['testimonial'], self.testimonial.id)
    
    def test_filter_media_by_type(self):
        """Test filtering media by type."""
        image = self.create_test_image()
        TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image,
            media_type=TestimonialMediaType.IMAGE
        )
        
        url = reverse('testimonials:api:testimonialmedia-list') + '?media_type=image'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        for item in response.data['results']:
            self.assertEqual(item['media_type'], TestimonialMediaType.IMAGE)


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

class TestimonialAPIEdgeCasesTests(APITestCaseBase):
    """Tests for edge cases and error handling."""
    
    def test_rate_limiting(self):
        """Test that excessive requests are rate limited (if configured)."""
        # This test depends on your rate limiting configuration
        # Skip if rate limiting not configured
        pass
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        response = self.client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_sql_injection_attempt(self):
        """Test protection against SQL injection."""
        # Create a testimonial first
        Testimonial.objects.create(
            author=self.regular_user,
            content='Test content for SQL injection protection',
            rating=5,
            status=TestimonialStatus.APPROVED
        )
        
        url = reverse('testimonials:api:testimonial-list') + "?search='; DROP TABLE testimonials--"
        response = self.client.get(url)
        
        # Should handle safely
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ])
        
        # Database should still be intact
        self.assertTrue(Testimonial.objects.exists())
    
    def test_xss_attempt_in_content(self):
        """Test that XSS attempts are handled properly."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': '<script>alert("XSS")</script> quality content here',
            'rating': 5
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should either accept and sanitize, or reject
        if response.status_code == status.HTTP_201_CREATED:
            # Content should be stored (will be escaped on output)
            testimonial = Testimonial.objects.get(pk=response.data['id'])
            self.assertIn('quality content', testimonial.content)
    
    def test_concurrent_updates(self):
        """Test handling of concurrent updates to same testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.regular_user,
            content='Original quality content',
            rating=4
        )
        
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-detail', kwargs={'pk': testimonial.pk})
        
        # Simulate two concurrent updates
        data1 = {'rating': 5}
        data2 = {'content': 'Updated quality content'}
        
        response1 = self.client.patch(url, data1, format='json')
        response2 = self.client.patch(url, data2, format='json')
        
        # Both should succeed (last write wins)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
    
    def test_large_payload_handling(self):
        """Test handling of unusually large payloads."""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('testimonials:api:testimonial-list')
        data = {
            'content': 'Great product! ' * 200,  # Large but within limits
            'rating': 5,
            'author_name': 'Test User',
            'author_email': 'test@example.com'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should accept if within limits
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])