# testimonials/mixins/manager_mixins.py

"""
Reusable manager mixins for statistics and aggregations.
Eliminates duplication in manager statistics methods.
"""

from django.db.models import Count, Avg, Sum, Q, Case, When, IntegerField
from django.utils.translation import gettext_lazy as _


class StatisticsAggregationMixin:
    """
    Provides reusable methods for gathering statistics and aggregations.
    Can be used by any Manager to reduce duplication.
    """
    
    def get_basic_aggregates(self, aggregations):
        """
        Generic aggregation method for getting counts, averages, etc.
        
        Args:
            aggregations: Dict of aggregation expressions
            
        Returns:
            Dict of aggregated values
            
        Example:
            manager.get_basic_aggregates({
                'total': Count('id'),
                'avg_rating': Avg('rating'),
            })
        """
        return self.aggregate(**aggregations)
    
    def get_choice_distribution(self, field_name, choices):
        """
        Get distribution statistics for a choice field.
        
        Args:
            field_name: Name of the field (e.g., 'status', 'source')
            choices: Tuple of choices from model constants
            
        Returns:
            Dict with counts and percentages for each choice
            
        Example:
            manager.get_choice_distribution('status', TestimonialStatus.choices)
        """
        total_count = self.count()
        distribution = {}
        
        for code, label in choices:
            count = self.filter(**{field_name: code}).count()
            distribution[code] = {
                'count': count,
                'label': label,
                'percentage': round((count / max(total_count, 1)) * 100, 2)
            }
        
        return distribution
    
    def get_conditional_counts(self, conditions):
        """
        Get counts for multiple conditions in a single query.
        More efficient than multiple filter().count() calls.
        
        Args:
            conditions: Dict mapping name to Q objects
            
        Returns:
            Dict of condition counts
            
        Example:
            manager.get_conditional_counts({
                'approved': Q(status='approved'),
                'pending': Q(status='pending'),
            })
        """
        annotations = {}
        for name, condition in conditions.items():
            annotations[name] = Count(
                Case(When(condition, then=1), output_field=IntegerField())
            )
        
        return self.aggregate(**annotations)
    
    def get_boolean_field_counts(self, field_name):
        """
        Get counts for boolean field values.
        
        Args:
            field_name: Name of boolean field
            
        Returns:
            Dict with true_count and false_count
        """
        return self.aggregate(
            true_count=Count(Case(
                When(**{field_name: True}, then=1),
                output_field=IntegerField()
            )),
            false_count=Count(Case(
                When(**{field_name: False}, then=1),
                output_field=IntegerField()
            ))
        )
    
    def get_null_vs_filled_counts(self, field_name):
        """
        Get counts for null vs filled values of a field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Dict with null_count and filled_count
        """
        return self.aggregate(
            null_count=Count(Case(
                When(**{f'{field_name}__isnull': True}, then=1),
                output_field=IntegerField()
            )),
            filled_count=Count(Case(
                When(**{f'{field_name}__isnull': False}, then=1),
                output_field=IntegerField()
            ))
        )


class TimePeriodFilterMixin:
    """
    Provides time-based filtering methods for querysets.
    """
    
    def in_date_range(self, start_date, end_date, date_field='created_at'):
        """
        Filter queryset by date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            date_field: Field name for date filtering
            
        Returns:
            Filtered queryset
        """
        filters = {}
        if start_date:
            filters[f'{date_field}__gte'] = start_date
        if end_date:
            filters[f'{date_field}__lte'] = end_date
        
        return self.filter(**filters) if filters else self
    
    def created_in_last_days(self, days, date_field='created_at'):
        """
        Filter to items created in the last N days.
        
        Args:
            days: Number of days to look back
            date_field: Field name for date filtering
            
        Returns:
            Filtered queryset
        """
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(**{f'{date_field}__gte': cutoff_date})


class BulkOperationMixin:
    """
    Provides optimized bulk operation methods.
    """
    
    def bulk_update_status(self, ids, status):
        """
        Bulk update status for multiple objects.
        More efficient than updating one by one.
        
        Args:
            ids: List of object IDs
            status: New status value
            
        Returns:
            Number of updated objects
        """
        return self.filter(id__in=ids).update(status=status)
    
    def bulk_delete_by_ids(self, ids):
        """
        Bulk delete objects by IDs.
        
        Args:
            ids: List of object IDs
            
        Returns:
            Tuple (count, dict) of deleted objects
        """
        return self.filter(id__in=ids).delete()
    
    def batch_process(self, batch_size=100):
        """
        Iterator for processing queryset in batches.
        Memory efficient for large querysets.
        
        Args:
            batch_size: Size of each batch
            
        Yields:
            Batches of objects
        """
        queryset = self.all()
        iterator = queryset.iterator(chunk_size=batch_size)
        batch = []
        
        for item in iterator:
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch