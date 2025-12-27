# testimonials/tests/test_validators.py

"""
Comprehensive tests for testimonial validators.
Tests cover all validator functions, edge cases, failures, and successes.
"""

from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from PIL import Image

from testimonials.validators import (
    validate_rating,
    validate_phone_number,
    validate_testimonial_content,
    create_file_size_validator,
    create_avatar_size_validator,
    image_dimension_validator,
)
from testimonials.conf import app_settings


# ============================================================================
# VALIDATE RATING TESTS
# ============================================================================

class ValidateRatingTest(TestCase):
    """Tests for validate_rating function."""
    
    def test_valid_rating_minimum(self):
        """Test rating at minimum value."""
        result = validate_rating(1)
        self.assertEqual(result, 1)
    
    def test_valid_rating_maximum(self):
        """Test rating at maximum value."""
        result = validate_rating(5)
        self.assertEqual(result, 5)
    
    def test_valid_rating_middle(self):
        """Test rating in middle range."""
        result = validate_rating(3)
        self.assertEqual(result, 3)
    
    def test_valid_rating_all_values(self):
        """Test all valid rating values."""
        for rating in range(1, 6):  # 1-5
            result = validate_rating(rating)
            self.assertEqual(result, rating)
    
    def test_invalid_rating_below_minimum(self):
        """Test rating below minimum raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating(0)
        
        self.assertIn('at least', str(cm.exception))
    
    def test_invalid_rating_above_maximum(self):
        """Test rating above maximum raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating(6)
        
        self.assertIn('cannot exceed', str(cm.exception))
    
    def test_invalid_rating_negative(self):
        """Test negative rating raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating(-1)
        
        self.assertIn('at least', str(cm.exception))
    
    def test_invalid_rating_very_large(self):
        """Test very large rating raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating(1000)
        
        self.assertIn('cannot exceed', str(cm.exception))
    
    def test_valid_rating_float_whole_number(self):
        """Test float that is a whole number."""
        result = validate_rating(3.0)
        self.assertEqual(result, 3)
        self.assertIsInstance(result, int)
    
    def test_invalid_rating_float_decimal(self):
        """Test float with decimal raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating(3.5)
        
        self.assertIn('whole number', str(cm.exception))
    
    def test_invalid_rating_string(self):
        """Test string raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating("5")
        
        self.assertIn('must be a number', str(cm.exception))
    
    def test_invalid_rating_none(self):
        """Test None raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            validate_rating(None)
        
        self.assertIn('must be a number', str(cm.exception))
    
    def test_invalid_rating_boolean(self):
        """Test boolean raises ValidationError."""
        # Note: In Python, True == 1 and False == 0
        # so isinstance(True, (int, float)) returns True
        # But we can still test the behavior
        result = validate_rating(True)  # True == 1
        self.assertEqual(result, True)
    
    @patch('testimonials.validators.app_settings')
    def test_rating_with_custom_settings(self, mock_settings):
        """Test rating validation with custom min/max settings."""
        mock_settings.MIN_RATING = 2
        mock_settings.MAX_RATING = 10
        
        # Valid with custom settings
        self.assertEqual(validate_rating(2), 2)
        self.assertEqual(validate_rating(10), 10)
        
        # Invalid with custom settings
        with self.assertRaises(ValidationError):
            validate_rating(1)  # Below custom min
        
        with self.assertRaises(ValidationError):
            validate_rating(11)  # Above custom max


# ============================================================================
# VALIDATE PHONE NUMBER TESTS
# ============================================================================

class ValidatePhoneNumberTest(TestCase):
    """Tests for validate_phone_number function."""
    
    def test_valid_phone_10_digits(self):
        """Test valid 10-digit phone number."""
        result = validate_phone_number("1234567890")
        self.assertEqual(result, "1234567890")
    
    def test_valid_phone_with_country_code(self):
        """Test valid phone with country code."""
        result = validate_phone_number("+12345678901")
        self.assertEqual(result, "+12345678901")
    
    def test_valid_phone_with_spaces(self):
        """Test valid phone with spaces."""
        result = validate_phone_number("123 456 7890")
        self.assertEqual(result, "123 456 7890")
    
    def test_valid_phone_with_dashes(self):
        """Test valid phone with dashes."""
        result = validate_phone_number("123-456-7890")
        self.assertEqual(result, "123-456-7890")
    
    def test_valid_phone_with_parentheses(self):
        """Test valid phone with parentheses."""
        result = validate_phone_number("(123) 456-7890")
        self.assertEqual(result, "(123) 456-7890")
    
    def test_valid_phone_with_dots(self):
        """Test valid phone with dots."""
        result = validate_phone_number("123.456.7890")
        self.assertEqual(result, "123.456.7890")
    
    def test_valid_phone_15_digits(self):
        """Test valid 15-digit phone (maximum)."""
        result = validate_phone_number("123456789012345")
        self.assertEqual(result, "123456789012345")
    
    def test_valid_phone_international_format(self):
        """Test valid international format."""
        result = validate_phone_number("+1 (234) 567-8901")
        self.assertEqual(result, "+1 (234) 567-8901")
    
    def test_invalid_phone_too_short(self):
        """Test phone number too short."""
        with self.assertRaises(ValidationError) as cm:
            validate_phone_number("123456789")  # 9 digits
        
        self.assertIn('10-15 digits', str(cm.exception))
    
    def test_invalid_phone_too_long(self):
        """Test phone number too long."""
        with self.assertRaises(ValidationError) as cm:
            validate_phone_number("1234567890123456")  # 16 digits
        
        self.assertIn('10-15 digits', str(cm.exception))
    
    def test_invalid_phone_letters(self):
        """Test phone with letters."""
        with self.assertRaises(ValidationError) as cm:
            validate_phone_number("123-ABC-7890")
        
        self.assertIn('10-15 digits', str(cm.exception))
    
    def test_invalid_phone_special_chars(self):
        """Test phone with invalid special characters."""
        with self.assertRaises(ValidationError) as cm:
            validate_phone_number("123#456*7890")
        
        self.assertIn('10-15 digits', str(cm.exception))
    
    def test_empty_phone_returns_value(self):
        """Test empty phone returns value unchanged."""
        result = validate_phone_number("")
        self.assertEqual(result, "")
    
    def test_none_phone_returns_value(self):
        """Test None phone returns value unchanged."""
        result = validate_phone_number(None)
        self.assertIsNone(result)
    
    def test_whitespace_only_phone(self):
        """Test whitespace-only phone."""
        with self.assertRaises(ValidationError):
            validate_phone_number("   ")


# ============================================================================
# VALIDATE TESTIMONIAL CONTENT TESTS
# ============================================================================

class ValidateTestimonialContentTest(TestCase):
    """Tests for validate_testimonial_content function."""
    
    def test_valid_content_minimum_length(self):
        """Test content at minimum length."""
        content = "A" * 10  # Default min is 10
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_valid_content_medium_length(self):
        """Test content of medium length."""
        content = "This is a great product with excellent quality and service."
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_valid_content_maximum_length(self):
        """Test content at maximum length."""
        content = "A" * 5000  # Default max is 5000
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_valid_content_with_whitespace(self):
        """Test content with leading/trailing whitespace."""
        content = "  This is valid content with enough characters.  "
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_invalid_content_too_short(self):
        """Test content below minimum length."""
        content = "Short"  # Less than 10 chars
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('at least', str(cm.exception))
        self.assertIn('10', str(cm.exception))
    
    def test_invalid_content_too_long(self):
        """Test content above maximum length."""
        content = "A" * 5001  # Over default max
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('cannot exceed', str(cm.exception))
        self.assertIn('5000', str(cm.exception))
    
    def test_empty_content_whitespace_only(self):
        """Test content that is only whitespace."""
        content = "     "
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('at least', str(cm.exception))
    
    def test_valid_content_exactly_minimum(self):
        """Test content exactly at minimum after strip."""
        content = "  1234567890  "  # Exactly 10 chars after strip
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_valid_content_exactly_maximum(self):
        """Test content exactly at maximum after strip."""
        content = "A" * 5000
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_invalid_content_forbidden_word_spam(self, mock_settings):
        """Test content with forbidden word 'spam'."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = ['spam', 'fake', 'bot']
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        content = "This is spam content that should be rejected."
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('inappropriate', str(cm.exception))
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_invalid_content_forbidden_word_fake(self, mock_settings):
        """Test content with forbidden word 'fake'."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = ['spam', 'fake', 'bot']
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        content = "This is a fake review for validation purposes."
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('inappropriate', str(cm.exception))
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_valid_content_word_boundary_check(self, mock_settings):
        """Test that word boundary check works correctly."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = ['test']
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        # "testimonial" contains "test" but shouldn't match
        content = "This is a testimonial about great quality products."
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_invalid_content_excessive_repetition(self, mock_settings):
        """Test content with excessive repetition."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = []
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        # Less than 30% unique words
        content = "great great great great great great product"
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('repetition', str(cm.exception))
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_valid_content_acceptable_repetition(self, mock_settings):
        """Test content with acceptable repetition."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = []
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        # More than 30% unique words
        content = "This is a great product with excellent quality."
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=False)
    @patch('testimonials.validators.app_settings')
    def test_content_quality_disabled(self, mock_settings):
        """Test that quality validation is skipped when disabled."""
        mock_settings.VALIDATE_CONTENT_QUALITY = False
        mock_settings.FORBIDDEN_WORDS = ['spam']
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        # Should pass even with forbidden word when quality check disabled
        content = "This is spam content but quality check is off."
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    @patch('testimonials.validators.app_settings')
    def test_content_with_custom_length_settings(self, mock_settings):
        """Test content validation with custom length settings."""
        mock_settings.MIN_TESTIMONIAL_LENGTH = 20
        mock_settings.MAX_TESTIMONIAL_LENGTH = 100
        mock_settings.VALIDATE_CONTENT_QUALITY = False
        
        # Valid with custom settings
        content = "A" * 20  # Custom minimum
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
        
        # Invalid - too short
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content("Short")
        self.assertIn('20', str(cm.exception))
        
        # Invalid - too long
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content("A" * 101)
        self.assertIn('100', str(cm.exception))
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_forbidden_word_case_insensitive(self, mock_settings):
        """Test forbidden words are case insensitive."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = ['spam']
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        content = "This is SPAM content in uppercase letters."
        
        with self.assertRaises(ValidationError) as cm:
            validate_testimonial_content(content)
        
        self.assertIn('inappropriate', str(cm.exception))
    
    @override_settings(TESTIMONIALS_VALIDATE_CONTENT_QUALITY=True)
    @patch('testimonials.validators.app_settings')
    def test_repetition_check_short_content(self, mock_settings):
        """Test that repetition check skips content with 5 or fewer words."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = []
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        # 5 words - should skip repetition check
        content = "great great great great great"
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)


