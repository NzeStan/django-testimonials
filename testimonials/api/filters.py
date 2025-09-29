import django_filters
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from ..models import Testimonial, TestimonialCategory
from ..constants import TestimonialStatus, TestimonialSource


class TestimonialFilter(django_filters.FilterSet):
    """
    Filter for testimonials.
    """
    status = django_filters.ChoiceFilter(
        choices=TestimonialStatus.choices,
        help_text=_("Filter by testimonial status")
    )
    
    category = django_filters.ModelChoiceFilter(
        queryset=TestimonialCategory.objects.all(),
        help_text=_("Filter by category ID")
    )
    
    category_slug = django_filters.CharFilter(
        field_name='category__slug',
        help_text=_("Filter by category slug")
    )
    
    min_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte',
        help_text=_("Filter by minimum rating")
    )
    
    max_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='lte',
        help_text=_("Filter by maximum rating")
    )
    
    source = django_filters.ChoiceFilter(
        choices=TestimonialSource.choices,
        help_text=_("Filter by testimonial source")
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text=_("Filter by creation date (after)")
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text=_("Filter by creation date (before)")
    )
    
    author = django_filters.CharFilter(
        method='filter_author',
        help_text=_("Filter by author name or email")
    )
    
    is_anonymous = django_filters.BooleanFilter(
        help_text=_("Filter anonymous testimonials")
    )
    
    is_verified = django_filters.BooleanFilter(
        help_text=_("Filter verified testimonials")
    )
    
    search = django_filters.CharFilter(
        method='filter_search',
        help_text=_("Search in content, author name, or company")
    )
    
    has_media = django_filters.BooleanFilter(
        method='filter_has_media',
        help_text=_("Filter testimonials with media")
    )
    
    has_response = django_filters.BooleanFilter(
        method='filter_has_response',
        help_text=_("Filter testimonials with responses")
    )
    
    class Meta:
        model = Testimonial
        fields = [
            'status', 'category', 'rating', 'source', 'author',
            'is_anonymous', 'is_verified', 'min_rating', 'max_rating',
            'created_after', 'created_before', 'search'
        ]
    
    def filter_author(self, queryset, name, value):
        """Filter by author name or email."""
        return queryset.filter(
            Q(author_name__icontains=value) | 
            Q(author_email__icontains=value)
        )
    
    def filter_search(self, queryset, name, value):
        """Search in content, author name, or company."""
        return queryset.filter(
            Q(content__icontains=value) | 
            Q(author_name__icontains=value) |
            Q(company__icontains=value) |
            Q(title__icontains=value)
        )
    
    def filter_has_media(self, queryset, name, value):
        """Filter testimonials with media."""
        if value:
            return queryset.filter(media__isnull=False).distinct()
        else:
            return queryset.filter(media__isnull=True)
    
    def filter_has_response(self, queryset, name, value):
        """Filter testimonials with responses."""
        if value:
            return queryset.exclude(response='').exclude(response__isnull=True)
        else:
            return queryset.filter(Q(response='') | Q(response__isnull=True))