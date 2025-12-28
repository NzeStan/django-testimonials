# testimonials/tests/test_utils.py

"""
Comprehensive tests for utility functions.
Tests cover file utilities, slug generation, search utilities, cache utilities,
task utilities, thumbnail generation, batch processing, and edge cases.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from io import BytesIO
from PIL import Image
import os
import tempfile

from testimonials.models import Testimonial, TestimonialCategory
from testimonials.constants import TestimonialStatus, TestimonialMediaType
from testimonials import utils

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class UtilsTestCase(TestCase):
    """Base test case for utils tests."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = TestimonialCategory.objects.create(
            name='Products',
            slug='products'
        )
        
        self.testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Test User',
            content='Test content',
            rating=5,
            category=self.category
        )
    
    def _create_test_image(self, filename='test.jpg'):
        """Helper to create test image file."""
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(filename, image_io.read(), content_type='image/jpeg')


# ============================================================================
# FILE UTILITIES TESTS
# ============================================================================

class GenerateUploadPathTest(UtilsTestCase):
    """Tests for generate_upload_path function."""
    
    def test_basic_path_generation(self):
        """Test basic upload path generation."""
        instance = Mock()
        filename = 'test-image.jpg'
        
        path = utils.generate_upload_path(instance, filename)
        
        # Should contain testimonials/media
        self.assertIn('testimonials/media', path)
        # Should contain year and month
        now = datetime.now()
        self.assertIn(str(now.year), path)
        self.assertIn(now.strftime('%m'), path)
        # Should have .jpg extension
        self.assertTrue(path.endswith('.jpg'))
    
    def test_path_with_spaces_in_filename(self):
        """Test path generation with spaces in filename."""
        instance = Mock()
        filename = 'my test image.jpg'
        
        path = utils.generate_upload_path(instance, filename)
        
        # Should slugify the filename
        self.assertIn('my-test-image', path)
        # Should not have spaces
        self.assertNotIn(' ', path)
    
    def test_path_with_special_characters(self):
        """Test path generation with special characters."""
        instance = Mock()
        filename = 'Tëst_Îmågé!@#$.jpg'
        
        path = utils.generate_upload_path(instance, filename)
        
        # Should handle special characters
        self.assertIn('testimonials/media', path)
        # Should still have extension
        self.assertTrue(path.endswith('.jpg'))
    
    def test_path_with_long_filename(self):
        """Test path generation with very long filename."""
        instance = Mock()
        filename = 'a' * 200 + '.jpg'
        
        path = utils.generate_upload_path(instance, filename)
        
        # Should truncate to max_length (50)
        name_part = path.split('/')[-1].split('_')[0]
        self.assertLessEqual(len(name_part), 50)
    
    def test_path_without_extension(self):
        """Test path generation without file extension."""
        instance = Mock()
        filename = 'noextension'
        
        path = utils.generate_upload_path(instance, filename)
        
        # Should default to 'file' extension
        self.assertTrue(path.endswith('.file'))
    
    def test_path_includes_timestamp(self):
        """Test path includes timestamp to avoid collisions."""
        instance = Mock()
        filename = 'test.jpg'
        
        path1 = utils.generate_upload_path(instance, filename)
        path2 = utils.generate_upload_path(instance, filename)
        
        # Different timestamps, so different paths
        # (May be same if called in same second, but unlikely)
        # Check that path contains timestamp format
        self.assertRegex(path1, r'\d{8}_\d{6}')
    
    def test_path_with_multiple_dots(self):
        """Test path with multiple dots in filename."""
        instance = Mock()
        filename = 'my.test.image.jpg'
        
        path = utils.generate_upload_path(instance, filename)
        
        # Should use last extension
        self.assertTrue(path.endswith('.jpg'))


