'''
This module provides functionality for interacting with the Indaleko schema.
'''
import argparse
import json
import importlib
import os
import re

from icecream import ic

from Indaleko import Indaleko

class IndalekoSchema:
    '''This class exports schema functionality related to Indaleko'''
    def __init__(self, **kwargs) -> None:
        '''Initialize the schema object'''
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def build_from_definitions() -> 'IndalekoSchema':
        '''Build the schema from the definitions.'''
        schema = {}
        for collection, attributes  in Indaleko.Collections.items():
            if 'schema' in attributes:
                schema[collection] = attributes['schema']
        return IndalekoSchema(
            offline=True,
            schema=schema
        )

    @staticmethod
    def build_from_db() -> 'IndalekoSchema':
        '''Build the schema from the database.'''
        db_config = importlib.import_module('IndalekoDBConfig').IndalekoDBConfig()
        db_config.start()
        schema = {}
        for collection in db_config.db.collections():
            name = collection['name']
            if name.startswith('_'):
                continue
            x = db_config.db.collection(name)
            properties = x.properties()
            schema[name] = properties['schema']
        return IndalekoSchema(
            offline=False,
            schema=schema
        )

    @staticmethod
    def build_from_libraries() -> 'IndalekoSchema':
        '''Build the schema from the python libraries.'''
        this_file = os.path.basename(__file__)
        libraries = [x for x in os.listdir('.') if x.endswith('Schema.py')]
        schema_interfaces = [x[:-3] for x in libraries]
        schema = {}
        for interface in schema_interfaces:
            if interface == this_file[:-3]: # self-identify this file
                continue
            module = importlib.import_module(interface)
            collection_name = interface[8:-6]
            if collection_name not in Indaleko.Collections:
                if 'Object' == collection_name:
                    schema['Objects'] = getattr(module, interface)
                if 'Relationship' == collection_name:
                    schema['Relationships'] = getattr(module, interface)
                if 'ActivityDataProvider' == collection_name:
                    schema['ActivityDataProviders'] = getattr(module, interface)
                if 'UserRelationship' == collection_name:
                    schema['UserRelationships'] = getattr(module, interface)
                if 'User' == collection_name:
                    schema['Users'] = getattr(module, interface)
                else:
                    ic(f'Skipping schema file for {collection_name}')
                    continue
            else:
                schema[collection_name] = getattr(module, interface)().get_json_schema()
        return IndalekoSchema(
            offline=True,
            schema=schema
        )

    @staticmethod
    def camel_to_snake(name: str) -> str:
        '''Convert a camel case name to snake case.'''
        return re.sub('([a-z])([A-Z])', r'\1_\2', name).lower()


class IndalekoSchemaInterface:
    '''This class provides an interface for interacting with this library.'''
    def __init__(self) ->None:
        '''Initialize the object.'''
        self.indaleko_schema = None
        self.parser = argparse.ArgumentParser(description='Indaleko Schema Gatherer')
        self.parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        command_parser = self.parser.add_subparsers(dest='command', help='Command to run')
        show_command = command_parser.add_parser('show', help='Show Indaleko schema')
        show_command_parser = show_command.add_subparsers(dest='subcommand', help='Subcommand to run')
        show_db_schema = show_command_parser.show_db = show_command_parser.add_parser('db', help='Show the database schema')
        show_db_schema.set_defaults(func=IndalekoSchemaInterface.show_db_schema)
        show_library_schema = show_command_parser.show_library = show_command_parser.add_parser('library', help='Show the library schema')
        show_library_schema.set_defaults(func=IndalekoSchemaInterface.show_library_schema)
        show_definitions = show_command_parser.add_parser('definitions', help='Show the schema from the definitions')
        show_definitions.set_defaults(func=IndalekoSchemaInterface.show_definitions_schema)
        show_command.set_defaults(func=self.show_library_schema)
        self.parser.set_defaults(func=self.show_library_schema)
        self.args = self.parser.parse_args()
        print(self.args)
        self.args.func()

    @staticmethod
    def show_db_schema():
        '''Show the database schema.'''
        print('Showing the database schema.')
        indaleko_schema = IndalekoSchema.build_from_db()
        if hasattr(indaleko_schema, 'schema'):
            ic(indaleko_schema.schema)
            ic(type(indaleko_schema.schema))
            ic(len(json.dumps(indaleko_schema.schema)))

    @staticmethod
    def show_library_schema():
        '''Show the library schema.'''
        print('Showing the library schema.')
        indaleko_schema = IndalekoSchema.build_from_libraries()
        if hasattr(indaleko_schema, 'schema'):
            ic(indaleko_schema.schema)
            ic(type(indaleko_schema.schema))
            ic(len(json.dumps(indaleko_schema.schema)))

    @staticmethod
    def show_definitions_schema():
        '''Show the schema from the definitions.'''
        print('Showing the schema from the definitions.')
        indaleko_schema = IndalekoSchema.build_from_definitions()
        if hasattr(indaleko_schema, 'schema'):
            ic(indaleko_schema.schema)
            ic(type(indaleko_schema.schema))
            ic(len(json.dumps(indaleko_schema.schema)))

def main():
    '''Main entry point for the program.'''
    print('This is the Indaleko Schema Gatherer.')
    IndalekoSchemaInterface()


if __name__ == '__main__':
    main()
