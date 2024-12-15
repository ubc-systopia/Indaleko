"""
This module defines the data model for the Indaleko data object.

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
"""
import os
import sys
import uuid

from typing import List, Union

from pydantic import Field
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
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
# pylint: enable=wrong-import-position

class IndalekoObjectDataModel(IndalekoBaseModel):
    '''
    This class defines the data model for the Indaleko object.
    '''
    Record : IndalekoRecordDataModel = Field(None,
                                    title='Record',
                                    description='The record associated with the object.')

    URI : str = Field(None,
                        title='URI',
                        description='The URI for the object.')

    ObjectIdentifier : uuid.UUID = Field(uuid.uuid4(),
                                         title='ObjectIdentifier',
                                         description='The UUID representing this object.')

    Timestamps : List[IndalekoTimestampDataModel] = Field(None,
                                    title='Timestamps',
                                    description='The timestamps associated with the object.')

    Size : int = Field(None,
                        title='Size',
                        description='The size of the object in bytes.')

    SemanticAttributes : List[IndalekoSemanticAttributeDataModel] \
        = Field(None,
                title='SemanticAttributes',
                description='The semantic attributes related to this object by the storage service.')

    Label: Union[str, None] = Field(None,
                                    title='Label',
                                    description='The label associated with the object in the storage system.  This field is indexed.')

    LocalIdentifier: Union[str, None] = Field(None,
                                    title='LocalIdentifier',
                                    description='The local identifier associated with the object in the storage system.  Typically this is the inode number or equivalent.')

    Volume : Union[uuid.UUID, None] = Field(None,
                                            title='Volume',
                                            description='The volume associated with the object.  This field is optional.')

    PosixFileAttributes: Union[str, None] = Field(None,
                                    title='PosixFileAttributes',
                                    description='The POSIX file attributes associated with the object in the storage system (e.g., S_IFREG, S_IFDIR, etc.). This field is optional.')

    WindowsFileAttributes : Union[str, None] = Field(None,
                                    title='WindowsFileAttributes',
                                    description='The Windows file attributes associated with the object in the storage system (e.g., FILE_ATTRIBUTE_READ_ONLY, FILE_ATTRIBUTE_ARCHIVE, etc.) This field is optional.')

    class Config:
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra['example'],
                "URI": "https://www.example.com/this/is/a/sample/uri",
                "ObjectIdentifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                "Timestamps": [IndalekoTimestampDataModel.Config.json_schema_extra['example']],
                "Size": 1024,
                "SemanticAttributes": [
                    IndalekoSemanticAttributeDataModel.Config.json_schema_extra['example']
                ],
                "Label": "This is a sample label",
                "LocalIdentifier": "This is a sample local identifier",
                "Volume": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                "PosixFileAttributes": "S_IFREG",
                "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE",
            }
        }


def main():
    '''This allows testing the data model.'''
    ic('Testing IndalekoObjectDataModel')
    IndalekoObjectDataModel.test_model_main()

if __name__ == '__main__':
    main()
