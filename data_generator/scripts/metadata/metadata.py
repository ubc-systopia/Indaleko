import random
from typing import Callable, Any
from abc import ABC, abstractmethod
import json

class Metadata(ABC):
    """
    Abstract class for Metadata.
    """
    TEXT_FILE_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt", ".rtf", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"]

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
        default_min: float, default_max: float, 
        target_min: float, target_max: float, 
        random_func: Callable[[float, float], float], 
        delta: float = 0
    ) -> float:
        """
        General function to check and return a value (int or float) that is not within 
        the specified target range.
        """

        if target_min - delta >= default_min and target_max + delta <= default_max:
            return random.choice([
                random_func(default_min, target_min - delta),
                random_func(target_max + delta, default_max)
            ])
        elif target_min - delta < default_min and target_max + delta <= default_max:
            return random_func(target_max + delta, default_max)
        elif target_min - delta >= default_min and target_max + delta > default_max:
            return random_func(default_min, target_min - delta)
        else:
            raise ValueError("Invalid query")

    def _define_truth_attribute(self, attribute: str, truth_file: bool, truthlike_file: bool, truth_attributes: list[str]) -> bool:
        """
        Returns true if the file is a truth file or the attribute is contained in the truthlike attribute list
        """
        return truth_file or (truthlike_file and attribute in truth_attributes)
    
    def _generate_number(self, is_truth_file:bool, general_dict: dict[str], lower_bound: float, upper_bound:float) -> float:
        """
        Generates number based on general dict given in the format:
        {start: float, end: float, command: one of [“range”, “equals”], lower_bound, upper_bound}
        """
        target_min = general_dict["start"]
        target_max = general_dict["end"]
        command = general_dict["command"]
        delta = 0.5

        if target_max == upper_bound and target_min == lower_bound:
                raise ValueError(
                    "The range cannot be the whole boundary from ", target_min, " to ", target_max
                )
        elif target_min > target_max:
            raise ValueError(
                f"The target min {target_min} cannot be greater than the target max {target_max}"
            )


        # if the size is the same as the target_max then just choose that file size
        if target_min == target_max and command == "equal":
            if is_truth_file:
                return target_min
            else:
                return self._check_return_value_within_range(
                    lower_bound, upper_bound, target_min,  target_max, random.uniform, delta
                )

        #if command specifies getting the range between two values
        elif target_min != target_max and command == "range":
            if is_truth_file:
                return random.uniform(target_min, target_max)
            else:
                return self._check_return_value_within_range(
                    lower_bound, upper_bound, target_min,  target_max, random.uniform, delta
                )
        else:
            raise ValueError("Invalid parameter or command, please check your query again.")