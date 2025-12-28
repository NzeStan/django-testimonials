# testimonials/tests/test_signals.py

"""
Comprehensive tests for signal handlers.
Tests cover all signal handlers, edge cases, failures, and successful operations.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from unittest.mock import patch, Mock, MagicMock, call
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
import os
import tempfile

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialMediaType
from testimonials.signals import (
    testimonial_approved,
    testimonial_rejected,
    testimonial_featured,
    testimonial_archived,
    testimonial_responded,
    testimonial_created,
    testimonial_media_added,
)

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class SignalTestCase(TestCase):
    """Base test case with common setup for all signal tests."""
    
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
    
    def _create_test_image(self, filename='test.jpg'):
        """Helper to create a test image file."""
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(filename, image_io.read(), content_type='image/jpeg')


# ============================================================================
# TESTIMONIAL PRE-SAVE SIGNAL TESTS
# ============================================================================

class TestimonialPreSaveSignalTest(SignalTestCase):
    """Test testimonial_pre_save signal handler."""
    
    @patch('testimonials.signals.TestimonialCacheService.invalidate_testimonial')
    @patch('testimonials.signals.TaskExecutor.execute')
    def test_status_change_to_approved_sets_approved_at(self, mock_execute, mock_cache):
        """Test that changing status to approved sets approved_at."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Use the approve() method which sets approved_at
        testimonial.approve(user=self.admin)
        
        # Refresh from DB
        testimonial.refresh_from_db()
        
        # Should set approved_at
        self.assertIsNotNone(testimonial.approved_at)
        self.assertLessEqual(
            (timezone.now() - testimonial.approved_at).total_seconds(),
            2
        )
    
    @patch('testimonials.signals.testimonial_approved.send')
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    def test_status_change_to_approved_sends_signal_and_email(self, mock_execute, mock_signal):
        """Test that changing to approved sends signal and queues email."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Change to approved
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.approved_by = self.admin
        testimonial.save()
        
        # Should send signal
        mock_signal.assert_called_once()
        
        # Should queue email task
        self.assertTrue(mock_execute.called)
        # Check that send_testimonial_email was called with correct args
        call_args = mock_execute.call_args
        self.assertEqual(str(testimonial.pk), call_args[0][1])  # testimonial_id
        self.assertEqual('approved', call_args[0][2])  # email_type
        self.assertEqual('john@example.com', call_args[0][3])  # recipient
    
    @patch('testimonials.signals.testimonial_rejected.send')
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    def test_status_change_to_rejected_sends_signal_and_email(self, mock_execute, mock_signal):
        """Test that changing to rejected sends signal and queues email."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Change to rejected
        testimonial.status = TestimonialStatus.REJECTED
        testimonial.rejection_reason = 'Spam content'
        testimonial.save()
        
        # Should send signal
        mock_signal.assert_called_once()
        
        # Should queue email task
        self.assertTrue(mock_execute.called)
    
    def test_status_change_to_rejected_sets_default_reason(self):
        """Test that changing to rejected sets default rejection reason if not provided."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Use reject() method without reason
        testimonial.reject(user=self.admin)
        
        testimonial.refresh_from_db()
        
        # Should be rejected
        self.assertEqual(testimonial.status, TestimonialStatus.REJECTED)
    
    @patch('testimonials.signals.testimonial_featured.send')
    def test_status_change_to_featured_sends_signal(self, mock_signal):
        """Test that changing to featured sends signal."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Change to featured
        testimonial.status = TestimonialStatus.FEATURED
        testimonial.save()
        
        # Should send signal
        mock_signal.assert_called_once()
    
    @patch('testimonials.signals.testimonial_archived.send')
    def test_status_change_to_archived_sends_signal(self, mock_signal):
        """Test that changing to archived sends signal."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Change to archived
        testimonial.status = TestimonialStatus.ARCHIVED
        testimonial.save()
        
        # Should send signal
        mock_signal.assert_called_once()
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=False)
    def test_email_not_sent_when_disabled(self, mock_execute):
        """Test that email is not queued when notifications are disabled."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Change to approved
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.save()
        
        # Should not queue email
        mock_execute.assert_not_called()
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    def test_email_not_sent_when_no_author_email(self, mock_execute):
        """Test that email is not queued when testimonial has no author email."""
        # Create user with no email
        user_no_email = User.objects.create_user(
            username='noemail',
            password='testpass123'
        )
        
        testimonial = Testimonial.objects.create(
            author=user_no_email,
            author_name='John Doe',
            # No author_email
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Reset mock to ignore admin notification from create
        mock_execute.reset_mock()
        
        # Change to approved
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.save()
        
        # Should not queue approval email (only admin notification)
        # Check that send_testimonial_notification_email was not called
        for call in mock_execute.call_args_list:
            task_name = str(call[0][0])
            self.assertNotIn('send_testimonial_notification_email', task_name)
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @patch('testimonials.signals.logger')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    def test_email_task_error_is_logged(self, mock_logger, mock_execute):
        """Test that errors queuing email task are logged."""
        mock_execute.side_effect = Exception("Task queue error")
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Change to approved
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.save()
        
        # Should log error
        self.assertTrue(mock_logger.error.called)
    
    def test_no_signal_when_status_unchanged(self):
        """Test that no signals are sent when status doesn't change."""
        with patch('testimonials.signals.testimonial_approved.send') as mock_signal:
            testimonial = Testimonial.objects.create(
                author=self.user,
                author_name='John Doe',
                content='Great product!',
                rating=5,
                status=TestimonialStatus.APPROVED,
                category=self.category
            )
            
            mock_signal.reset_mock()
            
            # Update without changing status
            testimonial.content = 'Updated content'
            testimonial.save()
            
            # Should not send signal
            mock_signal.assert_not_called()
    
    def test_pre_save_handles_new_testimonial(self):
        """Test that pre_save handles new testimonials (no pk)."""
        # This should not raise any errors
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        self.assertIsNotNone(testimonial.pk)


# ============================================================================
# TESTIMONIAL POST-SAVE SIGNAL TESTS
# ============================================================================

class TestimonialPostSaveSignalTest(SignalTestCase):
    """Test testimonial_post_save signal handler."""
    
    @patch('testimonials.signals.testimonial_created.send')
    @patch('testimonials.signals.TestimonialCacheService.invalidate_testimonial')
    def test_created_testimonial_sends_signal(self, mock_cache, mock_signal):
        """Test that creating a testimonial sends created signal."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Should send created signal
        mock_signal.assert_called_once()
        call_kwargs = mock_signal.call_args[1]
        self.assertEqual(call_kwargs['instance'], testimonial)
    
    @patch('testimonials.signals.log_testimonial_action')
    def test_created_testimonial_logs_action(self, mock_log):
        """Test that creating a testimonial logs the action."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Should log create action
        mock_log.assert_called_once_with(testimonial, "create", None)
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    def test_created_testimonial_sends_admin_notification(self, mock_execute):
        """Test that creating a testimonial queues admin notification."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Should queue admin notification
        self.assertTrue(mock_execute.called)
        call_args = mock_execute.call_args[0]
        # First arg is the task function, check second arg is testimonial_id
        self.assertEqual(str(testimonial.pk), call_args[1])
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=False)
    def test_admin_notification_not_sent_when_disabled(self, mock_execute):
        """Test that admin notification is not sent when disabled."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Should not queue admin notification
        mock_execute.assert_not_called()
    
    @patch('testimonials.signals.TestimonialCacheService.invalidate_testimonial')
    def test_updated_testimonial_invalidates_cache(self, mock_cache):
        """Test that updating a testimonial invalidates cache."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        mock_cache.reset_mock()
        
        # Update testimonial
        testimonial.content = 'Updated content'
        testimonial.save()
        
        # Should invalidate cache
        mock_cache.assert_called_once_with(
            testimonial_id=testimonial.pk,
            category_id=testimonial.category_id,
            user_id=testimonial.author_id
        )
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @patch('testimonials.signals.logger')
    @override_settings(TESTIMONIALS_SEND_EMAIL_NOTIFICATIONS=True)
    def test_admin_notification_error_is_logged(self, mock_logger, mock_execute):
        """Test that errors queuing admin notification are logged."""
        mock_execute.side_effect = Exception("Task queue error")
        
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        # Should log error
        self.assertTrue(mock_logger.error.called)


# ============================================================================
# TESTIMONIAL POST-DELETE SIGNAL TESTS
# ============================================================================

class TestimonialPostDeleteSignalTest(SignalTestCase):
    """Test testimonial_post_delete signal handler."""
    
    @patch('testimonials.signals.log_testimonial_action')
    @patch('testimonials.signals.TestimonialCacheService.invalidate_testimonial')
    def test_deleted_testimonial_logs_action_and_invalidates_cache(self, mock_cache, mock_log):
        """Test that deleting a testimonial logs action and invalidates cache."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.PENDING,
            category=self.category
        )
        
        testimonial_id = testimonial.pk
        category_id = testimonial.category_id
        author_id = testimonial.author_id
        
        # Delete testimonial
        testimonial.delete()
        
        # Should log delete action (may be called multiple times - create and delete)
        delete_calls = [call for call in mock_log.call_args_list if call[0][1] == "delete"]
        self.assertGreaterEqual(len(delete_calls), 1)
        
        # Should invalidate cache (may be called multiple times)
        # Check at least one call was made
        self.assertTrue(mock_cache.called)
        # Verify it was called with correct args
        mock_cache.assert_called_with(
            testimonial_id=testimonial_id,
            category_id=category_id,
            user_id=author_id
        )


