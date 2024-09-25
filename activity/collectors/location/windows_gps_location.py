'''
This module defines a utility for acquiring GPS data for a windows system and
recording it in the database.

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
import os
import sys
import uuid

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from activity.provider_registration import IndalekoActivityDataProviderRegistration
from data_models.activity_data_provider_registration import IndalekoActivityDataProviderRegistrationDataModel
from data_models.indaleko_record_data_model import IndalekoRecordDataModel
from data_models.indaleko_source_identifier_data_model import IndalekoSourceIdentifierDataModel
# pylint: enable=wrong-import-position

class WindowsGPSLocationCollector:
    '''This class provides a utility for acquiring GPS data for a windows system
    and recording it in the database.'''

    identifier = uuid.UUID('7e85669b-ecc7-4d57-8b51-8d325ea84930')
    version = '1.0.0'
    description = 'Windows GPS Location Collector'

    def __init__(self):
        '''Initialize the Windows GPS Location Collector.'''
        self.db_config = IndalekoDBConfig()
        assert self.db_config is not None, 'Failed to get the database configuration'
        kwargs = {
            'Identifier' : str(self.identifier),
            'Version' : self.version,
            'Description' : self.description,
            'Record' : IndalekoRecordDataModel(
                SourceIdentifier=IndalekoSourceIdentifierDataModel(
                    Identifier=str(self.identifier),
                    Version=self.version,
                    Description=self.description
                ),
                Timestamp=datetime.now(),
                Attributes={},
                Data=''
            )
        }

        self.registration_data_object = IndalekoActivityDataProviderRegistration(**kwargs)



def main():
    '''Main entry point for the Windows GPS Location Collector.'''
    ic('Starting Windows GPS Location Collector')
    collector = WindowsGPSLocationCollector()
    ic('Finished Windows GPS Location Collector')

if __name__ == '__main__':
    main()
