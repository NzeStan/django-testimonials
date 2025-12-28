# testimonials/tests/test_fields.py

"""
Comprehensive tests for custom fields and widgets.
Tests cover all field types, validation, edge cases, and failures.

NOTE: These tests assume TestimonialContentField is FIXED per BUGFIX_TestimonialContentField.md
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django import forms

from testimonials.fields import (
    RatingField,
    StatusField,
    SourceField,
    StarRatingWidget,
    TestimonialContentField,
    JSONField,
)
from testimonials.constants import TestimonialStatus, TestimonialSource
from testimonials.conf import app_settings


# ============================================================================
# RATING FIELD TESTS
# ============================================================================

class RatingFieldTest(TestCase):
    """Test RatingField custom field."""
    
    def test_rating_field_creation_default(self):
        """Test RatingField creation with defaults."""
        field = RatingField()
        
        self.assertEqual(field.min_value, 1)
        self.assertEqual(field.max_value, app_settings.MAX_RATING)
        self.assertEqual(field.max_rating, app_settings.MAX_RATING)
    
    def test_rating_field_creation_custom_max(self):
        """Test RatingField creation with custom max_rating."""
        field = RatingField(max_rating=10)
        
        self.assertEqual(field.max_value, 10)
        self.assertEqual(field.max_rating, 10)
    
    def test_rating_field_valid_values(self):
        """Test RatingField accepts valid values."""
        field = RatingField(max_rating=5)
        
        for value in [1, 2, 3, 4, 5]:
            try:
                field.clean(value)
            except ValidationError:
                self.fail(f"RatingField raised ValidationError for valid value {value}")
    
    def test_rating_field_rejects_below_minimum(self):
        """Test RatingField rejects values below minimum."""
        field = RatingField(max_rating=5)
        
        with self.assertRaises(ValidationError) as context:
            field.clean(0)
        
        self.assertIn('rating', str(context.exception).lower())
    
    def test_rating_field_rejects_above_maximum(self):
        """Test RatingField rejects values above maximum."""
        field = RatingField(max_rating=5)
        
        with self.assertRaises(ValidationError) as context:
            field.clean(6)
        
        self.assertIn('rating', str(context.exception).lower())
    
    def test_rating_field_rejects_negative(self):
        """Test RatingField rejects negative values."""
        field = RatingField(max_rating=5)
        
        with self.assertRaises(ValidationError):
            field.clean(-1)
    
    def test_rating_field_rejects_zero(self):
        """Test RatingField rejects zero."""
        field = RatingField(max_rating=5)
        
        with self.assertRaises(ValidationError):
            field.clean(0)
    
    def test_rating_field_accepts_string_numbers(self):
        """Test RatingField accepts string numbers."""
        field = RatingField(max_rating=5)
        
        # Should convert and validate
        result = field.clean('3')
        self.assertEqual(result, 3)
    
    def test_rating_field_rejects_non_numeric(self):
        """Test RatingField rejects non-numeric values."""
        field = RatingField(max_rating=5)
        
        with self.assertRaises(ValidationError):
            field.clean('abc')
    
    def test_rating_field_required_validation(self):
        """Test RatingField required validation."""
        field = RatingField(required=True, max_rating=5)
        
        with self.assertRaises(ValidationError):
            field.clean(None)
    
    def test_rating_field_optional_accepts_none(self):
        """Test optional RatingField accepts None."""
        field = RatingField(required=False, max_rating=5)
        
        result = field.clean(None)
        self.assertIsNone(result)


# ============================================================================
# STATUS FIELD TESTS
# ============================================================================

class StatusFieldTest(TestCase):
    """Test StatusField custom field."""
    
    def test_status_field_has_correct_choices(self):
        """Test StatusField has all status choices."""
        field = StatusField()
        
        # Get choice values
        choice_values = [choice[0] for choice in field.choices]
        
        # Should have all status values
        for status in TestimonialStatus.values:
            self.assertIn(status, choice_values)
    
    def test_status_field_default_initial(self):
        """Test StatusField has default initial value."""
        field = StatusField()
        
        self.assertEqual(field.initial, TestimonialStatus.PENDING)
    
    def test_status_field_accepts_valid_status(self):
        """Test StatusField accepts valid status values."""
        field = StatusField()
        
        for status in TestimonialStatus.values:
            try:
                result = field.clean(status)
                self.assertEqual(result, status)
            except ValidationError:
                self.fail(f"StatusField rejected valid status: {status}")
    
    def test_status_field_rejects_invalid_status(self):
        """Test StatusField rejects invalid status."""
        field = StatusField()
        
        with self.assertRaises(ValidationError):
            field.clean('invalid_status')
    
    def test_status_field_required_by_default(self):
        """Test StatusField is required by default."""
        field = StatusField()
        
        # Default ChoiceField behavior
        self.assertTrue(field.required)
    
    def test_status_field_optional_validation(self):
        """Test StatusField can be optional."""
        field = StatusField(required=False)
        
        # Should accept empty value
        result = field.clean('')
        self.assertEqual(result, '')


# ============================================================================
# SOURCE FIELD TESTS
# ============================================================================

class SourceFieldTest(TestCase):
    """Test SourceField custom field."""
    
    def test_source_field_has_correct_choices(self):
        """Test SourceField has all source choices."""
        field = SourceField()
        
        # Get choice values
        choice_values = [choice[0] for choice in field.choices]
        
        # Should have all source values
        for source in TestimonialSource.values:
            self.assertIn(source, choice_values)
    
    def test_source_field_default_initial(self):
        """Test SourceField has default initial value."""
        field = SourceField()
        
        self.assertEqual(field.initial, TestimonialSource.WEBSITE)
    
    def test_source_field_accepts_valid_source(self):
        """Test SourceField accepts valid source values."""
        field = SourceField()
        
        for source in TestimonialSource.values:
            try:
                result = field.clean(source)
                self.assertEqual(result, source)
            except ValidationError:
                self.fail(f"SourceField rejected valid source: {source}")
    
    def test_source_field_rejects_invalid_source(self):
        """Test SourceField rejects invalid source."""
        field = SourceField()
        
        with self.assertRaises(ValidationError):
            field.clean('invalid_source')


# ============================================================================
# STAR RATING WIDGET TESTS
# ============================================================================

class StarRatingWidgetTest(TestCase):
    """Test StarRatingWidget custom widget."""
    
    def test_star_widget_creation_default(self):
        """Test StarRatingWidget creation with defaults."""
        widget = StarRatingWidget()
        
        self.assertEqual(widget.max_rating, app_settings.MAX_RATING)
        self.assertEqual(len(widget.choices), app_settings.MAX_RATING)
    
    def test_star_widget_creation_custom_max(self):
        """Test StarRatingWidget creation with custom max_rating."""
        widget = StarRatingWidget(max_rating=10)
        
        self.assertEqual(widget.max_rating, 10)
        self.assertEqual(len(widget.choices), 10)
    
    def test_star_widget_generates_correct_choices(self):
        """Test StarRatingWidget generates correct choices."""
        widget = StarRatingWidget(max_rating=5)
        
        expected_choices = [(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]
        self.assertEqual(widget.choices, expected_choices)
    
    def test_star_widget_get_context(self):
        """Test StarRatingWidget get_context includes max_rating."""
        widget = StarRatingWidget(max_rating=7)
        
        context = widget.get_context('rating', 4, {})
        
        self.assertIn('max_rating', context)
        self.assertEqual(context['max_rating'], 7)
    
    def test_star_widget_template_name(self):
        """Test StarRatingWidget has correct template."""
        widget = StarRatingWidget()
        
        self.assertEqual(widget.template_name, 'testimonials/widgets/star_rating.html')
    
    def test_star_widget_has_correct_properties(self):
        """Test StarRatingWidget has correct properties."""
        widget = StarRatingWidget(max_rating=5)
        
        # Widget is a RadioSelect with max_rating property
        self.assertEqual(widget.max_rating, 5)
        # RadioSelect widgets have choices
        self.assertEqual(len(widget.choices), 5)


# ============================================================================
# TESTIMONIAL CONTENT FIELD TESTS  
# NOTE: Requires bug fix in TestimonialContentField (see BUGFIX_TestimonialContentField.md)
# ============================================================================

class TestimonialContentFieldTest(TestCase):
    """Test TestimonialContentField custom field.
    
    NOTE: These tests require the bug fix documented in BUGFIX_TestimonialContentField.md
    """
    
    def test_content_field_default_min_length(self):
        """Test TestimonialContentField has default min_length."""
        field = TestimonialContentField()
        
        # After fix, CharField properly sets min_length
        self.assertEqual(field.min_length, 10)
    
    def test_content_field_custom_min_length(self):
        """Test TestimonialContentField with custom min_length."""
        field = TestimonialContentField(min_length=20)
        
        self.assertEqual(field.min_length, 20)
    
    def test_content_field_accepts_valid_length(self):
        """Test TestimonialContentField accepts valid length content."""
        field = TestimonialContentField(min_length=10)
        
        content = "This is a valid testimonial content."
        result = field.clean(content)
        
        self.assertEqual(result, content)
    
    def test_content_field_rejects_too_short(self):
        """Test TestimonialContentField rejects too short content."""
        field = TestimonialContentField(min_length=10)
        
        with self.assertRaises(ValidationError):
            field.clean("Short")
    
    def test_content_field_exact_min_length(self):
        """Test TestimonialContentField accepts exact min_length."""
        field = TestimonialContentField(min_length=10)
        
        content = "1234567890"  # Exactly 10 chars
        result = field.clean(content)
        
        self.assertEqual(result, content)
    
    def test_content_field_textarea_widget(self):
        """Test TestimonialContentField uses Textarea widget."""
        field = TestimonialContentField()
        
        self.assertIsInstance(field.widget, forms.Textarea)
    
    def test_content_field_widget_attributes(self):
        """Test TestimonialContentField widget has correct attributes."""
        field = TestimonialContentField()
        
        self.assertIn('testimonial-content', field.widget.attrs.get('class', ''))
        self.assertEqual(field.widget.attrs.get('rows'), 4)
    
    def test_content_field_required_validation(self):
        """Test TestimonialContentField required validation."""
        field = TestimonialContentField(required=True, min_length=10)
        
        with self.assertRaises(ValidationError):
            field.clean('')
    
    def test_content_field_optional_accepts_empty(self):
        """Test optional TestimonialContentField accepts empty."""
        field = TestimonialContentField(required=False, min_length=10)
        
        # Empty string should be accepted
        result = field.clean('')
        self.assertEqual(result, '')


# ============================================================================
# JSON FIELD TESTS
# ============================================================================

class JSONFieldTest(TestCase):
    """Test JSONField custom field."""
    
    def test_json_field_to_python_with_dict(self):
        """Test JSONField to_python with dict input."""
        field = JSONField()
        
        input_dict = {'key': 'value'}
        result = field.to_python(input_dict)
        
        self.assertEqual(result, input_dict)
    
    def test_json_field_to_python_with_valid_json_string(self):
        """Test JSONField to_python with valid JSON string."""
        field = JSONField()
        
        json_string = '{"key": "value", "number": 42}'
        result = field.to_python(json_string)
        
        self.assertEqual(result, {'key': 'value', 'number': 42})
    
    def test_json_field_to_python_with_invalid_json(self):
        """Test JSONField to_python with invalid JSON."""
        field = JSONField()
        
        with self.assertRaises(ValidationError) as context:
            field.to_python('invalid json {')
        
        self.assertIn('json', str(context.exception).lower())
    
    def test_json_field_to_python_with_empty_string(self):
        """Test JSONField to_python with empty string."""
        field = JSONField()
        
        result = field.to_python('')
        
        self.assertEqual(result, {})
    
    def test_json_field_to_python_with_none(self):
        """Test JSONField to_python with None."""
        field = JSONField()
        
        result = field.to_python(None)
        
        self.assertEqual(result, {})
    
    def test_json_field_prepare_value_with_dict(self):
        """Test JSONField prepare_value with dict."""
        field = JSONField()
        
        input_dict = {'key': 'value', 'nested': {'inner': 'data'}}
        result = field.prepare_value(input_dict)
        
        # Should be formatted JSON string
        self.assertIn('"key"', result)
        self.assertIn('"value"', result)
    
    def test_json_field_prepare_value_with_string(self):
        """Test JSONField prepare_value with string."""
        field = JSONField()
        
        json_string = '{"key": "value"}'
        result = field.prepare_value(json_string)
        
        # Should return as-is
        self.assertEqual(result, json_string)
    
    def test_json_field_prepare_value_with_empty(self):
        """Test JSONField prepare_value with empty value."""
        field = JSONField()
        
        result = field.prepare_value(None)
        self.assertEqual(result, '')
        
        result = field.prepare_value('')
        self.assertEqual(result, '')
    
    def test_json_field_prepare_value_with_complex_data(self):
        """Test JSONField prepare_value with complex nested data."""
        field = JSONField()
        
        complex_data = {
            'users': [
                {'name': 'John', 'age': 30},
                {'name': 'Jane', 'age': 25}
            ],
            'metadata': {
                'version': '1.0',
                'active': True
            }
        }
        
        result = field.prepare_value(complex_data)
        
        # Should be valid JSON
        import json
        parsed = json.loads(result)
        self.assertEqual(parsed, complex_data)
    
    def test_json_field_textarea_widget(self):
        """Test JSONField uses Textarea widget."""
        field = JSONField()
        
        self.assertIsInstance(field.widget, forms.Textarea)
    
    def test_json_field_widget_attributes(self):
        """Test JSONField widget has correct attributes."""
        field = JSONField()
        
        self.assertIn('json-field', field.widget.attrs.get('class', ''))
        self.assertEqual(field.widget.attrs.get('rows'), 4)
    
    def test_json_field_round_trip(self):
        """Test JSONField round-trip (prepare -> to_python)."""
        field = JSONField()
        
        original_data = {'test': 'data', 'number': 123}
        
        # Prepare for display
        prepared = field.prepare_value(original_data)
        
        # Parse back
        parsed = field.to_python(prepared)
        
        self.assertEqual(parsed, original_data)
    
    def test_json_field_handles_special_characters(self):
        """Test JSONField handles special characters."""
        field = JSONField()
        
        data = {'message': 'Hello "world"', 'path': r'C:\Users\test'}
        
        # Should handle escaping
        prepared = field.prepare_value(data)
        parsed = field.to_python(prepared)
        
        self.assertEqual(parsed, data)


# ============================================================================
# FIELD INTEGRATION TESTS
# ============================================================================

class FieldIntegrationTest(TestCase):
    """Test fields working together in forms."""
    
    def test_fields_in_form_context(self):
        """Test custom fields work correctly in form context."""
        
        class TestForm(forms.Form):
            rating = RatingField(max_rating=5)
            status = StatusField()
            content = TestimonialContentField(min_length=10)
        
        # Valid data
        form = TestForm({
            'rating': '4',
            'status': TestimonialStatus.APPROVED,
            'content': 'This is a valid testimonial content.'
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['rating'], 4)
    
    def test_fields_validation_errors_in_form(self):
        """Test custom fields validation errors in form."""
        
        class TestForm(forms.Form):
            rating = RatingField(max_rating=5)
            content = TestimonialContentField(min_length=10)
        
        # Invalid data
        form = TestForm({
            'rating': '10',  # Too high
            'content': 'Short'  # Too short
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
        self.assertIn('content', form.errors)