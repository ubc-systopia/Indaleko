"""Serialization and deserialization utilities for the ablation framework."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from ..error import ErrorSeverity, ValidationError
from ..models import (
    ActivityData,
    ActivityType,
    TruthData,
    get_model_class_for_activity_type,
)

logger = logging.getLogger(__name__)

# Type variable for generic serialization functions
T = TypeVar("T", bound=ActivityData)


class AblationJSONEncoder(json.JSONEncoder):
    """JSON encoder for ablation framework models."""

    def default(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable types.

        Args:
            obj: The object to convert.

        Returns:
            Any: The converted object.
        """
        # Handle datetimes
        if isinstance(obj, datetime):
            return obj.isoformat()

        # Handle UUIDs
        if hasattr(obj, "hex") and callable(getattr(obj, "hex", None)):
            return str(obj)

        # Handle enums
        if isinstance(obj, Enum):
            return obj.name

        # Handle Pydantic models
        if hasattr(obj, "dict") and callable(getattr(obj, "dict", None)):
            return obj.dict()

        # Let the base class default method raise the TypeError
        return super().default(obj)


def to_dict(data: ActivityData | TruthData | dict[str, Any]) -> dict[str, Any]:
    """Convert an activity or truth data object to a dictionary.

    Args:
        data: The data to convert.

    Returns:
        Dict[str, Any]: The data as a dictionary.
    """
    if isinstance(data, (ActivityData, TruthData)):
        # Convert the Pydantic model to a dictionary
        return data.dict()

    # If it's already a dictionary, return it as is
    return data


def to_json(data: ActivityData | TruthData | dict[str, Any], pretty: bool = False) -> str:
    """Convert an activity or truth data object to a JSON string.

    Args:
        data: The data to convert.
        pretty: Whether to format the JSON string for readability.

    Returns:
        str: The data as a JSON string.
    """
    # Convert to dictionary
    data_dict = to_dict(data)

    # Convert to JSON
    indent = 2 if pretty else None
    return json.dumps(data_dict, cls=AblationJSONEncoder, indent=indent)


def from_dict(data: dict[str, Any]) -> ActivityData | TruthData:
    """Convert a dictionary to an activity or truth data object.

    Args:
        data: The dictionary to convert.

    Returns:
        Union[ActivityData, TruthData]: The converted object.

    Raises:
        ValidationError: If the dictionary cannot be converted.
    """
    # Check if it's a TruthData object
    if "query_id" in data and "query_text" in data and "matching_entities" in data:
        return TruthData(**data)

    # Check if it's an ActivityData object
    if "activity_type" in data:
        # Get the activity type
        activity_type_str = data["activity_type"]

        # Convert the activity type string to an ActivityType enum
        try:
            if isinstance(activity_type_str, str):
                activity_type = ActivityType[activity_type_str]
            else:
                activity_type = activity_type_str
        except (KeyError, TypeError):
            raise ValidationError(
                message=f"Invalid activity type: {activity_type_str}",
                field_name="activity_type",
                severity=ErrorSeverity.ERROR,
            )

        # Get the model class for the activity type
        model_class = get_model_class_for_activity_type(activity_type)

        # If we don't have a model class for this activity type, use the base class
        if model_class is None:
            model_class = ActivityData

        # Create and return an instance of the model class
        return model_class(**data)

    # If we can't determine the type, raise an error
    raise ValidationError(
        message="Cannot determine the type of the data",
        severity=ErrorSeverity.ERROR,
    )


def from_json(json_str: str) -> ActivityData | TruthData:
    """Convert a JSON string to an activity or truth data object.

    Args:
        json_str: The JSON string to convert.

    Returns:
        Union[ActivityData, TruthData]: The converted object.

    Raises:
        ValidationError: If the JSON string cannot be converted.
    """
    try:
        # Parse the JSON string
        data = json.loads(json_str)

        # Convert the dictionary to an activity or truth data object
        return from_dict(data)
    except json.JSONDecodeError as e:
        # If the JSON string is invalid, raise an error
        raise ValidationError(
            message=f"Invalid JSON string: {e}",
            severity=ErrorSeverity.ERROR,
        ) from e


