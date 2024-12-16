'''
This module provides a base for the IndalekoPerformance data object.

Project Indaleko
Copyright (C) 2024 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

'''
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import uuid

from icecream import ic
import jsonlines
from typing import Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models import IndalekoPerformanceDataModel
from db import IndalekoCollections, IndalekoDBCollections
from utils.misc.data_management import encode_binary_data
from utils.misc.file_name_management import generate_file_name
from utils.misc.directory_management import indaleko_default_data_dir
from perf.perf_collector import IndalekoPerformanceDataCollector
# pylint: enable=wrong-import-position

class IndalekoPerformanceDataRecorder:
    '''
    The IndalekoPerformanceData class is used to collect, store,
    and query performance data gathered by Indaleko tools for
    further analysis.
    '''

    def __init__(self):
        '''Initialize the object.'''
        self.perf_data_collection = IndalekoCollections().get_collection(IndalekoDBCollections.Indaleko_Performance_Data_Collection)

    def generate_perf_file_name(self,
                                platform : str,
                                service : str,
                                machine : Union[str, uuid.UUID]) -> str:
        '''Generate a performance data file name.'''
        if isinstance(machine, uuid.UUID):
            machine = machine.hex
        return generate_file_name(
            prefix = 'indaleko',
            platform = platform,
            service = service.replace('-','_') + '_perf',
            machine = machine,
            timestamp = None,
        )

    def create_data(self, **kwargs) -> IndalekoPerformanceDataModel:
        '''Create a new performance data object.'''
        return IndalekoPerformanceDataModel(**kwargs)


    def add_data_to_db(self, perf_data: IndalekoPerformanceDataModel) -> None:
        '''
        Add performance data to the collection.

        Inputs:
            - file_name: the name of the file to write the data to
            - perf_data: the performance data to write to the file
        '''
        doc = perf_data.serialize()
        assert perf_data, "perf_data must be provided"
        self.perf_data_collection.insert(doc)

    def add_data_to_file(self, file_name : str, perf_data: IndalekoPerformanceDataModel) -> None:
        '''
        Add performance data to a file.

        Inputs:
            - file_name: the name of the file to write the data to
            - perf_data: the performance data to write to the file
        '''
        ic(file_name)
        assert file_name, "file_name must be provided"
        assert file_name.endswith('.jsonl'), f"{file_name} must be in JSONL format"
        assert perf_data, "perf_data must be provided"
        with jsonlines.open(file_name, mode='a') as writer:
            writer.write(perf_data.serialize())

def main():
    """Test code for the IndalekoPerformanceData class."""
    ic('IndalekoPerformanceDataRecorder test code')
    test_perf_data = IndalekoPerformanceDataCollector(
        **IndalekoPerformanceDataCollector.test_data
    )
    ic(test_perf_data.serialize())
    perf_data_recorder = IndalekoPerformanceDataRecorder()
    perf_data_recorder.add_data_to_db(test_perf_data)
    file_name = os.path.join(indaleko_default_data_dir, perf_data_recorder.generate_perf_file_name(
        platform = 'test',
        service = 'test',
        machine = uuid.UUID('27b1688c-86c0-4ca7-83e9-33e712bfaf54').hex
    ))
    ic(file_name)
    perf_data_recorder.add_data_to_file(file_name, test_perf_data)


if __name__ == "__main__":
    main()
