
"""
This module defines the performance data model for Indaleko.

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

from datetime import datetime, timezone
from typing import Dict, Any, Type, TypeVar, Union, Optional

from pydantic import Field, AwareDatetime, field_validator

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

T = TypeVar('T', bound='IndalekoPerformanceDataModel')

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
# pylint: enable=wrong-import-position

class IndalekoPerformanceDataModel(IndalekoBaseModel):
    '''
    This class defines the data model for the Indaleko performance data.
    '''
    Record : IndalekoRecordDataModel = Field(None,
                                    title='Record',
                                    description='The record associated with the performance data.')

    MachineConfigurationId: Union[uuid.UUID, None] = Field(None,
                                    title='MachineConfigurationId',
                                    description='The UUID for the machine configuration (e.g. a reference to the relevant record in the MachineConfig collection).')

    StartTimestamp : AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                      title='StartTimestamp',
                                      description='The timestamp of when collection of this performance data was started.')

    EndTimestamp : AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                    title='EndTimestamp',
                                    description='The timestamp of when collection of this performance data was ended.')

    ElapsedTime : Optional[float] = Field(None,
                                title='ElapsedTime',
                                description='The elapsed time in seconds.')

    UserCPUTime : float = Field(...,
                                title='UserCPUTime',
                                description='The user CPU time in seconds.')

    SystemCPUTime : float = Field(...,
                                title='SystemCPUTime',
                                description='The system CPU time in seconds.')

    InputSize : Optional[int] = Field(None,
                                        title='InputSize',
                                        description='The size of the input data in bytes.')

    OutputSize : Optional[int] = Field(None,
                                        title='OutputSize',
                                        description='The size of the output data in bytes.')

    PeakMemoryUsage : Optional[int] = Field(None,
                                            title='PeakMemoryUsage',
                                            description='The peak memory usage in bytes.')

    IOReadBytes : Optional[int] = Field(None,
                                        title='IOReadBytes',
                                        description='The number of bytes read during execution.')

    IOWriteBytes : Optional[int] = Field(None,
                                        title='IOWriteBytes',
                                        description='The number of bytes written during execution.')

    ThreadCount : Optional[int] = Field(None,
                                        title='ThreadCount',
                                        description='The number of threads used.')

    ErrorCount : Optional[int] = Field(None,
                                        title='ErrorCount',
                                        description='The number of errors encountered.')

    AdditionalData : Optional[Dict[str, Any]] = Field(default_factory=dict,
                                                        title='AdditionalData',
                                                        description='Additional performance data.')

    @staticmethod
    def validate_timestamp(ts : Union[str, datetime]) -> datetime:
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
        cls : Type[T],
        value: Union[float, None] = None,
        values: Union[Dict[str, Any], None] = None) -> float:
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
                "MachineConfigurationId": "a8343055-7d85-4424-b83e-9fa413a7ebf7",
                "StartTimestamp": "2024-07-30T23:38:48.319654+00:00",
                "EndTimestamp": "2024-07-30T23:38:48.319654+00:00",
                "ElapsedTime": 0.0,
                "UserCPUTime": 0.0,
                "SystemCPUTime": 0.0,
                "InputSize": 0,
                "OutputSize": 0,
                "PeakMemoryUsage": 0,
                "IOReadBytes": 0,
                "IOWriteBytes": 0,
                "ThreadCount": 0,
                "ErrorCount": 0,
                "AdditionalData": {
                    "Files" : 14279384,
                    "Directories" : 62172,
                }
            }
        }

def main():
    '''This allows testing the data model.'''
    IndalekoPerformanceDataModel.test_model_main()

if __name__ == '__main__':
    main()
