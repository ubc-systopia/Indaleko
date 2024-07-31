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

from IndalekoRecordSchema import IndalekoRecordSchema
from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel
from IndalekoDataSchema import IndalekoDataSchema
class IndalekoMachineConfigSchema(IndalekoRecordSchema):
    '''Define the schema for use with the MachineConfig collection.'''

    template = {key : value for key, value in IndalekoRecordSchema.template.items()}
    template['title'] = 'Machine Configuration Schema'
    template['$id'] = 'https://activitycontext.work/schema/machineconfig.json'
    template['description'] = 'Describes machine where data was captured'

    def __init__(self):
        '''Initialize the schema for the MachineConfig collection.'''
        if not hasattr(self, 'data_mode'):
            self.data_model = IndalekoMachineConfigDataModel()
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoMachineConfigDataModel.MachineConfig
        super().__init__()

    @staticmethod
    def get_old_schema():
        '''Return the old (static) schema for the MachineConfig.'''

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
                            "required" : ["OS", "Version"],
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
                            "required" : ["CPU", "Version"],
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
        machine_config_schema['rule']['Record'] = IndalekoRecordSchema().get_json_schema()['rule']
        machine_config_schema['rule']['required'].append('Record')
        return machine_config_schema

    def get_json_schema(self: IndalekoDataSchema) -> dict:
        '''
        For some reason the schema generation is marking Platform as
        required, which is not correct, so rather than fight it, I'm just
        removing it if it is found.
        '''
        broken_schema = super().get_json_schema()
        if 'rule' in broken_schema and 'required' in broken_schema['rule']:
            required_list = [x for x in broken_schema['rule']['required'] if x != 'Platform']
            broken_schema['rule']['required'] = required_list
        return broken_schema

def main():
    """Test the IndalekoMachineConfigSchema class."""
    machine_config_schema = IndalekoMachineConfigSchema()
    machine_config_schema.schema_detail(query=IndalekoMachineConfigDataModel.get_queries(),
                                        types=IndalekoMachineConfigDataModel.get_types())

if __name__ == "__main__":
    main()
