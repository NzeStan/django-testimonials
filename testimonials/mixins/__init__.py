# testimonials/mixins/__init__.py

"""
Mixins package for reusable components.
Eliminates code duplication across the package.
"""

from .validation_mixins import (
    FileValidationMixin,
    AnonymousUserValidationMixin,
    ChoiceFieldDisplayMixin,
)

from .manager_mixins import (
    StatisticsAggregationMixin,
    TimePeriodFilterMixin,
    BulkOperationMixin,
)

__all__ = [
    # Validation mixins
    'FileValidationMixin',
    'AnonymousUserValidationMixin',
    'ChoiceFieldDisplayMixin',
    
    # Manager mixins
    'StatisticsAggregationMixin',
    'TimePeriodFilterMixin',
    'BulkOperationMixin',
]