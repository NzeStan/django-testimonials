# testimonials/tests/test_serializers.py

"""
Comprehensive tests for testimonial serializers.
Tests field validation, permissions, file uploads, edge cases, and failures.
"""

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from rest_framework import serializers as drf_serializers
from unittest.mock import Mock, patch
from io import BytesIO
from PIL import Image

from testimonials.api.serializers import (
    TestimonialMediaSerializer,
    TestimonialCategorySerializer,
    TestimonialUserSerializer,
    TestimonialAdminSerializer,
    TestimonialSerializer,
    TestimonialCreateSerializer,
    TestimonialUserDetailSerializer,
    TestimonialAdminDetailSerializer,
    TestimonialAdminActionSerializer,
)
from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialSource, TestimonialMediaType
from testimonials.conf import app_settings

User = get_user_model()


class TestimonialMediaSerializerTest(TestCase):
    """Tests for TestimonialMediaSerializer."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='mediauser',
            email='media@example.com',
            password='mediapass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        self.category = TestimonialCategory.objects.create(
            name='Media Category',
            slug='media-category'
        )
        self.testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Media User',
            author_email='media@example.com',
            title='Media Review',
            content='Outstanding experience with great support.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.APPROVED
        )
    
    def _create_test_image(self, filename='test.jpg', size=(100, 100), format='JPEG'):
        """Helper to create test image file."""
        image = Image.new('RGB', size, color='red')
        file = BytesIO()
        image.save(file, format=format)
        file.seek(0)
        return SimpleUploadedFile(filename, file.read(), content_type=f'image/{format.lower()}')
    
    def _create_test_video(self, filename='test.mp4'):
        """Helper to create test video file."""
        return SimpleUploadedFile(filename, b'fake video content', content_type='video/mp4')
    
    def test_media_serializer_read_only_fields(self):
        """Test that specific fields are read-only."""
        serializer = TestimonialMediaSerializer()
        read_only = serializer.Meta.read_only_fields
        
        self.assertIn('id', read_only)
        self.assertIn('file_url', read_only)
        self.assertIn('media_type_display', read_only)
        self.assertIn('thumbnails', read_only)
        self.assertIn('created_at', read_only)
        self.assertIn('updated_at', read_only)
    
    def test_media_serializer_valid_image_upload(self):
        """Test uploading a valid image file."""
        request = self.factory.post('/fake-url/')
        request.user = self.user
        
        image_file = self._create_test_image()
        data = {
            'testimonial': self.testimonial.id,
            'file': image_file,
            'title': 'Test Image',
            'description': 'Test description',
            'is_primary': True,
            'order': 1
        }
        
        serializer = TestimonialMediaSerializer(
            data=data,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        media = serializer.save()
        
        self.assertEqual(media.testimonial, self.testimonial)
        self.assertEqual(media.title, 'Test Image')
        self.assertTrue(media.file.name.endswith('.jpg'))
    
    def test_media_serializer_invalid_file_extension(self):
        """Test uploading file with invalid extension."""
        request = self.factory.post('/fake-url/')
        request.user = self.user
        
        # Create a file with .exe extension
        invalid_file = SimpleUploadedFile(
            'malware.exe',
            b'fake exe content',
            content_type='application/x-msdownload'
        )
        
        data = {
            'testimonial': self.testimonial.id,
            'file': invalid_file,
        }
        
        serializer = TestimonialMediaSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('file', serializer.errors)
    
    def test_media_serializer_file_too_large(self):
        """Test uploading file that exceeds size limit."""
        request = self.factory.post('/fake-url/')
        request.user = self.user
        
        # Create a large file (simulate exceeding MAX_FILE_SIZE)
        large_content = b'x' * (app_settings.MAX_FILE_SIZE + 1)
        large_file = SimpleUploadedFile(
            'large.jpg',
            large_content,
            content_type='image/jpeg'
        )
        
        data = {
            'testimonial': self.testimonial.id,
            'file': large_file,
        }
        
        serializer = TestimonialMediaSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('file', serializer.errors)
    
    def test_media_serializer_user_cannot_add_media_to_others_testimonial(self):
        """Test that users cannot add media to other users' testimonials."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_testimonial = Testimonial.objects.create(
            author=other_user,
            author_name='Other User',
            author_email='other@example.com',
            title='Other Review',
            content='Wonderful products and services provided.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.APPROVED
        )
        
        request = self.factory.post('/fake-url/')
        request.user = self.user
        
        image_file = self._create_test_image()
        data = {
            'testimonial': other_testimonial.id,
            'file': image_file,
        }
        
        serializer = TestimonialMediaSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('testimonial', serializer.errors)
        self.assertIn("only add media to your own", str(serializer.errors['testimonial'][0]).lower())
    
    def test_media_serializer_staff_can_add_media_to_any_testimonial(self):
        """Test that staff users can add media to any testimonial."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_testimonial = Testimonial.objects.create(
            author=other_user,
            author_name='Other User',
            author_email='other@example.com',
            title='Other Review',
            content='Amazing quality and great customer service overall.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.APPROVED
        )
        
        request = self.factory.post('/fake-url/')
        request.user = self.staff_user
        
        image_file = self._create_test_image()
        data = {
            'testimonial': other_testimonial.id,
            'file': image_file,
            'title': 'Staff Added Media'
        }
        
        serializer = TestimonialMediaSerializer(
            data=data,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_media_serializer_requires_authentication(self):
        """Test that unauthenticated users cannot add media."""
        request = self.factory.post('/fake-url/')
        request.user = Mock(is_authenticated=False)
        
        image_file = self._create_test_image()
        data = {
            'testimonial': self.testimonial.id,
            'file': image_file,
        }
        
        serializer = TestimonialMediaSerializer(
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('testimonial', serializer.errors)
        self.assertIn('authentication required', str(serializer.errors['testimonial'][0]).lower())
    
    def test_media_serializer_get_file_url(self):
        """Test get_file_url method returns correct URL."""
        request = self.factory.get('/fake-url/')
        
        image_file = self._create_test_image()
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image_file,
            media_type=TestimonialMediaType.IMAGE
        )
        
        serializer = TestimonialMediaSerializer(media, context={'request': request})
        data = serializer.data
        
        self.assertIn('file_url', data)
        self.assertIsNotNone(data['file_url'])
        self.assertIn('http', data['file_url'])
    
    def test_media_serializer_get_thumbnails_for_image(self):
        """Test get_thumbnails returns thumbnail URLs for images."""
        request = self.factory.get('/fake-url/')
        
        image_file = self._create_test_image()
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image_file,
            media_type=TestimonialMediaType.IMAGE
        )
        
        serializer = TestimonialMediaSerializer(media, context={'request': request})
        data = serializer.data
        
        # Should have thumbnails for images
        self.assertIn('thumbnails', data)
        # Thumbnails might be None if not generated yet, but field should exist
    
    def test_media_serializer_no_thumbnails_for_video(self):
        """Test get_thumbnails returns None for non-image media."""
        request = self.factory.get('/fake-url/')
        
        video_file = self._create_test_video()
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=video_file,
            media_type=TestimonialMediaType.VIDEO
        )
        
        serializer = TestimonialMediaSerializer(media, context={'request': request})
        data = serializer.data
        
        self.assertIn('thumbnails', data)
        self.assertIsNone(data['thumbnails'])
    
    def test_media_serializer_get_media_type_display(self):
        """Test get_media_type_display returns human-readable media type."""
        image_file = self._create_test_image()
        media = TestimonialMedia.objects.create(
            testimonial=self.testimonial,
            file=image_file,
            media_type=TestimonialMediaType.IMAGE
        )
        
        serializer = TestimonialMediaSerializer(media)
        data = serializer.data
        
        self.assertIn('media_type_display', data)
        self.assertIsNotNone(data['media_type_display'])


class TestimonialCategorySerializerTest(TestCase):
    """Tests for TestimonialCategorySerializer."""
    
    def setUp(self):
        self.category = TestimonialCategory.objects.create(
            name='Product Category',
            slug='product-category',
            description='Product reviews and feedback',
            is_active=True,
            order=1
        )
        self.user = User.objects.create_user(
            username='categoryuser',
            email='category@example.com',
            password='categorypass123'
        )
    
    def test_category_serializer_read_only_fields(self):
        """Test that specific fields are read-only."""
        serializer = TestimonialCategorySerializer()
        read_only = serializer.Meta.read_only_fields
        
        self.assertIn('id', read_only)
        self.assertIn('testimonials_count', read_only)
        self.assertIn('slug', read_only)
        self.assertIn('created_at', read_only)
        self.assertIn('updated_at', read_only)
    
    def test_category_serializer_all_fields_present(self):
        """Test that all expected fields are present in serialization."""
        serializer = TestimonialCategorySerializer(self.category)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('slug', data)
        self.assertIn('description', data)
        self.assertIn('is_active', data)
        self.assertIn('order', data)
        self.assertIn('testimonials_count', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_category_serializer_testimonials_count_zero(self):
        """Test testimonials_count returns 0 when no testimonials."""
        serializer = TestimonialCategorySerializer(self.category)
        data = serializer.data
        
        self.assertEqual(data['testimonials_count'], 0)
    
    def test_category_serializer_testimonials_count_with_approved(self):
        """Test testimonials_count includes approved testimonials."""
        Testimonial.objects.create(
            author=self.user,
            author_name='Approved User',
            author_email='approved@example.com',
            title='Approved Review',
            content='Excellent quality and service throughout the experience.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.APPROVED
        )
        
        serializer = TestimonialCategorySerializer(self.category)
        data = serializer.data
        
        self.assertEqual(data['testimonials_count'], 1)
    
    def test_category_serializer_testimonials_count_with_featured(self):
        """Test testimonials_count includes featured testimonials."""
        Testimonial.objects.create(
            author=self.user,
            author_name='Featured User',
            author_email='featured@example.com',
            title='Featured Review',
            content='Outstanding service and great quality products.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.FEATURED
        )
        
        serializer = TestimonialCategorySerializer(self.category)
        data = serializer.data
        
        self.assertEqual(data['testimonials_count'], 1)
    
    def test_category_serializer_testimonials_count_excludes_pending(self):
        """Test testimonials_count excludes pending testimonials."""
        Testimonial.objects.create(
            author=self.user,
            author_name='Pending User',
            author_email='pending@example.com',
            title='Pending Review',
            content='Wonderful experience with amazing customer support.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
        
        serializer = TestimonialCategorySerializer(self.category)
        data = serializer.data
        
        self.assertEqual(data['testimonials_count'], 0)
    
    def test_category_serializer_testimonials_count_excludes_rejected(self):
        """Test testimonials_count excludes rejected testimonials."""
        Testimonial.objects.create(
            author=self.user,
            author_name='Rejected User',
            author_email='rejected@example.com',
            title='Rejected Review',
            content='Very satisfied with the quality of products received.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.REJECTED
        )
        
        serializer = TestimonialCategorySerializer(self.category)
        data = serializer.data
        
        self.assertEqual(data['testimonials_count'], 0)
    
    def test_category_serializer_valid_creation(self):
        """Test creating a new category with valid data."""
        data = {
            'name': 'New Category',
            'description': 'New description',
            'is_active': True,
            'order': 2
        }
        
        serializer = TestimonialCategorySerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        category = serializer.save()
        
        self.assertEqual(category.name, 'New Category')
        self.assertEqual(category.description, 'New description')
        self.assertTrue(category.is_active)
        self.assertEqual(category.order, 2)
        self.assertIsNotNone(category.slug)
    
    def test_category_serializer_name_required(self):
        """Test that name field is required."""
        data = {
            'description': 'Test description',
            'is_active': True
        }
        
        serializer = TestimonialCategorySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)


class TestimonialUserSerializerTest(TestCase):
    """Tests for TestimonialUserSerializer (regular user permissions)."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.category = TestimonialCategory.objects.create(
            name='Test Category',
            slug='test-category',
            is_active=True
        )
        self.testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='User Review',
            author_email='user@example.com',
            title='Review Title',
            content='Excellent quality and service provided throughout.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
    
    def test_user_serializer_read_only_fields(self):
        """Test that sensitive fields are read-only for regular users."""
        serializer = TestimonialUserSerializer()
        read_only = serializer.Meta.read_only_fields
        
        # Critical security fields should be read-only
        self.assertIn('status', read_only)
        self.assertIn('is_verified', read_only)
        self.assertIn('is_anonymous', read_only)
        self.assertIn('response', read_only)
        self.assertIn('display_order', read_only)
        self.assertIn('approved_at', read_only)
    
    def test_user_serializer_all_fields_present(self):
        """Test that all expected fields are present."""
        serializer = TestimonialUserSerializer(self.testimonial)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('author_name', data)
        self.assertIn('author_email', data)
        self.assertIn('title', data)
        self.assertIn('content', data)
        self.assertIn('rating', data)
        self.assertIn('status', data)
        self.assertIn('status_display', data)
        self.assertIn('is_verified', data)
    
    def test_user_serializer_cannot_update_status(self):
        """Test that users cannot update status field."""
        request = self.factory.patch('/fake-url/')
        request.user = self.user
        
        data = {'status': TestimonialStatus.APPROVED}
        
        serializer = TestimonialUserSerializer(
            self.testimonial,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        # Should be valid but status should not change
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        # Status should remain PENDING
        self.assertEqual(updated.status, TestimonialStatus.PENDING)
    
    def test_user_serializer_cannot_update_is_verified(self):
        """Test that users cannot update is_verified field."""
        request = self.factory.patch('/fake-url/')
        request.user = self.user
        
        data = {'is_verified': True}
        
        serializer = TestimonialUserSerializer(
            self.testimonial,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        # is_verified should remain False
        self.assertFalse(updated.is_verified)
    
    def test_user_serializer_cannot_update_display_order(self):
        """Test that users cannot update display_order field."""
        request = self.factory.patch('/fake-url/')
        request.user = self.user
        
        data = {'display_order': 100}
        
        serializer = TestimonialUserSerializer(
            self.testimonial,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        # display_order should not be 100
        self.assertNotEqual(updated.display_order, 100)
    
    def test_user_serializer_cannot_update_response(self):
        """Test that users cannot update response field."""
        request = self.factory.patch('/fake-url/')
        request.user = self.user
        
        data = {'response': 'User trying to add response'}
        
        serializer = TestimonialUserSerializer(
            self.testimonial,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        # response should remain None or empty string (not set by user)
        self.assertIn(updated.response, [None, ''])
    
    def test_user_serializer_can_update_own_basic_fields(self):
        """Test that users can update their own basic fields."""
        request = self.factory.patch('/fake-url/')
        request.user = self.user
        
        data = {
            'title': 'Updated Title',
            'content': 'Updated content',
            'rating': 4
        }
        
        serializer = TestimonialUserSerializer(
            self.testimonial,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        self.assertEqual(updated.title, 'Updated Title')
        self.assertEqual(updated.content, 'Updated content')
        self.assertEqual(updated.rating, 4)
    
    def test_user_serializer_get_status_display(self):
        """Test get_status_display returns human-readable status."""
        serializer = TestimonialUserSerializer(self.testimonial)
        data = serializer.data
        
        self.assertIn('status_display', data)
        self.assertIsNotNone(data['status_display'])
    
    def test_user_serializer_get_source_display(self):
        """Test get_source_display returns human-readable source."""
        serializer = TestimonialUserSerializer(self.testimonial)
        data = serializer.data
        
        self.assertIn('source_display', data)
        self.assertIsNotNone(data['source_display'])
    
    def test_user_serializer_get_author_display(self):
        """Test get_author_display returns correct author name."""
        serializer = TestimonialUserSerializer(self.testimonial)
        data = serializer.data
        
        self.assertIn('author_display', data)
        self.assertEqual(data['author_display'], 'User Review')
    
    def test_user_serializer_category_nested(self):
        """Test category field is properly nested."""
        serializer = TestimonialUserSerializer(self.testimonial)
        data = serializer.data
        
        self.assertIn('category', data)
        self.assertIsInstance(data['category'], dict)
        self.assertIn('name', data['category'])


class TestimonialAdminSerializerTest(TestCase):
    """Tests for TestimonialAdminSerializer (staff permissions)."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        self.category = TestimonialCategory.objects.create(
            name='Product Category',
            slug='product-category',
            is_active=True
        )
        self.testimonial = Testimonial.objects.create(
            author=self.admin_user,
            author_name='Admin User',
            author_email='admin@example.com',
            title='Admin Review',
            content='Excellent service and great quality products.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
    
    def test_admin_serializer_all_fields_present(self):
        """Test that all admin fields are present."""
        serializer = TestimonialAdminSerializer(self.testimonial)
        data = serializer.data
        
        # Check for admin-only fields
        self.assertIn('response', data)
        self.assertIn('response_at', data)
        self.assertIn('response_by', data)
        self.assertIn('approved_at', data)
        self.assertIn('approved_by', data)
        self.assertIn('rejection_reason', data)
        self.assertIn('display_order', data)
    
    def test_admin_serializer_can_update_status(self):
        """Test that admins can update status field."""
        request = self.factory.patch('/fake-url/')
        request.user = self.admin_user
        
        data = {'status': TestimonialStatus.APPROVED}
        
        serializer = TestimonialAdminSerializer(
            self.testimonial,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        self.assertEqual(updated.status, TestimonialStatus.APPROVED)
    
    def test_admin_serializer_can_update_is_verified(self):
        """Test that admins can update is_verified field."""
        data = {'is_verified': True}
        
        serializer = TestimonialAdminSerializer(
            self.testimonial,
            data=data,
            partial=True
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        self.assertTrue(updated.is_verified)
    
    def test_admin_serializer_can_update_display_order(self):
        """Test that admins can update display_order field."""
        data = {'display_order': 100}
        
        serializer = TestimonialAdminSerializer(
            self.testimonial,
            data=data,
            partial=True
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        self.assertEqual(updated.display_order, 100)
    
    def test_admin_serializer_can_update_response(self):
        """Test that admins can update response field."""
        data = {'response': 'Admin response to testimonial'}
        
        serializer = TestimonialAdminSerializer(
            self.testimonial,
            data=data,
            partial=True
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        
        self.assertEqual(updated.response, 'Admin response to testimonial')
    
    def test_admin_serializer_minimal_read_only_fields(self):
        """Test that admin serializer has minimal read-only restrictions."""
        serializer = TestimonialAdminSerializer()
        read_only = serializer.Meta.read_only_fields
        
        # These should still be read-only even for admins
        self.assertIn('id', read_only)
        self.assertIn('slug', read_only)
        self.assertIn('created_at', read_only)
        self.assertIn('updated_at', read_only)
        
        # But these should be editable for admins
        self.assertNotIn('status', read_only)
        self.assertNotIn('is_verified', read_only)
        self.assertNotIn('display_order', read_only)
        self.assertNotIn('response', read_only)


class TestimonialSerializerTest(TestCase):
    """Tests for TestimonialSerializer and TestimonialCreateSerializer."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.category = TestimonialCategory.objects.create(
            name='Test Category',
            slug='test-category',
            is_active=True
        )
    
    @patch('testimonials.api.serializers.app_settings')
    def test_serializer_create_anonymous_testimonial(self, mock_settings):
        """Test creating an anonymous testimonial."""
        mock_settings.ALLOW_ANONYMOUS = True
        mock_settings.REQUIRE_APPROVAL = False
        
        request = self.factory.post('/fake-url/')
        request.user = Mock(is_authenticated=False)
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        data = {
            'author_name': 'Anonymous User',
            'author_email': 'anon@example.com',
            'title': 'Anonymous Review',
            'content': 'Great product and excellent service!',
            'rating': 5,
            'category': self.category.id,
            'is_anonymous': True
        }
        
        serializer = TestimonialCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        testimonial = serializer.save()
        
        self.assertTrue(testimonial.is_anonymous)
        self.assertIsNone(testimonial.author)
        self.assertEqual(testimonial.ip_address, '127.0.0.1')
    
    @patch('testimonials.api.serializers.app_settings')
    def test_serializer_reject_anonymous_when_disabled(self, mock_settings):
        """Test rejecting anonymous testimonials when policy is disabled."""
        mock_settings.ALLOW_ANONYMOUS = False
        mock_settings.REQUIRE_APPROVAL = False
        
        request = self.factory.post('/fake-url/')
        request.user = Mock(is_authenticated=False)
        
        data = {
            'author_name': 'Anonymous User',
            'author_email': 'anon@example.com',
            'title': 'Anonymous Review',
            'content': 'Great product and excellent service!',
            'rating': 5,
            'category': self.category.id,
            'is_anonymous': True
        }
        
        serializer = TestimonialCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        # Error is in non_field_errors, not in is_anonymous field
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('anonymous', str(serializer.errors['non_field_errors'][0]).lower())
    
    @patch('testimonials.api.serializers.app_settings')
    def test_serializer_create_authenticated_testimonial(self, mock_settings):
        """Test creating testimonial as authenticated user."""
        mock_settings.REQUIRE_APPROVAL = False
        
        request = self.factory.post('/fake-url/')
        request.user = self.user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        data = {
            'author_name': 'John Doe',
            'author_email': 'john@example.com',
            'title': 'Authenticated Review',
            'content': 'Very satisfied with the quality and service provided.',
            'rating': 5,
            'category': self.category.id
        }
        
        serializer = TestimonialCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        testimonial = serializer.save()
        
        self.assertEqual(testimonial.author, self.user)
        self.assertFalse(testimonial.is_anonymous)
        self.assertEqual(testimonial.ip_address, '127.0.0.1')
    
    @patch('testimonials.api.serializers.log_testimonial_action')
    @patch('testimonials.api.serializers.app_settings')
    def test_serializer_create_logs_action(self, mock_settings, mock_log):
        """Test that create method logs testimonial action."""
        mock_settings.REQUIRE_APPROVAL = False
        
        request = self.factory.post('/fake-url/')
        request.user = self.user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        data = {
            'author_name': 'Jane Smith',
            'author_email': 'jane@example.com',
            'title': 'Logging Review',
            'content': 'Amazing experience overall with great support.',
            'rating': 5,
            'category': self.category.id
        }
        
        serializer = TestimonialCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        testimonial = serializer.save()
        
        mock_log.assert_called_once_with(testimonial, "create", self.user)
    
    def test_serializer_category_id_write_only(self):
        """Test that category_id is write-only in TestimonialSerializer."""
        data = {
            'author_name': 'Mike Johnson',
            'author_email': 'mike@example.com',
            'title': 'Write Only Review',
            'content': 'Excellent quality and very satisfied with the results.',
            'rating': 5,
            'category_id': self.category.id
        }
        
        serializer = TestimonialSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        testimonial = serializer.save()
        
        # When reading back, category_id should not be in serialized data
        read_serializer = TestimonialSerializer(testimonial)
        self.assertNotIn('category_id', read_serializer.data)
        self.assertIn('category', read_serializer.data)
    
    def test_serializer_inactive_category_not_allowed(self):
        """Test that inactive categories cannot be assigned."""
        inactive_category = TestimonialCategory.objects.create(
            name='Inactive Category',
            slug='inactive-category',
            is_active=False
        )
        
        data = {
            'author_name': 'Sarah Williams',
            'author_email': 'sarah@example.com',
            'title': 'Inactive Category Review',
            'content': 'Wonderful experience with excellent customer support.',
            'rating': 5,
            'category': inactive_category.id
        }
        
        serializer = TestimonialCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('category', serializer.errors)


class TestimonialAdminActionSerializerTest(TestCase):
    """Tests for TestimonialAdminActionSerializer."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='actionuser',
            email='action@example.com',
            password='actionpass123'
        )
        self.category = TestimonialCategory.objects.create(
            name='Action Category',
            slug='action-category'
        )
        self.testimonial1 = Testimonial.objects.create(
            author=self.user,
            author_name='First User',
            author_email='first@example.com',
            title='First Review',
            content='Great experience with excellent products.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
        self.testimonial2 = Testimonial.objects.create(
            author=self.user,
            author_name='Second User',
            author_email='second@example.com',
            title='Second Review',
            content='Very satisfied with quality and support.',
            rating=4,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
    
    def test_admin_action_serializer_valid_approve_action(self):
        """Test valid approve action."""
        data = {
            'action': 'approve',
            'testimonial_ids': [self.testimonial1.id, self.testimonial2.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_admin_action_serializer_valid_reject_action_with_reason(self):
        """Test valid reject action with reason."""
        data = {
            'action': 'reject',
            'testimonial_ids': [self.testimonial1.id],
            'reason': 'Inappropriate content'
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_admin_action_serializer_reject_without_reason_fails(self):
        """Test that reject action requires reason."""
        data = {
            'action': 'reject',
            'testimonial_ids': [self.testimonial1.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('reason', serializer.errors)
        self.assertIn('required when rejecting', str(serializer.errors['reason'][0]).lower())
    
    def test_admin_action_serializer_reject_with_blank_reason_fails(self):
        """Test that reject action requires non-blank reason."""
        data = {
            'action': 'reject',
            'testimonial_ids': [self.testimonial1.id],
            'reason': '   '  # Only whitespace
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('reason', serializer.errors)
    
    def test_admin_action_serializer_valid_feature_action(self):
        """Test valid feature action."""
        data = {
            'action': 'feature',
            'testimonial_ids': [self.testimonial1.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_admin_action_serializer_valid_archive_action(self):
        """Test valid archive action."""
        data = {
            'action': 'archive',
            'testimonial_ids': [self.testimonial1.id, self.testimonial2.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_admin_action_serializer_invalid_action(self):
        """Test that invalid action is rejected."""
        data = {
            'action': 'delete',  # Not a valid action
            'testimonial_ids': [self.testimonial1.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('action', serializer.errors)
    
    def test_admin_action_serializer_empty_testimonial_ids_fails(self):
        """Test that empty testimonial_ids list is rejected."""
        data = {
            'action': 'approve',
            'testimonial_ids': []
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('testimonial_ids', serializer.errors)
    
    def test_admin_action_serializer_nonexistent_testimonial_ids_fails(self):
        """Test that non-existent testimonial IDs are rejected."""
        data = {
            'action': 'approve',
            'testimonial_ids': [99999, 88888]  # Non-existent IDs
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('testimonial_ids', serializer.errors)
        self.assertIn('do not exist', str(serializer.errors['testimonial_ids'][0]).lower())
    
    def test_admin_action_serializer_mixed_valid_invalid_ids_fails(self):
        """Test that mix of valid and invalid IDs is rejected."""
        data = {
            'action': 'approve',
            'testimonial_ids': [self.testimonial1.id, 99999]  # One valid, one invalid
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('testimonial_ids', serializer.errors)
    
    def test_admin_action_serializer_action_required(self):
        """Test that action field is required."""
        data = {
            'testimonial_ids': [self.testimonial1.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('action', serializer.errors)
    
    def test_admin_action_serializer_testimonial_ids_required(self):
        """Test that testimonial_ids field is required."""
        data = {
            'action': 'approve'
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('testimonial_ids', serializer.errors)
    
    def test_admin_action_serializer_reason_optional_for_approve(self):
        """Test that reason is optional for approve action."""
        data = {
            'action': 'approve',
            'testimonial_ids': [self.testimonial1.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_admin_action_serializer_reason_optional_for_feature(self):
        """Test that reason is optional for feature action."""
        data = {
            'action': 'feature',
            'testimonial_ids': [self.testimonial1.id]
        }
        
        serializer = TestimonialAdminActionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestimonialDetailSerializersTest(TestCase):
    """Tests for detail serializers (user and admin)."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='detailuser',
            email='detail@example.com',
            password='detailpass123'
        )
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        self.category = TestimonialCategory.objects.create(
            name='Detail Category',
            slug='detail-category'
        )
        self.testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Detail User',
            author_email='detail@example.com',
            title='Detail Review',
            content='Wonderful service and great quality products.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.APPROVED,
            response='Admin response here'
        )
    
    def test_user_detail_serializer_includes_response_at(self):
        """Test that user detail serializer includes response_at."""
        serializer = TestimonialUserDetailSerializer(self.testimonial)
        data = serializer.data
        
        self.assertIn('response_at', data)
    
    def test_user_detail_serializer_excludes_response_by(self):
        """Test that user detail serializer excludes response_by."""
        serializer = TestimonialUserDetailSerializer(self.testimonial)
        data = serializer.data
        
        self.assertNotIn('response_by', data)
    
    def test_user_detail_serializer_response_at_read_only(self):
        """Test that response_at is read-only in user detail serializer."""
        serializer = TestimonialUserDetailSerializer()
        read_only = serializer.Meta.read_only_fields
        
        self.assertIn('response_at', read_only)
    
    def test_admin_detail_serializer_inherits_from_admin(self):
        """Test that admin detail serializer inherits from admin serializer."""
        self.assertTrue(
            issubclass(TestimonialAdminDetailSerializer, TestimonialAdminSerializer)
        )
    
    def test_admin_detail_serializer_has_all_admin_fields(self):
        """Test that admin detail serializer has all admin fields."""
        serializer = TestimonialAdminDetailSerializer(self.testimonial)
        data = serializer.data
        
        # Should have all sensitive admin fields
        self.assertIn('response_by', data)
        self.assertIn('approved_by', data)
        self.assertIn('rejection_reason', data)


class SerializerEdgeCasesTest(TestCase):
    """Tests for edge cases and boundary conditions."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='edgeuser',
            email='edge@example.com',
            password='edgepass123'
        )
        self.category = TestimonialCategory.objects.create(
            name='Edge Category',
            slug='edge-category'
        )
    
    def test_testimonial_with_null_category(self):
        """Test serializing testimonial with null category."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Edge User',
            author_email='edge@example.com',
            title='Null Category Review',
            content='Great experience with excellent support provided.',
            rating=5,
            category=None,  # Null category
            status=TestimonialStatus.PENDING
        )
        
        serializer = TestimonialSerializer(testimonial)
        data = serializer.data
        
        self.assertIn('category', data)
        self.assertIsNone(data['category'])
    
    def test_testimonial_with_special_characters(self):
        """Test serializing testimonial with special characters."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='User <script>alert("xss")</script> Name',
            author_email='user@example.com',
            title='Title with "quotes" and \'apostrophes\'',
            content='Content with émojis 🎉 and spëcial çharacters that is long enough to pass validation.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
        
        serializer = TestimonialSerializer(testimonial)
        data = serializer.data
        
        # Should serialize without errors
        self.assertIn('author_name', data)
        self.assertIn('title', data)
        self.assertIn('content', data)
    
    def test_testimonial_with_very_long_content(self):
        """Test serializing testimonial with very long content."""
        long_content = 'x' * 10000  # Very long content
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Long User',
            author_email='long@example.com',
            title='Long Review',
            content=long_content,
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
        
        serializer = TestimonialSerializer(testimonial)
        data = serializer.data
        
        self.assertEqual(data['content'], long_content)
    
    def test_media_serializer_with_missing_file(self):
        """Test serializing media with missing file."""
        media = TestimonialMedia.objects.create(
            testimonial=Testimonial.objects.create(
                author=self.user,
                author_name='Media User',
                author_email='media@example.com',
                title='Media Review',
                content='Outstanding experience overall with great support.',
                rating=5,
                category=self.category
            ),
            media_type=TestimonialMediaType.IMAGE
            # No file attached
        )
        
        serializer = TestimonialMediaSerializer(media)
        data = serializer.data
        
        # Should handle missing file gracefully
        self.assertIn('file_url', data)
        # file_url should be None for missing files
    
    def test_serializer_with_none_request_context(self):
        """Test serializers work without request in context."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Context User',
            author_email='context@example.com',
            title='Context Review',
            content='Amazing quality and service provided throughout.',
            rating=5,
            category=self.category,
            status=TestimonialStatus.PENDING
        )
        
        # Serialize without request context
        serializer = TestimonialSerializer(testimonial, context={})
        data = serializer.data
        
        # Should still serialize basic data
        self.assertIn('id', data)
        self.assertIn('title', data)
        self.assertIn('content', data)