"""Validation utilities for the ablation framework."""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TypeVar, Union

from pydantic import BaseModel, ValidationError

from ..error import AblationError, ErrorSeverity
from ..error import ValidationError as AblationValidationError
from ..models.activity import ActivityType

logger = logging.getLogger(__name__)

# Type variable for generic validation functions
T = TypeVar("T")


def validate_model(
    model_class: type[BaseModel], data: dict[str, Any],
) -> tuple[BaseModel | None, AblationError | None]:
    """Validate data against a Pydantic model.

    Args:
        model_class: The Pydantic model class.
        data: The data to validate.

    Returns:
        Tuple[Optional[BaseModel], Optional[AblationError]]: The validated model and any error.
    """
    try:
        model = model_class(**data)
        return model, None
    except ValidationError as e:
        error = AblationValidationError(
            message=f"Validation error for {model_class.__name__}",
            severity=ErrorSeverity.ERROR,
            details={
                "model_class": model_class.__name__,
                "errors": str(e),
            },
        )
        return None, error


def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> AblationError | None:
    """Validate that the data contains all required fields.

    Args:
        data: The data to validate.
        required_fields: The required fields.

    Returns:
        Optional[AblationError]: Any error that occurred.
    """
    missing_fields = []

    for field in required_fields:
        if field not in data:
            missing_fields.append(field)

    if missing_fields:
        return AblationValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            severity=ErrorSeverity.ERROR,
            details={
                "missing_fields": missing_fields,
                "required_fields": required_fields,
            },
        )

    return None


