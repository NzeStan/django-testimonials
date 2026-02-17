import logging
from threading import Thread, Timer
from typing import Callable, Any, Optional
from ..conf import app_settings

logger = logging.getLogger("testimonials")


class TaskExecutor:
    """
    Service for executing tasks either synchronously or in background threads.
    Eliminates duplicate checking logic across the codebase.
    """

    @staticmethod
    def is_async_enabled():
        """
        Check if background task execution is enabled.

        Returns:
            True if background tasks can be used, False otherwise
        """
        return app_settings.USE_BACKGROUND_TASKS

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
        Execute a task either asynchronously (in a thread) or synchronously.

        Args:
            task_func: Task function to execute
            *args: Positional arguments for the task
            use_async: Force async (True) or sync (False). None uses config default.
            fallback_to_sync: If async fails, fall back to sync execution
            **kwargs: Keyword arguments for the task

        Returns:
            Task result (immediate for sync, Thread for async)

        Example:
            # Use configured default (async if enabled)
            TaskExecutor.execute(send_email, recipient, subject, body)

            # Force synchronous execution
            TaskExecutor.execute(send_email, recipient, subject, body, use_async=False)
        """
        # Determine execution mode
        if use_async is None:
            use_async = cls.is_async_enabled()

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
        """Execute task asynchronously in a background thread."""
        # Get task name safely
        task_name = getattr(task_func, '__name__', repr(task_func))

        # Remove async-specific kwargs before passing to the task
        kwargs.pop('countdown', None)
        kwargs.pop('eta', None)
        kwargs.pop('expires', None)

        def run():
            try:
                task_func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Background execution of '{task_name}' failed: {e}",
                    exc_info=True
                )

        try:
            thread = Thread(target=run, daemon=True)
            thread.start()
            logger.debug(
                f"Task '{task_name}' started in background thread"
            )
            return thread
        except Exception as e:
            logger.error(
                f"Failed to start background thread for '{task_name}': {e}",
                exc_info=True
            )
            return None

    @staticmethod
    def _execute_sync(task_func: Callable, *args, **kwargs) -> Any:
        """Execute task synchronously."""
        try:
            # Remove async-specific kwargs if present
            kwargs.pop('countdown', None)
            kwargs.pop('eta', None)
            kwargs.pop('expires', None)

            result = task_func(*args, **kwargs)
            # Get task name safely
            task_name = getattr(task_func, '__name__', repr(task_func))
            logger.debug(f"Task '{task_name}' executed synchronously")
            return result
        except Exception as e:
            # Get task name safely
            task_name = getattr(task_func, '__name__', repr(task_func))
            logger.error(
                f"Sync execution of '{task_name}' failed: {e}",
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
        """Execute a task with a delay using threading.Timer."""
        if not cls.is_async_enabled():
            # Get task name safely
            task_name = getattr(task_func, '__name__', repr(task_func))
            logger.warning(
                f"Delayed execution requested but background tasks unavailable. "
                f"Executing '{task_name}' immediately."
            )
            return cls._execute_sync(task_func, *args, **kwargs)

        try:
            # Get task name safely
            task_name = getattr(task_func, '__name__', repr(task_func))

            def run():
                try:
                    task_func(*args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"Delayed execution of '{task_name}' failed: {e}",
                        exc_info=True
                    )

            timer = Timer(delay_seconds, run)
            timer.daemon = True
            timer.start()
            logger.debug(
                f"Task '{task_name}' scheduled in {delay_seconds}s"
            )
            return timer
        except Exception as e:
            # Get task name safely
            task_name = getattr(task_func, '__name__', repr(task_func))
            logger.error(
                f"Delayed execution of '{task_name}' failed: {e}",
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
        """Execute a task for multiple items in batches."""
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            # Get task name safely
            task_name = getattr(task_func, '__name__', repr(task_func))
            logger.debug(
                f"Processing batch {i // batch_size + 1} "
                f"({len(batch)} items) with '{task_name}'"
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