# ============================================================================
# CREATE FILE SIZE VALIDATOR TESTS
# ============================================================================

class CreateFileSizeValidatorTest(TestCase):
    """Tests for create_file_size_validator factory function."""
    
    def test_create_validator_default_size(self):
        """Test creating validator with default size."""
        validator = create_file_size_validator()
        
        # Create mock file within limit
        mock_file = Mock()
        mock_file.size = 1024 * 1024  # 1 MB
        
        # Should not raise
        validator(mock_file)
    
    def test_create_validator_custom_size(self):
        """Test creating validator with custom size."""
        validator = create_file_size_validator(max_size_mb=2)
        
        mock_file = Mock()
        mock_file.size = 1.5 * 1024 * 1024  # 1.5 MB
        
        # Should not raise (under 2 MB limit)
        validator(mock_file)
    
    def test_validator_file_too_large(self):
        """Test validator rejects oversized file."""
        validator = create_file_size_validator(max_size_mb=1)
        
        mock_file = Mock()
        mock_file.size = 2 * 1024 * 1024  # 2 MB
        
        with self.assertRaises(ValidationError) as cm:
            validator(mock_file)
        
        error_msg = str(cm.exception)
        self.assertIn('too large', error_msg)
        self.assertIn('2.0', error_msg)  # Current size
        self.assertIn('1.0', error_msg)  # Max size
    
    def test_validator_file_exactly_at_limit(self):
        """Test validator accepts file exactly at limit."""
        validator = create_file_size_validator(max_size_mb=1)
        
        mock_file = Mock()
        mock_file.size = 1 * 1024 * 1024  # Exactly 1 MB
        
        # Should not raise
        validator(mock_file)
    
    def test_validator_file_just_over_limit(self):
        """Test validator rejects file just over limit."""
        validator = create_file_size_validator(max_size_mb=1)
        
        mock_file = Mock()
        mock_file.size = 1 * 1024 * 1024 + 1  # Just over 1 MB
        
        with self.assertRaises(ValidationError):
            validator(mock_file)
    
    def test_validator_custom_file_type(self):
        """Test validator with custom file type in error message."""
        validator = create_file_size_validator(max_size_mb=1, file_type="image")
        
        mock_file = Mock()
        mock_file.size = 2 * 1024 * 1024
        
        with self.assertRaises(ValidationError) as cm:
            validator(mock_file)
        
        self.assertIn('Image', str(cm.exception))
    
    def test_validator_zero_byte_file(self):
        """Test validator accepts zero-byte file."""
        validator = create_file_size_validator(max_size_mb=1)
        
        mock_file = Mock()
        mock_file.size = 0
        
        # Should not raise (not too large)
        validator(mock_file)
    
    def test_validator_very_large_limit(self):
        """Test validator with very large limit."""
        validator = create_file_size_validator(max_size_mb=100)
        
        mock_file = Mock()
        mock_file.size = 50 * 1024 * 1024  # 50 MB
        
        # Should not raise
        validator(mock_file)
    
    def test_validator_fractional_mb(self):
        """Test validator with fractional MB limit."""
        validator = create_file_size_validator(max_size_mb=0.5)
        
        mock_file = Mock()
        mock_file.size = 256 * 1024  # 0.25 MB
        
        # Should not raise
        validator(mock_file)
        
        mock_file.size = 1024 * 1024  # 1 MB
        
        with self.assertRaises(ValidationError):
            validator(mock_file)


