"""
This module provides an interface for retrieving information about the activity metadata
providers.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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
"""
# import argparse
import os
# import json
from pathlib import Path
# import tempfile
# import shutil
# import subprocess
import sys

from icecream import ic
# from typing import Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(Path(current_path) / 'Indaleko.py'):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
# pylint: enable=wrong-import-position


class IndalekoActivityMetadata:
    '''
    This class provides an interface for retrieving information about the activity metadata providers.
    '''

    def __init__(self):
        '''Initialize the object.'''
        self.activity_providers = IndalekoActivityDataRegistrationService.get_provider_list()
        ic(self.activity_providers)

    def get_activity_metadata_providers(self) -> list:
        '''
        This method retrieves the activity metadata providers.
        '''

    def get_activity_provider_information(self, provider: str) -> dict:
        '''
        This method retrieves the information for a specific activity metadata provider.
        '''


def main():
    '''This is a CLI tool for managing the Indaleko collection metadata.'''
    ic('Hello, world!')
    IndalekoActivityMetadata()


if __name__ == "__main__":
    main()
