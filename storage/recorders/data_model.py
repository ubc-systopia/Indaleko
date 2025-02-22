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
import os
import platform
import sys
from typing import Optional, Union
from uuid import UUID, uuid4

from pydantic import Field, BaseModel
from icecream import ic


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants
# pylint: enable=wrong-import-position


class IndalekoStorageRecorderDataModel(BaseModel):
    '''Defines the base data model for the storage recorders'''
    PlatformName: Optional[Union[str, None]] = \
        Field(None,
              title='PlatformName',
              description='The name of the platform (e.g., Linux, Windows, etc.) if any (default=None).'
              )

    ServiceRegistrationName: str = Field(
        ...,
        title='ServiceRegistrationName',
        description='The service name used when registering this recorder in the database.'
    )

    ServiceFileName: str = Field(
        ...,
        title='ServiceFileName',
        description='The service name to use when building file names.'
    )

    ServiceUUID: UUID = Field(
        ...,
        title='ServiceUUID',
        description='The UUID of the recorder.'
    )

    ServiceVersion: str = Field(
        ...,
        title='ServiceVersion',
        description='The version of the recorder.'
    )

    ServiceDescription: str = Field(
        ...,
        title='ServiceDescription',
        description='The description of the recorder.'
    )

    ServiceType: str = Field(
        IndalekoConstants.service_type_storage_recorder,
        title='RecorderType',
        description=f'The type of the recorder. (default is {IndalekoConstants.service_type_storage_recorder})'
    )

    class Config:
        '''Configuration for the base CLI data model'''
        json_schema_extra = {
            'example': {
                'PlatformName': 'Linux',
                'ServiceRegistrationName': 'Linux Local Recorder',
                'ServiceFileName': 'recorder',
                'ServiceUUID': uuid4(),
                'ServiceVersion': '1.0',
                'ServiceDescription': 'This service record local filesystem metadata of a Linux machine.',
                'ServiceType': IndalekoConstants.service_type_storage_recorder  # same as default
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