def validate_field_type(data: dict[str, Any], field: str, expected_type: type) -> AblationError | None:
    """Validate that a field is of the expected type.

    Args:
        data: The data to validate.
        field: The field to validate.
        expected_type: The expected type.

    Returns:
        Optional[AblationError]: Any error that occurred.
    """
    if field not in data:
        return AblationValidationError(
            message=f"Missing field: {field}",
            field_name=field,
            severity=ErrorSeverity.ERROR,
        )

    value = data[field]

    # Handle None values
    if value is None:
        if expected_type is None or expected_type is type(None):
            return None

        return AblationValidationError(
            message=f"Field {field} is None, expected {expected_type.__name__}",
            field_name=field,
            expected_type=expected_type,
            actual_value=value,
            severity=ErrorSeverity.ERROR,
        )

    # Handle Union types
    if hasattr(expected_type, "__origin__") and expected_type.__origin__ is Union:
        # Get the Union argument types
        union_types = expected_type.__args__

        # Check if the value is one of the Union types
        if not any(isinstance(value, t) for t in union_types):
            return AblationValidationError(
                message=f"Field {field} is of type {type(value).__name__}, expected one of {[t.__name__ for t in union_types]}",
                field_name=field,
                expected_type=expected_type,
                actual_value=value,
                severity=ErrorSeverity.ERROR,
            )

        return None

    # Handle List types
    if hasattr(expected_type, "__origin__") and expected_type.__origin__ is list:
        # Get the List item type
        item_type = expected_type.__args__[0]

        # Check if the value is a list
        if not isinstance(value, list):
            return AblationValidationError(
                message=f"Field {field} is of type {type(value).__name__}, expected List",
                field_name=field,
                expected_type=expected_type,
                actual_value=value,
                severity=ErrorSeverity.ERROR,
            )

        # Check each item in the list
        for i, item in enumerate(value):
            if not isinstance(item, item_type):
                return AblationValidationError(
                    message=f"Item {i} in field {field} is of type {type(item).__name__}, expected {item_type.__name__}",
                    field_name=f"{field}[{i}]",
                    expected_type=item_type,
                    actual_value=item,
                    severity=ErrorSeverity.ERROR,
                )

        return None

    # Handle Dict types
    if hasattr(expected_type, "__origin__") and expected_type.__origin__ is dict:
        # Get the Dict key and value types
        key_type, value_type = expected_type.__args__

        # Check if the value is a dict
        if not isinstance(value, dict):
            return AblationValidationError(
                message=f"Field {field} is of type {type(value).__name__}, expected Dict",
                field_name=field,
                expected_type=expected_type,
                actual_value=value,
                severity=ErrorSeverity.ERROR,
            )

        # Check each key and value in the dict
        for k, v in value.items():
            if not isinstance(k, key_type):
                return AblationValidationError(
                    message=f"Key {k} in field {field} is of type {type(k).__name__}, expected {key_type.__name__}",
                    field_name=f"{field}[{k}]",
                    expected_type=key_type,
                    actual_value=k,
                    severity=ErrorSeverity.ERROR,
                )

            if not isinstance(v, value_type):
                return AblationValidationError(
                    message=f"Value for key {k} in field {field} is of type {type(v).__name__}, expected {value_type.__name__}",
                    field_name=f"{field}[{k}]",
                    expected_type=value_type,
                    actual_value=v,
                    severity=ErrorSeverity.ERROR,
                )

        return None

    # Handle Enum types
    if issubclass(expected_type, Enum):
        # Check if the value is an instance of the Enum
        if isinstance(value, expected_type):
            return None

        # Check if the value is a string and can be converted to the Enum
        if isinstance(value, str):
            try:
                expected_type[value]
                return None
            except KeyError:
                pass

        # Check if the value is an integer and can be converted to the Enum
        if isinstance(value, int):
            try:
                expected_type(value)
                return None
            except ValueError:
                pass

        return AblationValidationError(
            message=f"Field {field} is of type {type(value).__name__}, expected {expected_type.__name__}",
            field_name=field,
            expected_type=expected_type,
            actual_value=value,
            severity=ErrorSeverity.ERROR,
        )

    # Handle datetime type
    if expected_type is datetime:
        # Check if the value is a datetime
        if isinstance(value, datetime):
            # Check if the datetime has a timezone
            if value.tzinfo is None:
                return AblationValidationError(
                    message=f"Field {field} is a datetime without timezone",
                    field_name=field,
                    expected_type=expected_type,
                    actual_value=value,
                    severity=ErrorSeverity.ERROR,
                )

            return None

        # Check if the value is a string and can be converted to a datetime
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)

                # Check if the parsed datetime has a timezone
                if parsed.tzinfo is None:
                    return AblationValidationError(
                        message=f"Field {field} is a datetime string without timezone: {value}",
                        field_name=field,
                        expected_type=expected_type,
                        actual_value=value,
                        severity=ErrorSeverity.ERROR,
                    )

                return None
            except ValueError:
                pass

        return AblationValidationError(
            message=f"Field {field} is of type {type(value).__name__}, expected {expected_type.__name__}",
            field_name=field,
            expected_type=expected_type,
            actual_value=value,
            severity=ErrorSeverity.ERROR,
        )

    # Handle regular types
    if not isinstance(value, expected_type):
        return AblationValidationError(
            message=f"Field {field} is of type {type(value).__name__}, expected {expected_type.__name__}",
            field_name=field,
            expected_type=expected_type,
            actual_value=value,
            severity=ErrorSeverity.ERROR,
        )

    return None


