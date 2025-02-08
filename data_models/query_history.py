
"""
This module defines the query history data model for Indaleko.

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
from typing import Dict, Any, Type, TypeVar, Union

from pydantic import Field, field_validator

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

T = TypeVar('T', bound='IndalekoQueryHistoryDataModel')

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel  # noqa: E402
from data_models.record import IndalekoRecordDataModel  # noqa: E402
# pylint: enable=wrong-import-position


class IndalekoQueryHistoryDataModel(IndalekoBaseModel):
    '''
    This class defines the data model for the Indaleko query history.
    '''
    Record: IndalekoRecordDataModel = Field(
        None,
        title='Record',
        description='The record associated with the performance data.'
    )

    @staticmethod
    def validate_timestamp(ts: Union[str, datetime]) -> datetime:
        '''Ensure that the timestamp is in UTC'''
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts

    @field_validator('StartTimestamp', mode='before')
    @classmethod
    def ensure_starttime(cls, value: datetime):
        return cls.validate_timestamp(value)

    @field_validator('EndTimestamp', mode='before')
    @classmethod
    def ensure_endtime(cls, value: datetime):
        return cls.validate_timestamp(value)

    @field_validator('ElapsedTime', mode='before')
    @classmethod
    def calculate_elapsed_time(
        cls: Type[T],
        value: Union[float, None] = None,
        values: Union[Dict[str, Any], None] = None
    ) -> float:
        '''Calculate the elapsed time if it is not provided.'''
        if value is None:
            start = values.get('StartTimestamp', datetime.now(timezone.utc))
            end = values.get('EndTimestamp', datetime.now(timezone.utc))
            value = (end - start).total_seconds()
        return value

    class Config:
        '''Sample configuration data for the data model.'''
        json_schema_extra = {
            "example": {
                "Record": {
                    "SourceIdentifier": {
                        "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                        "Version": "1.0",
                    },
                    "Timestamp": "2024-07-30T23:38:48.319654+00:00",
                    "Attributes": {
                        "Key": "Value"
                    },
                    "Data": "Base64EncodedData"
                },
            }
        }


def main():
    '''This allows testing the data model.'''
    IndalekoQueryHistoryDataModel.test_model_main()


if __name__ == '__main__':
    main()
