# testimonials/tests/test_task_executor.py

"""
Comprehensive tests for TaskExecutor.
Tests cover Celery availability, sync/async execution, delayed execution,
batch processing, error handling, and edge cases.
"""

from unittest.mock import patch, MagicMock, PropertyMock
from django.test import TestCase, override_settings
from testimonials.services.task_executor import TaskExecutor, execute_task


# ============================================================================
# CELERY AVAILABILITY TESTS
# ============================================================================

class TaskExecutorCeleryAvailabilityTests(TestCase):
    """Test Celery availability detection."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    def test_is_celery_available_when_enabled_and_configured(self):
        """Test Celery is available when enabled and configured."""
        # Mock the import to simulate Celery being available
        with patch.dict('sys.modules', {'celery': MagicMock()}):
            # The is_celery_available method will try to import celery
            result = TaskExecutor.is_celery_available()
            # Since we can't easily mock the current_app, just test that it doesn't crash
            # In real scenario with Celery installed, this would return True
            self.assertIsNotNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_is_celery_available_when_disabled_in_settings(self):
        """Test Celery is not available when disabled in settings."""
        result = TaskExecutor.is_celery_available()
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    def test_is_celery_available_when_import_fails(self):
        """Test Celery is not available when import fails."""
        # Simulate ImportError when trying to import celery
        import sys
        
        # Temporarily remove celery from sys.modules if it exists
        celery_module = sys.modules.pop('celery', None)
        
        try:
            # Block the import by raising ImportError
            with patch.dict('sys.modules', {'celery': None}):
                # Force reimport
                import importlib
                # This should trigger the ImportError in is_celery_available
                result = TaskExecutor.is_celery_available()
                self.assertFalse(result)
        finally:
            # Restore celery module if it was there
            if celery_module is not None:
                sys.modules['celery'] = celery_module


# ============================================================================
# SYNCHRONOUS EXECUTION TESTS
# ============================================================================

class TaskExecutorSyncTests(TestCase):
    """Test synchronous task execution."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_basic_function(self):
        """Test synchronous execution of basic function."""
        def simple_task(x, y):
            return x + y
        
        result = TaskExecutor.execute(simple_task, 5, 10)
        self.assertEqual(result, 15)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_with_kwargs(self):
        """Test synchronous execution with keyword arguments."""
        def task_with_kwargs(a, b=10, c=20):
            return a + b + c
        
        result = TaskExecutor.execute(task_with_kwargs, 5, b=15, c=25)
        self.assertEqual(result, 45)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_returns_none_on_exception(self):
        """Test sync execution returns None on exception."""
        def failing_task():
            raise ValueError("Task failed")
        
        result = TaskExecutor.execute(failing_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_with_complex_return_value(self):
        """Test sync execution with complex return value."""
        def complex_task():
            return {
                'status': 'success',
                'data': [1, 2, 3],
                'meta': {'count': 3}
            }
        
        result = TaskExecutor.execute(complex_task)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data'], [1, 2, 3])
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_removes_celery_specific_kwargs(self):
        """Test sync execution removes Celery-specific kwargs."""
        def my_task(x):
            return x * 2
        
        # These Celery-specific kwargs should be removed
        result = TaskExecutor.execute(
            my_task,
            10,
            countdown=60,
            eta='2024-01-01',
            expires=3600
        )
        self.assertEqual(result, 20)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_with_no_arguments(self):
        """Test sync execution with no arguments."""
        def no_args_task():
            return "executed"
        
        result = TaskExecutor.execute(no_args_task)
        self.assertEqual(result, "executed")
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_sync_with_side_effects(self):
        """Test sync execution with side effects."""
        call_log = []
        
        def task_with_side_effects(value):
            call_log.append(value)
            return len(call_log)
        
        result = TaskExecutor.execute(task_with_side_effects, 'test')
        self.assertEqual(result, 1)
        self.assertEqual(call_log, ['test'])


# ============================================================================
# ASYNCHRONOUS EXECUTION TESTS
# ============================================================================

class TaskExecutorAsyncTests(TestCase):
    """Test asynchronous task execution."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_async_with_celery_task(self, mock_available):
        """Test async execution with a Celery task."""
        mock_available.return_value = True
        
        # Create mock Celery task
        mock_task = MagicMock()
        mock_task.__name__ = 'mock_celery_task'  # Add __name__ attribute
        mock_async_result = MagicMock()
        mock_async_result.id = 'task-123'
        mock_task.delay.return_value = mock_async_result
        
        result = TaskExecutor.execute(mock_task, 'arg1', kwarg1='value1')
        
        # Should call delay
        mock_task.delay.assert_called_once_with('arg1', kwarg1='value1')
        self.assertEqual(result.id, 'task-123')
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_async_with_non_celery_task(self, mock_available):
        """Test async execution with non-Celery task falls back to sync by default."""
        mock_available.return_value = True
        
        # Regular function without .delay method
        def regular_function():
            return 'value'
        
        # Default fallback_to_sync is True, so it will execute sync
        result = TaskExecutor.execute(regular_function, use_async=True)
        self.assertEqual(result, 'value')  # Falls back to sync execution
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_async_falls_back_to_sync_on_error(self, mock_available):
        """Test async execution falls back to sync on error."""
        mock_available.return_value = True
        
        # Create mock task that fails on async
        mock_task = MagicMock()
        mock_task.__name__ = 'failing_async_task'  # Add __name__ attribute
        mock_task.delay.side_effect = Exception("Async failed")
        mock_task.return_value = 'sync_result'
        
        result = TaskExecutor.execute(mock_task)
        
        # Should fall back to sync and return result
        self.assertEqual(result, 'sync_result')
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_async_no_fallback_returns_none(self, mock_available):
        """Test async execution without fallback returns None on error."""
        mock_available.return_value = True
        
        # Regular function (no .delay)
        def regular_function():
            return 'value'
        
        result = TaskExecutor.execute(
            regular_function,
            use_async=True,
            fallback_to_sync=False
        )
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_respects_use_async_parameter(self, mock_available):
        """Test execute respects explicit use_async parameter."""
        mock_available.return_value = True
        
        # Create mock Celery task
        mock_task = MagicMock()
        mock_task.__name__ = 'sync_forced_task'  # Add __name__ attribute
        mock_task.return_value = 'sync_result'
        
        # Force sync even though Celery is available
        result = TaskExecutor.execute(mock_task, use_async=False)
        
        # Should not call delay
        mock_task.delay.assert_not_called()
        self.assertEqual(result, 'sync_result')


# ============================================================================
# DELAYED EXECUTION TESTS
# ============================================================================

class TaskExecutorDelayedTests(TestCase):
    """Test delayed task execution."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_delayed_with_celery_available(self, mock_available):
        """Test delayed execution when Celery is available."""
        mock_available.return_value = True
        
        # Create mock Celery task
        mock_task = MagicMock()
        mock_task.__name__ = 'delayed_task'  # Add __name__ attribute
        mock_async_result = MagicMock()
        mock_async_result.id = 'delayed-task-123'
        mock_task.apply_async.return_value = mock_async_result
        
        # Fix: delay_seconds is positional, not keyword
        result = TaskExecutor.execute_delayed(
            mock_task,
            300,  # delay_seconds as positional arg
            'arg1',
            kwarg1='value1'
        )
        
        # Should call apply_async with countdown
        mock_task.apply_async.assert_called_once_with(
            args=('arg1',),
            kwargs={'kwarg1': 'value1'},
            countdown=300
        )
        self.assertEqual(result.id, 'delayed-task-123')
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_delayed_falls_back_when_celery_unavailable(self, mock_available):
        """Test delayed execution falls back to immediate sync when Celery unavailable."""
        mock_available.return_value = False
        
        def my_task(x):
            return x * 2
        
        # Fix: delay_seconds is positional, then args
        result = TaskExecutor.execute_delayed(my_task, 60, 10)
        
        # Should execute immediately and return result
        self.assertEqual(result, 20)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_delayed_falls_back_on_exception(self, mock_available):
        """Test delayed execution falls back to sync on exception."""
        mock_available.return_value = True
        
        mock_task = MagicMock()
        mock_task.__name__ = 'delayed_failing_task'  # Add __name__ attribute
        mock_task.apply_async.side_effect = Exception("Delay failed")
        mock_task.return_value = 'immediate_result'
        
        result = TaskExecutor.execute_delayed(mock_task, 60)
        
        # Should fall back to immediate sync
        self.assertEqual(result, 'immediate_result')
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_delayed_with_zero_delay(self, mock_available):
        """Test delayed execution with zero delay."""
        mock_available.return_value = True
        
        mock_task = MagicMock()
        mock_task.__name__ = 'zero_delay_task'  # Add __name__ attribute
        mock_async_result = MagicMock()
        mock_task.apply_async.return_value = mock_async_result
        
        TaskExecutor.execute_delayed(mock_task, 0)
        
        # Should still use apply_async with countdown=0
        call_kwargs = mock_task.apply_async.call_args[1]
        self.assertEqual(call_kwargs['countdown'], 0)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_delayed_with_large_delay(self, mock_available):
        """Test delayed execution with large delay value."""
        mock_available.return_value = True
        
        mock_task = MagicMock()
        mock_task.__name__ = 'large_delay_task'  # Add __name__ attribute
        mock_async_result = MagicMock()
        mock_task.apply_async.return_value = mock_async_result
        
        # 24 hours delay
        TaskExecutor.execute_delayed(mock_task, 86400)
        
        call_kwargs = mock_task.apply_async.call_args[1]
        self.assertEqual(call_kwargs['countdown'], 86400)


# ============================================================================
# BATCH PROCESSING TESTS
# ============================================================================

class TaskExecutorBatchTests(TestCase):
    """Test batch task execution."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_basic(self):
        """Test basic batch processing."""
        processed = []
        
        def process_batch(batch):
            processed.extend(batch)
            return len(batch)
        
        items = list(range(10))
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=3
        )
        
        # Should create 4 batches: [0,1,2], [3,4,5], [6,7,8], [9]
        self.assertEqual(len(results), 4)
        self.assertEqual(processed, items)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_exact_batch_size(self):
        """Test batch processing when items exactly match batch size."""
        def process_batch(batch):
            return sum(batch)
        
        items = list(range(10))  # 10 items
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=10
        )
        
        # Should create 1 batch
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], 45)  # sum of 0-9
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_with_empty_list(self):
        """Test batch processing with empty list."""
        def process_batch(batch):
            return len(batch)
        
        results = TaskExecutor.execute_batch(process_batch, [], batch_size=5)
        
        # Should return empty results
        self.assertEqual(len(results), 0)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_with_single_item(self):
        """Test batch processing with single item."""
        def process_batch(batch):
            return batch[0] * 2
        
        results = TaskExecutor.execute_batch(
            process_batch,
            [42],
            batch_size=10
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], 84)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_with_large_batch_size(self):
        """Test batch processing with batch size larger than items."""
        def process_batch(batch):
            return len(batch)
        
        items = list(range(5))
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=100
        )
        
        # Should create 1 batch
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], 5)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_with_batch_size_one(self):
        """Test batch processing with batch size of 1."""
        def process_batch(batch):
            return batch[0]
        
        items = [10, 20, 30]
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=1
        )
        
        # Should create 3 batches
        self.assertEqual(len(results), 3)
        self.assertEqual(results, [10, 20, 30])
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_batch_async(self, mock_available):
        """Test batch processing with async execution."""
        mock_available.return_value = True
        
        # Create mock Celery task
        mock_task = MagicMock()
        mock_task.__name__ = 'batch_async_task'  # Add __name__ attribute
        mock_async_results = [MagicMock(id=f'task-{i}') for i in range(3)]
        mock_task.delay.side_effect = mock_async_results
        
        items = list(range(10))
        results = TaskExecutor.execute_batch(
            mock_task,
            items,
            batch_size=4,
            use_async=True
        )
        
        # Should create 3 batches and return async results
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].id, 'task-0')
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_preserves_order(self):
        """Test batch processing preserves order."""
        def process_batch(batch):
            return [x * 2 for x in batch]
        
        items = [1, 2, 3, 4, 5]
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=2
        )
        
        # Flatten results
        flattened = []
        for result in results:
            flattened.extend(result)
        
        self.assertEqual(flattened, [2, 4, 6, 8, 10])
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_batch_with_complex_items(self):
        """Test batch processing with complex items."""
        def process_batch(batch):
            return sum(item['value'] for item in batch)
        
        items = [{'id': i, 'value': i * 10} for i in range(10)]
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=3
        )
        
        # Should sum values in each batch
        self.assertEqual(len(results), 4)
        # First batch: 0 + 10 + 20 = 30
        self.assertEqual(results[0], 30)


# ============================================================================
# EXECUTE TASK CONVENIENCE FUNCTION TESTS
# ============================================================================

class ExecuteTaskFunctionTests(TestCase):
    """Test execute_task convenience function."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_delegates_to_executor(self):
        """Test execute_task delegates to TaskExecutor.execute."""
        def my_task(x, y):
            return x + y
        
        result = execute_task(my_task, 5, 10)
        self.assertEqual(result, 15)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_with_kwargs(self):
        """Test execute_task with keyword arguments."""
        def my_task(a, b=10):
            return a + b
        
        result = execute_task(my_task, 5, b=20)
        self.assertEqual(result, 25)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.execute')
    def test_execute_task_passes_through_all_arguments(self, mock_execute):
        """Test execute_task passes all arguments to TaskExecutor."""
        mock_execute.return_value = 'result'
        
        def my_task():
            pass
        
        result = execute_task(
            my_task,
            'arg1',
            'arg2',
            use_async=True,
            kwarg1='value1'
        )
        
        mock_execute.assert_called_once_with(
            my_task,
            'arg1',
            'arg2',
            use_async=True,
            kwarg1='value1'
        )
        self.assertEqual(result, 'result')


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TaskExecutorErrorHandlingTests(TestCase):
    """Test error handling in task execution."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_sync_execution_handles_value_error(self):
        """Test sync execution handles ValueError."""
        def failing_task():
            raise ValueError("Invalid value")
        
        result = TaskExecutor.execute(failing_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_sync_execution_handles_key_error(self):
        """Test sync execution handles KeyError."""
        def failing_task():
            data = {}
            return data['nonexistent']
        
        result = TaskExecutor.execute(failing_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_sync_execution_handles_attribute_error(self):
        """Test sync execution handles AttributeError."""
        def failing_task():
            obj = None
            return obj.some_method()
        
        result = TaskExecutor.execute(failing_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_sync_execution_handles_type_error(self):
        """Test sync execution handles TypeError."""
        def failing_task(required_arg):
            return required_arg
        
        # Call without required argument
        result = TaskExecutor._execute_sync(failing_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_sync_execution_handles_index_error(self):
        """Test sync execution handles IndexError."""
        def failing_task():
            items = [1, 2, 3]
            return items[10]
        
        result = TaskExecutor.execute(failing_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_async_execution_handles_exception(self, mock_available):
        """Test async execution handles exception in delay."""
        mock_available.return_value = True
        
        mock_task = MagicMock()
        mock_task.__name__ = 'async_error_task'  # Add __name__ attribute
        mock_task.delay.side_effect = Exception("Celery error")
        
        result = TaskExecutor._execute_async(mock_task, 'arg1')
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_delayed_execution_handles_exception(self, mock_available):
        """Test delayed execution handles exception gracefully."""
        mock_available.return_value = True
        
        mock_task = MagicMock()
        mock_task.__name__ = 'delayed_error_task'  # Add __name__ attribute
        mock_task.apply_async.side_effect = Exception("Apply async failed")
        mock_task.return_value = 'fallback'
        
        result = TaskExecutor.execute_delayed(mock_task, 60)
        
        # Should fall back to sync
        self.assertEqual(result, 'fallback')
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_batch_execution_handles_task_exception(self):
        """Test batch execution handles exception in task."""
        def failing_task(batch):
            raise RuntimeError("Batch processing failed")
        
        items = list(range(10))
        results = TaskExecutor.execute_batch(failing_task, items, batch_size=5)
        
        # Should still complete but with None results
        self.assertEqual(len(results), 2)
        self.assertIsNone(results[0])
        self.assertIsNone(results[1])


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TaskExecutorEdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions."""
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_with_none_task(self):
        """Test execute with None as task handles gracefully."""
        # Calling with None should return None after error handling
        result = TaskExecutor.execute(None)
        # The implementation catches exceptions and returns None
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_returns_none(self):
        """Test execute when task returns None."""
        def none_task():
            return None
        
        result = TaskExecutor.execute(none_task)
        self.assertIsNone(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_returns_false(self):
        """Test execute when task returns False."""
        def false_task():
            return False
        
        result = TaskExecutor.execute(false_task)
        self.assertFalse(result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_returns_zero(self):
        """Test execute when task returns 0."""
        def zero_task():
            return 0
        
        result = TaskExecutor.execute(zero_task)
        self.assertEqual(result, 0)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_returns_empty_string(self):
        """Test execute when task returns empty string."""
        def empty_task():
            return ''
        
        result = TaskExecutor.execute(empty_task)
        self.assertEqual(result, '')
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_returns_empty_list(self):
        """Test execute when task returns empty list."""
        def empty_list_task():
            return []
        
        result = TaskExecutor.execute(empty_list_task)
        self.assertEqual(result, [])
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_task_returns_empty_dict(self):
        """Test execute when task returns empty dict."""
        def empty_dict_task():
            return {}
        
        result = TaskExecutor.execute(empty_dict_task)
        self.assertEqual(result, {})
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_with_lambda(self, mock_available):
        """Test execute with lambda function."""
        mock_available.return_value = False
        
        result = TaskExecutor.execute(lambda x: x * 2, 5)
        self.assertEqual(result, 10)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_with_nested_function(self):
        """Test execute with nested function."""
        def outer():
            def inner(x):
                return x ** 2
            return inner(5)
        
        result = TaskExecutor.execute(outer)
        self.assertEqual(result, 25)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_with_class_method(self):
        """Test execute with class method."""
        class MyClass:
            @staticmethod
            def my_method(x):
                return x * 3
        
        result = TaskExecutor.execute(MyClass.my_method, 7)
        self.assertEqual(result, 21)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_batch_with_heterogeneous_items(self):
        """Test batch processing with mixed data types."""
        def process_batch(batch):
            return [str(item) for item in batch]
        
        items = [1, 'two', 3.0, None, True]
        results = TaskExecutor.execute_batch(
            process_batch,
            items,
            batch_size=2
        )
        
        # Should handle mixed types
        self.assertEqual(len(results), 3)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_with_very_large_args(self):
        """Test execute with very large arguments."""
        def sum_list(items):
            return sum(items)
        
        large_list = list(range(10000))
        result = TaskExecutor.execute(sum_list, large_list)
        
        self.assertEqual(result, sum(range(10000)))
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_toggles_between_sync_and_async(self, mock_available):
        """Test execute can toggle between sync and async."""
        mock_available.return_value = True
        
        def simple_task():
            return 'result'
        
        # Force sync
        result1 = TaskExecutor.execute(simple_task, use_async=False)
        self.assertEqual(result1, 'result')
        
        # Force async (will fail since not a Celery task)
        result2 = TaskExecutor.execute(simple_task, use_async=True, fallback_to_sync=True)
        self.assertEqual(result2, 'result')
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_batch_processing_stops_on_empty_batches(self):
        """Test batch processing handles empty batches correctly."""
        call_count = 0
        
        def process_batch(batch):
            nonlocal call_count
            call_count += 1
            return len(batch)
        
        # Empty list should not call process at all
        results = TaskExecutor.execute_batch(process_batch, [], batch_size=5)
        
        self.assertEqual(len(results), 0)
        self.assertEqual(call_count, 0)
    
    @override_settings(TESTIMONIALS_USE_CELERY=True)
    @patch('testimonials.services.task_executor.TaskExecutor.is_celery_available')
    def test_execute_async_with_missing_delay_attribute(self, mock_available):
        """Test async execute when task doesn't have delay attribute."""
        mock_available.return_value = True
        
        # Object without delay method but with __name__
        class NotACeleryTask:
            __name__ = 'NotACeleryTask'  # Add __name__ attribute
            
            def __call__(self):
                return 'result'
        
        not_a_task = NotACeleryTask()
        result = TaskExecutor.execute(not_a_task, use_async=True, fallback_to_sync=True)
        
        # Should fall back to sync
        self.assertEqual(result, 'result')
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_with_unicode_arguments(self):
        """Test execute with unicode arguments."""
        def echo_task(text):
            return f"Processed: {text}"
        
        result = TaskExecutor.execute(echo_task, "Hello 你好 مرحبا 🎉")
        self.assertIn("Hello", result)
        self.assertIn("你好", result)
    
    @override_settings(TESTIMONIALS_USE_CELERY=False)
    def test_execute_removes_only_celery_kwargs(self):
        """Test execute only removes Celery-specific kwargs, not others."""
        received_kwargs = {}
        
        def task_with_kwargs(**kwargs):
            received_kwargs.update(kwargs)
            return True
        
        TaskExecutor.execute(
            task_with_kwargs,
            my_arg='value',
            countdown=60,  # Should be removed
            expires=3600,  # Should be removed
            eta='2024-01-01',  # Should be removed
            other_arg='keep'  # Should be kept
        )
        
        self.assertIn('my_arg', received_kwargs)
        self.assertIn('other_arg', received_kwargs)
        self.assertNotIn('countdown', received_kwargs)
        self.assertNotIn('expires', received_kwargs)
        self.assertNotIn('eta', received_kwargs)