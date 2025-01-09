"""
This module defines the data model for the Indaleko data object.

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
"""
This module defines the data model for the Indaleko data object.

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
import os
import sys

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from pydantic import Field, AwareDatetime
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
# pylint: enable=wrong-import-position

class IndalekoMetadataDataModel(IndalekoBaseModel):
    '''
    This class defines the metadata data model for Indaleko.
    '''
    Record : IndalekoRecordDataModel = Field(None,
                                    title='Record',
                                    description='The record associated with the object.')

    FieldId: IndalekoUUIDDataModel = Field(None,
                                    title='FieldId',
                                    description='The UUID for the metadata field.')

    FieldName : str = Field(None,
                            title='FieldName',
                            description='The name of the metadata field.')

    FieldType : str = Field(None,
                            title='FieldType',
                            description='The data type of the field (e.g., string, integer, date).')

    UsageCount : int = Field(None,
                             title='UsageCount',
                             description='How often this field is used in queries.')

    LastUsed : Optional[AwareDatetime] = Field(datetime.now(timezone.utc),
                                          title='LastUsed',
                                          description='The timestamp of when this field was last used in a query.')

    Indexed : bool = Field(False,
                           title='Indexed',
                           description='Whether the field is indexed.')

    ArchiveRelevance : Optional[bool] = Field(True,
                                              title='ArchiveRelevance',
                                              description='Flag for relevance to archived queries.')

    class Config:
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra['example'],
                "FieldId": IndalekoUUIDDataModel.Config.json_schema_extra['example'],
                "FieldName": "Name",
                "FieldType": "string",
                "UsageCount": 0,
                "LastUsed": None,
                "Indexed": False,
            }
        }


def main():
    '''This allows testing the data model.'''
    ic('Testing IndalekoObjectDataModel')
    IndalekoMetadataDataModel.test_model_main()

if __name__ == '__main__':
    main()
