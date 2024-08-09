'''
This module defines the database schema for the MachineConfig collection.

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

import json
import jsonschema
import apischema

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from icecream import ic

from apischema import schema, deserialize, serialize
from apischema.graphql import graphql_schema
from apischema.metadata import required
from apischema.json_schema import deserialization_schema, serialization_schema
from graphql import print_schema

from IndalekoRecordDataModel import IndalekoRecordDataModel


class IndalekoMachineConfigDataModel:
    '''
    This class defines the data model for the MachineConfig collection.
    '''

    @dataclass
    class Software:
        '''Define the software data model.'''
        OS: Annotated[str,
                      schema(description="Name of the software."),
                      required]

        Version: Annotated[str,
                           schema(description="Version of the software."),
                           required]

        Architecture: Annotated[
            Optional[str],
            schema(description="Processor architecture.")
        ]

    @staticmethod
    def get_software() -> 'IndalekoMachineConfigDataModel.Software':
        '''Return the software information.'''
        return IndalekoMachineConfigDataModel.Software(
            OS='Linux',
            Version='5.0.0'
        )

    @dataclass
    class Hardware:
        '''Define the hardware data model.'''
        CPU: Annotated[
            str,
            schema(description="Processor Architecture."),
            required]

        Version: Annotated[
            str,
            schema(description="Version of the hardware."),
            required]

        Cores: Annotated[
            Optional[int],
            schema(description="Number of cores.")
        ] = 1

    @staticmethod
    def get_hardware() -> 'IndalekoMachineConfigDataModel.Hardware':
        '''Return the hardware information.'''
        return IndalekoMachineConfigDataModel.Hardware(
            CPU='x86_64',
            Version='1.0'
        )

    @dataclass
    class Platform:
        '''Define the platform data model.'''

        software: Annotated[
            'IndalekoMachineConfigDataModel.Software',
            required
            ]

        hardware: Annotated[
            'IndalekoMachineConfigDataModel.Hardware',
            required
        ]

    @staticmethod
    def get_platform() -> 'IndalekoMachineConfigDataModel.Platform':
        '''Return the platform information.'''
        return IndalekoMachineConfigDataModel.Platform(
            software=IndalekoMachineConfigDataModel.get_software(),
            hardware=IndalekoMachineConfigDataModel.get_hardware()
        )

    @dataclass
    class Captured:
        '''Define the captured data model.'''
        Label: Annotated[UUID,
                         schema(description="UUID representing the semantic meaning of this timestamp."),
                         required]
        Value: Annotated[datetime,
                         schema(description="Timestamp in ISO date and time format.",
                                format="date-time"),
                         required]

    @staticmethod
    def get_captured() -> 'IndalekoMachineConfigDataModel.Captured':
        '''Return the captured information.'''
        return IndalekoMachineConfigDataModel.Captured(
            Label=UUID('12345678-1234-5678-1234-567812345678'),
            Value=datetime.now()
        )

    @dataclass
    class MachineConfig:
        '''Define the machine configuration data model.'''
        Captured: Annotated[
            'IndalekoMachineConfigDataModel.Captured',
            schema(description="Raw platform data captured."),
            required
        ]

        Record: Annotated[
            IndalekoRecordDataModel.IndalekoRecord,
            schema(description="The base record information."),
            required
        ]

        Platform: Annotated[
            Optional['IndalekoMachineConfigDataModel.Platform'],
            schema(description="The platform.")
        ] = None

        @staticmethod
        def deserialize(data: dict) -> 'IndalekoMachineConfigDataModel.MachineConfig':
            '''Deserialize a dictionary to an object.'''
            return deserialize(IndalekoMachineConfigDataModel.MachineConfig,
                            data,
                            additional_properties=True)

        @staticmethod
        def serialize(data) -> dict:
            '''Serialize the object to a dictionary.'''
            return serialize(IndalekoMachineConfigDataModel.MachineConfig,
                             data),


    @staticmethod
    def get_machine_config() -> 'IndalekoMachineConfigDataModel.MachineConfig':
        '''Return the machine configuration.'''
        return IndalekoMachineConfigDataModel.MachineConfig(
            Platform=IndalekoMachineConfigDataModel.get_platform(),
            Captured=IndalekoMachineConfigDataModel.get_captured(),
            Record=IndalekoRecordDataModel.get_indaleko_record()
        )

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the MachineConfig collection.'''
        return [
            IndalekoMachineConfigDataModel.get_software,
            IndalekoMachineConfigDataModel.get_hardware,
            IndalekoMachineConfigDataModel.get_platform,
            IndalekoMachineConfigDataModel.get_machine_config]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the MachineConfig collection.'''
        return [IndalekoMachineConfigDataModel.Platform,
                IndalekoMachineConfigDataModel.Captured,
                IndalekoMachineConfigDataModel.MachineConfig]



def main():
    '''Test code for IndalekoMachineConfigDataModel.'''
    ic('GraphQL Schema:')
    ic(print_schema(graphql_schema(query=IndalekoMachineConfigDataModel.get_queries(),
                                      types=IndalekoMachineConfigDataModel.get_types())))
    unpack_schema = deserialization_schema(IndalekoMachineConfigDataModel.MachineConfig, additional_properties=True)
    pack_schema = serialization_schema(IndalekoMachineConfigDataModel.MachineConfig, additional_properties=True)
    json_unpack_schema = json.dumps(unpack_schema, indent=2)
    #print(json_unpack_schema)
    json_pack_schema = json.dumps(pack_schema, indent=2)
    #print(json_pack_schema)


    data_object = {
        "Captured": {
            "Label": "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4",
            "Value": "2024-08-08T21:26:22.418196+00:00"
        },
        "Record": {
            "SourceIdentifier": {
                "Identifier": "8a948e74-6e43-4a6e-91c0-0cb5fd97355e",
                "Version": "1.0",
                "Description": "This service provides the configuration information for a macOS machine."
            },
            "Timestamp": "2024-08-09T07:52:59.839237+00:00",
            "Attributes": {
                "MachineGuid": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b"
            },
            "Data": "xx"
        },
        "Platform": {
            "software": {
                "OS": "Linux",
                "Version": "5.4.0-104-generic",
                "Architecture": "x86_64"
            },
            "hardware": {
                "CPU": "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz",
                "Version": "06_9E_09",
                "Cores": 8
            }
        },
        "_key": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        "hostname": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b"
    }

    #machine_config = IndalekoMachineConfigDataModel.MachineConfig.deserialize(data_object)
    #serialized_object = IndalekoMachineConfigDataModel.MachineConfig.serialize(machine_config)
    #jsonschema.validate(instance=serialized_object, schema=pack_schema)
    #jsonschema.validate(instance=data_object, schema=unpack_schema)

    ic('check record')
    record = IndalekoRecordDataModel.IndalekoRecord.deserialize(data_object['Record'])
    jsonschema.validate(instance=record, schema=serialization_schema(IndalekoRecordDataModel.IndalekoRecord, additional_properties=True))

    ic('check captured')
    captured = IndalekoMachineConfigDataModel.Captured.deserialize(data_object['Captured'])
    jsonschema.validate(instance=captured, schema=IndalekoMachineConfigDataModel.Captured.get_json_schema())


if __name__ == "__main__":
    main()
