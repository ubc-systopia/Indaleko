import argparse
from icecream import ic

from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollections

class IndalekoSchemaMapping:
    '''The purpose of this class is to capture the mechanisms used for
    schema mapping in Indaleko between ArangoDB and GraphQL.
    '''


    def __init__(self, db_config: IndalekoDBConfig = None):
        '''Initialize the schema mapping object.'''
        if db_config is None:
            self.db_config = IndalekoDBConfig()
        else:
            self.db_config = db_config
        self.collections = IndalekoCollections()
        self.schema = {}
        self.mapped_schema = {}
        for collection in self.collections.collections.values():
            if collection.name.startswith('_'):
                continue # skip system collections
            self.schema[collection.name] = collection.get_schema()
            self.mapped_schema[collection.name] = self.map_schema(collection.name,
                                                                  self.schema[collection.name])

    @staticmethod
    def string_handler(value):
        '''Handle string values.'''
        assert isinstance(value, str), f"Expected string, got {type(value)} ({value})"
        return value

    @staticmethod
    def integer_handler(value):
        '''Handle integer values.'''
        assert isinstance(value, int), f"Expected integer, got {type(value)} ({value})"
        return value

    @staticmethod
    def boolean_handler(value):
        '''Handle boolean values.'''
        assert isinstance(value, bool), f"Expected boolean, got {type(value)} ({value})"
        return value

    @staticmethod
    def number_handler(value):
        '''Handle number values.'''
        assert isinstance(value, float), f"Expected number, got {type(value)} ({value})"
        return value

    @staticmethod
    def array_handler(value):
        '''Handle array values.'''
        assert isinstance(value, list), f"Expected list, got {type(value)} ({value})"
        # TODO: this needs to iterate over the array and process the elements
        return value

    @staticmethod
    def object_handler(value):
        '''Handle object values.'''
        assert isinstance(value, dict), f"Expected dictionary, got {type(value)} ({value})"
        # TODO: this needs to iterate over the dictionary and process the
        # elements
        return value

    @staticmethod
    def date_time_handler(value):
        '''Handle date-time values.'''
        assert isinstance(value, str), f"Expected string, got {type(value)} ({value})"
        # TODO: all my timestamps are ISO format, so I can include this
        # in the graphql schema
        return value

    @staticmethod
    def uuid_handler(value):
        '''Handle UUID values.'''
        assert isinstance(value, str), f"Expected string, got {type(value)} ({value})"
        return value

    handler_table = {
        'string': string_handler,
        'integer': integer_handler,
        'boolean': boolean_handler,
        'number': number_handler,
        'array': array_handler,
        'object': object_handler,
        'date-time': date_time_handler,
        'uuid': uuid_handler
    }

    def map_schema(self, collection_name : str, schema : dict) -> dict:
        '''Map the schema from ArangoDB to GraphQL.'''
        mapped_schema = {}
        for label, value in schema.items():
            if not isinstance(value, dict):
                ic('Skipping non dictionary value', collection_name, label, value)
                continue
            if 'type' not in value and 'properties' not in value:
                ic('Skipping value without type or properties', collection_name, label, value)
                continue
            ic(collection_name, label, value)
        return mapped_schema

    @staticmethod
    def handle_arango_object(prefix : str, arango_type : str, value):
        '''Handle an ArangoDB object.'''
        handler = IndalekoSchemaMapping.handler_table.get(arango_type)
        if handler is None:
            raise AssertionError(f"No handler for type {arango_type}")
        return handler(value)

    def get_graphql_mapping(self):
        '''Return the GraphQL mapping.'''

    @staticmethod
    def arango_to_graphql_type_mapping(arango_type : str) -> str:
        '''Return the ArangoDB to GraphQL type mapping.'''
        type_mapping = {
                'string': 'String',
                'integer': 'Int',
                'boolean': 'Boolean',
                'number': 'Float',
                'array': 'List',
                'object': 'Object',
                'date-time': 'String',  # or you can use a custom scalar type for DateTime
                'uuid': 'ID'
        }
        return type_mapping.get(arango_type, 'String')

    @staticmethod
    def generate_graphql_field(name : str, details: dict, required_fields: list) -> str:
        '''Generate the GraphQL field from the AraongoDB field.'''
        if isinstance(details, dict):
            graphql_type = IndalekoSchemaMapping.arango_to_graphql_type_mapping(details.get('type', 'string'))
            field = f"  {name}: {graphql_type}"
            if name in required_fields:
                field += "!"
            return field
        elif isinstance(details, list):
            # Handle lists of embedded objects
            fields = []
            for item in details:
                if isinstance(item, dict):
                    fields.append(IndalekoSchemaMapping.\
                                  generate_graphql_field(name, item, required_fields))
                elif isinstance(item, str):
                    if name != 'required':
                        fields.append(IndalekoSchemaMapping.\
                                    generate_graphql_field(f'{name}.{item}', details[item], required_fields))
                else:
                    raise AssertionError(f"List items must be dictionaries or strings, not {type(item)} ({item}, {details})")
            return "\n".join(fields)
        else:
            raise AssertionError(f"Details must be a dictionary or list, not {type(details)} ({details})")

    @staticmethod
    def process_properties(properties : dict, required_fields: list) -> list:
        fields = []
        for prop, details in properties.items():
            if 'properties' in details:
                # Nested object, recurse
                nested_fields = IndalekoSchemaMapping.process_properties(details['properties'], details.get('required', []))
                fields.append(f"  {prop} {{\n" + "\n".join(nested_fields) + "\n  }}")
            elif details.get('type') == 'array' and 'items' in details:
                # Handle array of objects
                item_details = details['items']
                nested_fields = IndalekoSchemaMapping.process_properties(item_details['properties'], item_details.get('required', []))
                fields.append(f"  {prop}: [{details['type']} {{\n" + "\n".join(nested_fields) + "\n  }}]")
            else:
                fields.append(IndalekoSchemaMapping.generate_graphql_field(prop, details, required_fields))
        return fields

    @staticmethod
    def generate_graphql_type(name, schema):
        '''Generate the GraphQL type.'''
        fields = []
        required_fields = schema['rule'].get('required', [])
        if 'properties' in schema['rule']:
            fields = IndalekoSchemaMapping.process_properties(schema['rule']['properties'], required_fields)
        else:
            for key, value in schema['rule'].items():
                fields.append(IndalekoSchemaMapping.generate_graphql_field(key, value, required_fields))
        # Use the name parameter to define the type name
        return f"type {name} {{\n" + "\n".join(fields) + "\n}}"

    def generate_graphql_schema(self):
        '''Generate the GraphQL schema.'''
        graphql_types = []
        for collection, schema in self.schema.items():
            graphql_types.append(IndalekoSchemaMapping.generate_graphql_type(collection, schema))
        return "\n\n".join(graphql_types)

def main():
    '''Main entry point for the script.'''
    parser = argparse.ArgumentParser(description='Indaleko Schema Mapping')
    parser.add_argument('--input', help='Input file')
    parser.add_argument('--output', help='Output file')
    args = parser.parse_args()
    ic(args)
    IndalekoSchemaMapping()
    # graphql_schema = schema_map.generate_graphql_schema()
    # print(graphql_schema)

if __name__ == '__main__':
    main()
