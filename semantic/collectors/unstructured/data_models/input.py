'''
This module defines the input data model for the unstructured data collector.

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
# standard imports
import os
import sys

from uuid import UUID
from datetime import datetime, timezone

# third-party imports
from typing import Optional
from pydantic import Field, field_validator, AwareDatetime

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
# pylint: enable=wrong-import-position

class UnstructuredInputDataModel(IndalekoBaseModel):
    '''
    This class defines the input data model for the unstructured data collector.
    '''
    ObjectIdentifier : UUID =\
            Field(...,
                  description="Identifier of this file in Indaleko.")

    LocalPath : str =\
            Field(...,
                  description="The local path to the file.")

    ModificationTimestamp : AwareDatetime =\
            Field(...,
                  description="The last modified time for the file.")

    Length : int =\
            Field(...,
                  description="The length of the file in bytes.")

    Checksum : Optional[str] =\
            Field(...,
                  description="The checksum of the file.")

    class Config:
        '''Sample configuration data for the data model.'''
        json_schema_extra = {
            "example" : {
                "ObjectIdentifier" : "00000000-0000-0000-0000-000000000000",
                "LocalPath" : "/path/to/file",
                "ModificationTimestamp" : "2024-01-01T00:00:00Z",
                "Length" : 1024,
                "Checksum" : "000000000000000000000000000"
            }
        }

    @classmethod
    @field_validator('ModificationTimestamp')
    def ensure_timezone(cls, value:datetime):
        '''Ensure that the timestamp has a timezone.'''
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


def main():
    '''This is the main handler for the Indaleko unstructured data collector.'''
    UnstructuredInputDataModel.test_model_main()

if __name__ == '__main__':
    main()
