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
            schema(description="The platform."),
            required
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
                             data,
                             additional_properties=True,
                             exclude_unset=True,
                             exclude_none=True),


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
    print(json_unpack_schema)
    json_pack_schema = json.dumps(pack_schema, indent=2)
    print(json_pack_schema)


    data_object = {
        "Platform": {
            "software": {
                "OS": "macOS",
                "Version": "23.5.0",
                "Architecture": "arm64"
            },
            "hardware": {
                "CPU": "arm",
                "Version": "arm",
                "Cores": 8
            }
        },
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
            "Timestamp": "2024-08-09T05:12:20.250797+00:00",
            "Attributes": {
                "MachineGuid": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
                "OperatingSystem": {
                    "Caption": "macOS",
                    "OSArchitecture": "arm64",
                    "Version": "23.5.0"
                },
                "CPU": {
                    "Name": "arm",
                    "Cores": 8
                },
                "VolumeInfo": [
                    {
                        "UniqueId": "/dev/disk3s1s1",
                        "VolumeName": "disk3s1s1",
                        "Size": "1858.19 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk3s1s1"
                    },
                    {
                        "UniqueId": "/dev/disk3s6",
                        "VolumeName": "disk3s6",
                        "Size": "1858.19 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk3s6"
                    },
                    {
                        "UniqueId": "/dev/disk3s2",
                        "VolumeName": "disk3s2",
                        "Size": "1858.19 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk3s2"
                    },
                    {
                        "UniqueId": "/dev/disk3s4",
                        "VolumeName": "disk3s4",
                        "Size": "1858.19 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk3s4"
                    },
                    {
                        "UniqueId": "/dev/disk1s2",
                        "VolumeName": "disk1s2",
                        "Size": "0.49 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk1s2"
                    },
                    {
                        "UniqueId": "/dev/disk1s1",
                        "VolumeName": "disk1s1",
                        "Size": "0.49 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk1s1"
                    },
                    {
                        "UniqueId": "/dev/disk1s3",
                        "VolumeName": "disk1s3",
                        "Size": "0.49 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk1s3"
                    },
                    {
                        "UniqueId": "/dev/disk3s5",
                        "VolumeName": "disk3s5",
                        "Size": "1858.19 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk3s5"
                    },
                    {
                        "UniqueId": "/dev/disk5s1",
                        "VolumeName": "disk5s1",
                        "Size": "8.31 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk5s1"
                    },
                    {
                        "UniqueId": "/dev/disk7s1",
                        "VolumeName": "disk7s1",
                        "Size": "9.66 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk7s1"
                    },
                    {
                        "UniqueId": "/dev/disk9s1",
                        "VolumeName": "disk9s1",
                        "Size": "4.03 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk9s1"
                    },
                    {
                        "UniqueId": "/dev/disk11s1",
                        "VolumeName": "disk11s1",
                        "Size": "16.14 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk11s1"
                    },
                    {
                        "UniqueId": "/dev/disk13s1",
                        "VolumeName": "disk13s1",
                        "Size": "16.22 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk13s1"
                    },
                    {
                        "UniqueId": "/dev/disk15s1",
                        "VolumeName": "disk15s1",
                        "Size": "3.72 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk15s1"
                    },
                    {
                        "UniqueId": "/dev/disk17s1",
                        "VolumeName": "disk17s1",
                        "Size": "8.72 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk17s1"
                    },
                    {
                        "UniqueId": "/dev/disk19s1",
                        "VolumeName": "disk19s1",
                        "Size": "8.48 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk19s1"
                    },
                    {
                        "UniqueId": "/dev/disk21s1",
                        "VolumeName": "disk21s1",
                        "Size": "16.35 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk21s1"
                    },
                    {
                        "UniqueId": "/dev/disk23s1",
                        "VolumeName": "disk23s1",
                        "Size": "3.87 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk23s1"
                    },
                    {
                        "UniqueId": "/dev/disk25s1",
                        "VolumeName": "disk25s1",
                        "Size": "8.68 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk25s1"
                    },
                    {
                        "UniqueId": "/dev/disk27s1",
                        "VolumeName": "disk27s1",
                        "Size": "4.31 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk27s1"
                    },
                    {
                        "UniqueId": "/dev/disk29s1",
                        "VolumeName": "disk29s1",
                        "Size": "9.46 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk29s1"
                    },
                    {
                        "UniqueId": "/dev/disk31s1",
                        "VolumeName": "disk31s1",
                        "Size": "9.71 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk31s1"
                    },
                    {
                        "UniqueId": "/dev/disk33s1",
                        "VolumeName": "disk33s1",
                        "Size": "15.95 GB",
                        "Filesystem": "apfs",
                        "GUID": "disk33s1"
                    }
                ]
            },
        "Data": "hKtNYWNoaW5lR3VpZNkkZjdhNDM5ZWMtYzJkMC00ODQ0LWEwNDMtZDhhYzI0ZDlhYzBir09wZXJhdGluZ1N5c3RlbYOnQ2FwdGlvbqVtYWNPU65PU0FyY2hpdGVjdHVyZaVhcm02NKdWZXJzaW9upjIzLjUuMKNDUFWCpE5hbWWjYXJtpUNvcmVzCKpWb2x1bWVJbmZv3AAXhKhVbmlxdWVJZK4vZGV2L2Rpc2szczFzMapWb2x1bWVOYW1lqWRpc2szczFzMaRTaXplqjE4NTguMTkgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZKwvZGV2L2Rpc2szczaqVm9sdW1lTmFtZadkaXNrM3M2pFNpemWqMTg1OC4xOSBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrC9kZXYvZGlzazNzMqpWb2x1bWVOYW1lp2Rpc2szczKkU2l6ZaoxODU4LjE5IEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWSsL2Rldi9kaXNrM3M0qlZvbHVtZU5hbWWnZGlzazNzNKRTaXplqjE4NTguMTkgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZKwvZGV2L2Rpc2sxczKqVm9sdW1lTmFtZadkaXNrMXMypFNpemWnMC40OSBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrC9kZXYvZGlzazFzMapWb2x1bWVOYW1lp2Rpc2sxczGkU2l6ZacwLjQ5IEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWSsL2Rldi9kaXNrMXMzqlZvbHVtZU5hbWWnZGlzazFzM6RTaXplpzAuNDkgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZKwvZGV2L2Rpc2szczWqVm9sdW1lTmFtZadkaXNrM3M1pFNpemWqMTg1OC4xOSBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrC9kZXYvZGlzazVzMapWb2x1bWVOYW1lp2Rpc2s1czGkU2l6Zac4LjMxIEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWSsL2Rldi9kaXNrN3MxqlZvbHVtZU5hbWWnZGlzazdzMaRTaXplpzkuNjYgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZKwvZGV2L2Rpc2s5czGqVm9sdW1lTmFtZadkaXNrOXMxpFNpemWnNC4wMyBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrS9kZXYvZGlzazExczGqVm9sdW1lTmFtZahkaXNrMTFzMaRTaXplqDE2LjE0IEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWStL2Rldi9kaXNrMTNzMapWb2x1bWVOYW1lqGRpc2sxM3MxpFNpemWoMTYuMjIgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZK0vZGV2L2Rpc2sxNXMxqlZvbHVtZU5hbWWoZGlzazE1czGkU2l6ZaczLjcyIEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWStL2Rldi9kaXNrMTdzMapWb2x1bWVOYW1lqGRpc2sxN3MxpFNpemWnOC43MiBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrS9kZXYvZGlzazE5czGqVm9sdW1lTmFtZahkaXNrMTlzMaRTaXplpzguNDggR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZK0vZGV2L2Rpc2syMXMxqlZvbHVtZU5hbWWoZGlzazIxczGkU2l6ZagxNi4zNSBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrS9kZXYvZGlzazIzczGqVm9sdW1lTmFtZahkaXNrMjNzMaRTaXplpzMuODcgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZK0vZGV2L2Rpc2syNXMxqlZvbHVtZU5hbWWoZGlzazI1czGkU2l6Zac4LjY4IEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWStL2Rldi9kaXNrMjdzMapWb2x1bWVOYW1lqGRpc2syN3MxpFNpemWnNC4zMSBHQqpGaWxlc3lzdGVtpGFwZnOEqFVuaXF1ZUlkrS9kZXYvZGlzazI5czGqVm9sdW1lTmFtZahkaXNrMjlzMaRTaXplpzkuNDYgR0KqRmlsZXN5c3RlbaRhcGZzhKhVbmlxdWVJZK0vZGV2L2Rpc2szMXMxqlZvbHVtZU5hbWWoZGlzazMxczGkU2l6Zac5LjcxIEdCqkZpbGVzeXN0ZW2kYXBmc4SoVW5pcXVlSWStL2Rldi9kaXNrMzNzMapWb2x1bWVOYW1lqGRpc2szM3MxpFNpemWoMTUuOTUgR0KqRmlsZXN5c3RlbaRhcGZz"
        },
        "_key": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        "hostname": "wam-msi"
    }

    machine_config = IndalekoMachineConfigDataModel.MachineConfig.deserialize(data_object)
    serialized_object = IndalekoMachineConfigDataModel.MachineConfig.serialize(machine_config)
    jsonschema.validate(instance=serialized_object, schema=pack_schema)
    jsonschema.validate(instance=data_object, schema=unpack_schema)


if __name__ == "__main__":
    main()