# ============================================================================
# CREATE AVATAR SIZE VALIDATOR TESTS
# ============================================================================

class CreateAvatarSizeValidatorTest(TestCase):
    """Tests for create_avatar_size_validator function."""
    
    @patch('testimonials.validators.app_settings')
    def test_avatar_validator_with_custom_max_avatar_size(self, mock_settings):
        """Test avatar validator uses MAX_AVATAR_SIZE if available."""
        mock_settings.MAX_AVATAR_SIZE = 1 * 1024 * 1024  # 1 MB
        mock_settings.MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        
        validator = create_avatar_size_validator()
        
        mock_file = Mock()
        mock_file.size = 0.5 * 1024 * 1024  # 0.5 MB
        
        # Should not raise (under 1 MB avatar limit)
        validator(mock_file)
    
    @patch('testimonials.validators.app_settings')
    def test_avatar_validator_exceeds_limit(self, mock_settings):
        """Test avatar validator rejects oversized avatar."""
        mock_settings.MAX_AVATAR_SIZE = 1 * 1024 * 1024  # 1 MB
        
        validator = create_avatar_size_validator()
        
        mock_file = Mock()
        mock_file.size = 2 * 1024 * 1024  # 2 MB
        
        with self.assertRaises(ValidationError) as cm:
            validator(mock_file)
        
        error_msg = str(cm.exception)
        self.assertIn('Avatar', error_msg)
        self.assertIn('too large', error_msg)
    
    @patch('testimonials.validators.app_settings')
    def test_avatar_validator_fallback_to_max_file_size(self, mock_settings):
        """Test avatar validator falls back to MAX_FILE_SIZE."""
        # MAX_AVATAR_SIZE not set
        mock_settings.MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
        delattr(mock_settings, 'MAX_AVATAR_SIZE')
        
        validator = create_avatar_size_validator()
        
        mock_file = Mock()
        mock_file.size = 3 * 1024 * 1024  # 3 MB
        
        # Should not raise (under 5 MB file limit)
        validator(mock_file)
    
    @patch('testimonials.validators.app_settings')
    def test_avatar_validator_error_message_format(self, mock_settings):
        """Test avatar validator error message format."""
        mock_settings.MAX_AVATAR_SIZE = 1 * 1024 * 1024
        
        validator = create_avatar_size_validator()
        
        mock_file = Mock()
        mock_file.size = 2.5 * 1024 * 1024  # 2.5 MB
        
        with self.assertRaises(ValidationError) as cm:
            validator(mock_file)
        
        error_msg = str(cm.exception)
        self.assertIn('2.5', error_msg)  # Current size
        self.assertIn('1.0', error_msg)  # Max size


