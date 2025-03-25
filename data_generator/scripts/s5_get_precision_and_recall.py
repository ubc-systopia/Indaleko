from icecream import ic
import math


class ResultCalculator:
    """
    A service for calculating the precision and recall of the search
    """

    def __init__(self) -> None:
        """
        Initializes the calculator.
        """
        self.selected_uuid = []
        self.selected_metadata = []

    def calculate_n_truth_metadata(self, raw_results: list[str]) -> int:
        """
        Calculates the number of truth metadata given the raw_results based on UUID
        Args:
            raw_results (list[str]): items returned by the Indaleko search result
        Returns:
            int: the total number of truth metadata returned by Indaleko
        """
        truth_set = set()

        for result in raw_results:
            uuid = result["result"]["Record"]["SourceIdentifier"]["Identifier"]
            self.selected_uuid.append(uuid)
            self.selected_metadata.append(result["result"])

            assert uuid not in truth_set, "Result contains duplicate objects."

            if uuid.startswith("c"):
                truth_set.add(uuid)
        return len(truth_set)

    def calculate_precision(self, total_n_truth: int, total_n_results: int) -> float:
        """
        Calculates the precision of the search
        Args:
            total_n_truth (int): total number of truth files returned
            total_n_results (int): total number of files returned
        Returns:
            int: precision
        """
        if total_n_results == 0:
            return math.nan
        return total_n_truth / total_n_results

    def calculate_recall(self, total_n_truth: int, n_truth_metadata: int) -> float:
        """
        Calculates the precision of the search
        Args:
            total_n_truth (int): total number of truth files returned
            n_truth_metadata (int): total number of truth files
        Returns:
            int: recall
        """
        if n_truth_metadata == 0:
            return math.nan
        return total_n_truth / n_truth_metadata

    def run(
        self, raw_results: list[str], theoretical_truth_n: int
    ) -> tuple[int, int, int]:
        """
        Main function to calculate precision and recall
        Args:
            raw_results (list[str]): list of items returned by the Indaleko search
            theoretical_truth_n (int): total number of truth files in the dataset
        Returns:
            tuple[int, int, int]: recall, precision
        """
        n_truth_number = self.calculate_n_truth_metadata(raw_results)
        total_returned_n = len(raw_results)

        precision = self.calculate_precision(n_truth_number, total_returned_n)
        recall = self.calculate_recall(n_truth_number, theoretical_truth_n)

        return n_truth_number, precision, recall
