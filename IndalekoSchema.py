'''
This module provides functionality for interacting with the Indaleko schema.
'''
import argparse
import importlib
import inspect
import os

from icecream import ic

from IndalekoDataModel import IndalekoDataModel, IndalekoUUID

class IndalekoSchema:
    '''This class exports schema functionality related to Indaleko'''

    def __init__(self) -> None:
        '''Initialize the object.'''

class IndalekoSchemaInterface:
    '''This class provides an interface for interacting with this library.'''
    def __init__(self) ->None:
        '''Initialize the object.'''
        self.parser = argparse.ArgumentParser(description='Indaleko Schema Gatherer')
        self.parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        command_parser = self.parser.add_subparsers(dest='command', help='Command to run')
        show_command = command_parser.add_parser('show', help='Show Indaleko schema')
        show_command_parser = show_command.add_subparsers(dest='subcommand', help='Subcommand to run')
        show_db_schema = show_command_parser.show_db = show_command_parser.add_parser('db', help='Show the database schema')
        show_db_schema.set_defaults(func=self.show_db_schema)
        show_library_schema = show_command_parser.show_library = show_command_parser.add_parser('library', help='Show the library schema')
        show_library_schema.set_defaults(func=self.show_library_schema)
        show_command.set_defaults(func=self.show_library_schema)
        self.parser.set_defaults(func=self.show_library_schema)
        self.args = self.parser.parse_args()
        print(self.args)
        self.args.func()

    def show_db_schema(self):
        '''Show the database schema.'''
        print('Showing the database schema.')

    def show_library_schema(self):
        '''Show the library schema.'''
        print('Showing the library schema.')
        schema_files = [x for x in os.listdir('.') if x.endswith('Schema.py')]
        ic(schema_files)
        schema_interfaces = [x[:-3] for x in schema_files]
        ic(schema_interfaces)
        for interface in schema_interfaces:
            ic(f'Importing {interface}')
            module = importlib.import_module(interface)
            ic(module)

def main():
    '''Main entry point for the program.'''
    print('This is the Indaleko Schema Gatherer.')
    interface = IndalekoSchemaInterface()
    ic(interface)

if __name__ == '__main__':
    main()