def batch_to_json(data_list: list[ActivityData | TruthData | dict[str, Any]], pretty: bool = False) -> str:
    """Convert a list of activity or truth data objects to a JSON string.

    Args:
        data_list: The list of data to convert.
        pretty: Whether to format the JSON string for readability.

    Returns:
        str: The data as a JSON string.
    """
    # Convert to dictionaries
    data_dicts = [to_dict(data) for data in data_list]

    # Convert to JSON
    indent = 2 if pretty else None
    return json.dumps(data_dicts, cls=AblationJSONEncoder, indent=indent)


def batch_from_json(json_str: str) -> list[ActivityData | TruthData]:
    """Convert a JSON string to a list of activity or truth data objects.

    Args:
        json_str: The JSON string to convert.

    Returns:
        List[Union[ActivityData, TruthData]]: The converted objects.

    Raises:
        ValidationError: If the JSON string cannot be converted.
    """
    try:
        # Parse the JSON string
        data_list = json.loads(json_str)

        # Make sure it's a list
        if not isinstance(data_list, list):
            raise ValidationError(
                message="JSON string does not contain a list",
                severity=ErrorSeverity.ERROR,
            )

        # Convert each dictionary to an activity or truth data object
        result = []
        for data in data_list:
            result.append(from_dict(data))

        return result
    except json.JSONDecodeError as e:
        # If the JSON string is invalid, raise an error
        raise ValidationError(
            message=f"Invalid JSON string: {e}",
            severity=ErrorSeverity.ERROR,
        ) from e


def save_to_file(data: ActivityData | TruthData | dict[str, Any], file_path: str) -> None:
    """Save data to a file as JSON.

    Args:
        data: The data to save.
        file_path: The file path.
    """
    # Convert to JSON
    json_str = to_json(data, pretty=True)

    # Write to file
    with open(file_path, "w") as f:
        f.write(json_str)


def load_from_file(file_path: str) -> ActivityData | TruthData:
    """Load data from a file.

    Args:
        file_path: The file path.

    Returns:
        Union[ActivityData, TruthData]: The loaded data.

    Raises:
        ValidationError: If the file cannot be loaded.
    """
    try:
        # Read from file
        with open(file_path) as f:
            json_str = f.read()

        # Convert from JSON
        return from_json(json_str)
    except FileNotFoundError as e:
        # If the file is not found, raise an error
        raise ValidationError(
            message=f"File not found: {file_path}",
            severity=ErrorSeverity.ERROR,
        ) from e
    except PermissionError as e:
        # If the file cannot be read, raise an error
        raise ValidationError(
            message=f"Permission denied: {file_path}",
            severity=ErrorSeverity.ERROR,
        ) from e


def batch_save_to_file(data_list: list[ActivityData | TruthData | dict[str, Any]], file_path: str) -> None:
    """Save a list of data to a file as JSON.

    Args:
        data_list: The list of data to save.
        file_path: The file path.
    """
    # Convert to JSON
    json_str = batch_to_json(data_list, pretty=True)

    # Write to file
    with open(file_path, "w") as f:
        f.write(json_str)


def batch_load_from_file(file_path: str) -> list[ActivityData | TruthData]:
    """Load a list of data from a file.

    Args:
        file_path: The file path.

    Returns:
        List[Union[ActivityData, TruthData]]: The loaded data.

    Raises:
        ValidationError: If the file cannot be loaded.
    """
    try:
        # Read from file
        with open(file_path) as f:
            json_str = f.read()

        # Convert from JSON
        return batch_from_json(json_str)
    except FileNotFoundError as e:
        # If the file is not found, raise an error
        raise ValidationError(
            message=f"File not found: {file_path}",
            severity=ErrorSeverity.ERROR,
        ) from e
    except PermissionError as e:
        # If the file cannot be read, raise an error
        raise ValidationError(
            message=f"Permission denied: {file_path}",
            severity=ErrorSeverity.ERROR,
        ) from e
