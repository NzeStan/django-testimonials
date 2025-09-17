from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings  # Import settings for the PublicTestimonialForm
from .models import Testimonial, TestimonialCategory, TestimonialMedia
from .constants import TestimonialStatus, TestimonialSource
from .fields import RatingField, StatusField, SourceField, StarRatingWidget
from .conf import app_settings


class TestimonialForm(forms.ModelForm):
    """
    Form for creating and editing testimonials.
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
        
        # Set initial values based on user
        if self.user and self.user.is_authenticated and not self.instance.pk:
            self.fields['author_name'].initial = getattr(self.user, 'get_full_name', lambda: self.user.username)()
            if hasattr(self.user, 'email'):
                self.fields['author_email'].initial = self.user.email
        
        # Hide status field for non-staff users
        if not (self.user and self.user.is_staff):
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].initial = TestimonialStatus.DEFAULT
        
        # Hide source field for non-staff users
        if not (self.user and self.user.is_staff):
            self.fields['source'].widget = forms.HiddenInput()
            self.fields['source'].initial = TestimonialSource.DEFAULT
        
        # Make category field more user-friendly
        if 'category' in self.fields:
            self.fields['category'].queryset = TestimonialCategory.objects.active()
            self.fields['category'].empty_label = _("No category")
            self.fields['category'].required = False
        
        # Adjust required fields
        if not app_settings.ALLOW_ANONYMOUS:
            self.fields['is_anonymous'].widget = forms.HiddenInput()
            self.fields['is_anonymous'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        is_anonymous = cleaned_data.get('is_anonymous')
        
        # Validate anonymous testimonials
        if is_anonymous and not app_settings.ALLOW_ANONYMOUS:
            raise ValidationError(_("Anonymous testimonials are not allowed."))
        
        # Validate user is authenticated for non-anonymous testimonials if required
        if not is_anonymous and not app_settings.ALLOW_ANONYMOUS and not self.user:
            raise ValidationError(_("You must be logged in to submit a testimonial."))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the author if the user is authenticated
        if self.user and self.user.is_authenticated and not instance.author:
            instance.author = self.user
        
        # Set status based on settings
        if not instance.status:
            if app_settings.REQUIRE_APPROVAL:
                instance.status = TestimonialStatus.PENDING
            else:
                instance.status = TestimonialStatus.APPROVED
        
        if commit:
            instance.save()
        
        return instance


class TestimonialAdminForm(forms.ModelForm):
    """
    Form for testimonial administration.
    Extends the basic form with additional admin-specific fields.
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
        
        # Require rejection reason when status is rejected
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
            if TestimonialCategory.objects.filter(slug=slug).exists():
                count = 1
                while TestimonialCategory.objects.filter(slug=f"{slug}-{count}").exists():
                    count += 1
                slug = f"{slug}-{count}"
        
        return slug


class TestimonialMediaForm(forms.ModelForm):
    """
    Form for testimonial media.
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
        file_obj = self.cleaned_data.get('file')
        
        # Validate file size
        max_size_mb = 5  # 5MB limit
        if file_obj and file_obj.size > max_size_mb * 1024 * 1024:
            raise ValidationError(
                _("File size exceeds the limit of %(max)s MB."),
                params={'max': max_size_mb}
            )
        
        # Validate file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mov', 'mp3', 'wav', 'ogg', 'pdf']
        ext = file_obj.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                _("File type not allowed. Allowed types: %(types)s"),
                params={'types': ', '.join(allowed_extensions)}
            )
        
        return file_obj
    
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


class PublicTestimonialForm(TestimonialForm):
    """
    Simplified form for public testimonial submission.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove admin-only fields
        for field in ['status', 'source']:
            if field in self.fields:
                self.fields[field].widget = forms.HiddenInput()
        
        # Make certain fields required
        self.fields['author_name'].required = True
        self.fields['content'].required = True
        self.fields['rating'].required = True
        
        # Make certain fields optional
        self.fields['author_email'].required = False
        self.fields['author_phone'].required = False
        
        # Add privacy consent if needed
        if getattr(settings, 'TESTIMONIALS_REQUIRE_PRIVACY_CONSENT', False):
            self.fields['privacy_consent'] = forms.BooleanField(
                required=True,
                label=_("I consent to the storage and processing of my personal data."),
                error_messages={
                    'required': _("You must consent to the privacy policy to submit a testimonial.")
                }
            )


class TestimonialFilterForm(forms.Form):
    """
    Form for filtering testimonials in the admin interface.
    """
    status = forms.ChoiceField(
        choices=[('', _('All Statuses'))] + list(TestimonialStatus.CHOICES),
        required=False
    )
    
    category = forms.ModelChoiceField(
        queryset=TestimonialCategory.objects.all(),
        required=False,
        empty_label=_('All Categories')
    )
    
    min_rating = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=app_settings.MAX_RATING,
        label=_('Minimum Rating')
    )
    
    max_rating = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=app_settings.MAX_RATING,
        label=_('Maximum Rating')
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label=_('Date From')
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label=_('Date To')
    )
    
    search = forms.CharField(
        required=False,
        label=_('Search'),
        widget=forms.TextInput(attrs={'placeholder': _('Search testimonials...')})
    )


