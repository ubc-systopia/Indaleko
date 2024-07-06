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
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from apischema import schema
from apischema.graphql import graphql_schema
from apischema.metadata import required
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
        software: 'IndalekoMachineConfigDataModel.Software'
        hardware: 'IndalekoMachineConfigDataModel.Hardware'

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
        Platform: Annotated['IndalekoMachineConfigDataModel.Platform',
                            schema(description="The platform."), required]
        Captured: Annotated['IndalekoMachineConfigDataModel.Captured',
                            schema(description="Raw platform data captured."), required]
        Record: Annotated[IndalekoRecordDataModel.IndalekoRecord,
                          schema(description="The base record information."),
                          required]

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
        return [IndalekoMachineConfigDataModel.Software,
                IndalekoMachineConfigDataModel.Hardware,
                IndalekoMachineConfigDataModel.Platform,
                IndalekoMachineConfigDataModel.Captured,
                IndalekoMachineConfigDataModel.MachineConfig]

def main():
    '''Test code for IndalekoMachineConfigDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(query=IndalekoMachineConfigDataModel.get_queries(),
                                      types=IndalekoMachineConfigDataModel.get_types())))

if __name__ == "__main__":
    main()
