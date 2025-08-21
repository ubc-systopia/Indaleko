"""Metadata class for generating metadata."""

import random

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Metadata(ABC):
    """Abstract class for Metadata."""

    TEXT_FILE_EXTENSIONS = [  # noqa: RUF012
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".rtf",
        ".csv",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
    ]

    def __init__(self, selected_md: dict) -> None:
        self.selected_md = selected_md

    @abstractmethod
    def generate_metadata(self, **kwargs: Any) -> Any:
        """Generates metadata specific to the subclass."""
        raise NotImplementedError("Ensure that the subclass implements this method")

    def _check_return_value_within_range(
        self,
        default_min: float,
        default_max: float,
        target_min: float,
        target_max: float,
        random_func: Callable[[float, float], float],
        delta: float = 0,
    ) -> float:
        """
        Check if the target range is within the default range and return a value.

        General function to check and return a value (int or float) that is not within
        the specified target range.
        """
        if target_min - delta >= default_min and target_max + delta <= default_max:
            return random.choice(  # noqa: S311
                [
                    random_func(default_min, target_min - delta),
                    random_func(target_max + delta, default_max),
                ],
            )
        if target_min - delta < default_min and target_max + delta <= default_max:
            return random_func(target_max + delta, default_max)
        if target_min - delta >= default_min and target_max + delta > default_max:
            return random_func(default_min, target_min - delta)
        raise ValueError("Invalid query")

    def _define_truth_attribute(
        self,
        attribute: str,
        truth_file: bool,  # noqa: FBT001
        truthlike_file: bool,  # noqa: FBT001
        truth_attributes: list[str],
    ) -> bool:
        """
        Defines truth attribute.

        Returns true if the file is a truth file or the attribute is
        contained in the truthlike attribute list.
        """
        return truth_file or (truthlike_file and attribute in truth_attributes)

    @staticmethod
    def return_JSON(obj):
        """Convert an object to its dictionary representation for JSON serialization."""
        if hasattr(obj, "dict"):
            data = obj.dict()
            # Process the dictionary to make it JSON serializable
            return Metadata._make_json_serializable(data)
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
            return Metadata._make_json_serializable(data)
        if hasattr(obj, "hex"):  # UUID object
            return str(obj)
        if hasattr(obj, "isoformat"):  # datetime object
            return obj.isoformat()
        return obj

    @staticmethod
    def _make_json_serializable(data):
        """Helper method to convert objects in a dictionary to JSON serializable format."""
        import datetime

        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = Metadata._make_json_serializable(value)
            return result
        if isinstance(data, list):
            return [Metadata._make_json_serializable(item) for item in data]
        if hasattr(data, "hex"):  # UUID objects have a hex attribute
            return str(data)
        if isinstance(data, (datetime.datetime, datetime.date)):
            return data.isoformat()
        return data

    def _generate_number(
        self,
        is_truth_file: bool,  # noqa: FBT001
        general_dict: dict[str],
        lower_bound: float,
        upper_bound: float,
    ) -> float:
        """
        Generate number.

        Generates number based on general dict given in the format:
        {start: float, end: float, command: one of [“range”, “equals”], lower_bound, upper_bound}.
        """
        target_min = general_dict["start"]
        target_max = general_dict["end"]
        command = general_dict["command"]
        delta = 0.5

        if target_max == upper_bound and target_min == lower_bound:
            raise ValueError(
                "The range cannot be the whole boundary from ",
                target_min,
                " to ",
                target_max,
            )
        if target_min > target_max:
            raise ValueError(
                f"The target min {target_min} cannot be greater than the target max {target_max}",
            )

        # if the size is the same as the target_max then just choose that file size
        if target_min == target_max and command == "equal":
            if is_truth_file:
                return target_min
            return self._check_return_value_within_range(
                lower_bound,
                upper_bound,
                target_min,
                target_max,
                random.uniform,
                delta,
            )

        # if command specifies getting the range between two values
        if target_min != target_max and command == "range":
            if is_truth_file:
                return random.uniform(target_min, target_max)  # noqa: S311
            return self._check_return_value_within_range(
                lower_bound,
                upper_bound,
                target_min,
                target_max,
                random.uniform,
                delta,
            )
        raise ValueError("Invalid parameter or command, please check your query again.")
