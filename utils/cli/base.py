'''
This module provides a baseline definition of the Indaleko CLI.

Indaleko Windows Local Collector
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
from abc import ABC, abstractmethod
import argparse
import datetime
import logging
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
from utils import IndalekoLogging
from data_model import IndalekoBaseCliDataModel
# pylint: enable=wrong-import-position

class IndalekoBaseCli(ABC):
    '''This defines the base CLI class for Indaleko'''

    def __init__(self):
        '''Initializes the CLI class'''
        logging_levels = IndalekoLogging.get_logging_levels()
        pre_parser = argparse.ArgumentParser(add_help=False)
        # step 1: set up the config, log, and data directories
        # because we need them to determine what other options
        # might be.
        pre_parser.add_argument('--config-dir', type=str, default=None, help='The configuration directory.')
        pre_parser.add_argument('--data-dir', type=str, default=None, help='The data directory.')
        pre_parser.add_argument('--log-dir', type=str, default=None, help='The log directory.')