def validate_activity_data(data: dict[str, Any], activity_type: ActivityType) -> list[AblationError]:
    """Validate activity data for a specific activity type.

    Args:
        data: The activity data to validate.
        activity_type: The activity type.

    Returns:
        List[AblationError]: Any errors that occurred.
    """
    errors = []

    # Validate common fields
    common_fields = [
        ("id", str),
        ("activity_type", ActivityType),
        ("created_at", datetime),
        ("modified_at", datetime),
        ("source", str),
        ("semantic_attributes", dict),
    ]

    for field, expected_type in common_fields:
        error = validate_field_type(data, field, expected_type)
        if error:
            errors.append(error)

    # Validate activity type
    if "activity_type" in data:
        if data["activity_type"] != activity_type:
            errors.append(
                AblationValidationError(
                    message=f"Activity type is {data['activity_type']}, expected {activity_type}",
                    field_name="activity_type",
                    expected_type=activity_type,
                    actual_value=data["activity_type"],
                    severity=ErrorSeverity.ERROR,
                ),
            )

    # Validate type-specific fields
    if activity_type == ActivityType.MUSIC:
        type_fields = [
            ("artist", str),
            ("track", str),
            ("album", Optional[str]),
            ("genre", Optional[str]),
            ("duration_seconds", int),
            ("platform", str),
        ]
    elif activity_type == ActivityType.LOCATION:
        type_fields = [
            ("location_name", str),
            ("coordinates", dict),
            ("accuracy_meters", float),
            ("location_type", str),
            ("device", str),
        ]
    elif activity_type == ActivityType.TASK:
        type_fields = [
            ("task_name", str),
            ("application", str),
            ("window_title", str),
            ("duration_seconds", int),
            ("is_active", bool),
        ]
    elif activity_type == ActivityType.COLLABORATION:
        type_fields = [
            ("platform", str),
            ("event_type", str),
            ("participants", list),
            ("content", str),
            ("duration_seconds", int),
        ]
    elif activity_type == ActivityType.STORAGE:
        type_fields = [
            ("path", str),
            ("file_type", str),
            ("size_bytes", int),
            ("operation", str),
            ("timestamp", datetime),
        ]
    elif activity_type == ActivityType.MEDIA:
        type_fields = [
            ("media_type", str),
            ("title", str),
            ("platform", str),
            ("duration_seconds", int),
            ("creator", str),
        ]
    else:
        return [
            AblationValidationError(
                message=f"Unknown activity type: {activity_type}",
                field_name="activity_type",
                severity=ErrorSeverity.ERROR,
            ),
        ]

    for field, expected_type in type_fields:
        error = validate_field_type(data, field, expected_type)
        if error:
            errors.append(error)

    return errors


def validate_truth_data(data: dict[str, Any]) -> list[AblationError]:
    """Validate truth data.

    Args:
        data: The truth data to validate.

    Returns:
        List[AblationError]: Any errors that occurred.
    """
    errors = []

    # Validate fields
    fields = [
        ("query_id", str),
        ("query_text", str),
        ("matching_entities", list),
        ("activity_types", list),
        ("created_at", datetime),
    ]

    for field, expected_type in fields:
        error = validate_field_type(data, field, expected_type)
        if error:
            errors.append(error)

    # Validate activity types
    if "activity_types" in data:
        activity_types = data["activity_types"]
        if isinstance(activity_types, list):
            for i, at in enumerate(activity_types):
                if not isinstance(at, (str, ActivityType)):
                    errors.append(
                        AblationValidationError(
                            message=f"Activity type at index {i} is of type {type(at).__name__}, expected str or ActivityType",
                            field_name=f"activity_types[{i}]",
                            expected_type=Union[str, ActivityType],
                            actual_value=at,
                            severity=ErrorSeverity.ERROR,
                        ),
                    )
                elif isinstance(at, str):
                    try:
                        ActivityType[at]
                    except KeyError:
                        errors.append(
                            AblationValidationError(
                                message=f"Unknown activity type: {at}",
                                field_name=f"activity_types[{i}]",
                                expected_type=ActivityType,
                                actual_value=at,
                                severity=ErrorSeverity.ERROR,
                            ),
                        )

    return errors


def validate_email(email: str) -> bool:
    """Validate an email address.

    Args:
        email: The email address to validate.

    Returns:
        bool: True if the email is valid, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate a URL.

    Args:
        url: The URL to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    pattern = r"^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
    return bool(re.match(pattern, url))


def validate_uuid(uuid_str: str) -> bool:
    """Validate a UUID string.

    Args:
        uuid_str: The UUID string to validate.

    Returns:
        bool: True if the UUID is valid, False otherwise.
    """
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(pattern, uuid_str, re.IGNORECASE))


def validate_date_format(date_str: str, format_str: str) -> bool:
    """Validate a date string against a format.

    Args:
        date_str: The date string to validate.
        format_str: The format string to validate against.

    Returns:
        bool: True if the date is valid, False otherwise.
    """
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def validate_with_function(
    value: T, validation_func: Callable[[T], bool], error_message: str,
) -> AblationError | None:
    """Validate a value with a custom function.

    Args:
        value: The value to validate.
        validation_func: The validation function.
        error_message: The error message to use if validation fails.

    Returns:
        Optional[AblationError]: Any error that occurred.
    """
    if not validation_func(value):
        return AblationValidationError(
            message=error_message,
            actual_value=value,
            severity=ErrorSeverity.ERROR,
        )

    return None
