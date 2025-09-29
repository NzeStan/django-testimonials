"""
Tests for the testimonials app forms.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from testimonials.forms import (
    TestimonialForm,
    TestimonialAdminForm,
    TestimonialCategoryForm,
    TestimonialMediaForm,
    PublicTestimonialForm,
    TestimonialFilterForm
)
from testimonials.models import Testimonial, TestimonialCategory
from testimonials.constants import TestimonialStatus


@pytest.mark.django_db
class TestTestimonialForm:
    """Tests for the TestimonialForm."""
    
    def test_valid_form(self, category):
        """Test that valid data passes form validation."""
        form_data = {
            'author_name': 'Form Test User',
            'author_email': 'formtest@example.com',
            'content': 'This is a testimonial submitted via form.',
            'rating': 4,
            'category': category.id
        }
        
        form = TestimonialForm(data=form_data)
        assert form.is_valid()
    
    def test_required_fields(self):
        """Test required field validation."""
        # Empty form
        form = TestimonialForm(data={})
        assert not form.is_valid()
        
        # Required fields should be in the errors dictionary
        assert 'author_name' in form.errors
        assert 'content' in form.errors
        assert 'rating' in form.errors
    
    def test_content_min_length(self):
        """Test content minimum length validation."""
        form_data = {
            'author_name': 'Short Content User',
            'author_email': 'short@example.com',
            'content': 'Too short',  # Less than 10 characters
            'rating': 4
        }
        
        form = TestimonialForm(data=form_data)
        assert not form.is_valid()
        assert 'content' in form.errors
    
    def test_rating_range(self):
        """Test rating range validation."""
        # Test with invalid rating (too high)
        form_data = {
            'author_name': 'Invalid Rating User',
            'content': 'This testimonial has an invalid rating.',
            'rating': 6  # Max should be 5
        }
        
        form = TestimonialForm(data=form_data)
        assert not form.is_valid()
        assert 'rating' in form.errors
        
        # Test with invalid rating (too low)
        form_data['rating'] = 0
        form = TestimonialForm(data=form_data)
        assert not form.is_valid()
        assert 'rating' in form.errors
    
    def test_user_initial_values(self, user):
        """Test that form is initialized with user data."""
        form = TestimonialForm(user=user)
        
        assert form.fields['author_name'].initial == user.username
        assert form.fields['author_email'].initial == user.email
    
    def test_status_hidden_for_non_staff(self, user):
        """Test that status field is hidden for non-staff users."""
        form = TestimonialForm(user=user)
        
        # Status field should be a HiddenInput for non-staff users
        assert form.fields['status'].widget.__class__.__name__ == 'HiddenInput'
        assert form.fields['status'].initial == TestimonialStatus.PENDING
    
    def test_save_method(self, user, category):
        """Test the form's save method."""
        form_data = {
            'author_name': 'Save Method User',
            'content': 'This testimonial tests the save method.',
            'rating': 5,
            'category': category.id,
            'is_anonymous': False
        }
        
        form = TestimonialForm(data=form_data, user=user)
        assert form.is_valid()
        
        # Save the form
        testimonial = form.save()
        
        # Check that author was set to the user
        assert testimonial.author == user
        
        # Check that status was set based on settings (default is PENDING)
        assert testimonial.status == TestimonialStatus.PENDING


@pytest.mark.django_db
class TestTestimonialAdminForm:
    """Tests for the TestimonialAdminForm."""
    
    def test_rejection_reason_required(self):
        """Test that rejection reason is required when status is rejected."""
        # Create a testimonial instance
        testimonial = Testimonial.objects.create(
            author_name="Admin Form Test",
            content="This testimonial tests the admin form.",
            rating=4,
            status=TestimonialStatus.APPROVED
        )
        
        # Initial form with instance
        form = TestimonialAdminForm(instance=testimonial)
        assert not form.fields['rejection_reason'].required
        
        # Change to rejected without reason
        form_data = {
            'author_name': testimonial.author_name,
            'content': testimonial.content,
            'rating': testimonial.rating,
            'status': TestimonialStatus.REJECTED,
            'rejection_reason': ''  # Empty reason
        }
        
        form = TestimonialAdminForm(data=form_data, instance=testimonial)
        assert not form.is_valid()
        assert 'rejection_reason' in form.errors


