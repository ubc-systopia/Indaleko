'''
This module defines the base data model used by the Indaleko storage recorders.

Indaleko Storage Recorder Data Model
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
'''
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import os
import platform
import sys
from typing import Optional, List, Dict, Any, Union
from uuid import UUID, uuid4

from pydantic import Field, AwareDatetime, BaseModel
from icecream import ic


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models.base import IndalekoBaseModel
from db import IndalekoDBConfig
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
from utils.misc.file_name_management import indaleko_file_name_prefix
from utils.misc.file_name_management import find_candidate_files
# pylint: enable=wrong-import-position

class IndalekoStorageRecorderDataModel(BaseModel):
    '''Defines the base data model for the storage recorders'''
    RecorderPlatformName : Optional[Union[str, None]] = \
        Field(None,
              title='PlatformName',
              description='The name of the platform (e.g., Linux, Windows, etc.) if any (default=None).'
              )
    RecorderServiceName : str = Field(..., title='RecorderName', description='The service name of the recorder.')
    RecorderServiceUUID : UUID = Field(..., title='RecorderUUID', description='The UUID of the recorder.')
    RecorderServiceVersion : str = Field(..., title='RecorderVersion', description='The version of the recorder.')
    RecorderServiceDescription : str = Field(..., title='RecorderDescription', description='The description of the recorder.')
    RecorderServiceType : str = Field(IndalekoConstants.service_type_storage_recorder,
                                       title='RecorderType',
                                       description=f'The type of the recorder. (default is {IndalekoConstants.service_type_storage_recorder})')

    class Config:
        '''Configuration for the base CLI data model'''
        json_schema_extra = {
            'example': {
                'RecorderPlatformName': 'Linux',
                'RecorderServiceName': 'Linux Local Recorder',
                'RecorderServiceUUID': uuid4(),
                'RecorderServiceVersion': '1.0',
                'RecorderServiceDescription': 'This service record local filesystem metadata of a Linux machine.',
                'RecorderServiceType': IndalekoConstants.service_type_storage_recorder # same as default
            }
        }

def main():
    '''Test code for the base CLI data model'''
    ic('Testing Storage Recorder Data Model')
    storage_recorder_data = IndalekoStorageRecorderDataModel(
        **IndalekoStorageRecorderDataModel.Config.json_schema_extra['example']
    )
    ic(storage_recorder_data)
    ic(platform.system())
    print(storage_recorder_data.model_dump(exclude_unset=True))
    print(storage_recorder_data.model_dump_json(indent=2))

if __name__ == '__main__':
    main()
