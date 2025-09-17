"""
Pytest configuration for the testimonials app tests.
"""

import pytest
from rest_framework.test import APIClient
import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from .factories import (
    UserFactory,
    AdminUserFactory,
    TestimonialCategoryFactory,
    TestimonialFactory,
    PendingTestimonialFactory,
    FeaturedTestimonialFactory,
    AnonymousTestimonialFactory,
    TestimonialMediaFactory,
)


@pytest.fixture
def api_client():
    """Return an APIClient instance."""
    return APIClient()


@pytest.fixture
def user():
    """Return a user instance."""
    return UserFactory()


@pytest.fixture
def admin_user():
    """Return an admin user instance."""
    return AdminUserFactory()


@pytest.fixture
def category():
    """Return a testimonial category instance."""
    return TestimonialCategoryFactory()


@pytest.fixture
def testimonial(user, category):
    """Return a testimonial instance."""
    return TestimonialFactory(author=user, category=category)


@pytest.fixture
def pending_testimonial(user, category):
    """Return a pending testimonial instance."""
    return PendingTestimonialFactory(author=user, category=category)


@pytest.fixture
def featured_testimonial(user, category):
    """Return a featured testimonial instance."""
    return FeaturedTestimonialFactory(author=user, category=category)


@pytest.fixture
def anonymous_testimonial(category):
    """Return an anonymous testimonial instance."""
    return AnonymousTestimonialFactory(category=category)


@pytest.fixture
def testimonial_media(testimonial):
    """Return a testimonial media instance."""
    return TestimonialMediaFactory(testimonial=testimonial)

@pytest.fixture
def test_image():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile("test.png", buf.read(), content_type="image/png")