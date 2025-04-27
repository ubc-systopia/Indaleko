"""
Recorder for incremental file system collector that writes JSONL output.
"""

import json
from pathlib import Path
from typing import Any


class FsIncrementalRecorder:
    """
    Recorder that appends file metadata events to a JSONL file.
    """

    def __init__(self, output_file: str = "data/fs_incremental_records.jsonl"):
        self.out_path = Path(output_file)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)

    def store_activities(self, activities: list[dict[str, Any]]) -> int:
        """
        Append activities to the JSONL file.

        Returns the number of records written.
        """
        count = 0
        with self.out_path.open("a", encoding="utf-8") as f:
            for act in activities:
                f.write(json.dumps(act) + "\n")
                count += 1
        return count