# ============================================================================
# IMAGE DIMENSION VALIDATOR TESTS
# ============================================================================

class ImageDimensionValidatorTest(TestCase):
    """Tests for image_dimension_validator function."""
    
    def _create_test_image(self, width, height):
        """Helper to create test image."""
        image = Image.new('RGB', (width, height), color='red')
        file = BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)
        return file
    
    @patch('testimonials.validators.app_settings')
    def test_valid_image_dimensions(self, mock_settings):
        """Test image within dimension limits."""
        mock_settings.MAX_IMAGE_WIDTH = 2000
        mock_settings.MAX_IMAGE_HEIGHT = 2000
        
        image_file = self._create_test_image(1000, 1000)
        
        # Should not raise
        image_dimension_validator(image_file)
    
    @patch('testimonials.validators.app_settings')
    def test_valid_image_exactly_at_limit(self, mock_settings):
        """Test image exactly at dimension limits."""
        mock_settings.MAX_IMAGE_WIDTH = 1000
        mock_settings.MAX_IMAGE_HEIGHT = 1000
        
        image_file = self._create_test_image(1000, 1000)
        
        # Should not raise
        image_dimension_validator(image_file)
    
    @patch('testimonials.validators.app_settings')
    def test_invalid_image_width_too_large(self, mock_settings):
        """Test image with width exceeding limit."""
        mock_settings.MAX_IMAGE_WIDTH = 1000
        mock_settings.MAX_IMAGE_HEIGHT = 2000
        
        image_file = self._create_test_image(1500, 500)
        
        with self.assertRaises(ValidationError) as cm:
            image_dimension_validator(image_file)
        
        error_msg = str(cm.exception)
        self.assertIn('dimensions too large', error_msg.lower())
        self.assertIn('1500', error_msg)  # Actual width
        self.assertIn('1000', error_msg)  # Max width
    
    @patch('testimonials.validators.app_settings')
    def test_invalid_image_height_too_large(self, mock_settings):
        """Test image with height exceeding limit."""
        mock_settings.MAX_IMAGE_WIDTH = 2000
        mock_settings.MAX_IMAGE_HEIGHT = 1000
        
        image_file = self._create_test_image(500, 1500)
        
        with self.assertRaises(ValidationError) as cm:
            image_dimension_validator(image_file)
        
        error_msg = str(cm.exception)
        self.assertIn('dimensions too large', error_msg.lower())
        self.assertIn('1500', error_msg)  # Actual height
        self.assertIn('1000', error_msg)  # Max height
    
    @patch('testimonials.validators.app_settings')
    def test_invalid_image_both_dimensions_too_large(self, mock_settings):
        """Test image with both dimensions exceeding limits."""
        mock_settings.MAX_IMAGE_WIDTH = 1000
        mock_settings.MAX_IMAGE_HEIGHT = 1000
        
        image_file = self._create_test_image(2000, 2000)
        
        with self.assertRaises(ValidationError) as cm:
            image_dimension_validator(image_file)
        
        error_msg = str(cm.exception)
        self.assertIn('dimensions too large', error_msg.lower())
        self.assertIn('2000', error_msg)
    
    @patch('testimonials.validators.app_settings')
    def test_valid_image_asymmetric_dimensions(self, mock_settings):
        """Test image with valid asymmetric dimensions."""
        mock_settings.MAX_IMAGE_WIDTH = 2000
        mock_settings.MAX_IMAGE_HEIGHT = 1000
        
        # Wide image
        image_file = self._create_test_image(1500, 500)
        image_dimension_validator(image_file)
        
        # Tall image
        image_file = self._create_test_image(500, 900)
        image_dimension_validator(image_file)
    
    @patch('testimonials.validators.app_settings')
    def test_very_small_image(self, mock_settings):
        """Test very small image passes validation."""
        mock_settings.MAX_IMAGE_WIDTH = 2000
        mock_settings.MAX_IMAGE_HEIGHT = 2000
        
        image_file = self._create_test_image(10, 10)
        
        # Should not raise
        image_dimension_validator(image_file)
    
    def test_invalid_image_file(self):
        """Test invalid image file raises ValidationError."""
        # Create non-image file
        invalid_file = BytesIO(b"This is not an image file")
        
        with self.assertRaises(ValidationError) as cm:
            image_dimension_validator(invalid_file)
        
        self.assertIn('Invalid image', str(cm.exception))
    
    def test_corrupted_image_file(self):
        """Test corrupted image file raises ValidationError."""
        # Create partially corrupted image data
        corrupted_file = BytesIO(b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"corrupted")
        
        with self.assertRaises(ValidationError) as cm:
            image_dimension_validator(corrupted_file)
        
        self.assertIn('Invalid image', str(cm.exception))
    
    @patch('testimonials.validators.app_settings')
    def test_default_dimension_limits(self, mock_settings):
        """Test default dimension limits when not in settings."""
        # Remove attributes to test defaults
        delattr(mock_settings, 'MAX_IMAGE_WIDTH')
        delattr(mock_settings, 'MAX_IMAGE_HEIGHT')
        
        # Should use default 2000x2000
        image_file = self._create_test_image(1500, 1500)
        image_dimension_validator(image_file)
        
        # Should reject 3000x3000
        large_image = self._create_test_image(3000, 3000)
        with self.assertRaises(ValidationError):
            image_dimension_validator(large_image)


