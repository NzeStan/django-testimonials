"""
Tests for the testimonials app utilities.
"""

import pytest
import os
import uuid
from django.utils import timezone
from unittest.mock import patch, MagicMock

from testimonials.utils import (
    get_unique_slug,
    validate_rating,
    generate_upload_path,
    get_file_type,
    log_testimonial_action
)
from testimonials.models import Testimonial
from testimonials.constants import TestimonialMediaType


@pytest.mark.django_db
def test_get_unique_slug():
    """Test generating a unique slug."""
    # Create a model instance with a source for the slug
    testimonial = Testimonial.objects.create(
        author_name="Test User",
        content="This is a test testimonial.",
        rating=5
    )
    
    # Get a slug based on author_name
    slug = get_unique_slug(testimonial, 'author_name')
    assert slug == "test-user"
    
    # Create another instance with the same author_name
    testimonial2 = Testimonial.objects.create(
        author_name="Test User",
        content="This is another test testimonial.",
        rating=4
    )
    
    # Get a slug for the second instance - should be unique
    slug2 = get_unique_slug(testimonial2, 'author_name')
    assert slug2 != slug
    assert slug2 == "test-user-1"
    
    # Test max_length parameter
    long_name_testimonial = Testimonial.objects.create(
        author_name="This is a very long author name that should be truncated in the slug",
        content="Test content",
        rating=5
    )
    
    short_slug = get_unique_slug(long_name_testimonial, 'author_name', max_length=20)
    assert len(short_slug) <= 20


def test_validate_rating():
    """Test validation of rating values."""
    # Valid ratings
    for i in range(1, 6):
        assert validate_rating(i, max_rating=5) == None  # No exception should be raised
    
    # Invalid ratings
    invalid_ratings = [0, 6, -1, "not a number"]
    for rating in invalid_ratings:
        with pytest.raises(Exception):
            validate_rating(rating, max_rating=5)
    
    # Test with different max_rating
    assert validate_rating(8, max_rating=10) == None  # Valid for max 10
    with pytest.raises(Exception):
        validate_rating(11, max_rating=10)  # Invalid for max 10


def test_generate_upload_path():
    """Test generating upload paths for media files."""
    # Create a mock instance with a testimonial_id
    mock_instance = MagicMock()
    mock_instance.testimonial_id = uuid.uuid4()
    
    # Test with a simple filename
    path = generate_upload_path(mock_instance, "test_image.jpg")
    
    # Path should include the testimonial ID and a UUID filename
    assert str(mock_instance.testimonial_id) in path
    assert path.endswith(".jpg")
    assert "test_image" not in path  # Original filename should be replaced with UUID
    
    # Test with an instance that has no testimonial_id
    mock_instance = MagicMock()
    mock_instance.testimonial_id = None
    
    path = generate_upload_path(mock_instance, "test_doc.pdf")
    
    # Path should include 'misc' directory and a UUID filename
    assert "/misc/" in path
    assert path.endswith(".pdf")


def test_get_file_type():
    """Test determining file types from extensions."""
    # Test image file types
    image_files = ["test.jpg", "image.jpeg", "logo.png", "graphic.gif", "icon.webp", "vector.svg"]
    for file in image_files:
        assert get_file_type(file) == TestimonialMediaType.IMAGE
    
    # Test video file types
    video_files = ["video.mp4", "clip.webm", "movie.mov", "recording.avi"]
    for file in video_files:
        assert get_file_type(file) == TestimonialMediaType.VIDEO
    
    # Test audio file types
    audio_files = ["song.mp3", "recording.wav", "audio.ogg"]
    for file in audio_files:
        assert get_file_type(file) == TestimonialMediaType.AUDIO
    
    # Test document file types
    document_files = ["doc.pdf", "report.doc", "spreadsheet.docx", "notes.txt"]
    for file in document_files:
        assert get_file_type(file) == TestimonialMediaType.DOCUMENT
    
    # Test with file-like object
    mock_file = MagicMock()
    mock_file.name = "test_image.jpg"
    assert get_file_type(mock_file) == TestimonialMediaType.IMAGE


@pytest.mark.django_db
def test_log_testimonial_action(caplog):
    """Test logging testimonial actions."""
    # Create a testimonial
    testimonial = Testimonial.objects.create(
        author_name="Log Test User",
        content="This testimonial is for testing logging.",
        rating=5
    )
    
    # Test logging with various parameters
    log_testimonial_action(testimonial, "create")
    log_testimonial_action(testimonial, "approve", user="admin")
    log_testimonial_action(testimonial, "reject", user="moderator", notes="Not relevant")
    
    # Check log records were created (using pytest's caplog fixture)
    assert "Testimonial Action: create" in caplog.text
    assert "Testimonial Action: approve" in caplog.text
    assert "Testimonial Action: reject" in caplog.text
    assert "User: admin" in caplog.text
    assert "User: moderator" in caplog.text
    assert "Notes: Not relevant" in caplog.text