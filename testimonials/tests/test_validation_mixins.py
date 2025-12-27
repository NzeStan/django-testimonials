# testimonials/tests/test_validation_mixins.py

"""
Comprehensive tests for validation mixins.
Tests cover all mixin methods, edge cases, and error handling.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers
from unittest.mock import Mock

from testimonials.mixins.validation_mixins import (
    FileValidationMixin,
    AnonymousUserValidationMixin,
    ChoiceFieldDisplayMixin
)
from testimonials.models import Testimonial
from testimonials.constants import TestimonialStatus, TestimonialSource

User = get_user_model()


# ============================================================================
# FILE VALIDATION MIXIN TESTS
# ============================================================================

class FileValidationMixinTests(TestCase):
    """Tests for FileValidationMixin methods."""
    
    def setUp(self):
        """Set up for each test."""
        self.mixin = FileValidationMixin()
    
    # === validate_file_extension tests ===
    
    def test_validate_file_extension_jpg(self):
        """Test validating JPG extension."""
        file_obj = Mock()
        file_obj.name = 'test.jpg'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg', 'png', 'gif']
        )
        
        self.assertEqual(ext, 'jpg')
    
    def test_validate_file_extension_uppercase(self):
        """Test validating uppercase extension."""
        file_obj = Mock()
        file_obj.name = 'test.JPG'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg', 'png']
        )
        
        # Should be normalized to lowercase
        self.assertEqual(ext, 'jpg')
    
    def test_validate_file_extension_with_dots(self):
        """Test filename with multiple dots."""
        file_obj = Mock()
        file_obj.name = 'my.test.file.png'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg', 'png']
        )
        
        self.assertEqual(ext, 'png')
    
    def test_validate_file_extension_not_allowed(self):
        """Test invalid file extension."""
        file_obj = Mock()
        file_obj.name = 'test.exe'
        
        with self.assertRaises(serializers.ValidationError) as cm:
            FileValidationMixin.validate_file_extension(
                file_obj,
                ['jpg', 'png']
            )
        
        self.assertIn('exe', str(cm.exception))
        self.assertIn('not allowed', str(cm.exception).lower())
    
    def test_validate_file_extension_no_extension(self):
        """Test filename without extension."""
        file_obj = Mock()
        file_obj.name = 'testfile'
        
        with self.assertRaises(serializers.ValidationError) as cm:
            FileValidationMixin.validate_file_extension(
                file_obj,
                ['jpg', 'png']
            )
        
        self.assertIn('extension', str(cm.exception).lower())
    
    def test_validate_file_extension_none_file(self):
        """Test with None file object."""
        with self.assertRaises(serializers.ValidationError) as cm:
            FileValidationMixin.validate_file_extension(
                None,
                ['jpg', 'png']
            )
        
        self.assertIn('required', str(cm.exception).lower())
    
    def test_validate_file_extension_case_insensitive(self):
        """Test case-insensitive extension matching."""
        file_obj = Mock()
        file_obj.name = 'test.PNG'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg', 'png']
        )
        
        self.assertEqual(ext, 'png')
    
    def test_validate_file_extension_with_spaces(self):
        """Test extension with spaces."""
        file_obj = Mock()
        file_obj.name = 'test.jpg '  # Trailing space
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg', 'png']
        )
        
        self.assertEqual(ext, 'jpg')
    
    # === validate_file_size tests ===
    
    def test_validate_file_size_valid(self):
        """Test validating file within size limit."""
        file_obj = Mock()
        file_obj.size = 1024 * 1024  # 1 MB
        
        # Should not raise exception
        FileValidationMixin.validate_file_size(
            file_obj,
            max_size=5 * 1024 * 1024  # 5 MB limit
        )
    
    def test_validate_file_size_exactly_at_limit(self):
        """Test file exactly at size limit."""
        file_obj = Mock()
        file_obj.size = 5 * 1024 * 1024  # Exactly 5 MB
        
        # Should not raise exception
        FileValidationMixin.validate_file_size(
            file_obj,
            max_size=5 * 1024 * 1024
        )
    
    def test_validate_file_size_too_large(self):
        """Test file exceeding size limit."""
        file_obj = Mock()
        file_obj.size = 10 * 1024 * 1024  # 10 MB
        
        with self.assertRaises(serializers.ValidationError) as cm:
            FileValidationMixin.validate_file_size(
                file_obj,
                max_size=5 * 1024 * 1024  # 5 MB limit
            )
        
        error_msg = str(cm.exception).lower()
        self.assertIn('large', error_msg)
        self.assertIn('10.0', str(cm.exception))  # Current size
        self.assertIn('5.0', str(cm.exception))  # Max size
    
    def test_validate_file_size_zero_bytes(self):
        """Test zero-byte file."""
        file_obj = Mock()
        file_obj.size = 0
        
        # Should be valid (not too large)
        FileValidationMixin.validate_file_size(
            file_obj,
            max_size=5 * 1024 * 1024
        )
    
    def test_validate_file_size_very_small_limit(self):
        """Test with very small size limit."""
        file_obj = Mock()
        file_obj.size = 1024  # 1 KB
        
        with self.assertRaises(serializers.ValidationError):
            FileValidationMixin.validate_file_size(
                file_obj,
                max_size=512  # 512 bytes limit
            )
    
    # === validate_uploaded_file tests ===
    
    def test_validate_uploaded_file_valid(self):
        """Test complete file validation with valid file."""
        file_obj = Mock()
        file_obj.name = 'test.jpg'
        file_obj.size = 1024 * 1024  # 1 MB
        
        result = self.mixin.validate_uploaded_file(
            file_obj,
            allowed_extensions=['jpg', 'png'],
            max_size=5 * 1024 * 1024
        )
        
        self.assertEqual(result, file_obj)
    
    def test_validate_uploaded_file_invalid_extension(self):
        """Test complete validation with invalid extension."""
        file_obj = Mock()
        file_obj.name = 'test.exe'
        file_obj.size = 1024
        
        with self.assertRaises(serializers.ValidationError):
            self.mixin.validate_uploaded_file(
                file_obj,
                allowed_extensions=['jpg', 'png'],
                max_size=5 * 1024 * 1024
            )
    
    def test_validate_uploaded_file_too_large(self):
        """Test complete validation with oversized file."""
        file_obj = Mock()
        file_obj.name = 'test.jpg'
        file_obj.size = 10 * 1024 * 1024  # 10 MB
        
        with self.assertRaises(serializers.ValidationError):
            self.mixin.validate_uploaded_file(
                file_obj,
                allowed_extensions=['jpg', 'png'],
                max_size=5 * 1024 * 1024  # 5 MB limit
            )
    
    def test_validate_uploaded_file_real_file(self):
        """Test validation with real uploaded file."""
        content = b'fake image content'
        file_obj = SimpleUploadedFile('test.jpg', content)
        
        result = self.mixin.validate_uploaded_file(
            file_obj,
            allowed_extensions=['jpg', 'png', 'gif'],
            max_size=1024 * 1024
        )
        
        self.assertEqual(result, file_obj)


# ============================================================================
# ANONYMOUS USER VALIDATION MIXIN TESTS
# ============================================================================

class AnonymousUserValidationMixinTests(TestCase):
    """Tests for AnonymousUserValidationMixin methods."""
    
    def setUp(self):
        """Set up for each test."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
    
    # === ensure_anonymous_display_name tests ===
    
    def test_ensure_anonymous_display_name_with_name(self):
        """Test with existing author name."""
        data = {'author_name': 'John Doe'}
        
        result = AnonymousUserValidationMixin.ensure_anonymous_display_name(data)
        
        self.assertEqual(result['author_name'], 'John Doe')
    
    def test_ensure_anonymous_display_name_empty_string(self):
        """Test with empty author name."""
        data = {'author_name': ''}
        
        result = AnonymousUserValidationMixin.ensure_anonymous_display_name(data)
        
        self.assertEqual(result['author_name'], 'Anonymous')
    
    def test_ensure_anonymous_display_name_whitespace(self):
        """Test with whitespace-only name."""
        data = {'author_name': '   '}
        
        result = AnonymousUserValidationMixin.ensure_anonymous_display_name(data)
        
        self.assertEqual(result['author_name'], 'Anonymous')
    
    def test_ensure_anonymous_display_name_none(self):
        """Test with None author name."""
        data = {'author_name': None}
        
        result = AnonymousUserValidationMixin.ensure_anonymous_display_name(data)
        
        self.assertEqual(result['author_name'], 'Anonymous')
    
    def test_ensure_anonymous_display_name_missing_key(self):
        """Test with missing author_name key."""
        data = {}
        
        result = AnonymousUserValidationMixin.ensure_anonymous_display_name(data)
        
        self.assertEqual(result['author_name'], 'Anonymous')
    
    # === prefill_author_from_user tests ===
    
    def test_prefill_author_from_user_authenticated(self):
        """Test prefilling from authenticated user."""
        data = {}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, self.user
        )
        
        self.assertEqual(result['author'], self.user)
        self.assertEqual(result['author_name'], 'Test User')
        self.assertEqual(result['author_email'], 'test@example.com')
    
    def test_prefill_author_from_user_no_full_name(self):
        """Test prefilling when user has no full name."""
        user = User.objects.create_user(
            username='noname',
            email='noname@example.com'
        )
        data = {}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, user
        )
        
        self.assertEqual(result['author_name'], 'noname')
    
    def test_prefill_author_from_user_existing_name(self):
        """Test that existing author_name is preserved."""
        data = {'author_name': 'Custom Name'}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, self.user
        )
        
        # Should keep custom name
        self.assertEqual(result['author_name'], 'Custom Name')
    
    def test_prefill_author_from_user_existing_email(self):
        """Test that existing author_email is preserved."""
        data = {'author_email': 'custom@example.com'}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, self.user
        )
        
        # Should keep custom email
        self.assertEqual(result['author_email'], 'custom@example.com')
    
    def test_prefill_author_from_user_none_user(self):
        """Test prefilling with None user."""
        data = {}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, None
        )
        
        # Should not modify data
        self.assertNotIn('author', result)
        self.assertNotIn('author_name', result)
    
    def test_prefill_author_from_user_unauthenticated(self):
        """Test prefilling with unauthenticated user."""
        user = Mock()
        user.is_authenticated = False
        data = {}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, user
        )
        
        # Should not modify data
        self.assertNotIn('author', result)
        self.assertNotIn('author_name', result)
    
    def test_prefill_author_from_user_no_email(self):
        """Test prefilling when user has no email."""
        user = User.objects.create_user(
            username='noemail',
            email=''  # No email
        )
        data = {}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, user
        )
        
        # Should prefill author and name but not email
        self.assertEqual(result['author'], user)
        self.assertIn('author_name', result)
        self.assertNotIn('author_email', result)
    
    def test_prefill_author_from_user_whitespace_name(self):
        """Test prefilling when data has whitespace-only name."""
        data = {'author_name': '  '}
        
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, self.user
        )
        
        # Should replace whitespace with actual name
        self.assertEqual(result['author_name'], 'Test User')
    
    # === validate_anonymous_policy tests ===
    
    def test_validate_anonymous_policy_allowed(self):
        """Test validation when anonymous is allowed."""
        # Should not raise exception
        AnonymousUserValidationMixin.validate_anonymous_policy(
            is_anonymous=True,
            allow_anonymous=True
        )
    
    def test_validate_anonymous_policy_not_anonymous(self):
        """Test validation when not anonymous."""
        # Should not raise exception even if not allowed
        AnonymousUserValidationMixin.validate_anonymous_policy(
            is_anonymous=False,
            allow_anonymous=False
        )
    
    def test_validate_anonymous_policy_not_allowed(self):
        """Test validation when anonymous not allowed."""
        with self.assertRaises(DjangoValidationError) as cm:
            AnonymousUserValidationMixin.validate_anonymous_policy(
                is_anonymous=True,
                allow_anonymous=False
            )
        
        self.assertIn('not allowed', str(cm.exception).lower())
        self.assertEqual(cm.exception.code, 'anonymous_not_allowed')
    
    def test_validate_anonymous_policy_both_false(self):
        """Test when both anonymous and allow_anonymous are False."""
        # Should not raise exception
        AnonymousUserValidationMixin.validate_anonymous_policy(
            is_anonymous=False,
            allow_anonymous=False
        )


