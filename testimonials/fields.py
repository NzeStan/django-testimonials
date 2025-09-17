from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .constants import TestimonialStatus, TestimonialSource
from .conf import app_settings


class RatingField(forms.IntegerField):
    """
    Custom field for testimonial ratings.
    
    Ensures that the rating is within the configured range.
    """
    
    def __init__(self, *args, **kwargs):
        self.max_rating = kwargs.pop('max_rating', app_settings.MAX_RATING)
        kwargs.setdefault('min_value', 1)
        kwargs.setdefault('max_value', self.max_rating)
        kwargs.setdefault('widget', forms.NumberInput(attrs={'class': 'rating-input'}))
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        super().validate(value)
        if value is not None and (value < 1 or value > self.max_rating):
            raise ValidationError(
                _('Rating must be between 1 and %(max)s.'),
                params={'max': self.max_rating},
                code='invalid_rating'
            )


class StatusField(forms.ChoiceField):
    """
    Custom field for testimonial status.
    
    Uses the defined status choices.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('choices', TestimonialStatus.CHOICES)
        kwargs.setdefault('initial', TestimonialStatus.DEFAULT)
        super().__init__(*args, **kwargs)


class SourceField(forms.ChoiceField):
    """
    Custom field for testimonial source.
    
    Uses the defined source choices.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('choices', TestimonialSource.CHOICES)
        kwargs.setdefault('initial', TestimonialSource.DEFAULT)
        super().__init__(*args, **kwargs)


class StarRatingWidget(forms.RadioSelect):
    """
    Custom widget for star ratings.
    
    Renders as a series of star icons.
    """
    template_name = 'testimonials/widgets/star_rating.html'
    
    def __init__(self, attrs=None, max_rating=None):
        self.max_rating = max_rating or app_settings.MAX_RATING
        choices = [(i, str(i)) for i in range(1, self.max_rating + 1)]
        super().__init__(attrs, choices)
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['max_rating'] = self.max_rating
        return context


class TestimonialContentField(forms.CharField):
    """
    Custom field for testimonial content.
    
    Validates that the content meets minimum length requirements.
    """
    
    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.pop('min_length', 10)
        kwargs.setdefault('widget', forms.Textarea(attrs={'rows': 4, 'class': 'testimonial-content'}))
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        super().validate(value)
        if value and len(value) < self.min_length:
            raise ValidationError(
                _('Content must be at least %(min)s characters long.'),
                params={'min': self.min_length},
                code='content_too_short'
            )


class JSONField(forms.CharField):
    """
    Custom field for JSON data.
    
    Validates that the input is valid JSON.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.Textarea(attrs={'rows': 4, 'class': 'json-field'}))
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        import json
        
        if not value:
            return {}
        
        if isinstance(value, dict):
            return value
        
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            raise ValidationError(_('Invalid JSON format.'), code='invalid_json')
    
    def prepare_value(self, value):
        import json
        
        if not value:
            return ''
        
        if isinstance(value, str):
            return value
        
        try:
            return json.dumps(value, indent=2)
        except (ValueError, TypeError):
            return value