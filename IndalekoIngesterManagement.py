"""
This is a data management tool for the Indaleko ingester files.

An ingester takes information about some (or all) of the data that is stored in
various storage repositories available to this machine.  It processes the output
from indexers and then generates additional metadata to associate with the
storage object (s) in the database.

See (IndalekoIngester.py)[IndalekoIngester.py] for more information about
ingesters in general.

The purpose of this management tool is to

1) Identify ingester files;
2) Construct the appropriate import commands for the ArangoDB import tool
3) Execute the import commands
4) Verify the import was successful

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
"""

import argparse
import logging
import os

from icecream import ic

from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoLogging import IndalekoLogging
from IndalekoSingleton import IndalekoSingleton

class IndalekoIngesterManagement(IndalekoSingleton):
    '''This is the primary class for the Indaleko Ingester Management tool.'''

    def __init__(self):
        '''Initialize the Indaleko Ingester Management tool.'''
        ic('Indaleko Ingester Management Tool: Init called')
        if self._initialized:
            return
        self._initialized = True
        self.db = IndalekoDBConfig()
        self.ingester_files = self.identify_ingester_files()
        self.indexer_files = self.identify_indexer_files()

    def identify_ingester_files(self, data_dir : str = Indaleko.default_data_dir) -> list:
        '''Identify the ingester files that are available for processing.'''
        ic('Identify ingester files called')
        candidate_files = [x for x in os.listdir(data_dir) if x.endswith('.jsonl')]
        ingester_files = {}
        ingester_files['objects'] = [x for x in candidate_files if 'collection=Objects' in x]
        ingester_files['relationships'] = [x for x in candidate_files if 'collection=Relationships' in x]
        return ingester_files

    def identify_indexer_files(self, data_dir : str = Indaleko.default_data_dir) -> list:
        '''Identify the indexer files that are available for processing.'''
        ic('Identify indexer files')
        indexer_files = [x for x in os.listdir(data_dir) if 'indexer' in x and x.endswith('.jsonl')]
        return indexer_files

    def build_import_command(self,
                             file_name : str,
                             collection : str = None,
                             data_dir : str = Indaleko.default_data_dir
                             ) -> str:
        '''
        Given a file name, build an import command for the ArangoDB import
        tool.
        '''
        if collection is None:
            if 'collection=Objects' in file_name:
                collection=Indaleko.Indaleko_Object_Collection
            elif 'collection=Relationships' in file_name:
                collection=Indaleko.Indaleko_Relationship_Collection
        if collection is None:
            raise ValueError(f'Unknown collection type for file {file_name}')
        endpoint_prototcol = 'http+tcp'
        if self.db.get_ssl_state():
            endpoint_prototcol = 'https+ssl://'
        else:
            endpoint_prototcol = 'http+tcp://'
        cmd = 'arangoimport'
        cmd += f' -collection {collection}'
        cmd += ' --create-collection false'
        cmd += f' --server.username {self.db.config['database']['user_name']}'
        cmd += f' --server.password {self.db.config['database']['user_password']}'
        cmd += f' --server.endpoint {endpoint_prototcol}'
        cmd += f'{self.db.config['database']['host']}:{self.db.config['database']['port']}'
        cmd += f' --server.database {self.db.config['database']['database']}'
        cmd += f' {data_dir}/{file_name}'
        return cmd


    def construct_import_commands(self, input_file : str = None) -> list:
        '''Construct the import commands for the ArangoDB import tool.'''
        ic(f'Construct import commands called: {input_file}')
        import_commands = []
        if input_file is not None:
            assert os.path.exists(input_file), f'Input file {input_file} does not exist'
            import_commands.append(self.build_import_command(input_file))
        else:
            for file in self.ingester_files['objects']:
                import_commands.append(self.build_import_command(file))
            for file in self.ingester_files['relationships']:
                import_commands.append(self.build_import_command(file, collection=Indaleko.Indaleko_Relationship_Collection))
        return import_commands

    def execute_import_commands(self):
        '''Execute the import commands for the ArangoDB import tool.'''
        ic('Execute import commands called')

    def verify_import(self):
        '''Verify the import was successful.'''
        ic('Verify import called')

    @staticmethod
    def identify_command(args : argparse.Namespace) -> None:
        '''Identify the ingester files that are available for processing.'''
        ic('Identify command called')
        ic(args)
        iim = IndalekoIngesterManagement()
        ic(iim.ingester_files)
        ic(iim.indexer_files)

    @staticmethod
    def construct_command(args : argparse.Namespace) -> None:
        '''Construct the import commands for the ArangoDB import tool.'''
        ic('Construct command called')
        ic(args)
        iim = IndalekoIngesterManagement()
        if args.input is not None:
            import_commands = iim.construct_import_commands(args.input)
        else:
            import_commands = iim.construct_import_commands()
        for command in import_commands:
            print(command)

    @staticmethod
    def execute_command(args : argparse.Namespace) -> None:
        '''Execute the import commands for the ArangoDB import tool.'''
        ic('Execute command called')
        ic(args)

    @staticmethod
    def verify_command(args : argparse.Namespace) -> None:
        '''Verify the import was successful.'''
        ic('Verify command called')
        ic(args)


def main():
    '''This is the main interface for the IndalekoIngesterManagement tool.'''
    pre_parser = argparse.ArgumentParser(description='Indaleko Ingester Management Tool', add_help=False)
    logging_levels = IndalekoLogging.get_logging_levels()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help=f'Path to the config directory (default is {Indaleko.default_config_dir})',
                            default=Indaleko.default_config_dir)
    pre_parser.add_argument('--logdir',
                            help=f'Path to the log directory (default is {Indaleko.default_log_dir})',
                            default=Indaleko.default_log_dir)
    pre_parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    pre_parser.add_argument('--datadir',
                            help=f'Path to the data directory (default is {Indaleko.default_data_dir})',
                            type=str,
                            default=Indaleko.default_data_dir)
    command_subparser = pre_parser.add_subparsers(dest='command')
    parser_identify = command_subparser.add_parser('identify', help='Identify the ingester files')
    parser_identify.set_defaults(func=IndalekoIngesterManagement.identify_command)
    parser_construct = command_subparser.add_parser('construct', help='Construct the import commands')
    parser_construct.add_argument('--input', default=None, help='Input file to process')
    parser_construct.set_defaults(func=IndalekoIngesterManagement.construct_command)
    parser_execute = command_subparser.add_parser('execute', help='Execute the import commands')
    parser_execute.set_defaults(func=IndalekoIngesterManagement.execute_command)
    parser_verify = command_subparser.add_parser('verify', help='Verify the import was successful')
    parser_verify.set_defaults(func=IndalekoIngesterManagement.verify_command)
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.command is None:
        pre_parser.print_help()
        return
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.set_defaults(func=IndalekoIngesterManagement.identify_command)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