# ============================================================================
# CHOICE FIELD DISPLAY MIXIN TESTS
# ============================================================================

class ChoiceFieldDisplayMixinTests(TestCase):
    """Tests for ChoiceFieldDisplayMixin methods."""
    
    def setUp(self):
        """Set up for each test."""
        self.mixin = ChoiceFieldDisplayMixin()
        
        # Create test testimonial
        self.user = User.objects.create_user(username='testuser')
        self.testimonial = Testimonial.objects.create(
            author=self.user,
            content='Test content',
            rating=5,
            status=TestimonialStatus.APPROVED,
            source=TestimonialSource.EMAIL
        )
    
    def test_get_display_value_status(self):
        """Test getting display value for status field."""
        display = self.mixin.get_display_value(
            self.testimonial,
            'status'
        )
        
        self.assertEqual(display, 'Approved')
    
    def test_get_display_value_source(self):
        """Test getting display value for source field."""
        display = self.mixin.get_display_value(
            self.testimonial,
            'source'
        )
        
        self.assertEqual(display, 'Email')
    
    def test_get_display_value_non_choice_field(self):
        """Test getting value for non-choice field."""
        display = self.mixin.get_display_value(
            self.testimonial,
            'rating'
        )
        
        # Should return the actual value
        self.assertEqual(display, 5)
    
    def test_get_display_value_nonexistent_field(self):
        """Test getting value for non-existent field."""
        display = self.mixin.get_display_value(
            self.testimonial,
            'nonexistent_field'
        )
        
        # Should return empty string as fallback
        self.assertEqual(display, '')
    
    def test_get_display_value_different_statuses(self):
        """Test display values for different statuses."""
        statuses = [
            (TestimonialStatus.PENDING, 'Pending'),
            (TestimonialStatus.APPROVED, 'Approved'),
            (TestimonialStatus.REJECTED, 'Rejected'),
            (TestimonialStatus.FEATURED, 'Featured'),
        ]
        
        for status_code, expected_display in statuses:
            self.testimonial.status = status_code
            self.testimonial.save()
            
            display = self.mixin.get_display_value(
                self.testimonial,
                'status'
            )
            
            self.assertEqual(display, expected_display)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class ValidationMixinIntegrationTests(TestCase):
    """Integration tests for validation mixins."""
    
    def setUp(self):
        """Set up for each test."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
    
    def test_file_and_anonymous_validation_together(self):
        """Test using both file and anonymous validation."""
        # This simulates a form/serializer using both mixins
        
        class TestValidator(FileValidationMixin, AnonymousUserValidationMixin):
            pass
        
        validator = TestValidator()
        
        # Test file validation
        file_obj = Mock()
        file_obj.name = 'test.jpg'
        file_obj.size = 1024
        
        result = validator.validate_uploaded_file(
            file_obj,
            ['jpg'],
            1024 * 1024
        )
        self.assertEqual(result, file_obj)
        
        # Test anonymous validation
        data = {}
        result = validator.prefill_author_from_user(data, self.user)
        self.assertEqual(result['author'], self.user)
    
    def test_all_mixins_together(self):
        """Test using all validation mixins together."""
        
        class TestValidator(
            FileValidationMixin,
            AnonymousUserValidationMixin,
            ChoiceFieldDisplayMixin
        ):
            pass
        
        validator = TestValidator()
        
        # Should have all methods
        self.assertTrue(hasattr(validator, 'validate_file_extension'))
        self.assertTrue(hasattr(validator, 'prefill_author_from_user'))
        self.assertTrue(hasattr(validator, 'get_display_value'))


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class ValidationMixinEdgeCaseTests(TestCase):
    """Tests for edge cases and error handling."""
    
    def test_file_extension_unicode(self):
        """Test file extension with unicode characters."""
        file_obj = Mock()
        file_obj.name = 'tëst.jpg'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg', 'png']
        )
        
        self.assertEqual(ext, 'jpg')
    
    def test_file_name_special_characters(self):
        """Test filename with special characters."""
        file_obj = Mock()
        file_obj.name = 'my#test$file%.jpg'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg']
        )
        
        self.assertEqual(ext, 'jpg')
    
    def test_very_long_filename(self):
        """Test with very long filename."""
        file_obj = Mock()
        file_obj.name = 'a' * 1000 + '.jpg'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['jpg']
        )
        
        self.assertEqual(ext, 'jpg')
    
    def test_file_size_boundary(self):
        """Test file size at exact boundary."""
        file_obj = Mock()
        file_obj.size = 5 * 1024 * 1024 + 1  # Just over 5MB
        
        with self.assertRaises(serializers.ValidationError):
            FileValidationMixin.validate_file_size(
                file_obj,
                max_size=5 * 1024 * 1024
            )
    
    def test_prefill_with_mock_user_no_methods(self):
        """Test prefilling with user lacking expected methods."""
        user = Mock()
        user.is_authenticated = True
        user.username = 'mockuser'
        # No get_full_name method
        
        data = {}
        result = AnonymousUserValidationMixin.prefill_author_from_user(
            data, user
        )
        
        # Should handle gracefully
        self.assertIn('author', result)
    
    def test_anonymous_display_name_with_numbers(self):
        """Test anonymous display name with numeric values."""
        data = {'author_name': 123}  # Not a string
        
        # The mixin expects string values - non-strings will cause AttributeError
        # In real usage, serializers/forms would validate types before this mixin runs
        with self.assertRaises(AttributeError):
            AnonymousUserValidationMixin.ensure_anonymous_display_name(data)
    
    def test_multiple_dots_in_extension(self):
        """Test file with multiple dots in extension."""
        file_obj = Mock()
        file_obj.name = 'test.tar.gz'
        
        ext = FileValidationMixin.validate_file_extension(
            file_obj,
            ['gz', 'zip']
        )
        
        # Should get last part after final dot
        self.assertEqual(ext, 'gz')
    
    def test_empty_allowed_extensions(self):
        """Test validation with empty allowed extensions list."""
        file_obj = Mock()
        file_obj.name = 'test.jpg'
        
        with self.assertRaises(serializers.ValidationError):
            FileValidationMixin.validate_file_extension(
                file_obj,
                []  # Empty list
            )
    
    def test_zero_max_file_size(self):
        """Test with zero max file size."""
        file_obj = Mock()
        file_obj.size = 1  # Any size > 0
        
        with self.assertRaises(serializers.ValidationError):
            FileValidationMixin.validate_file_size(
                file_obj,
                max_size=0
            )
    
    def test_negative_file_size(self):
        """Test with negative max file size."""
        file_obj = Mock()
        file_obj.size = 1024
        
        # Negative max size means everything is too large
        with self.assertRaises(serializers.ValidationError):
            FileValidationMixin.validate_file_size(
                file_obj,
                max_size=-1
            )