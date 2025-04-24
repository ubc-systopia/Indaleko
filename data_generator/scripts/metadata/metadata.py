import json
import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Metadata(ABC):
    """
    Abstract class for Metadata.
    """

    TEXT_FILE_EXTENSIONS = [
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

    def __init__(self, selected_md):
        self.selected_md = selected_md

    @abstractmethod
    def generate_metadata(self, **kwargs: Any) -> Any:
        """Generates metadata specific to the subclass"""
        raise NotImplementedError("Ensure that the subclass implements this method")

    def return_JSON(metadata: Any):
        return json.loads(metadata.json())

    def _check_return_value_within_range(
        self,
        default_min: int | float,
        default_max: int | float,
        target_min: int | float,
        target_max: int | float,
        random_func: Callable[
            [int | float, int | float],
            int | float,
        ],
        delta: int | float = 0,
    ) -> int | float:
        """General function to check and return a value (int or float) that is not within the specified target range."""
        if target_min - delta >= default_min and target_max + delta <= default_max:
            return random.choice(
                [
                    random_func(default_min, target_min - delta),
                    random_func(target_max + delta, default_max),
                ],
            )
        elif target_min - delta < default_min and target_max + delta <= default_max:
            return random_func(target_max + delta, default_max)
        elif target_min - delta >= default_min and target_max + delta > default_max:
            return random_func(default_min, target_min - delta)
        else:
            raise ValueError("Invalid query")

    def _define_truth_attribute(
        self,
        attribute: str,
        truth_file: bool,
        truthlike_file: bool,
        truth_attributes: list[str],
    ) -> bool:
        """Returns true if the file is a truth file or the attribute is contained in the truthlike attribute list"""
        return truth_file or (truthlike_file and attribute in truth_attributes)
