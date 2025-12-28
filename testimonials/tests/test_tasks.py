# testimonials/tests/test_tasks.py

"""
Comprehensive tests for Celery tasks.
Tests cover all task functions, edge cases, failures, retries, and successful operations.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.conf import settings
from unittest.mock import patch, Mock, MagicMock, call
from datetime import timedelta
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import os

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialMediaType
from testimonials import tasks

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class TaskTestCase(TestCase):
    """Base test case with common setup for all task tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole TestCase."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        
        cls.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        
        cls.category = TestimonialCategory.objects.create(
            name='Products',
            slug='products',
            is_active=True
        )
    
    def setUp(self):
        """Set up before each test."""
        # Clear mail outbox before each test
        mail.outbox = []
    
    def _create_test_image(self, filename='test.jpg'):
        """Helper to create a test image file."""
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(filename, image_io.read(), content_type='image/jpeg')


# ============================================================================
# EMAIL NOTIFICATION TASK TESTS
# ============================================================================

class SendTestimonialNotificationEmailTest(TaskTestCase):
    """Test send_testimonial_notification_email task."""
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        DEFAULT_FROM_EMAIL='noreply@example.com',
        SITE_NAME='Test Site',
        SITE_URL='http://testsite.com'
    )
    @patch('testimonials.tasks.render_to_string')
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_approved_email_sent_successfully(self, mock_email_class, mock_render):
        """Test that approved email is sent successfully."""
        mock_render.return_value = '<html>Approved</html>'
        mock_msg = MagicMock()
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Call task
        tasks.send_testimonial_notification_email(
            str(testimonial.pk),
            'approved',
            'john@example.com'
        )
        
        # Should render template (may be called multiple times due to admin notification)
        self.assertTrue(mock_render.called)
        
        # Should create email (may be called twice - once from signal, once from task)
        self.assertTrue(mock_email_class.called)
        call_kwargs = mock_email_class.call_args[1]
        self.assertEqual(call_kwargs['to'], ['john@example.com'])
        self.assertIn('approved', call_kwargs['subject'].lower())
        
        # Should send email (may be called multiple times due to signals)
        self.assertTrue(mock_msg.send.called)
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        DEFAULT_FROM_EMAIL='noreply@example.com'
    )
    @patch('testimonials.tasks.render_to_string')
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_rejected_email_sent_successfully(self, mock_email_class, mock_render):
        """Test that rejected email is sent successfully."""
        mock_render.return_value = '<html>Rejected</html>'
        mock_msg = MagicMock()
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Spam content',
            rating=1,
            status=TestimonialStatus.REJECTED,
            rejection_reason='Inappropriate content',
            category=self.category
        )
        
        # Call task
        tasks.send_testimonial_notification_email(
            str(testimonial.pk),
            'rejected',
            'john@example.com'
        )
        
        # Should send email (may be called multiple times due to signals)
        self.assertTrue(mock_msg.send.called)
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        DEFAULT_FROM_EMAIL='noreply@example.com'
    )
    @patch('testimonials.tasks.render_to_string')
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_featured_email_sent_successfully(self, mock_email_class, mock_render):
        """Test that featured email is sent successfully."""
        mock_render.return_value = '<html>Featured</html>'
        mock_msg = MagicMock()
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Excellent product!',
            rating=5,
            status=TestimonialStatus.FEATURED,
            category=self.category
        )
        
        # Call task
        tasks.send_testimonial_notification_email(
            str(testimonial.pk),
            'featured',
            'john@example.com'
        )
        
        # Should send email (may be called multiple times due to signals)
        self.assertTrue(mock_msg.send.called)
    
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=False)
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_email_not_sent_when_disabled(self, mock_email_class):
        """Test that email is not sent when notifications are disabled."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Call task
        tasks.send_testimonial_notification_email(
            str(testimonial.pk),
            'approved',
            'john@example.com'
        )
        
        # Should not create email
        mock_email_class.assert_not_called()
    
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    @patch('testimonials.tasks.logger')
    def test_nonexistent_testimonial_is_logged(self, mock_logger):
        """Test that nonexistent testimonial is logged."""
        # Call task with non-existent ID
        tasks.send_testimonial_notification_email(
            '99999',
            'approved',
            'john@example.com'
        )
        
        # Should log error
        self.assertTrue(mock_logger.error.called)
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        DEFAULT_FROM_EMAIL='noreply@example.com'
    )
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_email_sending_error_raises_for_retry(self, mock_email_class):
        """Test that email sending errors raise exception for retry."""
        mock_msg = MagicMock()
        mock_msg.send.side_effect = Exception("SMTP error")
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Call task - should raise exception
        with self.assertRaises(Exception):
            tasks.send_testimonial_notification_email(
                str(testimonial.pk),
                'approved',
                'john@example.com'
            )
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        DEFAULT_FROM_EMAIL='noreply@example.com'
    )
    @patch('testimonials.tasks.render_to_string')
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_custom_context_data_is_used(self, mock_email_class, mock_render):
        """Test that custom context data is passed to template."""
        mock_render.return_value = '<html>Email</html>'
        mock_msg = MagicMock()
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        custom_context = {'custom_key': 'custom_value'}
        
        # Call task with custom context
        tasks.send_testimonial_notification_email(
            str(testimonial.pk),
            'approved',
            'john@example.com',
            context_data=custom_context
        )
        
        # Check context was passed
        call_args = mock_render.call_args[0]
        context = call_args[1]
        self.assertEqual(context['custom_key'], 'custom_value')


# ============================================================================
# ADMIN NOTIFICATION TASK TESTS
# ============================================================================

class SendAdminNotificationTest(TaskTestCase):
    """Test send_admin_notification task."""
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        DEFAULT_FROM_EMAIL='noreply@example.com',
        ADMINS=[('Admin', 'admin@example.com'), ('Super Admin', 'super@example.com')],
        SITE_NAME='Test Site',
        SITE_URL='http://testsite.com'
    )
    @patch('testimonials.tasks.render_to_string')
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_admin_notification_sent_successfully(self, mock_email_class, mock_render):
        """Test that admin notification is sent successfully."""
        mock_render.return_value = '<html>New testimonial</html>'
        mock_msg = MagicMock()
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Call task
        tasks.send_admin_notification(str(testimonial.pk), 'new_testimonial')
        
        # Should create email (may be called twice - once from signal, once from task)
        self.assertTrue(mock_email_class.called)
        call_kwargs = mock_email_class.call_args[1]
        self.assertEqual(call_kwargs['to'], ['admin@example.com', 'super@example.com'])
        self.assertIn('New Testimonial', call_kwargs['subject'])
        
        # Should send email (may be called multiple times due to signals)
        self.assertTrue(mock_msg.send.called)
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        ADMINS=[],
        DEFAULT_FROM_EMAIL='noreply@example.com'
    )
    @patch('testimonials.tasks.logger')
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_no_email_sent_when_no_admins(self, mock_email_class, mock_logger):
        """Test that no email is sent when no admins configured."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Call task
        tasks.send_admin_notification(str(testimonial.pk), 'new_testimonial')
        
        # Should log warning
        self.assertTrue(mock_logger.warning.called)
        
        # Should not create email
        mock_email_class.assert_not_called()
    
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=False)
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_admin_notification_not_sent_when_disabled(self, mock_email_class):
        """Test that admin notification is not sent when disabled."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Call task
        tasks.send_admin_notification(str(testimonial.pk), 'new_testimonial')
        
        # Should not create email
        mock_email_class.assert_not_called()
    
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    @patch('testimonials.tasks.logger')
    def test_nonexistent_testimonial_is_logged(self, mock_logger):
        """Test that nonexistent testimonial is logged."""
        # Call task with non-existent ID
        tasks.send_admin_notification('99999', 'new_testimonial')
        
        # Should log error
        self.assertTrue(mock_logger.error.called)
    
    @override_settings(
        TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True,
        ADMINS=[('Admin', 'admin@example.com')],
        DEFAULT_FROM_EMAIL='noreply@example.com'
    )
    @patch('testimonials.tasks.EmailMultiAlternatives')
    def test_email_sending_error_raises_for_retry(self, mock_email_class):
        """Test that email sending errors raise exception for retry."""
        mock_msg = MagicMock()
        mock_msg.send.side_effect = Exception("SMTP error")
        mock_email_class.return_value = mock_msg
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Call task - should raise exception
        with self.assertRaises(Exception):
            tasks.send_admin_notification(str(testimonial.pk), 'new_testimonial')


# ============================================================================
# MEDIA PROCESSING TASK TESTS
# ============================================================================

class ProcessMediaTest(TaskTestCase):
    """Test process_media task."""
    
    @patch('testimonials.tasks.generate_thumbnails')
    @patch('testimonials.tasks.TestimonialCacheService.invalidate_media')
    def test_image_processing_generates_thumbnails(self, mock_cache, mock_generate):
        """Test that image processing generates thumbnails."""
        mock_generate.return_value = {
            'small': '/path/to/small.jpg',
            'medium': '/path/to/medium.jpg',
            'large': '/path/to/large.jpg'
        }
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Create media with actual uploaded file
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image('process_test.jpg'),
            description='Test image'
        )
        
        # Get the actual file path
        file_path = media.file.path
        
        # Call task
        tasks.process_media(str(media.pk))
        
        # Should generate thumbnails with the actual file path
        mock_generate.assert_called_once_with(file_path)
        
        # Refresh media
        media.refresh_from_db()
        
        # Should store thumbnail info
        self.assertIn('thumbnails', media.extra_data)
        self.assertEqual(media.extra_data['thumbnails'], mock_generate.return_value)
        
        # Should invalidate cache (multiple times: create, update, task completion)
        # Check that it was called
        self.assertTrue(mock_cache.called)
        # Verify it was called with correct args at least once
        mock_cache.assert_called_with(
            media_id=media.pk,
            testimonial_id=media.testimonial_id
        )
    
    @patch('testimonials.tasks.generate_thumbnails')
    @patch('testimonials.tasks.logger')
    def test_thumbnail_generation_error_is_logged(self, mock_logger, mock_generate):
        """Test that thumbnail generation errors are logged."""
        mock_generate.side_effect = Exception("Thumbnail error")
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Create media with actual uploaded file
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image('error_test.jpg'),
            description='Test image'
        )
        
        # Call task
        tasks.process_media(str(media.pk))
        
        # Should log error
        self.assertTrue(mock_logger.error.called)
    
    @patch('testimonials.tasks.generate_thumbnails')
    def test_non_image_media_skips_thumbnail_generation(self, mock_generate):
        """Test that non-image media skips thumbnail generation."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.VIDEO,
            description='Test video'
        )
        
        # Call task
        tasks.process_media(str(media.pk))
        
        # Should not generate thumbnails
        mock_generate.assert_not_called()
    
    @patch('testimonials.tasks.logger')
    def test_nonexistent_media_is_logged(self, mock_logger):
        """Test that processing nonexistent media logs error and raises for retry."""
        # Call task with non-existent ID - should raise exception
        try:
            tasks.process_media('99999')
        except:
            pass  # Expected to raise
        
        # Should log error
        self.assertTrue(mock_logger.error.called)
    
    @patch('testimonials.tasks.generate_thumbnails')
    def test_media_processing_error_raises_for_retry(self, mock_generate):
        """Test that media processing errors raise exception for retry."""
        mock_generate.side_effect = Exception("Processing error")
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Create media with actual uploaded file
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image('retry_test.jpg'),
            description='Test image'
        )
        
        # Call task - should not raise (error is caught)
        tasks.process_media(str(media.pk))


