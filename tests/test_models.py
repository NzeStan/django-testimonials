"""
Tests for the testimonials app models.
"""

import pytest
from django.core.exceptions import ValidationError

from testimonials.models import TestimonialCategory, Testimonial, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialMediaType
from tests.factories import TestimonialFactory, PendingTestimonialFactory


@pytest.mark.django_db
class TestTestimonialCategory:
    """Tests for the TestimonialCategory model."""

    def test_create_category(self, category):
        """Test creating a category (using fixture)."""
        assert category.name is not None
        assert category.slug is not None
        assert category.is_active is True

    def test_category_str(self, category):
        """Test the string representation of a category."""
        assert str(category) == category.name

    def test_auto_slug_generation(self):
        """Test that a slug is automatically generated if not provided."""
        category = TestimonialCategory.objects.create(name="Auto Slug Category")
        assert category.slug == "auto-slug-category"

    def test_unique_slug(self):
        """Test that duplicate slugs are made unique."""
        category1 = TestimonialCategory.objects.create(name="Duplicate", slug="duplicate")
        category2 = TestimonialCategory.objects.create(name="Duplicate", slug="duplicate")

        assert category1.slug != category2.slug
        assert category2.slug == "duplicate-1"


@pytest.mark.django_db
class TestTestimonial:
    """Tests for the Testimonial model."""

    def test_create_testimonial(self, testimonial):
        """Test creating a testimonial (using fixture)."""
        assert testimonial.author_name is not None
        assert testimonial.content != ""
        assert testimonial.rating == 5
        assert testimonial.status == TestimonialStatus.APPROVED

    def test_testimonial_str(self, testimonial):
        """Test the string representation of a testimonial."""
        assert str(testimonial).startswith(testimonial.author_name)

    def test_auto_slug_generation(self, testimonial):
        """Test that a slug is automatically generated if not provided."""
        assert testimonial.slug is not None
        assert testimonial.slug != ""

    def test_is_published_property(self, testimonial, pending_testimonial, featured_testimonial):
        """Test the is_published property (mixing fixtures)."""
        assert testimonial.is_published is True
        assert pending_testimonial.is_published is False
        assert featured_testimonial.is_published is True

    def test_anonymous_testimonial(self, anonymous_testimonial):
        """Test anonymous testimonial handling."""
        assert anonymous_testimonial.is_anonymous is True
        assert anonymous_testimonial.author_name == "Anonymous"
        assert anonymous_testimonial.author is None

    def test_approve_method(self, pending_testimonial, admin_user):
        """Test the approve method."""
        assert pending_testimonial.status == TestimonialStatus.PENDING

        pending_testimonial.approve(admin_user)

        assert pending_testimonial.status == TestimonialStatus.APPROVED
        assert pending_testimonial.approved_at is not None
        assert pending_testimonial.approved_by == admin_user

    def test_reject_method(self, testimonial, admin_user):
        """Test the reject method."""
        assert testimonial.status == TestimonialStatus.APPROVED

        reason = "Does not meet our standards"
        testimonial.reject(reason, admin_user)

        assert testimonial.status == TestimonialStatus.REJECTED
        assert testimonial.rejection_reason == reason

    def test_feature_method(self, testimonial, admin_user):
        """Test the feature method."""
        testimonial.feature(admin_user)
        assert testimonial.status == TestimonialStatus.FEATURED

    def test_archive_method(self, testimonial, admin_user):
        """Test the archive method."""
        testimonial.archive(admin_user)
        assert testimonial.status == TestimonialStatus.ARCHIVED

    def test_add_response(self, testimonial, admin_user):
        """Test adding a response to a testimonial."""
        response_text = "Thank you for your feedback!"
        testimonial.add_response(response_text, admin_user)

        assert testimonial.response == response_text
        assert testimonial.response_by == admin_user

    def test_validation_rating_range(self, user, category):
        """Test validation of rating range."""
        with pytest.raises(ValidationError):
            testimonial = Testimonial(
                author=user,
                author_name="Invalid Rating",
                content="Invalid rating test",
                rating=10,  # invalid
                category=category,
            )
            testimonial.full_clean()

    def test_author_display_property(self, testimonial, anonymous_testimonial):
        """Test the author_display property."""
        assert testimonial.author_display == testimonial.author_name
        assert anonymous_testimonial.author_display == "Anonymous"

    def test_factory_override(self, user, category):
        """Test using factory directly for a custom testimonial."""
        custom_testimonial = TestimonialFactory(
            author=user, category=category, status=TestimonialStatus.PENDING, rating=2
        )
        assert custom_testimonial.status == TestimonialStatus.PENDING
        assert custom_testimonial.rating == 2

    def test_pending_factory_direct(self, user, category):
        """Test pending testimonial using PendingTestimonialFactory directly."""
        t = PendingTestimonialFactory(author=user, category=category)
        assert t.status == TestimonialStatus.PENDING


@pytest.mark.django_db
class TestTestimonialMedia:
    """Tests for the TestimonialMedia model."""

    def test_create_media(self, testimonial_media):
        """Test creating testimonial media (fixture)."""
        assert testimonial_media.testimonial is not None
        assert testimonial_media.media_type == TestimonialMediaType.IMAGE
        assert testimonial_media.title == "Test Image"

    def test_media_str(self, testimonial_media):
        """Test the string representation of media."""
        assert str(testimonial_media) == "Image - Test Image"

    def test_primary_media(self, testimonial, test_image):
        """Test primary media functionality (manual object create)."""
        # Create first media as primary
        media1 = TestimonialMedia.objects.create(
            testimonial=testimonial,
            file=test_image,
            media_type=TestimonialMediaType.IMAGE,
            title="Primary Image",
            is_primary=True,
        )

        # Create second media as primary
        media2 = TestimonialMedia.objects.create(
            testimonial=testimonial,
            file=test_image,
            media_type=TestimonialMediaType.IMAGE,
            title="New Primary Image",
            is_primary=True,
        )

        media1.refresh_from_db()
        assert media1.is_primary is False
        assert media2.is_primary is True

    def test_add_media_method(self, testimonial, test_image):
        """Test the add_media method on Testimonial."""
        media = testimonial.add_media(
            test_image,
            title="Added via method",
            description="This media was added via the add_media method",
        )
        assert testimonial.media.count() == 1
        assert media.title == "Added via method"
        assert media.media_type == TestimonialMediaType.IMAGE