class GetFileTypeTest(UtilsTestCase):
    """Tests for get_file_type function."""
    
    def test_image_jpg(self):
        """Test JPG image detection."""
        file_obj = Mock()
        file_obj.name = 'test.jpg'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.IMAGE)
    
    def test_image_png(self):
        """Test PNG image detection."""
        file_obj = Mock()
        file_obj.name = 'test.png'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.IMAGE)
    
    def test_image_gif(self):
        """Test GIF image detection."""
        file_obj = Mock()
        file_obj.name = 'animated.gif'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.IMAGE)
    
    def test_image_webp(self):
        """Test WebP image detection."""
        file_obj = Mock()
        file_obj.name = 'modern.webp'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.IMAGE)
    
    def test_video_mp4(self):
        """Test MP4 video detection."""
        file_obj = Mock()
        file_obj.name = 'video.mp4'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.VIDEO)
    
    def test_video_webm(self):
        """Test WebM video detection."""
        file_obj = Mock()
        file_obj.name = 'video.webm'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.VIDEO)
    
    def test_audio_mp3(self):
        """Test MP3 audio detection."""
        file_obj = Mock()
        file_obj.name = 'audio.mp3'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.AUDIO)
    
    def test_audio_wav(self):
        """Test WAV audio detection."""
        file_obj = Mock()
        file_obj.name = 'sound.wav'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.AUDIO)
    
    def test_document_pdf(self):
        """Test PDF document detection."""
        file_obj = Mock()
        file_obj.name = 'document.pdf'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.DOCUMENT)
    
    def test_document_default(self):
        """Test unknown extension defaults to document."""
        file_obj = Mock()
        file_obj.name = 'file.xyz'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.DOCUMENT)
    
    def test_case_insensitive_detection(self):
        """Test file type detection is case insensitive."""
        file_obj = Mock()
        file_obj.name = 'TEST.JPG'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.IMAGE)
    
    def test_none_file_object(self):
        """Test None file object."""
        result = utils.get_file_type(None)
        self.assertEqual(result, TestimonialMediaType.DOCUMENT)
    
    def test_file_without_name_attribute(self):
        """Test file object without name attribute."""
        file_obj = Mock(spec=[])  # No attributes
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.DOCUMENT)
    
    def test_file_without_extension(self):
        """Test file without extension."""
        file_obj = Mock()
        file_obj.name = 'noextension'
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.DOCUMENT)
    
    def test_all_image_extensions(self):
        """Test all supported image extensions."""
        image_exts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp']
        
        for ext in image_exts:
            file_obj = Mock()
            file_obj.name = f'image.{ext}'
            result = utils.get_file_type(file_obj)
            self.assertEqual(result, TestimonialMediaType.IMAGE, f'{ext} should be IMAGE')
    
    def test_all_video_extensions(self):
        """Test all supported video extensions."""
        video_exts = ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv']
        
        for ext in video_exts:
            file_obj = Mock()
            file_obj.name = f'video.{ext}'
            result = utils.get_file_type(file_obj)
            self.assertEqual(result, TestimonialMediaType.VIDEO, f'{ext} should be VIDEO')
    
    def test_all_audio_extensions(self):
        """Test all supported audio extensions."""
        audio_exts = ['mp3', 'wav', 'ogg', 'aac', 'm4a', 'flac']
        
        for ext in audio_exts:
            file_obj = Mock()
            file_obj.name = f'audio.{ext}'
            result = utils.get_file_type(file_obj)
            self.assertEqual(result, TestimonialMediaType.AUDIO, f'{ext} should be AUDIO')


# ============================================================================
# SLUG UTILITIES TESTS
# ============================================================================

