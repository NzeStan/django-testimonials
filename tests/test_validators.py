"""
Tests for the testimonials app validators.
"""

import pytest
from django.core.exceptions import ValidationError

from testimonials.validators import (
    NoHTMLValidator,
    NoURLValidator,
    NoEmailValidator,
    NoPhoneValidator,
    ProfanityValidator,
    validate_rating,
    validate_testimonial_content,
    validate_file_size,
    validate_file_extension
)


class TestNoHTMLValidator:
    """Tests for the NoHTMLValidator."""
    
    def test_valid_text(self):
        """Test that text without HTML passes validation."""
        validator = NoHTMLValidator()
        valid_text = "This is just regular text without any HTML."
        
        # Should not raise an error
        assert validator(valid_text) == valid_text
    
    def test_invalid_text_with_html(self):
        """Test that text with HTML fails validation."""
        validator = NoHTMLValidator()
        invalid_text = "This contains <a href='#'>HTML</a> tags."
        
        # Should raise ValidationError
        with pytest.raises(ValidationError):
            validator(invalid_text)
    
    def test_custom_message(self):
        """Test custom error message."""
        custom_message = "No HTML allowed here!"
        validator = NoHTMLValidator(message=custom_message)
        invalid_text = "This contains <strong>HTML</strong> tags."
        
        try:
            validator(invalid_text)
            assert False, "Validation should have failed"
        except ValidationError as e:
            assert custom_message in str(e)


class TestNoURLValidator:
    """Tests for the NoURLValidator."""
    
    def test_valid_text(self):
        """Test that text without URLs passes validation."""
        validator = NoURLValidator()
        valid_text = "This is just regular text without any URLs."
        
        # Should not raise an error
        assert validator(valid_text) == valid_text
    
    def test_invalid_text_with_url(self):
        """Test that text with URLs fails validation."""
        validator = NoURLValidator()
        invalid_text = "Check out https://example.com for more information."
        
        # Should raise ValidationError
        with pytest.raises(ValidationError):
            validator(invalid_text)


class TestNoEmailValidator:
    """Tests for the NoEmailValidator."""
    
    def test_valid_text(self):
        """Test that text without email addresses passes validation."""
        validator = NoEmailValidator()
        valid_text = "This is just regular text without any email addresses."
        
        # Should not raise an error
        assert validator(valid_text) == valid_text
    
    def test_invalid_text_with_email(self):
        """Test that text with email addresses fails validation."""
        validator = NoEmailValidator()
        invalid_text = "Contact me at user@example.com for more information."
        
        # Should raise ValidationError
        with pytest.raises(ValidationError):
            validator(invalid_text)


class TestNoPhoneValidator:
    """Tests for the NoPhoneValidator."""
    
    def test_valid_text(self):
        """Test that text without phone numbers passes validation."""
        validator = NoPhoneValidator()
        valid_text = "This is just regular text without any phone numbers."
        
        # Should not raise an error
        assert validator(valid_text) == valid_text
    
    def test_invalid_text_with_phone(self):
        """Test that text with phone numbers fails validation."""
        validator = NoPhoneValidator()
        
        # Test various phone number formats
        phone_formats = [
            "Call me at 555-123-4567",
            "My number is (555) 123-4567",
            "Contact: 555.123.4567",
            "International: +1 555 123 4567"
        ]
        
        for text in phone_formats:
            with pytest.raises(ValidationError):
                validator(text)


class TestProfanityValidator:
    """Tests for the ProfanityValidator."""
    
    def test_clean_text(self):
        """Test that clean text passes validation."""
        validator = ProfanityValidator()
        valid_text = "This is just clean text without any profanity."
        
        # Should not raise an error
        assert validator(valid_text) == valid_text
    
    def test_custom_word_list(self):
        """Test that custom profanity list works."""
        custom_words = ['badword', 'anotherbadword']
        validator = ProfanityValidator(custom_words=custom_words)
        
        # Valid text should pass
        valid_text = "This is just clean text."
        assert validator(valid_text) == valid_text
        
        # Text with custom bad word should fail
        invalid_text = "This text contains badword which is not allowed."
        with pytest.raises(ValidationError):
            validator(invalid_text)


def test_validate_rating():
    """Test the validate_rating function."""
    # Valid ratings should not raise exceptions
    for i in range(1, 6):
        assert validate_rating(i) == i
    
    # Invalid ratings should raise ValidationError
    with pytest.raises(ValidationError):
        validate_rating(0)  # Too low
    
    with pytest.raises(ValidationError):
        validate_rating(6)  # Too high
    
    with pytest.raises(ValidationError):
        validate_rating("not a number")  # Not a number


def test_validate_testimonial_content():
    """Test the validate_testimonial_content function."""
    # Valid content
    valid_content = "This is a valid testimonial with enough characters."
    assert validate_testimonial_content(valid_content) == valid_content
    
    # Empty content should raise ValidationError
    with pytest.raises(ValidationError):
        validate_testimonial_content("")
    
    # Too short content should raise ValidationError
    with pytest.raises(ValidationError):
        validate_testimonial_content("Too short")


def test_validate_file_size():
    """Test the validate_file_size function."""
    # Create a mock file object
    class MockFile:
        def __init__(self, size):
            self.size = size
    
    # Valid file size
    valid_file = MockFile(2 * 1024 * 1024)  # 2MB
    assert validate_file_size(valid_file, max_size_mb=5) == valid_file
    
    # File too large
    invalid_file = MockFile(10 * 1024 * 1024)  # 10MB
    with pytest.raises(ValidationError):
        validate_file_size(invalid_file, max_size_mb=5)


def test_validate_file_extension():
    """Test the validate_file_extension function."""
    # Create a mock file object
    class MockFile:
        def __init__(self, name):
            self.name = name
    
    # Valid file extensions
    valid_extensions = [
        "image.jpg",
        "document.pdf",
        "video.mp4",
        "audio.mp3"
    ]
    
    for filename in valid_extensions:
        file_obj = MockFile(filename)
        # Should not raise an exception with default allowed extensions
        assert validate_file_extension(file_obj) == file_obj
    
    # Invalid file extension
    invalid_file = MockFile("malicious.exe")
    with pytest.raises(ValidationError):
        validate_file_extension(invalid_file)
    
    # Test with custom allowed extensions
    custom_extensions = ["csv", "xlsx"]
    
    # Valid for custom list
    valid_file = MockFile("data.csv")
    assert validate_file_extension(valid_file, allowed_extensions=custom_extensions) == valid_file
    
    # Invalid for custom list
    invalid_for_custom = MockFile("image.jpg")
    with pytest.raises(ValidationError):
        validate_file_extension(invalid_for_custom, allowed_extensions=custom_extensions)