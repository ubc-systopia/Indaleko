from typing import Dict, Any
import random
from datetime import datetime
from data_models.record import IndalekoRecordDataModel
from data_generator.scripts.metadata.metadata import Metadata

class ActivityMetadata(Metadata):
    """
    Abstract class for Activity Metadata.
    Consists of helper functions for activity context subclasses
    """
    def __init__(self, selected_AC_md):
        super().__init__(selected_AC_md)
    
    def generate_metadata(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], 
                            is_truth_file: bool, truth_like:bool, truthlike_attributes:list[str]) -> Any:
        raise NotImplementedError("This method must be implemented by subclasses")

    # helper functions for activity timestamps:
    def _generate_ac_timestamp(self, is_truth_file:bool, timestamps: Dict[str, str], activity_type: str) -> str:
        """
        Generate the activity context timestamp
        """
        timestamp_types = ["birthtime", "modified", "accessed", "changed"]
        if activity_type in self.selected_md and "timestamp" in self.selected_md[activity_type]:
            time_query = self.selected_md[activity_type]["timestamp"]
            if is_truth_file:
                return timestamps[time_query].strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp_types.remove(time_query)
                return timestamps[random.choice(timestamp_types)].strftime("%Y-%m-%dT%H:%M:%SZ")
        else: 
            return timestamps[random.choice(timestamp_types)].strftime("%Y-%m-%dT%H:%M:%SZ")

    def _generate_number(self, is_truth_file:bool, general_dict: dict[str], lower_bound: float, upper_bound:float) -> float:
        """
        generates number based on general dict given in the format:
        {start: float, end: float, command: one of [“range”, “equals”], lower_bound, upper_bound}
        """
        target_min = general_dict["start"]
        target_max = general_dict["end"]
        command = general_dict["command"]
        delta = 0.5

        if target_max == upper_bound and target_min == lower_bound:
                raise ValueError("The range cannot be the whole boundary from ", target_min, " to ", target_max)
        elif target_min > target_max:
            raise ValueError(f"The target min {target_min} cannot be greater than the target max {target_max}")


        # if the size is the same as the target_max then just choose that file size
        if target_min == target_max and command == "equal":
            if is_truth_file:
                return target_min
            else:
                return self._check_return_value_within_range(lower_bound, upper_bound, target_min,  target_max, random.uniform, delta)

        #if command specifies getting the range between two values
        elif target_min != target_max and command == "range":
            if is_truth_file:
                return random.uniform(target_min, target_max)
            else:
                return self._check_return_value_within_range(lower_bound, upper_bound, target_min,  target_max, random.uniform, delta)
        else:
            raise ValueError("Invalid parameter or command, please check your query again.")


    def _choose_random_element(self, is_truth_file: bool, truth_attribute: str, attribute_lists: list[str]) -> str:
        """based on whether the file is a truth or filler file, returns the appropriate value"""
        if is_truth_file:
            return truth_attribute
        else:
            attribute_lists.remove(truth_attribute)
            return random.choice(attribute_lists)