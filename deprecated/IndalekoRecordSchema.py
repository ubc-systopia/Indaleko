'''
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.

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

from icecream import ic

import apischema

from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataSchema import IndalekoDataSchema

class IndalekoRecordSchema(IndalekoDataSchema):
    '''
    This is the schema for the Indaleko Record. Note that it is inherited and
    merged by other classes that derive from this base type.
    '''
    def __init__(self, **kwargs):
        '''Initialize the schema.'''
        if not hasattr(self, 'data_model'):
            self.data_model = IndalekoRecordDataModel()
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoRecordDataModel.IndalekoRecord
        record_rules = apischema.json_schema.deserialization_schema(IndalekoRecordDataModel.IndalekoRecord,
                                                                    additional_properties=True)
        if not hasattr(self, 'rules'):
            self.rules = record_rules
        else:
            self.rules['properties'].update({'Record' : record_rules['properties']})
        schema_id = kwargs.get('schema_id',
                               "https://activitycontext.work/indaleko/schema/record.json")
        schema_title = kwargs.get('schema_title', "Indaleko Record Schema")
        schema_description = kwargs.get('schema_description', "Schema for the JSON representation of an abstract record in Indaleko.")
        super().__init__(
            schema_id = schema_id,
            schema_title = schema_title,
            schema_description = schema_description,
            data_model = self.data_model,
            base_type = self.base_type,
            schema_rules = self.rules
        )

    @staticmethod
    def get_old_schema():
        """
        Return the schema for data managed by this class.
        """
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://fsgeek.ca/indaleko/schema/record.json",
            "title": "Indaleko Record Schema",
            "description": "Schema for the JSON representation of an abstract record within Indaleko.",
            "type": "object",
            "rule" : {
                "type" : "object",
                "properties": {
                    "Source Identifier": {
                        "type" : "object",
                        "properties" : {
                            "Identifier" : {
                                "type" : "string",
                                "description" : "The identifier of the source of the data.",
                                "format" : "uuid",
                            },
                            "Version" : {
                                "type" : "string",
                                "description" : "The version of the source of the data.",
                            },
                            "Description" : {
                                "type" : "string",
                                "description" : "A human readable description of the source of the data.",
                            }
                        },
                        "required" : ["Identifier", "Version"],
                    },
                    "Timestamp": {
                        "type" : "string",
                        "description" : "The timestamp of when this record was created.",
                        "format" : "date-time",
                    },
                    "Attributes" : {
                        "type" : "object",
                        "description" : "The attributes extracted from the source data.",
                    },
                    "Data" : {
                        "type" : "string",
                        "description" : "The raw (uninterpreted) data from the source.",
                    }
                },
                "required": ["Source Identifier", "Timestamp", "Attributes", "Data"]
            }
        }

    def old_get_schema(self : 'IndalekoRecordSchema') -> dict:
        if IndalekoRecordDataModel.IndalekoRecord == self.base_type:
            return super().get_json_schema()
        record_schema = IndalekoRecordSchema()
        schema= {'rule': {'type': 'object', 'properties': {}, 'required': []}}
        if hasattr(self, 'get_schema'):
            schema = super().get_json_schema()
        schema['rule']['properties']['Record'] = record_schema.get_json_schema()['rule']['properties']
        schema['rule']['required'].append('Record')
        return schema


def main():
    '''Test code for IndalekoRecordSchema.'''
    record_schema = IndalekoRecordSchema()
    record_schema.schema_detail()

if __name__ == "__main__":
    main()
