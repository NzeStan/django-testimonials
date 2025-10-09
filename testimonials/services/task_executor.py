# testimonials/services/task_executor.py

"""
Unified task execution service.
Handles both synchronous and asynchronous task execution.
"""

import logging
from typing import Callable, Any, Optional
from ..conf import app_settings

logger = logging.getLogger("testimonials")


class TaskExecutor:
    """
    Service for executing tasks either synchronously or asynchronously.
    Eliminates duplicate Celery checking logic across the codebase.
    """
    
    @staticmethod
    def is_celery_available():
        """
        Check if Celery is available and configured.
        
        Returns:
            True if Celery can be used, False otherwise
        """
        if not app_settings.USE_CELERY:
            return False
        
        try:
            from celery import current_app
            return current_app is not None
        except ImportError:
            return False
    
    @classmethod
    def execute(
        cls,
        task_func: Callable,
        *args,
        use_async: Optional[bool] = None,
        fallback_to_sync: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute a task either asynchronously or synchronously.
        
        Args:
            task_func: Task function to execute
            *args: Positional arguments for the task
            use_async: Force async (True) or sync (False). None uses config default.
            fallback_to_sync: If async fails, fall back to sync execution
            **kwargs: Keyword arguments for the task
            
        Returns:
            Task result (immediate for sync, AsyncResult for async)
            
        Example:
            # Use configured default (async if enabled)
            TaskExecutor.execute(send_email, recipient, subject, body)
            
            # Force synchronous execution
            TaskExecutor.execute(send_email, recipient, subject, body, use_async=False)
        """
        # Determine execution mode
        if use_async is None:
            use_async = cls.is_celery_available()
        
        # Try asynchronous execution
        if use_async:
            result = cls._execute_async(task_func, *args, **kwargs)
            
            if result is not None or not fallback_to_sync:
                return result
            
            logger.warning(
                f"Async execution of '{task_func.__name__}' failed, "
                f"falling back to sync"
            )
        
        # Execute synchronously
        return cls._execute_sync(task_func, *args, **kwargs)
    
    @staticmethod
    def _execute_async(task_func: Callable, *args, **kwargs) -> Any:
        """
        Execute task asynchronously using Celery.
        
        Args:
            task_func: Task function (must be a Celery task)
            *args: Task arguments
            **kwargs: Task keyword arguments
            
        Returns:
            AsyncResult or None if failed
        """
        if not hasattr(task_func, 'delay'):
            logger.error(
                f"Function '{task_func.__name__}' is not a Celery task. "
                f"Cannot execute asynchronously."
            )
            return None
        
        try:
            # Use .delay() for simple async execution
            async_result = task_func.delay(*args, **kwargs)
            logger.debug(
                f"Task '{task_func.__name__}' queued with ID: {async_result.id}"
            )
            return async_result
        except Exception as e:
            logger.error(
                f"Async execution of '{task_func.__name__}' failed: {e}",
                exc_info=True
            )
            return None
    
    @staticmethod
    def _execute_sync(task_func: Callable, *args, **kwargs) -> Any:
        """
        Execute task synchronously.
        
        Args:
            task_func: Task function
            *args: Task arguments
            **kwargs: Task keyword arguments
            
        Returns:
            Task result or None if failed
        """
        try:
            # Remove Celery-specific kwargs if present
            kwargs.pop('countdown', None)
            kwargs.pop('eta', None)
            kwargs.pop('expires', None)
            
            result = task_func(*args, **kwargs)
            logger.debug(f"Task '{task_func.__name__}' executed synchronously")
            return result
        except Exception as e:
            logger.error(
                f"Sync execution of '{task_func.__name__}' failed: {e}",
                exc_info=True
            )
            return None
    
    @classmethod
    def execute_delayed(
        cls,
        task_func: Callable,
        delay_seconds: int,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a task with a delay (only works with async).
        Falls back to immediate execution if async unavailable.
        
        Args:
            task_func: Task function
            delay_seconds: Number of seconds to delay
            *args: Task arguments
            **kwargs: Task keyword arguments
            
        Returns:
            AsyncResult or immediate result
        """
        if not cls.is_celery_available():
            logger.warning(
                f"Delayed execution requested but Celery unavailable. "
                f"Executing '{task_func.__name__}' immediately."
            )
            return cls._execute_sync(task_func, *args, **kwargs)
        
        try:
            # Use .apply_async() for delayed execution
            async_result = task_func.apply_async(
                args=args,
                kwargs=kwargs,
                countdown=delay_seconds
            )
            logger.debug(
                f"Task '{task_func.__name__}' scheduled in {delay_seconds}s "
                f"with ID: {async_result.id}"
            )
            return async_result
        except Exception as e:
            logger.error(
                f"Delayed execution of '{task_func.__name__}' failed: {e}",
                exc_info=True
            )
            # Fallback to immediate sync execution
            return cls._execute_sync(task_func, *args, **kwargs)
    
    @classmethod
    def execute_batch(
        cls,
        task_func: Callable,
        items: list,
        batch_size: int = 100,
        use_async: Optional[bool] = None
    ) -> list:
        """
        Execute a task for multiple items in batches.
        
        Args:
            task_func: Task function to execute
            items: List of items to process
            batch_size: Number of items per batch
            use_async: Force async or sync execution
            
        Returns:
            List of results for each batch
            
        Example:
            # Process 1000 testimonials in batches of 100
            results = TaskExecutor.execute_batch(
                process_testimonial,
                testimonial_ids,
                batch_size=100
            )
        """
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            logger.debug(
                f"Processing batch {i // batch_size + 1} "
                f"({len(batch)} items) with '{task_func.__name__}'"
            )
            
            # Execute task for the batch
            result = cls.execute(task_func, batch, use_async=use_async)
            results.append(result)
        
        logger.info(
            f"Completed batch processing: {len(results)} batches, "
            f"{len(items)} total items"
        )
        
        return results


# Convenience function for backward compatibility
def execute_task(task_func: Callable, *args, **kwargs) -> Any:
    """
    Backward compatible function for task execution.
    Delegates to TaskExecutor.
    
    Args:
        task_func: Task function to execute
        *args: Task arguments
        **kwargs: Task keyword arguments
        
    Returns:
        Task result
    """
    return TaskExecutor.execute(task_func, *args, **kwargs)