'''
Result calculator that calculates the final precision and recall
'''

from icecream import ic

class ResultCalculator():
    def __init__(self) -> None:
        self.selected_uuid = []
        self.selected_metadata = []
    
    # calculate the number of truth metadata given the raw_results based on UUID
    def calculate_n_truth_metadata(self, raw_results:list[str]) -> int:
        n_actual_truth = 0
        for result in raw_results:
            uuid = result['result']['Record']['SourceIdentifier']['Identifier']
            self.selected_uuid.append(uuid)
            self.selected_metadata.append(result['result'])

            if uuid.startswith("c"):
                n_actual_truth += 1
        self.n_truth_metadata = n_actual_truth
        return n_actual_truth
    
    # calculate the precision 
    def calculate_precision(self, total_n_truth, total_n_results):
        if total_n_results == 0:
            return "precision NA: total number of retrieved results is 0"
        return total_n_truth / total_n_results

    #calculate the recall
    def calculate_recall(self, total_n_truth, n_truth_metadata):
        return total_n_truth / n_truth_metadata

    # main run function to calculate precision and recall
    def run(self, raw_results, theoretical_truth_n) -> tuple[int, int]:
        n_truth_number = self.calculate_n_truth_metadata(raw_results)
        total_returned_n = len(raw_results)
        
        recall = self.calculate_recall(n_truth_number, theoretical_truth_n)
        precision = self.calculate_precision(n_truth_number, total_returned_n)
        return recall, precision
        