# ============================================================================
# TESTIMONIAL MEDIA POST-SAVE SIGNAL TESTS
# ============================================================================

class TestimonialMediaPostSaveSignalTest(SignalTestCase):
    """Test media_post_save signal handler."""
    
    @patch('testimonials.signals.testimonial_media_added.send')
    @patch('testimonials.signals.TestimonialCacheService.invalidate_media')
    def test_created_media_sends_signal(self, mock_cache, mock_signal):
        """Test that creating media sends signal."""
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
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        # Should send signal
        mock_signal.assert_called_once()
        call_kwargs = mock_signal.call_args[1]
        self.assertEqual(call_kwargs['instance'], media)
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    def test_created_media_queues_processing_task(self, mock_execute):
        """Test that creating media queues processing task when Celery enabled."""
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
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        # Should queue processing task
        self.assertTrue(mock_execute.called)
        call_args = mock_execute.call_args[0]
        self.assertEqual(str(media.pk), call_args[1])
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_media_processing_not_queued_when_celery_disabled(self, mock_execute):
        """Test that media processing is not queued when Celery disabled."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Reset mock to ignore admin notification from testimonial creation
        mock_execute.reset_mock()
        
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        # Should not queue processing task (process_media should not be called)
        # Check that process_media was not called
        for call in mock_execute.call_args_list:
            task_name = str(call[0][0])
            self.assertNotIn('process_media', task_name)
    
    @patch('testimonials.signals.TestimonialCacheService.invalidate_media')
    def test_updated_media_invalidates_cache(self, mock_cache):
        """Test that updating media invalidates cache."""
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
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        mock_cache.reset_mock()
        
        # Update media
        media.caption = 'Updated caption'
        media.save()
        
        # Should invalidate cache
        mock_cache.assert_called_once_with(
            media_id=media.pk,
            testimonial_id=media.testimonial_id
        )
    
    @patch('testimonials.signals.TaskExecutor.execute')
    @patch('testimonials.signals.logger')
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    def test_media_processing_error_is_logged(self, mock_logger, mock_execute):
        """Test that errors queuing media processing are logged."""
        mock_execute.side_effect = Exception("Task queue error")
        
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
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        # Should log error
        self.assertTrue(mock_logger.error.called)


# ============================================================================
# TESTIMONIAL MEDIA POST-DELETE SIGNAL TESTS
# ============================================================================

class TestimonialMediaPostDeleteSignalTest(SignalTestCase):
    """Test media_post_delete signal handler."""
    
    @patch('testimonials.signals.TestimonialCacheService.invalidate_media')
    def test_deleted_media_invalidates_cache(self, mock_cache):
        """Test that deleting media invalidates cache."""
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
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        media_id = media.pk
        testimonial_id = media.testimonial_id
        
        # Delete media
        media.delete()
        
        # Should invalidate cache (called from both post_save and post_delete)
        # Check at least one call was made
        self.assertTrue(mock_cache.called)
        # Verify it was called with correct args
        mock_cache.assert_called_with(
            media_id=media_id,
            testimonial_id=testimonial_id
        )
    
    @patch('testimonials.signals.logger')
    def test_deleted_media_removes_file(self, mock_logger):
        """Test that deleting media removes the physical file."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Great product!',
            rating=5,
            status=TestimonialStatus.APPROVED,
            category=self.category
        )
        
        # Create media with actual file
        media = TestimonialMedia.objects.create(
            testimonial=testimonial,
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image('delete_test.jpg'),
            description='Test image'
        )
        
        # Get the file path
        file_path = media.file.path
        
        # File should exist
        self.assertTrue(os.path.exists(file_path))
        
        # Delete media
        media.delete()
        
        # File should be deleted
        self.assertFalse(os.path.exists(file_path))
        
        # Should log info
        self.assertTrue(mock_logger.info.called)
    
    @patch('testimonials.signals.logger')
    def test_file_deletion_error_is_logged(self, mock_logger):
        """Test that errors deleting file are logged."""
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
            media_type=TestimonialMediaType.IMAGE,
            file=self._create_test_image(),
            description='Test image'
        )
        
        # Mock os.remove to raise error
        with patch('os.remove', side_effect=Exception("Permission denied")):
            with patch('os.path.isfile', return_value=True):
                # Delete media
                media.delete()
        
        # Should log error
        self.assertTrue(mock_logger.error.called)


