import math
from collections import namedtuple
from typing import Tuple

Results = namedtuple(
    'Results', ['truth_number', 'filler_number', 'original_number', 'precision', 'recall', 'returned_uuid']
)

class ResultCalculator():
    """
    A service for calculating the precision and recall of the search 
    """
    def __init__(self) -> None:
        """
        Initializes the calculator.
        """
        pass
    
    def calculate_stats(self, list_truth: list[str], list_filler: list[str], raw_results:list[str]) -> \
        Tuple[int, int, list[str]]:
        '''
        Calculates the number of truth metadata given the raw_results based on UUID
        Args: 
            raw_results (list[str]): items returned by the Indaleko search result
        Returns:
            int: the total number of truth, filler metdata and the list of returned uuid
        '''
        truth_set = set()
        filler_set = set()
        selected_uuid = []

        for result in raw_results:
            print(result)
            uuid = result['result']['Record']['SourceIdentifier']['Identifier']
            selected_uuid.append(uuid)
            
            assert uuid not in truth_set, "Search result contains duplicate objects."
            assert uuid not in filler_set, "Search result contains duplicate objects."

            if uuid in list_truth:
                truth_set.add(uuid)
            elif uuid in list_filler:
                filler_set.add(uuid)
        return len(truth_set), len(filler_set), selected_uuid
    
    def calculate_precision(self, total_n_truth: int, total_n_results: int) -> float:
        '''
        Calculates the precision of the search
        Args: 
            total_n_truth (int): total number of truth files returned
            total_n_results (int): total number of files returned
        Returns:
            int: precision
        '''
        if total_n_results == 0:
            return math.nan
        return total_n_truth / total_n_results

    def calculate_recall(self, total_n_truth: int, n_truth_metadata:int) -> float:
        '''
            Calculates the precision of the search
            Args: 
                total_n_truth (int): total number of truth files returned
                n_truth_metadata (int): total number of truth files
            Returns:
                int: recall
        '''
        if n_truth_metadata == 0:
            return math.nan
        return total_n_truth / n_truth_metadata
    
    
    def run(self, truth_list: list[str], filler_list: list[str], raw_results: list[str], expected_truth_number: int) \
        -> Results:
        '''
            Main function to calculate precision and recall
            Args: 
                raw_results (list[str]): list of items returned by the Indaleko search 
                n_truth_md (int): total number of truth files in the dataset
            Returns:
                tuple[int, int, int]: recall, precision
        '''
        actual_truth_number, filler_number, selected_uuid = self.calculate_stats(truth_list, filler_list, raw_results)
        returned_number = len(raw_results)
        original_number = returned_number - actual_truth_number - filler_number

        precision = self.calculate_precision(actual_truth_number, returned_number)
        recall = self.calculate_recall(actual_truth_number, expected_truth_number)
        return Results(actual_truth_number, filler_number, original_number, precision, recall, selected_uuid)
