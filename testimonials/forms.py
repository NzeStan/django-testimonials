# testimonials/forms.py - REFACTORED

"""
Refactored forms using validation mixins to eliminate duplication.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import Testimonial, TestimonialCategory, TestimonialMedia
from .constants import TestimonialStatus, TestimonialSource
from .fields import RatingField, StatusField, SourceField, StarRatingWidget
from .conf import app_settings

# Import validation mixin
from .mixins import FileValidationMixin, AnonymousUserValidationMixin


class TestimonialForm(AnonymousUserValidationMixin, forms.ModelForm):
    """
    Form for creating and editing testimonials.
    Uses AnonymousUserValidationMixin for validation.
    """
    rating = RatingField(
        max_rating=app_settings.MAX_RATING,
        widget=StarRatingWidget(max_rating=app_settings.MAX_RATING),
        help_text=_("Rate your experience from 1 to %(max)s.") % {'max': app_settings.MAX_RATING}
    )
    
    status = StatusField(required=False)
    source = SourceField(required=False)
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'testimonial-content'}),
        min_length=10,
        help_text=_("Please share your experience in detail.")
    )
    
    class Meta:
        model = Testimonial
        fields = [
            'author_name', 'author_email', 'author_phone', 'author_title',
            'company', 'location', 'avatar', 'title', 'content', 'rating',
            'category', 'source', 'status', 'is_anonymous', 'website', 'social_media'
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Prefill from user using mixin method
        if self.user and self.user.is_authenticated and not self.instance.pk:
            initial_data = {}
            initial_data = self.prefill_author_from_user(initial_data, self.user)
            self.fields['author_name'].initial = initial_data.get('author_name')
            self.fields['author_email'].initial = initial_data.get('author_email')
        
        # Hide admin fields for non-staff
        if not (self.user and self.user.is_staff):
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].initial = TestimonialStatus.PENDING
            self.fields['source'].widget = forms.HiddenInput()
            self.fields['source'].initial = TestimonialSource.WEBSITE
        
        # Configure category field
        if 'category' in self.fields:
            self.fields['category'].queryset = TestimonialCategory.objects.active()
            self.fields['category'].empty_label = _("No category")
            self.fields['category'].required = False
        
        # Handle anonymous setting
        if not app_settings.ALLOW_ANONYMOUS:
            self.fields['is_anonymous'].widget = forms.HiddenInput()
            self.fields['is_anonymous'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        is_anonymous = cleaned_data.get('is_anonymous', False)
        
        # Validate anonymous policy using mixin
        try:
            self.validate_anonymous_policy(is_anonymous, app_settings.ALLOW_ANONYMOUS)
        except Exception as e:
            raise ValidationError(str(e))
        
        # Validate authenticated requirement
        if not is_anonymous and not app_settings.ALLOW_ANONYMOUS and not self.user:
            raise ValidationError(_("You must be logged in to submit a testimonial."))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set author if authenticated
        if self.user and self.user.is_authenticated and not instance.author:
            instance.author = self.user
        
        # Set default status
        if not instance.status:
            instance.status = (
                TestimonialStatus.PENDING if app_settings.REQUIRE_APPROVAL
                else TestimonialStatus.APPROVED
            )
        
        if commit:
            instance.save()
        
        return instance


class PublicTestimonialForm(TestimonialForm):
    """
    Simplified form for public testimonial submission.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hide admin-only fields
        for field in ['status', 'source']:
            if field in self.fields:
                self.fields[field].widget = forms.HiddenInput()
        
        # Required fields for public
        self.fields['author_name'].required = True
        self.fields['content'].required = True
        self.fields['rating'].required = True
        
        # Optional fields
        self.fields['author_email'].required = False
        self.fields['author_phone'].required = False
        
        # Privacy consent if required
        if getattr(settings, 'TESTIMONIALS_REQUIRE_PRIVACY_CONSENT', False):
            self.fields['privacy_consent'] = forms.BooleanField(
                required=True,
                label=_("I consent to the storage and processing of my personal data."),
                error_messages={
                    'required': _("You must consent to the privacy policy to submit a testimonial.")
                }
            )


