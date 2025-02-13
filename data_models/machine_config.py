'''
This module defines the database schema for the MachineConfig collection.

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
'''

import os
import sys

from icecream import ic
from pydantic import Field

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.record import IndalekoRecordDataModel
from platforms.data_models.software import Software as software
from platforms.data_models.hardware import Hardware as hardware
# pylint: enable=wrong-import-position


class IndalekoMachineConfigDataModel(IndalekoBaseModel):
    '''
    This class defines the data model for the MachineConfig collection.
    '''
    Record: IndalekoRecordDataModel = Field(
        ...,
        title='Record',
        description='The record associated with the object.'
    )

    Captured: IndalekoTimestampDataModel = \
        Field(...,
              title='Captured',
              description='The timestamp of when this data was captured.')

    Hardware: hardware = \
        Field(...,
              title='Hardware',
              description='The hardware information for the machine.')

    Software: software = Field(
        ...,
        title='Software',
        description='The software information for the machine.'
    )

    class Config:
        '''Configuration for the machine config data model'''
        json_schema_extra = {
            'example': {
                'Record': IndalekoRecordDataModel.Config.json_schema_extra['example'],
                'Captured': IndalekoTimestampDataModel.Config.json_schema_extra['example'],
                'Hardware': hardware.Config.json_schema_extra['example'],
                'Software': software.Config.json_schema_extra['example']
            }
        }


def main():
    '''Main function for the machine config data model'''
    ic('Testing Machine Config Data Model')
    IndalekoMachineConfigDataModel.test_model_main()


if __name__ == '__main__':
    main()