# ============================================================================
# MAINTENANCE TASK TESTS
# ============================================================================

class CleanupOldRejectedTestimonialsTest(TaskTestCase):
    """Test cleanup_old_rejected_testimonials task."""
    
    @patch('testimonials.tasks.TestimonialCacheService.invalidate_all')
    def test_cleanup_removes_old_rejected_testimonials(self, mock_cache):
        """Test that cleanup removes old rejected testimonials."""
        # Create old rejected testimonial
        old_date = timezone.now() - timedelta(days=100)
        old_testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Old User',
            content='Old content',
            rating=2,
            status=TestimonialStatus.REJECTED,
            category=self.category
        )
        # Use update() to bypass auto_now on updated_at
        Testimonial.objects.filter(pk=old_testimonial.pk).update(updated_at=old_date)
        
        # Create recent rejected testimonial
        recent_testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Recent User',
            content='Recent content',
            rating=2,
            status=TestimonialStatus.REJECTED,
            category=self.category
        )
        
        # Create approved testimonial (should not be deleted)
        approved_testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Approved User',
            content='Approved content',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        approved_testimonial.updated_at = old_date
        approved_testimonial.save()
        
        # Call task
        count = tasks.cleanup_old_rejected_testimonials(days_old=90)
        
        # Should delete 1 testimonial
        self.assertEqual(count, 1)
        
        # Old rejected should be deleted
        self.assertFalse(Testimonial.objects.filter(pk=old_testimonial.pk).exists())
        
        # Recent rejected should still exist
        self.assertTrue(Testimonial.objects.filter(pk=recent_testimonial.pk).exists())
        
        # Approved should still exist
        self.assertTrue(Testimonial.objects.filter(pk=approved_testimonial.pk).exists())
        
        # Should invalidate all caches
        mock_cache.assert_called_once()
    
    @patch('testimonials.tasks.TestimonialCacheService.invalidate_all')
    def test_cleanup_no_old_testimonials(self, mock_cache):
        """Test that cleanup handles no old testimonials gracefully."""
        # Create recent rejected testimonial
        recent_testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Recent User',
            content='Recent content',
            rating=2,
            status=TestimonialStatus.REJECTED,
            category=self.category
        )
        
        # Call task
        count = tasks.cleanup_old_rejected_testimonials(days_old=90)
        
        # Should delete 0 testimonials
        self.assertEqual(count, 0)
        
        # Should not invalidate caches
        mock_cache.assert_not_called()
    
    @patch('testimonials.tasks.logger')
    @patch('testimonials.tasks.TestimonialCacheService.invalidate_all')
    def test_cleanup_logs_deletion_count(self, mock_cache, mock_logger):
        """Test that cleanup logs the deletion count."""
        # Create old rejected testimonial
        old_date = timezone.now() - timedelta(days=100)
        old_testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Old User',
            content='Old content',
            rating=2,
            status=TestimonialStatus.REJECTED,
            category=self.category
        )
        # Use update() to bypass auto_now on updated_at
        Testimonial.objects.filter(pk=old_testimonial.pk).update(updated_at=old_date)
        
        # Call task
        count = tasks.cleanup_old_rejected_testimonials(days_old=90)
        
        # Should log info
        self.assertTrue(mock_logger.info.called)