class TestimonialAdminForm(forms.ModelForm):
    """
    Form for testimonial administration.
    """
    
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text=_("Provide a reason if you're rejecting this testimonial.")
    )
    
    response = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text=_("Optional response to this testimonial.")
    )
    
    class Meta:
        model = Testimonial
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make rejection reason required when status is rejected
        if self.instance.status == TestimonialStatus.REJECTED:
            self.fields['rejection_reason'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        # Require rejection reason when rejecting
        if status == TestimonialStatus.REJECTED and not rejection_reason:
            self.add_error('rejection_reason', _("Please provide a reason for rejection."))
        
        return cleaned_data


class TestimonialCategoryForm(forms.ModelForm):
    """
    Form for testimonial categories.
    """
    
    class Meta:
        model = TestimonialCategory
        fields = ['name', 'slug', 'description', 'is_active', 'order']
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        
        # Auto-generate slug if not provided
        if not slug and 'name' in self.cleaned_data:
            from django.utils.text import slugify
            slug = slugify(self.cleaned_data['name'])
            
            # Check for uniqueness
            if TestimonialCategory.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
                count = 1
                while TestimonialCategory.objects.filter(slug=f"{slug}-{count}").exists():
                    count += 1
                slug = f"{slug}-{count}"
        
        return slug


class TestimonialMediaForm(FileValidationMixin, forms.ModelForm):
    """
    Form for testimonial media.
    Uses FileValidationMixin for file validation.
    """
    
    class Meta:
        model = TestimonialMedia
        fields = ['testimonial', 'file', 'media_type', 'title', 'description', 'is_primary', 'order']
    
    def __init__(self, *args, **kwargs):
        self.testimonial_instance = kwargs.pop('testimonial', None)
        super().__init__(*args, **kwargs)
        
        # Set testimonial if provided
        if self.testimonial_instance:
            self.fields['testimonial'].initial = self.testimonial_instance
            self.fields['testimonial'].widget = forms.HiddenInput()
    
    def clean_file(self):
        """
        Validate file using mixin method.
        Much cleaner than duplicated validation!
        """
        file_obj = self.cleaned_data.get('file')
        
        if not file_obj:
            return file_obj
        
        # Use mixin for validation
        allowed_extensions = app_settings.ALLOWED_FILE_EXTENSIONS
        max_size = app_settings.MAX_FILE_SIZE
        
        try:
            return self.validate_uploaded_file(file_obj, allowed_extensions, max_size)
        except Exception as e:
            raise ValidationError(str(e))
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Set testimonial if provided in constructor
        if self.testimonial_instance and 'testimonial' not in cleaned_data:
            cleaned_data['testimonial'] = self.testimonial_instance
        
        # Auto-detect media type if not provided
        if 'file' in cleaned_data and not cleaned_data.get('media_type'):
            from .utils import get_file_type
            cleaned_data['media_type'] = get_file_type(cleaned_data['file'])
        
        return cleaned_data


class TestimonialFilterForm(forms.Form):
    """
    Form for filtering testimonials in the admin interface.
    """
    
    status = forms.ChoiceField(
        choices=[('', _('All'))] + list(TestimonialStatus.choices),
        required=False,
        label=_("Status")
    )
    
    category = forms.ModelChoiceField(
        queryset=TestimonialCategory.objects.active(),
        required=False,
        empty_label=_("All categories"),
        label=_("Category")
    )
    
    rating = forms.ChoiceField(
        choices=[('', _('All'))] + [(str(i), f"{i} ★") for i in range(1, app_settings.MAX_RATING + 1)],
        required=False,
        label=_("Minimum Rating")
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Search...')}),
        label=_("Search")
    )