class GetUniqueSlugTest(UtilsTestCase):
    """Tests for get_unique_slug function."""
    
    def test_basic_unique_slug(self):
        """Test basic unique slug generation."""
        category = TestimonialCategory(name='Test Category')
        category.slug = 'test-category'
        
        slug = utils.get_unique_slug(category, 'name')
        
        # Should generate slug from name
        self.assertEqual(slug, 'test-category')
    
    def test_duplicate_slug_gets_suffix(self):
        """Test duplicate slug gets numeric suffix."""
        # Create existing category
        TestimonialCategory.objects.create(name='Existing', slug='existing')
        
        # Try to create another with same slug
        category = TestimonialCategory(name='Existing')
        category.slug = 'existing'
        category.pk = None  # New instance
        
        slug = utils.get_unique_slug(category, 'name')
        
        # Should have -1 suffix
        self.assertEqual(slug, 'existing-1')
    
    def test_multiple_duplicates(self):
        """Test handling multiple duplicate slugs."""
        # Create existing categories
        TestimonialCategory.objects.create(name='Test', slug='test')
        TestimonialCategory.objects.create(name='Test', slug='test-1')
        TestimonialCategory.objects.create(name='Test', slug='test-2')
        
        # Create new one
        category = TestimonialCategory(name='Test')
        category.slug = 'test'
        category.pk = None
        
        slug = utils.get_unique_slug(category, 'name')
        
        # Should be test-3
        self.assertEqual(slug, 'test-3')
    
    def test_max_length_truncation(self):
        """Test slug is truncated to max_length."""
        long_name = 'a' * 100
        category = TestimonialCategory(name=long_name)
        category.slug = 'a' * 100
        
        slug = utils.get_unique_slug(category, 'name', max_length=50)
        
        # Should be truncated
        self.assertEqual(len(slug), 50)
    
    def test_max_length_with_suffix(self):
        """Test max_length accounts for suffix."""
        # Create existing
        TestimonialCategory.objects.create(
            name='a' * 50,
            slug='a' * 50
        )
        
        category = TestimonialCategory(name='a' * 50)
        category.slug = 'a' * 50
        category.pk = None
        
        slug = utils.get_unique_slug(category, 'name', max_length=50)
        
        # Should fit within max_length including suffix
        self.assertLessEqual(len(slug), 50)
        # Should have suffix
        self.assertTrue(slug.endswith('-1'))
    
    def test_updating_existing_instance(self):
        """Test updating existing instance doesn't cause duplicate."""
        category = TestimonialCategory.objects.create(
            name='Original',
            slug='original'
        )
        
        # Update the same instance
        category.name = 'Updated'
        slug = utils.get_unique_slug(category, 'name')
        
        # Should return 'updated' without suffix since it's the same object
        self.assertEqual(slug, 'updated')


# ============================================================================
# SEARCH UTILITIES TESTS
# ============================================================================

class GetSearchQueryTest(UtilsTestCase):
    """Tests for get_search_query function."""
    
    @override_settings(TESTIMONIALS_SEARCH_MIN_LENGTH=3)
    def test_valid_search_query(self):
        """Test valid search query is returned."""
        query = 'test search'
        result = utils.get_search_query(query)
        self.assertEqual(result, 'test search')
    
    def test_query_is_trimmed(self):
        """Test search query is trimmed."""
        query = '  test search  '
        result = utils.get_search_query(query)
        self.assertEqual(result, 'test search')
    
    @override_settings(TESTIMONIALS_SEARCH_MIN_LENGTH=3)
    def test_too_short_query_returns_none(self):
        """Test too short query returns None."""
        query = 'ab'  # Less than min length of 3
        result = utils.get_search_query(query)
        self.assertIsNone(result)
    
    def test_empty_query_returns_none(self):
        """Test empty query returns None."""
        result = utils.get_search_query('')
        self.assertIsNone(result)
    
    def test_none_query_returns_none(self):
        """Test None query returns None."""
        result = utils.get_search_query(None)
        self.assertIsNone(result)
    
    def test_whitespace_only_query_returns_none(self):
        """Test whitespace-only query returns None."""
        result = utils.get_search_query('   ')
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_SEARCH_MIN_LENGTH=3)
    def test_exact_min_length_is_valid(self):
        """Test query at exact min length is valid."""
        query = 'abc'  # Exactly 3 characters
        result = utils.get_search_query(query)
        self.assertEqual(result, 'abc')
    
    @override_settings(TESTIMONIALS_SEARCH_MIN_LENGTH=1)
    def test_single_character_valid_with_min_1(self):
        """Test single character is valid when min is 1."""
        query = 'a'
        result = utils.get_search_query(query)
        self.assertEqual(result, 'a')


# ============================================================================
# LOGGING UTILITIES TESTS
# ============================================================================

