"""Retry utilities for the ablation framework."""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from . import AblationError, AblationErrorHandler, ErrorSeverity

logger = logging.getLogger(__name__)

# Type variable for the return type of the function
T = TypeVar("T")


def retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: list[type[Exception]] | None = None,
    error_handler: AblationErrorHandler | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for the ablation framework.

    This decorator retries a function if it raises an exception.

    Args:
        max_retries: The maximum number of retries.
        retry_delay: The initial delay between retries in seconds.
        backoff_factor: The factor to multiply the delay by after each retry.
        exceptions: The list of exceptions to catch and retry.
        error_handler: The error handler to use for logging errors.

    Returns:
        Callable: The decorated function.
    """
    exceptions = exceptions or [Exception]
    error_handler = error_handler or AblationErrorHandler(max_retries=max_retries)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = retry_delay
            last_exception = None

            for attempt in range(1, max_retries + 2):  # +2 because we count from 1 and want to include the initial try
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    if attempt > max_retries:
                        # If we've exceeded the maximum number of retries, re-raise the exception
                        if isinstance(e, AblationError):
                            error_handler.handle_error(e)
                        else:
                            # Convert standard exceptions to AblationError
                            ablation_error = AblationError(
                                message=f"Function {func.__name__} failed after {max_retries} retries: {e!s}",
                                severity=ErrorSeverity.ERROR,
                                details={
                                    "function": func.__name__,
                                    "attempt": attempt,
                                    "max_retries": max_retries,
                                    "last_exception": str(e),
                                },
                            )
                            error_handler.handle_error(ablation_error)
                        raise

                    logger.warning(
                        f"Attempt {attempt}/{max_retries + 1} for {func.__name__} failed: {e!s}. "
                        f"Retrying in {delay} seconds...",
                    )

                    time.sleep(delay)
                    delay *= backoff_factor

            # This should never happen, but just in case
            assert last_exception is not None
            raise last_exception

        return cast(Callable[..., T], wrapper)

    return decorator


class RetryContext:
    """Context manager for retrying operations.

    This class provides a context manager for retrying operations that might fail.
    It can be used in with statements to retry a block of code.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: list[type[Exception]] | None = None,
        error_handler: AblationErrorHandler | None = None,
        on_failure: Callable[[Exception], None] | None = None,
    ):
        """Initialize the retry context.

        Args:
            max_retries: The maximum number of retries.
            retry_delay: The initial delay between retries in seconds.
            backoff_factor: The factor to multiply the delay by after each retry.
            exceptions: The list of exceptions to catch and retry.
            error_handler: The error handler to use for logging errors.
            on_failure: A callback to call when all retries have failed.
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions or [Exception]
        self.error_handler = error_handler or AblationErrorHandler(max_retries=max_retries)
        self.on_failure = on_failure
        self.attempt = 0
        self.delay = retry_delay
        self.last_exception: Exception | None = None

    def __enter__(self) -> "RetryContext":
        """Enter the context manager.

        Returns:
            RetryContext: The retry context.
        """
        self.attempt += 1
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any,
    ) -> bool:
        """Exit the context manager.

        Args:
            exc_type: The type of the exception raised, if any.
            exc_value: The exception raised, if any.
            traceback: The traceback of the exception raised, if any.

        Returns:
            bool: True if the exception was handled, False otherwise.
        """
        if exc_type is None:
            # No exception was raised, context manager executed successfully
            return False

        # Check if the exception is one we want to retry
        should_retry = False
        for exception_type in self.exceptions:
            if issubclass(exc_type, exception_type):
                should_retry = True
                break

        if not should_retry:
            # Exception type not in our retry list, don't handle it
            return False

        # Store the last exception
        assert exc_value is not None
        self.last_exception = exc_value

        # Check if we've exceeded the maximum number of retries
        if self.attempt > self.max_retries:
            # We've exceeded the maximum number of retries, handle the failure
            if isinstance(exc_value, AblationError):
                self.error_handler.handle_error(exc_value)
            else:
                # Convert standard exceptions to AblationError
                ablation_error = AblationError(
                    message=f"Operation failed after {self.max_retries} retries: {exc_value!s}",
                    severity=ErrorSeverity.ERROR,
                    details={
                        "attempt": self.attempt,
                        "max_retries": self.max_retries,
                        "last_exception": str(exc_value),
                    },
                )
                self.error_handler.handle_error(ablation_error)

            # Call the on_failure callback if provided
            if self.on_failure:
                self.on_failure(exc_value)

            # Don't handle the exception, let it propagate
            return False

        # We should retry, log the exception and sleep
        logger.warning(
            f"Attempt {self.attempt}/{self.max_retries + 1} failed: {exc_value!s}. "
            f"Retrying in {self.delay} seconds...",
        )

        time.sleep(self.delay)
        self.delay *= self.backoff_factor

        # Increment the attempt counter for the next try
        self.attempt += 1

        # Handle the exception by retrying
        return True

    def reset(self) -> None:
        """Reset the retry context.

        This method resets the attempt counter and delay so the context can be reused.
        """
        self.attempt = 0
        self.delay = self.retry_delay
        self.last_exception = None
