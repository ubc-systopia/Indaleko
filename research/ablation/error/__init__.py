"""Error handling utilities for the ablation framework."""

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, Union


class ErrorSeverity(Enum):
    """Error severity levels for the ablation framework."""

    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class AblationError(Exception):
    """Base exception class for the ablation framework."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            severity: The error severity.
            details: Additional error details.
        """
        self.message = message
        self.severity = severity
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Get the string representation of the error.

        Returns:
            str: The error message.
        """
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.severity.name}: {self.message} - {details_str}"
        return f"{self.severity.name}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert the error to a dictionary.

        Returns:
            Dict[str, Any]: The error as a dictionary.
        """
        return {
            "message": self.message,
            "severity": self.severity.name,
            "details": self.details,
            "type": self.__class__.__name__,
        }


class DatabaseError(AblationError):
    """Exception raised for database-related errors."""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            severity: The error severity.
            details: Additional error details.
        """
        super().__init__(message, severity, details)


class CollectionError(DatabaseError):
    """Exception raised for collection-related errors."""

    def __init__(
        self,
        message: str,
        collection_name: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            collection_name: The name of the collection.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        details["collection_name"] = collection_name
        super().__init__(message, severity, details)


class DocumentError(DatabaseError):
    """Exception raised for document-related errors."""

    def __init__(
        self,
        message: str,
        collection_name: str,
        document_key: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            collection_name: The name of the collection.
            document_key: The key of the document.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        details["collection_name"] = collection_name
        if document_key:
            details["document_key"] = document_key
        super().__init__(message, severity, details)


class QueryError(DatabaseError):
    """Exception raised for query-related errors."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        bind_vars: dict[str, Any] | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            query: The query that caused the error.
            bind_vars: The bind variables used.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        if query:
            details["query"] = query
        if bind_vars:
            details["bind_vars"] = bind_vars
        super().__init__(message, severity, details)


class CollectorError(AblationError):
    """Exception raised for collector-related errors."""

    def __init__(
        self,
        message: str,
        collector_name: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            collector_name: The name of the collector.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        details["collector_name"] = collector_name
        super().__init__(message, severity, details)


class RecorderError(AblationError):
    """Exception raised for recorder-related errors."""

    def __init__(
        self,
        message: str,
        recorder_name: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            recorder_name: The name of the recorder.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        details["recorder_name"] = recorder_name
        super().__init__(message, severity, details)


class ValidationError(AblationError):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        expected_type: type | None = None,
        actual_value: Any = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            field_name: The name of the field that failed validation.
            expected_type: The expected type of the field.
            actual_value: The actual value of the field.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        if field_name:
            details["field_name"] = field_name
        if expected_type:
            details["expected_type"] = str(expected_type)
        if actual_value is not None:
            details["actual_value"] = str(actual_value)
        super().__init__(message, severity, details)


class ConfigurationError(AblationError):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            config_key: The configuration key that caused the error.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, severity, details)


class TestingError(AblationError):
    """Exception raised for testing-related errors."""

    def __init__(
        self,
        message: str,
        test_name: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the error.

        Args:
            message: The error message.
            test_name: The name of the test that caused the error.
            severity: The error severity.
            details: Additional error details.
        """
        details = details or {}
        if test_name:
            details["test_name"] = test_name
        super().__init__(message, severity, details)


class AblationErrorHandler:
    """Error handler for the ablation framework.

    This class provides methods for handling errors, including logging,
    raising exceptions, and retrying operations.
    """

    def __init__(self, max_retries: int = 3):
        """Initialize the error handler.

        Args:
            max_retries: The maximum number of retries for operations.
        """
        self.max_retries = max_retries
        self.errors: list[AblationError] = []

    def handle_error(self, error: AblationError) -> None:
        """Handle an error.

        This method logs the error and adds it to the error list.

        Args:
            error: The error to handle.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Log the error with the appropriate severity
        if error.severity == ErrorSeverity.DEBUG:
            logger.debug(str(error))
        elif error.severity == ErrorSeverity.INFO:
            logger.info(str(error))
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(str(error))
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(str(error))
        elif error.severity == ErrorSeverity.CRITICAL:
            logger.critical(str(error))

        # Add the error to the list
        self.errors.append(error)

    def clear_errors(self) -> None:
        """Clear the error list."""
        self.errors.clear()

    def get_errors(self, min_severity: ErrorSeverity = ErrorSeverity.DEBUG) -> list[AblationError]:
        """Get the list of errors with at least the specified severity.

        Args:
            min_severity: The minimum severity to include.

        Returns:
            List[AblationError]: The list of errors.
        """
        return [e for e in self.errors if e.severity.value >= min_severity.value]

    def has_errors(self, min_severity: ErrorSeverity = ErrorSeverity.ERROR) -> bool:
        """Check if there are any errors with at least the specified severity.

        Args:
            min_severity: The minimum severity to check.

        Returns:
            bool: True if there are errors, False otherwise.
        """
        return any(e.severity.value >= min_severity.value for e in self.errors)

    def get_last_error(self) -> AblationError | None:
        """Get the last error.

        Returns:
            Optional[AblationError]: The last error or None if there are no errors.
        """
        return self.errors[-1] if self.errors else None
