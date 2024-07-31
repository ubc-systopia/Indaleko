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

from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoSchema import IndalekoSchema

class IndalekoRecordSchema(IndalekoSchema):
    '''
    This is the schema for the Indaleko Record. Note that it is inherited and
    merged by other classes that derive from this base type.
    '''
    def __init__(self):
        '''Initialize the schema.'''
        if not hasattr(self, 'data_model'):
            self.data_model = IndalekoRecordDataModel()
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoRecordDataModel.IndalekoRecord
        super().__init__()

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

    def get_schema(self : 'IndalekoRecordSchema') -> dict:
        if IndalekoRecordDataModel.IndalekoRecord == self.base_type:
            return super().get_schema()
        record_schema = IndalekoRecordSchema()
        schema = super().get_schema()
        schema['rule']['properties']['Record'] = record_schema.get_schema()
        schema['rule']['required'].append('Record')
        return schema


def main():
    '''Test code for IndalekoRecordSchema.'''
    record_schema = IndalekoRecordSchema()
    record_schema.schema_detail(query=IndalekoRecordDataModel.get_queries(),
                                types=IndalekoRecordDataModel.get_types())

if __name__ == "__main__":
    main()