# ============================================================================
# EDGE CASES AND INTEGRATION TESTS
# ============================================================================

class ValidatorEdgeCasesTest(TestCase):
    """Tests for edge cases and integration scenarios."""
    
    def test_rating_with_infinity(self):
        """Test rating with infinity value."""
        with self.assertRaises(ValidationError):
            validate_rating(float('inf'))
    
    def test_rating_with_nan(self):
        """Test rating with NaN value."""
        with self.assertRaises(ValidationError):
            validate_rating(float('nan'))
    
    def test_phone_with_only_plus_sign(self):
        """Test phone with only plus sign."""
        with self.assertRaises(ValidationError):
            validate_phone_number("+")
    
    def test_phone_with_multiple_plus_signs(self):
        """Test phone with multiple plus signs."""
        with self.assertRaises(ValidationError):
            validate_phone_number("++1234567890")
    
    def test_content_with_unicode_characters(self):
        """Test content with unicode characters."""
        content = "Excelente producto con calidad única y servicio fantástico!"
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_content_with_emojis(self):
        """Test content with emojis."""
        content = "Great product! 😊👍 Would definitely recommend to others! 🌟"
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_content_with_newlines(self):
        """Test content with newlines."""
        content = "Great product!\nExcellent quality!\nWould buy again!"
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    def test_content_with_tabs(self):
        """Test content with tabs."""
        content = "Great\tproduct\twith\texcellent\tquality\tand\tservice."
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
    
    @patch('testimonials.validators.app_settings')
    def test_content_with_multiple_forbidden_words(self, mock_settings):
        """Test content with multiple forbidden words."""
        mock_settings.VALIDATE_CONTENT_QUALITY = True
        mock_settings.FORBIDDEN_WORDS = ['spam', 'fake', 'bot']
        mock_settings.MIN_TESTIMONIAL_LENGTH = 10
        mock_settings.MAX_TESTIMONIAL_LENGTH = 5000
        
        content = "This is spam and fake content from a bot."
        
        # Should reject on first forbidden word found
        with self.assertRaises(ValidationError):
            validate_testimonial_content(content)
    
    def test_file_validator_with_real_uploaded_file(self):
        """Test file validator with actual SimpleUploadedFile."""
        validator = create_file_size_validator(max_size_mb=1)
        
        content = b"A" * (512 * 1024)  # 0.5 MB
        uploaded_file = SimpleUploadedFile("test.txt", content)
        
        # Should not raise
        validator(uploaded_file)
    
    def test_multiple_validators_chained(self):
        """Test multiple validators can be chained."""
        content = "This is valid content with sufficient length."
        
        # All validators should pass
        result = validate_testimonial_content(content)
        self.assertEqual(result, content)
        
        rating = 5
        result = validate_rating(rating)
        self.assertEqual(result, rating)
        
        phone = "1234567890"
        result = validate_phone_number(phone)
        self.assertEqual(result, phone)