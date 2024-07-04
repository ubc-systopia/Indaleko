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
from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Dict, Any, Annotated
from uuid import UUID

from apischema import schema
from apischema.graphql import graphql_schema
from apischema.json_schema import deserialization_schema
from apischema.metadata import required
from graphql import print_schema
import jsonschema
from jsonschema import validate, Draft202012Validator, exceptions

from IndalekoRecordSchema import IndalekoRecordSchema, IndalekoRecordDataModel

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

    @dataclass
    class Platform:
        '''Define the platform data model.'''
        software: 'IndalekoMachineConfigDataModel.Software'
        hardware: 'IndalekoMachineConfigDataModel.Hardware'

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


class IndalekoMachineConfigSchema(IndalekoRecordSchema):
    '''Define the schema for use with the MachineConfig collection.'''

    @staticmethod
    def check_against_schema(data : dict, schema : dict) -> bool:
        '''Given a dict, determine if it conforms to the given schema.'''
        return IndalekoRecordSchema.check_against_schema(data, schema)

    @staticmethod
    def get_schema():

        machine_config_schema = {
            '''
            This schema relates to the machine configuration collection,
            which captures meta-data about the machine where the data was indexed.
            '''
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/machineconfig.json",
            "title": "Data source schema",
            "description": "This schema describes information about the machine where the data was indesxed.",
            "type": "object",
            "rule" : {
                "Platform" : {
                    "type" : "object",
                    "properties" : {
                        "software" : {
                            "type" : "object",
                            "properties" : {
                                "OS" : {
                                    "type" : "string",
                                    "description" : "Name of the software.",
                                },
                                "Version" : {
                                    "type" : "string",
                                    "description" : "Version of the software.",
                                },
                            },
                            "required" : ["OS", "version"],
                        },
                        "hardware" : {
                            "type" : "object",
                            "properties" : {
                                "CPU" : {
                                    "type" : "string",
                                    "description" : "Processor Architecture.",
                                },
                                "Version" : {
                                    "type" : "string",
                                    "description" : "Version of the hardware.",
                                },
                            },
                            "required" : ["CPU", "version"],
                        },
                    },
                },
                "Captured" : {
                    "type" : "object",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" : "UUID representing the semantic meaning of this timestamp.",
                            "format": "uuid",
                        },
                        "Value" : {
                            "type" : "string",
                            "description" : "Timestamp in ISO date and time format.",
                            "format" : "date-time",
                        },
                    },
                    "required" : ["Label", "Value"],
                },
                "required" : ["Captured"],
            }
        }
        assert 'Record' not in machine_config_schema['rule'], \
            'Record should not be in machine config schema.'
        machine_config_schema['rule']['Record'] = IndalekoRecordSchema.get_schema()['rule']
        machine_config_schema['rule']['required'].append('Record')
        return machine_config_schema

    @staticmethod
    def get_record(identifier: UUID) -> IndalekoMachineConfigDataModel.MachineConfig:
        '''Return the machine configuration record with the given ID.'''
        return IndalekoMachineConfigDataModel.MachineConfig(
            Platform = IndalekoMachineConfigDataModel.Platform(
                software = IndalekoMachineConfigDataModel.Software(
                    OS = 'Linux',
                    Version = '5.4.0'
                ),
                hardware = IndalekoMachineConfigDataModel.Hardware(
                    CPU = 'x86_64',
                    Version = '1.0'
                )
            ),
            Captured = IndalekoMachineConfigDataModel.Captured(
                Label = identifier,
                Value = datetime.now()
            ),
            Record = IndalekoRecordSchema.get_record(identifier)
        )

    @staticmethod
    def get_records() -> list[IndalekoMachineConfigDataModel.MachineConfig]:
        '''Return all machine configuration records.'''
        return [IndalekoMachineConfigSchema.get_record(UUID()) for _ in range(10)]

    @staticmethod
    def get_graphql_schema():
        '''Return the GraphQL schema for the MachineConfig collection.'''
        gql_schema = graphql_schema(query=[IndalekoMachineConfigSchema.get_record,
                                           IndalekoMachineConfigSchema.get_records],
                                    types=[IndalekoMachineConfigDataModel.MachineConfig])
        return gql_schema

    @staticmethod
    def get_new_schema():
        '''Return the schema for the MachineConfig collection using data model.'''
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/machineconfig.json",
            "title": "Data source schema",
            "description": "This schema describes information about the machine where the data was indexed.",
            "type": "object",
            "rule" : deserialization_schema(IndalekoMachineConfigDataModel.MachineConfig)
        }

def main():
    """Test the IndalekoMachineConfigSchema class."""
    if IndalekoMachineConfigSchema.is_valid_schema(IndalekoMachineConfigSchema.get_schema()):
        print('Schema is valid.')
    print('JSON Schema (original):')
    print(json.dumps(IndalekoMachineConfigSchema.get_schema(), indent=4))
    print('JSON Schema (new):')
    print(json.dumps(IndalekoMachineConfigSchema.get_new_schema(), indent=4))
    print('GraphQL Schema:')
    print(print_schema(IndalekoMachineConfigSchema.get_graphql_schema()))

if __name__ == "__main__":
    main()