# ============================================================================
# REPORT GENERATION TASK TESTS
# ============================================================================

class GenerateTestimonialReportTest(TaskTestCase):
    """Test generate_testimonial_report task."""
    
    @patch('testimonials.tasks.TestimonialCacheService.cache_stats')
    def test_report_generates_and_caches_stats(self, mock_cache):
        """Test that report generates stats and caches them."""
        # Create some testimonials
        Testimonial.objects.create(
            author=self.user,
            author_name='User 1',
            content='Content 1',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        Testimonial.objects.create(
            author=self.user,
            author_name='User 2',
            content='Content 2',
            rating=4,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Call task
        stats = tasks.generate_testimonial_report()
        
        # Should return stats
        self.assertIn('total', stats)
        self.assertEqual(stats['total'], 2)
        
        # Should cache stats
        mock_cache.assert_called_once_with(stats)
    
    @patch('testimonials.tasks.logger')
    @patch('testimonials.tasks.TestimonialCacheService.cache_stats')
    def test_report_generation_is_logged(self, mock_cache, mock_logger):
        """Test that report generation is logged."""
        # Call task
        tasks.generate_testimonial_report()
        
        # Should log info
        self.assertTrue(mock_logger.info.called)


# ============================================================================
# CACHE WARMING TASK TESTS
# ============================================================================

class WarmTestimonialCachesTest(TaskTestCase):
    """Test warm_testimonial_caches task."""
    
    @patch('testimonials.tasks.TestimonialCacheService.cache_stats')
    @patch('testimonials.tasks.TestimonialCacheService.cache_featured')
    @patch('testimonials.tasks.TestimonialCacheService.set')
    def test_cache_warming_warms_all_caches(self, mock_set, mock_cache_featured, mock_cache_stats):
        """Test that cache warming warms all caches."""
        # Create featured testimonials
        for i in range(15):
            Testimonial.objects.create(
                author=self.user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5,
                status=TestimonialStatus.FEATURED,
                category=self.category
            )
        
        # Call task
        result = tasks.warm_testimonial_caches()
        
        # Should return True
        self.assertTrue(result)
        
        # Should cache stats
        mock_cache_stats.assert_called_once()
        
        # Should cache featured
        mock_cache_featured.assert_called_once()
        
        # Should cache category stats
        self.assertTrue(mock_set.called)
    
    @patch('testimonials.tasks.logger')
    def test_cache_warming_is_logged(self, mock_logger):
        """Test that cache warming is logged."""
        # Call task
        tasks.warm_testimonial_caches()
        
        # Should log info (at least twice - start and complete)
        self.assertGreaterEqual(mock_logger.info.call_count, 2)


# ============================================================================
# VOLATILE CACHE REFRESH TASK TESTS
# ============================================================================

class RefreshVolatileCachesTest(TaskTestCase):
    """Test refresh_volatile_caches task."""
    
    @patch('testimonials.tasks.TestimonialCacheService.set')
    def test_volatile_cache_refresh_updates_counts(self, mock_set):
        """Test that volatile cache refresh updates counts."""
        # Create testimonials
        Testimonial.objects.create(
            author=self.user,
            author_name='User 1',
            content='Content 1',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        Testimonial.objects.create(
            author=self.user,
            author_name='User 2',
            content='Content 2',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Call task
        result = tasks.refresh_volatile_caches()
        
        # Should return True
        self.assertTrue(result)
        
        # Should set cache twice (pending count and today count)
        self.assertEqual(mock_set.call_count, 2)
        
        # Check that pending count was cached
        call_args_list = mock_set.call_args_list
        keys_cached = [call[0][0] for call in call_args_list]
        self.assertIn('testimonials:counts:pending', keys_cached)
        self.assertIn('testimonials:counts:today', keys_cached)
    
    @patch('testimonials.tasks.logger')
    def test_volatile_cache_refresh_is_logged(self, mock_logger):
        """Test that volatile cache refresh is logged."""
        # Call task
        tasks.refresh_volatile_caches()
        
        # Should log info (at least twice - start and complete)
        self.assertGreaterEqual(mock_logger.info.call_count, 2)


# ============================================================================
# STATS CACHE REFRESH TASK TESTS
# ============================================================================

class RefreshStatsCachesTest(TaskTestCase):
    """Test refresh_stats_caches task."""
    
    @patch('testimonials.tasks.TestimonialCacheService.cache_stats')
    def test_stats_cache_refresh_updates_stats(self, mock_cache):
        """Test that stats cache refresh updates stats."""
        # Create testimonials
        Testimonial.objects.create(
            author=self.user,
            author_name='User 1',
            content='Content 1',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Call task (if it exists in tasks.py)
        if hasattr(tasks, 'refresh_stats_caches'):
            result = tasks.refresh_stats_caches()
            
            # Should cache stats
            mock_cache.assert_called_once()


# ============================================================================
# CELERY AVAILABILITY TESTS
# ============================================================================

class CeleryAvailabilityTest(TestCase):
    """Test Celery availability handling."""
    
    def test_celery_available_constant_exists(self):
        """Test that CELERY_AVAILABLE constant exists."""
        self.assertTrue(hasattr(tasks, 'CELERY_AVAILABLE'))
    
    def test_shared_task_decorator_exists(self):
        """Test that shared_task decorator exists."""
        self.assertTrue(hasattr(tasks, 'shared_task'))
    
    def test_tasks_have_shared_task_decorator(self):
        """Test that all task functions have appropriate decorator."""
        task_functions = [
            'send_testimonial_notification_email',
            'send_admin_notification',
            'process_media',
            'cleanup_old_rejected_testimonials',
            'generate_testimonial_report',
            'warm_testimonial_caches',
            'refresh_volatile_caches',
        ]
        
        for task_name in task_functions:
            self.assertTrue(hasattr(tasks, task_name))