"""
This module defines the data model for the indaleko record type.

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

from typing import Dict, Any

from datetime import datetime, timezone
from pydantic import Field, field_validator, AwareDatetime
# from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.source_identifer import IndalekoSourceIdentifierDataModel
from data_models.base import IndalekoBaseModel
# pylint: enable=wrong-import-position

class IndalekoRecordDataModel(IndalekoBaseModel):
    '''
    This class defines the UUID data model for Indaleko.
    '''
    SourceIdentifier : IndalekoSourceIdentifierDataModel = Field(...,
                                      title='SourceIdentifier',
                                      description='The source identifier for the record.')
    Timestamp : AwareDatetime = Field(...,
                                 title='Timestamp',
                                 description='The timestamp of when this record was created.')
    Attributes : Dict[str, Any] = \
                    Field(...,
                          title='Attributes',
                          description='The attributes extracted from the source data.')
    Data : str = Field(...,
                       title='Data',
                       description='The raw (uninterpreted) data from the source.')

    @field_validator('Timestamp', mode='before')
    @classmethod
    def ensure_timezone(cls, value: datetime):
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    class Config:
        '''Sample configuration data for the data model.'''
        json_schema_extra = {
            "example": {
                "SourceIdentifier": {
                    "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                    "Version": "1.0",
                },
                "Timestamp": "2024-07-30T23:38:48.319654+00:00",
                "Attributes": {
                    "st_atime": 1693223456.3334281,
                    "st_atime_ns": 1693223456333428100,
                    "st_birthtime": 1685891221.5591917,
                    "st_birthtime_ns": 1685891221559191700,
                    "st_ctime": 1685891221.5591917,
                    "st_ctime_ns": 1685891221559191700,
                    "st_dev": 2756347094955649599,
                    "st_file_attributes": 32,
                    "st_gid": 0,
                    "st_ino": 1125899910119832,
                    "st_mode": 33279,
                    "st_mtime": 1685891221.5597157,
                    "st_mtime_ns": 1685891221559715700,
                    "st_nlink": 1,
                    "st_reparse_tag": 0,
                    "st_size": 1410120,
                    "st_uid": 0,
                    "Name": "rufus-4.1.exe",
                    "Path": "d:\\dist",
                    "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\rufus-4.1.exe",
                    "Indexer": "0793b4d5-e549-4cb6-8177-020a738b66b7",
                    "Volume GUID": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
                    "ObjectIdentifier": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a"
                },
                "Data": "xQL6xQL3eyJzdF9hdGltZSI6IDE2OTMyMjM0NTYuMzMzNDI4MSwgInN0X2F0aW1lX25zIjogMTY5MzIyMzQ1NjMzMzQyODEwMCwgInN0X2JpcnRodGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2JpcnRodGltZV9ucyI6IDE2ODU4OTEyMjE1NTkxOTE3MDAsICJzdF9jdGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2N0aW1lX25zIjogMTY4NTg5MTIyMTU1OTE5MTcwMCwgInN0X2RldiI6IDI3NTYzNDcwOTQ5NTU2NDk1OTksICJzdF9maWxlX2F0dHJpYnV0ZXMiOiAzMiwgInN0X2dpZCI6IDAsICJzdF9pbm8iOiAxMTI1ODk5OTEwMTE5ODMyLCAic3RfbW9kZSI6IDMzMjc5LCAic3RfbXRpbWUiOiAxNjg1ODkxMjIxLjU1OTcxNTcsICJzdF9tdGltZV9ucyI6IDE2ODU4OTEyMjE1NTk3MTU3MDAsICJzdF9ubGluayI6IDEsICJzdF9yZXBhcnNlX3RhZyI6IDAsICJzdF9zaXplIjogMTQxMDEyMCwgInN0X3VpZCI6IDAsICJOYW1lIjogInJ1ZnVzLTQuMS5leGUiLCAiUGF0aCI6ICJkOlxcZGlzdCIsICJVUkkiOiAiXFxcXD9cXFZvbHVtZXszMzk3ZDk3Yi0yY2E1LTExZWQtYjJmYy1iNDBlZGU5YTVhM2N9XFxkaXN0XFxydWZ1cy00LjEuZXhlIiwgIkluZGV4ZXIiOiAiMDc5M2I0ZDUtZTU0OS00Y2I2LTgxNzctMDIwYTczOGI2NmI3IiwgIlZvbHVtZSBHVUlEIjogIjMzOTdkOTdiLTJjYTUtMTFlZC1iMmZjLWI0MGVkZTlhNWEzYyIsICJPYmplY3RJZGVudGlmaWVyIjogIjJjNzNkNmU1LWVhYmEtNGYwYS1hY2YzLWUwMmM1MjlmMDk3YSJ9"
            }
        }


def main():
    '''This allows testing the data model'''
    IndalekoRecordDataModel.test_model_main()

if __name__ == '__main__':
    main()
