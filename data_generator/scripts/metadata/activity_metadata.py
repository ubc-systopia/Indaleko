"""Generate Activity Context Metadata."""
import random

from data_generator.scripts.metadata.metadata import Metadata


class ActivityMetadata(Metadata):
    """
    Abstract class for Activity Metadata.

    Consists of helper functions for activity context subclasses.
    """

    TIMESTAMPS = ["birthtime", "modified", "accessed", "changed"]  # noqa: RUF012


    # helper functions for activity timestamps:
    def _generate_ac_timestamp(
        self,
        is_truth_file: bool,  # noqa: FBT001
        timestamps: dict[str, str],
        activity_type: str,
    ) -> str:
        """Generate the activity context timestamp."""
        timestamp_types = self.TIMESTAMPS.copy()
        if activity_type in self.selected_md and "timestamp" in self.selected_md[activity_type]:
            time_query = self.selected_md[activity_type]["timestamp"]
            if is_truth_file:
                return timestamps[time_query].strftime("%Y-%m-%dT%H:%M:%SZ")
            timestamp_types.remove(time_query)
            return timestamps[random.choice(timestamp_types)].strftime(  # noqa: S311
                "%Y-%m-%dT%H:%M:%SZ",
            )
        return timestamps[random.choice(timestamp_types)].strftime(  # noqa: S311
            "%Y-%m-%dT%H:%M:%SZ",
        )

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
        raise ValueError(
            "Invalid parameter or command, please check your query again.",
        )

    def _choose_random_element(
        self,
        is_truth_file: bool,  # noqa: FBT001
        truth_attribute: str,
        attribute_lists: list[str],
    ) -> str:
        """Based on whether the file is a truth or filler file, returns the appropriate value."""
    def _choose_random_element(
            self,
            is_truth_file: bool,  # noqa: FBT001
            truth_attribute: str,
            attribute_lists: list[str],
    ) -> str:
        """Based on whether the file is a truth or filler file, returns the appropriate value."""
        if is_truth_file:
            return truth_attribute
        attributes = attribute_lists.copy()
        attributes.remove(truth_attribute)
        return random.choice(attributes)  # noqa: S311