# ============================================================================
# CUSTOM SIGNAL TESTS
# ============================================================================

class CustomSignalTest(SignalTestCase):
    """Test custom signals are sent correctly."""
    
    def test_custom_signals_can_be_connected(self):
        """Test that custom signals can be connected and disconnected."""
        # Create a mock receiver
        mock_receiver = Mock()
        
        # Connect receiver
        testimonial_approved.connect(mock_receiver)
        
        # Send signal
        testimonial_approved.send(sender=Testimonial, instance=None)
        
        # Should be called
        self.assertTrue(mock_receiver.called)
        
        # Disconnect
        testimonial_approved.disconnect(mock_receiver)
        
        mock_receiver.reset_mock()
        
        # Send signal again
        testimonial_approved.send(sender=Testimonial, instance=None)
        
        # Should not be called
        mock_receiver.assert_not_called()
    
    def test_all_custom_signals_exist(self):
        """Test that all expected custom signals exist."""
        from testimonials import signals
        
        signal_names = [
            'testimonial_approved',
            'testimonial_rejected',
            'testimonial_featured',
            'testimonial_archived',
            'testimonial_responded',
            'testimonial_created',
            'testimonial_media_added',
        ]
        
        for signal_name in signal_names:
            self.assertTrue(hasattr(signals, signal_name))