@pytest.mark.django_db
class TestTestimonialCategoryForm:
    """Tests for the TestimonialCategoryForm."""
    
    def test_valid_form(self):
        """Test that valid data passes form validation."""
        form_data = {
            'name': 'Test Category from Form',
            'description': 'This category was created via form',
            'is_active': True,
            'order': 1
        }
        
        form = TestimonialCategoryForm(data=form_data)
        assert form.is_valid()
    
    def test_auto_generate_slug(self):
        """Test that slug is auto-generated if not provided."""
        form_data = {
            'name': 'Auto Slug Category',
            'description': 'This category should have an auto-generated slug',
        }
        
        form = TestimonialCategoryForm(data=form_data)
        assert form.is_valid()
        
        # Clean method should have generated a slug
        cleaned_data = form.clean()
        assert cleaned_data['slug'] == 'auto-slug-category'
    
    def test_unique_slug(self):
        """Test that auto-generated slugs are made unique."""
        # Create a category first
        TestimonialCategory.objects.create(
            name='Duplicate',
            slug='duplicate'
        )
        
        # Now try to create another with the same name
        form_data = {
            'name': 'Duplicate',
            'description': 'This should get a unique slug',
        }
        
        form = TestimonialCategoryForm(data=form_data)
        assert form.is_valid()
        
        # Clean method should have generated a unique slug
        cleaned_data = form.clean()
        assert cleaned_data['slug'] != 'duplicate'
        assert cleaned_data['slug'] == 'duplicate-1'


@pytest.mark.django_db
class TestTestimonialMediaForm:
    """Tests for the TestimonialMediaForm."""
    
    def test_valid_form(self, testimonial, test_image):
        """Test that valid data passes form validation."""
        form_data = {
            'testimonial': testimonial.id,
            'title': 'Test Media from Form',
            'description': 'This media was uploaded via form',
            'is_primary': True,
            'order': 1
        }
        
        form_files = {
            'file': test_image
        }
        
        form = TestimonialMediaForm(data=form_data, files=form_files)
        assert form.is_valid()
    
    def test_auto_detect_media_type(self, testimonial, test_image):
        """Test that media type is auto-detected from file extension."""
        form_data = {
            'testimonial': testimonial.id,
            'title': 'Auto Type Media',
        }
        
        form_files = {
            'file': test_image
        }
        
        form = TestimonialMediaForm(data=form_data, files=form_files)
        assert form.is_valid()
        
        # Media type should be detected
        assert 'media_type' in form.cleaned_data
        assert form.cleaned_data['media_type'] == 'image'
    
    def test_file_size_validation(self, testimonial):
        """Test file size validation."""
        # Create a file that's too large
        large_file = SimpleUploadedFile(
            name='large_file.jpg',
            content=b'X' * (6 * 1024 * 1024),  # 6MB (over the 5MB limit)
            content_type='image/jpeg'
        )
        
        form_data = {
            'testimonial': testimonial.id,
            'title': 'Large File Test',
        }
        
        form_files = {
            'file': large_file
        }
        
        form = TestimonialMediaForm(data=form_data, files=form_files)
        assert not form.is_valid()
        assert 'file' in form.errors
    
    def test_file_extension_validation(self, testimonial):
        """Test file extension validation."""
        # Create a file with invalid extension
        invalid_file = SimpleUploadedFile(
            name='invalid.exe',
            content=b'Not a valid file type',
            content_type='application/octet-stream'
        )
        
        form_data = {
            'testimonial': testimonial.id,
            'title': 'Invalid File Test',
        }
        
        form_files = {
            'file': invalid_file
        }
        
        form = TestimonialMediaForm(data=form_data, files=form_files)
        assert not form.is_valid()
        assert 'file' in form.errors
    
    def test_testimonial_from_constructor(self, testimonial, test_image):
        """Test passing testimonial through constructor."""
        form_data = {
            'title': 'Constructor Test',
        }
        
        form_files = {
            'file': test_image
        }
        
        # Pass testimonial via constructor
        form = TestimonialMediaForm(
            data=form_data,
            files=form_files,
            testimonial=testimonial
        )
        
        assert form.is_valid()
        
        # Check that the testimonial was set correctly
        assert form.cleaned_data['testimonial'] == testimonial


