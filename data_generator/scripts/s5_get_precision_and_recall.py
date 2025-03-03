from icecream import ic
import math

class ResultCalculator():
    """
    A service for calculating the precision and recall of the search 
    """
    def __init__(self) -> None:
        """
        Initializes the calculator.
        """
        self.selected_uuid = []
        self.selected_metadata = []
    
    def calculate_stats(self, list_truth: list[str], list_filler: list[str], raw_results:list[str]) -> int:
        '''
        Calculates the number of truth metadata given the raw_results based on UUID
        Args: 
            raw_results (list[str]): items returned by the Indaleko search result
        Returns:
            int: the total number of truth metadata returned by Indaleko
        '''
        truth_set = set()
        filler_set = set()

        for result in raw_results:
            uuid = result['result']['Record']['SourceIdentifier']['Identifier']
            self.selected_uuid.append(uuid)
            self.selected_metadata.append(result['result'])
            
            assert uuid not in truth_set, "Result contains duplicate objects."
            assert uuid not in filler_set, "Result contains duplicate objects."

            # if uuid.startswith("c"):

            if uuid in list_truth:
                truth_set.add(uuid)
            elif uuid in list_filler:
                filler_set.add(uuid)
        ic(list_truth)
        ic(list_filler)
        ic(truth_set)
        ic(filler_set)
        return len(truth_set), len(filler_set)
    
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
    
    
    def run(self, truth_list: list[str], filler_list: list[str], raw_results: list[str], n_truth_md: int) -> tuple[int, int, int]:
        '''
            Main function to calculate precision and recall
            Args: 
                raw_results (list[str]): list of items returned by the Indaleko search 
                n_truth_md (int): total number of truth files in the dataset
            Returns:
                tuple[int, int, int]: recall, precision
        '''
        n_truth_number, n_filler_number = self.calculate_stats(truth_list, filler_list, raw_results)
        total_returned_n = len(raw_results)
        original_number = total_returned_n - n_truth_number - n_filler_number


        precision = self.calculate_precision(n_truth_number, total_returned_n)
        recall = self.calculate_recall(n_truth_number, n_truth_md)

        return n_truth_number, n_filler_number, original_number, precision, recall
