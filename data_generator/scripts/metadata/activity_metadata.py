from typing import Dict, Any
import random
from datetime import datetime
from data_models.record import IndalekoRecordDataModel
from data_generator.scripts.metadata.metadata import Metadata

timestamp_types = ["birthtime", "modified", "accessed", "changed"]

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
        if activity_type in self.selected_md and "timestamp" in self.selected_md[activity_type]:
            time_query = self.selected_md[activity_type]["timestamp"]
            if is_truth_file:
                return timestamps[time_query].strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp_types.remove(time_query)
                return timestamps[random.choice(timestamp_types)].strftime("%Y-%m-%dT%H:%M:%SZ")
        else: 
            return timestamps[random.choice(timestamp_types)].strftime("%Y-%m-%dT%H:%M:%SZ")

    def _choose_random_element(self, is_truth_file: bool, truth_attribute: str, attribute_lists: list[str]) -> str:
        """based on whether the file is a truth or filler file, returns the appropriate value"""
        if is_truth_file:
            return truth_attribute
        else:
            attribute_lists.remove(truth_attribute)
            return random.choice(attribute_lists)