@pytest.mark.django_db
class TestPublicTestimonialForm:
    """Tests for the PublicTestimonialForm."""
    
    def test_simplified_fields(self):
        """Test that the form has simplified fields for public use."""
        form = PublicTestimonialForm()
        
        # Status and source should be hidden
        assert form.fields['status'].widget.__class__.__name__ == 'HiddenInput'
        assert form.fields['source'].widget.__class__.__name__ == 'HiddenInput'
        
        # Required fields check
        assert form.fields['author_name'].required is True
        assert form.fields['content'].required is True
        assert form.fields['rating'].required is True
        
        # Optional fields check
        assert form.fields['author_email'].required is False
        assert form.fields['author_phone'].required is False
    
    def test_valid_public_submission(self, category):
        """Test a valid public testimonial submission."""
        form_data = {
            'author_name': 'Public User',
            'content': 'This is a public testimonial submission with sufficient length.',
            'rating': 5,
            'category': category.id
        }
        
        form = PublicTestimonialForm(data=form_data)
        assert form.is_valid()
    
    def test_privacy_consent_field(self):
        """Test the privacy consent field when required."""
        # Mock the settings to require privacy consent
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('testimonials.forms.settings.TESTIMONIALS_REQUIRE_PRIVACY_CONSENT', True)
            
            # Create form - should now have privacy_consent field
            form = PublicTestimonialForm()
            assert 'privacy_consent' in form.fields
            assert form.fields['privacy_consent'].required is True
            
            # Test submission without consent
            form_data = {
                'author_name': 'Privacy Test User',
                'content': 'This testimonial tests privacy consent requirement.',
                'rating': 4,
                # Missing privacy_consent field
            }
            
            form = PublicTestimonialForm(data=form_data)
            assert not form.is_valid()
            assert 'privacy_consent' in form.errors


@pytest.mark.django_db
class TestTestimonialFilterForm:
    """Tests for the TestimonialFilterForm."""
    
    def test_filter_form_fields(self):
        """Test that the filter form has all expected fields."""
        form = TestimonialFilterForm()
        
        expected_fields = [
            'status', 'category', 'min_rating', 'max_rating',
            'date_from', 'date_to', 'search'
        ]
        
        for field in expected_fields:
            assert field in form.fields
    
    def test_status_choices(self):
        """Test that status field has all status choices plus empty option."""
        form = TestimonialFilterForm()
        
        # Should have empty choice plus all statuses
        assert len(form.fields['status'].choices) == len(TestimonialStatus.choices) + 1
        
        # First choice should be empty
        assert form.fields['status'].choices[0][0] == ''
    
    def test_date_fields(self):
        """Test date field widgets."""
        form = TestimonialFilterForm()
        
        # Date fields should use date input widgets
        assert form.fields['date_from'].widget.input_type == 'date'
        assert form.fields['date_to'].widget.input_type == 'date'
    
    def test_rating_range_validation(self):
        """Test validation of min/max rating fields."""
        # Valid range
        form_data = {
            'min_rating': 2,
            'max_rating': 4
        }
        
        form = TestimonialFilterForm(data=form_data)
        assert form.is_valid()
        
        # Invalid min rating (too low)
        form_data = {
            'min_rating': 0,  # Should be at least 1
            'max_rating': 4
        }
        
        form = TestimonialFilterForm(data=form_data)
        assert not form.is_valid()
        assert 'min_rating' in form.errors
        
        # Invalid max rating (too high)
        form_data = {
            'min_rating': 2,
            'max_rating': 6  # Should be at most 5
        }
        
        form = TestimonialFilterForm(data=form_data)
        assert not form.is_valid()
        assert 'max_rating' in form.errors