def main():
    raw_results = [
    {
        "result": {
            "_key": "547834",
            "_id": "Objects/547834",
            "_rev": "_i1RndYS---",
            "Record": {
                "SourceIdentifier": {
                    "Identifier": "c1000000-6888-9116-0545-724034001557",
                    "Version": "1.0",
                    "Description": "Record UUID"
                },
                "Timestamp": "2024-11-28T14:34:37Z",
                "Attributes": {
                    "Name": "GojlyXqa.pdf",
                    "Path": "/file/d/APx/view/view?name=GojlyXqa.pdf",
                    "st_birthtime": "1732774147.236861",
                    "st_birthtime_ns": "1.732774147236861e+18",
                    "st_mtime": "1732789319.114706",
                    "st_mtime_ns": "1.732789319114706e+18",
                    "st_atime": "1732774147.236861",
                    "st_atime_ns": "1.732774147236861e+18",
                    "st_ctime": "1732774147.236861",
                    "st_ctime_ns": "1.732774147236861e+18",
                    "st_size": 8896604808
                },
                "Data": "lh6RJTQ81iKUrozjixGRjJC6P4nYriL65qoaD8BXzedJcZMn4CQaHBhk6UUWSRicnBYtFOq4CEIg78MEuuA",
                "URI": "https://drive.google.com/file/d/APx/view/view?name=GojlyXqa.pdf",
                "ObjectIdentifier": "66703878-4803-7992-8873-929660305812",
                "Timestamps": [
                    {"Label": "c1000000-6888-9116-0545-724034001557", "Value": "2024-11-27T22:09:07Z", "Description": "birthtime"},
                    {"Label": "c1000000-6888-9116-0545-724034001557", "Value": "2024-11-27T22:09:07Z", "Description": "accessed"},
                    {"Label": "c1000000-6888-9116-0545-724034001557", "Value": "2024-11-27T22:09:07Z", "Description": "changed"},
                    {"Label": "c1000000-6888-9116-0545-724034001557", "Value": "2024-11-28T02:21:59Z", "Description": "modified"}
                ],
                "Size": 8896604808,
                "SemanticAttributes": [
                    {"Identifier": {"Identifier": "68891382-7966-4929-7211-497875296656", "Label": "LastModified"}, "Data": "2024-11-28T02:21:59"},
                    {"Identifier": {"Identifier": "68891382-7966-4929-7211-497875296656", "Label": "FileType"}, "Data": "pdf"}
                ],
                "Label": "Truth File #1",
                "LocalIdentifier": "1",
                "Volume": "66703878-4803-7992-8873-929660305812",
                "PosixFileAttributes": "S_IFREG",
                "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE"
            }
        }
    },
    {
        "result": {
            "_key": "547880",
            "_id": "Objects/547880",
            "_rev": "_i1RndnO---",
            "Record": {
                "SourceIdentifier": {
                    "Identifier": "f2000000-9682-1165-6769-137883870872",
                    "Version": "1.0",
                    "Description": "Record UUID"
                },
                "Timestamp": "2024-11-28T14:34:37Z",
                "Attributes": {
                    "Name": "Q.pdf",
                    "Path": "/file/d/hY9/view/view?name=Q.pdf",
                    "st_birthtime": "1732759553.851085",
                    "st_birthtime_ns": "1.732759553851085e+18",
                    "st_mtime": "1732759553.851085",
                    "st_mtime_ns": "1.732759553851085e+18",
                    "st_atime": "1732777333.034407",
                    "st_atime_ns": "1.732777333034407e+18",
                    "st_ctime": "1732832727.306405",
                    "st_ctime_ns": "1.732832727306405e+18",
                    "st_size": 9267869216
                },
                "Data": "SpaHMuBGAo5i6dghe16ldhnAKPfCmiA0a0E3DISnpxGyEw1sh1XgAIJjlN2lXtUTqU4iuCBZHxAOWNV1CI0S9Ka2GhMiI0UEIkYjEnSfEA1E1xXNr5SJDi93TKCqB5PCeMjcsgkj1qHxGgb8xvqwYsm5X0LIEfZPqZ0f9f4gHDWhSZagBGaBSZm97YpP8Mdg93ce5kG8QbuUL0ale3GsV0AeRgINUyDuDdXTgRso3wgyPfrHysINbSfdw4Q5W3CCCTKfaDAmK85KD8kE0C3kWF1Ja5y2sXdqaHneKEHHT4ToUPFeOz0OZNmUHd2jZHHhlycczi6pAD6g3TyHqXFH4aXSzBSVATLjEpCpv9KbzonxW0ZDKnOLjD0xsNFjBZWmKgMz2z5lSfH7gIgWboDVBYmpQAhHy9eCkzjUwK6MDzIh6uyzb4I9simGE4bBc1DPSzt8cnXARjD2700uKzkJC",
                "URI": "https://drive.google.com/file/d/hY9/view/view?name=Q.pdf",
                "ObjectIdentifier": "14413961-4018-3892-6642-955377935408",
                "Timestamps": [
                    {"Label": "c2000000-9682-1165-6769-137883870872", "Value": "2024-11-27T18:05:53Z", "Description": "birthtime"},
                    {"Label": "c2000000-9682-1165-6769-137883870872", "Value": "2024-11-27T18:05:53Z", "Description": "modified"},
                    {"Label": "c2000000-9682-1165-6769-137883870872", "Value": "2024-11-27T23:02:13Z", "Description": "accessed"},
                    {"Label": "c2000000-9682-1165-6769-137883870872", "Value": "2024-11-28T14:25:27Z", "Description": "changed"}
                ],
                "Size": 9267869216,
                "SemanticAttributes": [
                    {"Identifier": {"Identifier": "30433167-9100-2898-8352-312055959594", "Label": "LastModified"}, "Data": "2024-11-27T18:05:53"},
                    {"Identifier": {"Identifier": "30433167-9100-2898-8352-312055959594", "Label": "FileType"}, "Data": "pdf"}
                ],
                "Label": "Truth File #2",
                "LocalIdentifier": "2",
                "Volume": "14413961-4018-3892-6642-955377935408",
                "PosixFileAttributes": "S_IFREG",
                "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE"
            }
        }
    }
]
    calculator = ResultCalculator()
    recall, precision = calculator.run(raw_results, 2)
    ic(recall)
    ic(precision)



if __name__ == '__main__':
    main()
    

    
