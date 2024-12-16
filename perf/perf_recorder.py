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
import sys
import uuid

from icecream import ic

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
from perf_collector import IndalekoPerformanceDataCollector
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

    def create_data(self, **kwargs) -> IndalekoPerformanceDataModel:
        '''Create a new performance data object.'''
        return IndalekoPerformanceDataModel(**kwargs)

    def add_data(self, perf_data: IndalekoPerformanceDataModel) -> None:
        '''Add performance data to the collection.'''
        ic('add_data')
        ic(perf_data)
        doc = perf_data.serialize()
        ic(doc)
        self.perf_data_collection.insert(doc)

def main():
    """Test code for the IndalekoPerformanceData class."""
    ic('IndalekoPerformanceDataRecorder test code')
    test_perf_data = IndalekoPerformanceDataCollector(
        **IndalekoPerformanceDataCollector.test_data
    )
    ic(test_perf_data.serialize())
    perf_data_recorder = IndalekoPerformanceDataRecorder()
    perf_data_recorder.add_data(test_perf_data)

if __name__ == "__main__":
    main()