class LogTestimonialActionTest(UtilsTestCase):
    """Tests for log_testimonial_action function."""
    
    @patch('testimonials.utils.logger')
    def test_log_with_user(self, mock_logger):
        """Test logging with authenticated user."""
        utils.log_testimonial_action(
            self.testimonial,
            'approve',
            user=self.user
        )
        
        # Should call logger.info
        mock_logger.info.assert_called_once()
        # Check log message contains action and user
        call_args = mock_logger.info.call_args[0][0]
        self.assertIn('approve', call_args)
        self.assertIn(self.user.username, call_args)
    
    @patch('testimonials.utils.logger')
    def test_log_without_user(self, mock_logger):
        """Test logging without user (system action)."""
        utils.log_testimonial_action(
            self.testimonial,
            'auto_approve'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        self.assertIn('System', call_args)
    
    @patch('testimonials.utils.logger')
    def test_log_with_notes(self, mock_logger):
        """Test logging with notes."""
        utils.log_testimonial_action(
            self.testimonial,
            'reject',
            user=self.user,
            notes='Does not meet quality standards'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        self.assertIn('Does not meet quality standards', call_args)
    
    @patch('testimonials.utils.logger')
    def test_log_with_extra_data(self, mock_logger):
        """Test logging with extra structured data."""
        extra_data = {'category': 'products', 'rating': 5}
        
        utils.log_testimonial_action(
            self.testimonial,
            'create',
            user=self.user,
            extra_data=extra_data
        )
        
        # Check extra data was passed
        call_kwargs = mock_logger.info.call_args[1]
        self.assertIn('extra', call_kwargs)
        self.assertIn('category', call_kwargs['extra'])
    
    @patch('testimonials.utils.logger')
    def test_log_includes_timestamp(self, mock_logger):
        """Test log includes timestamp."""
        utils.log_testimonial_action(
            self.testimonial,
            'test_action',
            user=self.user
        )
        
        call_kwargs = mock_logger.info.call_args[1]
        self.assertIn('timestamp', call_kwargs['extra'])


# ============================================================================
# CACHE UTILITIES TESTS (BACKWARD COMPATIBLE)
# ============================================================================

class CacheUtilitiesTest(UtilsTestCase):
    """Tests for backward-compatible cache utility functions."""
    
    @patch('testimonials.utils.TestimonialCacheService.get_key')
    def test_get_cache_key_single_arg(self, mock_get_key):
        """Test get_cache_key with single argument."""
        mock_get_key.return_value = 'testimonials:testimonial:123'
        
        result = utils.get_cache_key('testimonial', 123)
        
        mock_get_key.assert_called_once_with('TESTIMONIAL', id=123)
        self.assertEqual(result, 'testimonials:testimonial:123')
    
    @patch('testimonials.utils.TestimonialCacheService.get_key')
    def test_get_cache_key_no_args(self, mock_get_key):
        """Test get_cache_key without arguments."""
        mock_get_key.return_value = 'testimonials:stats'
        
        result = utils.get_cache_key('stats')
        
        mock_get_key.assert_called_once_with('STATS')
    
    def test_get_cache_key_multiple_args_fallback(self):
        """Test get_cache_key with multiple args uses fallback."""
        result = utils.get_cache_key('custom', 'arg1', 'arg2')
        
        # Should create key with colon separation
        self.assertIn('custom', result)
        self.assertIn('arg1', result)
        self.assertIn('arg2', result)
    
    @patch('testimonials.utils.TestimonialCacheService.get_or_set')
    def test_cache_get_or_set_delegates(self, mock_get_or_set):
        """Test cache_get_or_set delegates to service."""
        def compute():
            return 'value'
        
        mock_get_or_set.return_value = 'value'
        
        result = utils.cache_get_or_set('key', compute, timeout=3600)
        
        mock_get_or_set.assert_called_once_with('key', compute, 3600)
        self.assertEqual(result, 'value')
    
    @patch('testimonials.utils.TestimonialCacheService.invalidate_testimonial')
    def test_invalidate_testimonial_cache_delegates(self, mock_invalidate):
        """Test invalidate_testimonial_cache delegates to service."""
        utils.invalidate_testimonial_cache(
            testimonial_id=1,
            category_id=2,
            user_id=3
        )
        
        mock_invalidate.assert_called_once_with(
            testimonial_id=1,
            category_id=2,
            user_id=3
        )


# ============================================================================
# TASK UTILITIES TESTS (BACKWARD COMPATIBLE)
# ============================================================================

class TaskUtilitiesTest(UtilsTestCase):
    """Tests for backward-compatible task utility functions."""
    
    @patch('testimonials.utils.TaskExecutor.execute')
    def test_execute_task_delegates(self, mock_execute):
        """Test execute_task delegates to TaskExecutor."""
        def my_task():
            return 'result'
        
        mock_execute.return_value = 'result'
        
        result = utils.execute_task(my_task, 'arg1', kwarg1='value1')
        
        mock_execute.assert_called_once_with(my_task, 'arg1', kwarg1='value1')
        self.assertEqual(result, 'result')


# ============================================================================
# THUMBNAIL UTILITIES TESTS
# ============================================================================

class GenerateThumbnailsTest(UtilsTestCase):
    """Tests for generate_thumbnails function."""
    
    @override_settings(TESTIMONIALS_ENABLE_THUMBNAILS=False)
    def test_thumbnails_disabled_returns_empty(self):
        """Test that thumbnails disabled returns empty dict."""
        result = utils.generate_thumbnails('/fake/path.jpg')
        self.assertEqual(result, {})
    
    @override_settings(
        TESTIMONIALS_ENABLE_THUMBNAILS=True,
        TESTIMONIALS_THUMBNAIL_SIZES={'small': (100, 100), 'medium': (300, 300)}
    )
    @patch('PIL.Image')
    def test_thumbnails_generation_success(self, mock_image_class):
        """Test successful thumbnail generation."""
        # Mock Image operations
        mock_img = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_img.copy.return_value = mock_img
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
        
        try:
            result = utils.generate_thumbnails(temp_path)
            
            # Should have generated thumbnails for each size
            self.assertIn('small', result)
            self.assertIn('medium', result)
            
            # Should have called thumbnail method
            self.assertTrue(mock_img.thumbnail.called)
            # Should have called save
            self.assertTrue(mock_img.save.called)
        
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    @override_settings(TESTIMONIALS_ENABLE_THUMBNAILS=True)
    @patch('PIL.Image.open')
    def test_thumbnails_handle_error(self, mock_open):
        """Test thumbnail generation handles errors."""
        mock_open.side_effect = Exception("Cannot open image")
        
        result = utils.generate_thumbnails('/fake/path.jpg')
        
        # Should return empty dict on error
        self.assertEqual(result, {})
    
    @override_settings(TESTIMONIALS_ENABLE_THUMBNAILS=True)
    @patch('testimonials.utils.logger')
    @patch('PIL.Image.open')
    def test_thumbnails_logs_error(self, mock_open, mock_logger):
        """Test thumbnail generation logs errors."""
        mock_open.side_effect = Exception("Cannot open image")
        
        utils.generate_thumbnails('/fake/path.jpg')
        
        # Should log error
        mock_logger.error.assert_called_once()


# ============================================================================
# BATCH PROCESSING TESTS
# ============================================================================

class BatchProcessTest(UtilsTestCase):
    """Tests for batch_process function."""
    
    @override_settings(TESTIMONIALS_BULK_OPERATION_BATCH_SIZE=5)
    def test_basic_batch_processing(self):
        """Test basic batch processing."""
        # Clear existing testimonials first
        Testimonial.objects.all().delete()
        
        # Create exactly 10 testimonials
        for i in range(10):
            Testimonial.objects.create(
                author=self.user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5
            )
        
        queryset = Testimonial.objects.all()
        batches = list(utils.batch_process(queryset, batch_size=3))
        
        # Should create 4 batches: 3, 3, 3, 1
        self.assertEqual(len(batches), 4)
        self.assertEqual(len(batches[0]), 3)
        self.assertEqual(len(batches[3]), 1)
    
    def test_batch_processing_with_callback(self):
        """Test batch processing with callback."""
        # Clear existing testimonials first
        Testimonial.objects.all().delete()
        
        # Create exactly 5 testimonials
        for i in range(5):
            Testimonial.objects.create(
                author=self.user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5
            )
        
        processed = []
        
        def callback(batch):
            processed.extend(batch)
        
        queryset = Testimonial.objects.all()
        list(utils.batch_process(queryset, batch_size=2, callback=callback))
        
        # Should have processed all items
        self.assertEqual(len(processed), 5)
    
    def test_batch_processing_empty_queryset(self):
        """Test batch processing with empty queryset."""
        queryset = Testimonial.objects.none()
        batches = list(utils.batch_process(queryset, batch_size=5))
        
        # Should return empty list
        self.assertEqual(len(batches), 0)
    
    @override_settings(TESTIMONIALS_BULK_OPERATION_BATCH_SIZE=10)
    def test_batch_processing_uses_default_size(self):
        """Test batch processing uses default size from settings."""
        # Clear existing testimonials first
        Testimonial.objects.all().delete()
        
        # Create exactly 15 testimonials
        for i in range(15):
            Testimonial.objects.create(
                author=self.user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5
            )
        
        queryset = Testimonial.objects.all()
        batches = list(utils.batch_process(queryset))  # No batch_size specified
        
        # Should use default size of 10, creating 2 batches
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 10)
        self.assertEqual(len(batches[1]), 5)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class UtilsEdgeCaseTests(UtilsTestCase):
    """Tests for edge cases in utility functions."""
    
    def test_generate_upload_path_with_empty_filename(self):
        """Test upload path with empty filename."""
        instance = Mock()
        path = utils.generate_upload_path(instance, '')
        
        # Should still generate path
        self.assertIn('testimonials/media', path)
    
    def test_get_file_type_with_empty_name(self):
        """Test file type with empty name."""
        file_obj = Mock()
        file_obj.name = ''
        
        result = utils.get_file_type(file_obj)
        self.assertEqual(result, TestimonialMediaType.DOCUMENT)
    
    def test_get_unique_slug_with_empty_name(self):
        """Test unique slug with empty name."""
        category = TestimonialCategory(name='')
        category.slug = ''
        
        # Should handle gracefully
        slug = utils.get_unique_slug(category, 'name')
        self.assertIsInstance(slug, str)
    
    def test_log_testimonial_action_with_unicode(self):
        """Test logging with unicode characters."""
        self.testimonial.author_name = 'Tëst Üser 你好'
        self.testimonial.save()
        
        # Should not crash
        with patch('testimonials.utils.logger'):
            utils.log_testimonial_action(
                self.testimonial,
                'test',
                notes='Üñíçödé nötés'
            )
    
    def test_get_cache_key_with_none_args(self):
        """Test get_cache_key with None in args."""
        result = utils.get_cache_key('custom', None, 'test')
        
        # Should handle None
        self.assertIsInstance(result, str)
    
    def test_batch_process_with_very_large_batch_size(self):
        """Test batch processing with batch size larger than queryset."""
        # Clear existing testimonials first
        Testimonial.objects.all().delete()
        
        # Create exactly 5 testimonials
        for i in range(5):
            Testimonial.objects.create(
                author=self.user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5
            )
        
        queryset = Testimonial.objects.all()
        batches = list(utils.batch_process(queryset, batch_size=100))
        
        # Should create 1 batch with all items
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 5)
    
    def test_batch_process_with_batch_size_one(self):
        """Test batch processing with batch size of 1."""
        # Clear existing testimonials first
        Testimonial.objects.all().delete()
        
        # Create exactly 3 testimonials
        for i in range(3):
            Testimonial.objects.create(
                author=self.user,
                author_name=f'User {i}',
                content=f'Content {i}',
                rating=5
            )
        
        queryset = Testimonial.objects.all()
        batches = list(utils.batch_process(queryset, batch_size=1))
        
        # Should create 3 batches with 1 item each
        self.assertEqual(len(batches), 3)
        for batch in batches:
            self.assertEqual(len(batch), 1)