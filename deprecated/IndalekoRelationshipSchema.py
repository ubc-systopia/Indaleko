'''
This module defines the schema for the Indaleko Relationship data.

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
from jsonschema import validate, exceptions
import apischema

from IndalekoRelationshipDataModel import IndalekoRelationshipDataModel
from IndalekoRecordSchema import IndalekoRecordSchema
class IndalekoRelationshipSchema(IndalekoRecordSchema):
    '''Define the schema for use with the Relationship collection.'''

    def __init__(self, **kwargs):
        '''Initialize the Relationship schema.'''
        if not hasattr(self, 'data_model'):
            self.data_model = IndalekoRelationshipDataModel()
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoRelationshipDataModel.IndalekoRelationship
        relationship_rules = apischema.json_schema.deserialization_schema(
            IndalekoRelationshipDataModel.IndalekoRelationship,
            additional_properties=True)
        if not hasattr(self, 'rules'):
            self.rules = relationship_rules
        else:
            self.rules.update(relationship_rules)
        schema_id = kwargs.get('schema_id', "https://activitycontext.work/schema/indaleko-relationship.json")
        schema_title = kwargs.get('schema_title', "Indaleko Relationship Schema")
        schema_description = kwargs.get('schema_description', "Schema for the JSON representation of an Indaleko Relationship.")
        super().__init__(
            schema_id = schema_id,
            schema_title = schema_title,
            schema_description = schema_description,
            data_model = self.data_model,
            base_type = self.base_type,
            schema_rules = relationship_rules
        )

    @staticmethod
    def is_valid_relationship(indaleko_relationship : dict) -> bool:
        '''Given a dict, determine if it is a valid Indaleko Relationship.'''
        assert isinstance(indaleko_relationship, dict), 'relationship must be a dict'
        valid = False
        try:
            validate(instance=indaleko_relationship,
                     schema=IndalekoRelationshipSchema().get_json_schema())
            valid = True
        except exceptions.ValidationError as error:
            print(f'Validation error: {error.message}')
        return valid


def main():
    """Test the IndalekoMachineConfigSchema class."""
    if IndalekoRelationshipSchema\
        .is_valid_json_schema_dict(IndalekoRelationshipSchema().get_json_schema()):
        print('Schema is valid.')
    print(json.dumps(IndalekoRelationshipSchema().get_json_schema(), indent=4))

if __name__ == "__main__":
    main()
