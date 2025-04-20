#!/usr/bin/env python3
"""
Prototype CLI: StorageIndexer
Inherits from IndalekoBaseCLI and indexes local storage via LocalStorageCollector.
"""
import json
from pathlib import Path

from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from activity.collectors.storage.local.collector import LocalStorageCollector

class StorageIndexerCLI(IndalekoBaseCLI):
    def __init__(self):
        cli_data = IndalekoBaseCliDataModel()
        super().__init__(cli_data=cli_data)

    def main(self):
        args = self.get_args()
        input_dir = Path(args.datadir).expanduser()
        collector = LocalStorageCollector(path=str(input_dir))
        records = list(collector.collect())

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, default=str, indent=2)
        print(f"Written {len(records)} records to {output_path}")

if __name__ == "__main__":
    StorageIndexerCLI().main()