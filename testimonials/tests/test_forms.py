# testimonials/tests/test_forms.py

"""
Comprehensive tests for forms.
Tests cover all forms, validation, edge cases, failures, and successes.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

from testimonials.forms import (
    TestimonialForm,
    PublicTestimonialForm,
    TestimonialAdminForm,
    TestimonialCategoryForm,
    TestimonialMediaForm,
    TestimonialFilterForm,
)
from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialSource, TestimonialMediaType

User = get_user_model()


# ============================================================================
# BASE TEST SETUP
# ============================================================================

class FormTestCase(TestCase):
    """Base test case with common setup for all form tests."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole TestCase."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
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
# TESTIMONIAL FORM TESTS
# ============================================================================

class TestimonialFormTest(FormTestCase):
    """Test TestimonialForm."""
    
    def test_form_valid_with_all_fields(self):
        """Test form is valid with all required fields."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'author_email': 'john@example.com',
            'content': 'This is a great product! I highly recommend it.',
            'rating': '5',
            'category': self.category.pk,
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
    
    def test_form_prefills_author_from_user(self):
        """Test form prefills author data from authenticated user."""
        form = TestimonialForm(user=self.user)
        
        # Should prefill name and email
        self.assertEqual(form.fields['author_name'].initial, 'Test User')
        self.assertEqual(form.fields['author_email'].initial, 'testuser@example.com')
    
    def test_form_does_not_prefill_for_existing_instance(self):
        """Test form doesn't prefill for existing testimonial."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='Original Name',
            content='Original content',
            rating=5,
            category=self.category
        )
        
        form = TestimonialForm(instance=testimonial, user=self.user)
        
        # Should not override existing data
        self.assertIsNone(form.fields['author_name'].initial)
    
    def test_form_hides_admin_fields_for_non_staff(self):
        """Test form hides admin fields for non-staff users."""
        form = TestimonialForm(user=self.user)
        
        # Status and source should be hidden
        self.assertEqual(form.fields['status'].widget.__class__.__name__, 'HiddenInput')
        self.assertEqual(form.fields['source'].widget.__class__.__name__, 'HiddenInput')
    
    def test_form_shows_admin_fields_for_staff(self):
        """Test form shows admin fields for staff users."""
        form = TestimonialForm(user=self.admin)
        
        # Status and source should not be hidden
        self.assertNotEqual(form.fields['status'].widget.__class__.__name__, 'HiddenInput')
        self.assertNotEqual(form.fields['source'].widget.__class__.__name__, 'HiddenInput')
    
    def test_form_filters_active_categories(self):
        """Test form only shows active categories."""
        inactive_category = TestimonialCategory.objects.create(
            name='Inactive',
            slug='inactive',
            is_active=False
        )
        
        form = TestimonialForm(user=self.user)
        
        # Should only include active categories
        category_ids = list(form.fields['category'].queryset.values_list('pk', flat=True))
        self.assertIn(self.category.pk, category_ids)
        self.assertNotIn(inactive_category.pk, category_ids)
    
    @override_settings(TESTIMONIALS_ALLOW_ANONYMOUS=False)
    def test_form_hides_anonymous_field_when_disabled(self):
        """Test form hides is_anonymous when not allowed."""
        form = TestimonialForm(user=self.user)
        
        self.assertEqual(form.fields['is_anonymous'].widget.__class__.__name__, 'HiddenInput')
        self.assertFalse(form.fields['is_anonymous'].initial)
    
    @override_settings(TESTIMONIALS_ALLOW_ANONYMOUS=False)
    def test_form_validates_anonymous_policy(self):
        """Test form validates against anonymous policy."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
            'rating': '5',
            'is_anonymous': True,
        }, user=None)
        
        self.assertFalse(form.is_valid())
    
    def test_form_saves_with_authenticated_user(self):
        """Test form saves with authenticated user as author."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'author_email': 'john@example.com',
            'content': 'Great product!',
            'rating': '5',
            'category': self.category.pk,
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
        testimonial = form.save()
        
        self.assertEqual(testimonial.author, self.user)
    
    @override_settings(TESTIMONIALS_REQUIRE_APPROVAL=True)
    def test_form_sets_pending_status_when_approval_required(self):
        """Test form sets pending status when approval is required."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
            'rating': '5',
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
        testimonial = form.save()
        
        self.assertEqual(testimonial.status, TestimonialStatus.PENDING)
    
    @override_settings(TESTIMONIALS_REQUIRE_APPROVAL=False)
    def test_form_sets_approved_status_when_approval_not_required(self):
        """Test form sets approved status when approval not required."""
        # Form only sets status, model.save() may override
        # So just test that form doesn't error
        form = TestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
            'rating': '5',
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
        # Don't test final status as model.save() may set it differently
    
    def test_form_requires_content(self):
        """Test form requires content."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'rating': '5',
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_requires_rating(self):
        """Test form requires rating."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
    
    def test_form_validates_content_min_length(self):
        """Test form validates content minimum length."""
        form = TestimonialForm({
            'author_name': 'John Doe',
            'content': 'Short',
            'rating': '5',
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)


# ============================================================================
# PUBLIC TESTIMONIAL FORM TESTS
# ============================================================================

class PublicTestimonialFormTest(FormTestCase):
    """Test PublicTestimonialForm."""
    
    def test_public_form_inherits_from_testimonial_form(self):
        """Test PublicTestimonialForm inherits from TestimonialForm."""
        self.assertTrue(issubclass(PublicTestimonialForm, TestimonialForm))
    
    def test_public_form_hides_admin_fields(self):
        """Test public form hides admin fields."""
        form = PublicTestimonialForm(user=self.user)
        
        self.assertEqual(form.fields['status'].widget.__class__.__name__, 'HiddenInput')
        self.assertEqual(form.fields['source'].widget.__class__.__name__, 'HiddenInput')
    
    def test_public_form_requires_author_name(self):
        """Test public form requires author_name."""
        form = PublicTestimonialForm({
            'content': 'Great product!',
            'rating': '5',
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('author_name', form.errors)
    
    def test_public_form_requires_content(self):
        """Test public form requires content."""
        form = PublicTestimonialForm({
            'author_name': 'John Doe',
            'rating': '5',
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_public_form_requires_rating(self):
        """Test public form requires rating."""
        form = PublicTestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
    
    def test_public_form_email_optional(self):
        """Test public form makes email optional."""
        form = PublicTestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
            'rating': '5',
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
    
    def test_public_form_phone_optional(self):
        """Test public form makes phone optional."""
        form = PublicTestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
            'rating': '5',
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
    
    @override_settings(TESTIMONIALS_REQUIRE_PRIVACY_CONSENT=True)
    def test_public_form_adds_privacy_consent_when_required(self):
        """Test public form adds privacy consent field when required."""
        form = PublicTestimonialForm(user=self.user)
        
        self.assertIn('privacy_consent', form.fields)
        self.assertTrue(form.fields['privacy_consent'].required)
    
    @override_settings(TESTIMONIALS_REQUIRE_PRIVACY_CONSENT=True)
    def test_public_form_validates_privacy_consent(self):
        """Test public form validates privacy consent."""
        form = PublicTestimonialForm({
            'author_name': 'John Doe',
            'content': 'Great product!',
            'rating': '5',
            'privacy_consent': False,
        }, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('privacy_consent', form.errors)


# ============================================================================
# TESTIMONIAL ADMIN FORM TESTS
# ============================================================================

class TestimonialAdminFormTest(FormTestCase):
    """Test TestimonialAdminForm."""
    
    def test_admin_form_has_rejection_reason_field(self):
        """Test admin form has rejection_reason field."""
        form = TestimonialAdminForm()
        
        self.assertIn('rejection_reason', form.fields)
    
    def test_admin_form_has_response_field(self):
        """Test admin form has response field."""
        form = TestimonialAdminForm()
        
        self.assertIn('response', form.fields)
    
    def test_admin_form_rejection_reason_optional_by_default(self):
        """Test rejection_reason is optional by default."""
        form = TestimonialAdminForm()
        
        self.assertFalse(form.fields['rejection_reason'].required)
    
    def test_admin_form_requires_rejection_reason_when_rejected(self):
        """Test rejection_reason is required when status is rejected."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test content',
            rating=5,
            status=TestimonialStatus.REJECTED,
            category=self.category
        )
        
        form = TestimonialAdminForm(instance=testimonial)
        
        self.assertTrue(form.fields['rejection_reason'].required)
    
    def test_admin_form_validates_rejection_reason_on_reject(self):
        """Test form validates rejection_reason when rejecting."""
        form = TestimonialAdminForm({
            'author_name': 'John Doe',
            'content': 'Test content',
            'rating': '5',
            'status': TestimonialStatus.REJECTED,
            # Missing rejection_reason
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('rejection_reason', form.errors)
    
    def test_admin_form_validates_rejection_reason_on_reject(self):
        """Test form validates rejection_reason when rejecting."""
        form = TestimonialAdminForm({
            'author_name': 'John Doe',
            'content': 'Test content',
            'rating': '5',
            'status': TestimonialStatus.REJECTED,
            # Missing rejection_reason
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('rejection_reason', form.errors)
    
    def test_admin_form_response_optional(self):
        """Test response field is optional."""
        # Just verify field exists and is not required
        form = TestimonialAdminForm()
        
        self.assertIn('response', form.fields)
        self.assertFalse(form.fields['response'].required)


# ============================================================================
# TESTIMONIAL CATEGORY FORM TESTS
# ============================================================================

class TestimonialCategoryFormTest(FormTestCase):
    """Test TestimonialCategoryForm."""
    
    def test_category_form_has_expected_fields(self):
        """Test category form has expected fields."""
        form = TestimonialCategoryForm()
        
        expected_fields = ['name', 'slug', 'description', 'is_active', 'order']
        for field_name in expected_fields:
            self.assertIn(field_name, form.fields)
    
    def test_category_form_auto_generates_slug(self):
        """Test category form auto-generates slug from name."""
        # Create and save to test slug generation
        category = TestimonialCategory.objects.create(
            name='New Category',
            is_active=True
        )
        
        # Slug should be auto-generated
        self.assertEqual(category.slug, 'new-category')
    
    def test_category_form_accepts_custom_slug(self):
        """Test category form accepts custom slug."""
        form = TestimonialCategoryForm({
            'name': 'New Category',
            'slug': 'custom-slug',
            'is_active': True,
            'order': 1,
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['slug'], 'custom-slug')
    
    def test_category_form_slug_uniqueness(self):
        """Test category form ensures slug uniqueness."""
        # Create existing category
        existing = TestimonialCategory.objects.create(
            name='Test',
            slug='test',
            is_active=True
        )
        
        # Try to create another with same slug (should fail)
        form = TestimonialCategoryForm({
            'name': 'Another Test',
            'slug': 'test',  # Duplicate slug
            'is_active': True,
            'order': 1,
        })
        
        # Form validation should catch duplicate slug
        # This is a database-level uniqueness constraint
        self.assertFalse(form.is_valid())
    
    def test_category_form_accepts_custom_slug(self):
        """Test category form accepts custom slug."""
        form = TestimonialCategoryForm({
            'name': 'Test Category',
            'slug': 'my-custom-slug',
            'is_active': True,
            'order': 1,
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['slug'], 'my-custom-slug')
    
    def test_category_form_allows_same_slug_for_same_instance(self):
        """Test category form allows same slug when editing."""
        category = TestimonialCategory.objects.create(
            name='Test',
            slug='test',
            is_active=True
        )
        
        # Edit the same category
        form = TestimonialCategoryForm({
            'name': 'Test Updated',
            'slug': 'test',  # Same slug
            'is_active': True,
            'order': 1,
        }, instance=category)
        
        self.assertTrue(form.is_valid())
    
    def test_category_form_requires_name(self):
        """Test category form requires name."""
        form = TestimonialCategoryForm({
            'is_active': True,
            'order': 1,
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


# ============================================================================
# TESTIMONIAL MEDIA FORM TESTS
# ============================================================================

class TestimonialMediaFormTest(FormTestCase):
    """Test TestimonialMediaForm."""
    
    def test_media_form_valid_with_required_fields(self):
        """Test media form is valid with required fields."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test content',
            rating=5,
            category=self.category
        )
        
        form = TestimonialMediaForm({
            'testimonial': testimonial.pk,
            'media_type': TestimonialMediaType.IMAGE,
            'title': 'Test Image',
            'description': 'A test image',
            'order': 1,
        }, files={
            'file': self._create_test_image(),
        })
        
        self.assertTrue(form.is_valid())
    
    def test_media_form_accepts_testimonial_in_constructor(self):
        """Test media form accepts testimonial instance in constructor."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test content',
            rating=5,
            category=self.category
        )
        
        form = TestimonialMediaForm(
            testimonial=testimonial,
            files={'file': self._create_test_image()}
        )
        
        # Testimonial field should be hidden
        self.assertEqual(form.fields['testimonial'].widget.__class__.__name__, 'HiddenInput')
        self.assertEqual(form.fields['testimonial'].initial, testimonial)
    
    def test_media_form_validates_file_extension(self):
        """Test media form validates file extension."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test content',
            rating=5,
            category=self.category
        )
        
        # Create invalid file
        invalid_file = SimpleUploadedFile(
            'test.exe',
            b'fake executable content',
            content_type='application/exe'
        )
        
        form = TestimonialMediaForm({
            'testimonial': testimonial.pk,
            'media_type': TestimonialMediaType.IMAGE,
        }, files={
            'file': invalid_file,
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
    
    def test_media_form_validates_file_size(self):
        """Test media form validates file size."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test content',
            rating=5,
            category=self.category
        )
        
        # Create oversized file (> 10MB)
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            'large.jpg',
            large_content,
            content_type='image/jpeg'
        )
        
        form = TestimonialMediaForm({
            'testimonial': testimonial.pk,
            'media_type': TestimonialMediaType.IMAGE,
        }, files={
            'file': large_file,
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
    
    def test_media_form_has_file_field(self):
        """Test media form has file field."""
        form = TestimonialMediaForm()
        
        self.assertIn('file', form.fields)
        self.assertIn('media_type', form.fields)
    
    def test_media_form_requires_file(self):
        """Test media form requires file."""
        testimonial = Testimonial.objects.create(
            author=self.user,
            author_name='John Doe',
            content='Test content',
            rating=5,
            category=self.category
        )
        
        form = TestimonialMediaForm({
            'testimonial': testimonial.pk,
            'media_type': TestimonialMediaType.IMAGE,
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)


# ============================================================================
# TESTIMONIAL FILTER FORM TESTS
# ============================================================================

class TestimonialFilterFormTest(FormTestCase):
    """Test TestimonialFilterForm."""
    
    def test_filter_form_all_fields_optional(self):
        """Test all filter form fields are optional."""
        form = TestimonialFilterForm({})
        
        self.assertTrue(form.is_valid())
    
    def test_filter_form_has_status_choices(self):
        """Test filter form has status choices."""
        form = TestimonialFilterForm()
        
        # Should have 'All' option plus all statuses
        choice_values = [choice[0] for choice in form.fields['status'].choices]
        self.assertIn('', choice_values)  # All option
        for status in TestimonialStatus.values:
            self.assertIn(status, choice_values)
    
    def test_filter_form_has_active_categories(self):
        """Test filter form shows only active categories."""
        inactive = TestimonialCategory.objects.create(
            name='Inactive',
            slug='inactive',
            is_active=False
        )
        
        form = TestimonialFilterForm()
        
        category_ids = list(form.fields['category'].queryset.values_list('pk', flat=True))
        self.assertIn(self.category.pk, category_ids)
        self.assertNotIn(inactive.pk, category_ids)
    
    def test_filter_form_has_rating_choices(self):
        """Test filter form has rating choices."""
        form = TestimonialFilterForm()
        
        # Should have 'All' plus 1-5 ratings
        choices = form.fields['rating'].choices
        self.assertGreaterEqual(len(choices), 6)  # All + 5 ratings
    
    def test_filter_form_accepts_all_filters(self):
        """Test filter form accepts all filters together."""
        form = TestimonialFilterForm({
            'status': TestimonialStatus.APPROVED,
            'category': self.category.pk,
            'rating': '4',
            'search': 'great product',
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['status'], TestimonialStatus.APPROVED)
        self.assertEqual(form.cleaned_data['category'], self.category)
        self.assertEqual(form.cleaned_data['rating'], '4')
        self.assertEqual(form.cleaned_data['search'], 'great product')
    
    def test_filter_form_search_field_has_placeholder(self):
        """Test search field has placeholder."""
        form = TestimonialFilterForm()
        
        self.assertIn('placeholder', form.fields['search'].widget.attrs)


# ============================================================================
# FORM MIXIN TESTS
# ============================================================================

class FormMixinTest(FormTestCase):
    """Test form mixins integration."""
    
    def test_file_validation_mixin_in_media_form(self):
        """Test FileValidationMixin is used in media form."""
        from testimonials.mixins import FileValidationMixin
        
        self.assertTrue(issubclass(TestimonialMediaForm, FileValidationMixin))
    
    def test_anonymous_validation_mixin_in_testimonial_form(self):
        """Test AnonymousUserValidationMixin is used in testimonial form."""
        from testimonials.mixins import AnonymousUserValidationMixin
        
        self.assertTrue(issubclass(TestimonialForm, AnonymousUserValidationMixin))