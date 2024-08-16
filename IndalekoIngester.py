"""
This is the generic class for an Indaleko Ingester.

An ingester takes information about some (or all) of the data that is stored in
various storage repositories available to this machine.  It processes the output
from indexers and then generates additional metadata to associate with the
storage object (s) in the database.

Examples of ingesters include:

* A file system specific metadata normalizer, which takes indexing information
  collected about one or more files and then converts that into a normalized
  form to be stored in the database. This includes common metadata such as
  length, label (the "name" of the file), timestamps, and so on.

* A semantic metadata generator, which takes the input from the indexer and then
  performs operations on one or more files described by the indexer to extract
  or compute metadata based upon the content of the file.  For example, this
  might include a "bag of words" from a text file, EXIF data from a JPEG
  file, or even commonly used checksums (e.g., MD5, SHA1, SHA256, etc.) that are
  computed from the file's contents.

* Environmental metadata generators, which take information about the
  environment in which the file is stored, such as the volume on which it is
  stored, additional non-standard metadata features that might be available,
  etc.


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

import logging
import json
import jsonlines
import datetime
import os
import uuid

from icecream import ic

from IndalekoServiceManager import IndalekoServiceManager
from IndalekoService import IndalekoService
from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig

class IndalekoIngester():
    '''
    IndalekoIngest is the generic class that we use for ingesting data from the
    various indexers that we have. Platform specific ingesters are built on top
    of this class to handle platform-specific ingestion.
    '''

    default_file_prefix = 'indaleko'
    default_file_suffix = '.jsonl'

    indaleko_generic_ingester_uuid_str = '526e0240-1ee4-46e9-9dac-3e557a8fb654'
    indaleko_generic_ingester_uuid = uuid.UUID(indaleko_generic_ingester_uuid_str)
    indaleko_generic_ingester_service_name = 'Indaleko Generic Ingester'
    indaleko_generic_ingester_service_description = \
        'This is the base (non-specialized) Indaleko Ingester. ' +\
        'You should not see it in the database.'
    indaleko_generic_ingester_service_version = '1.0'
    counter_values = (
        'input_count',
        'output_count',
        'dir_count',
        'file_count',
        'error_count',
        'edge_count',
    )



    def __init__(self : 'IndalekoIngester', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoIngest class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the ingester.
        '''
        self.file_prefix = IndalekoIngester.default_file_prefix
        if 'file_prefix' in kwargs:
            self.file_prefix = kwargs['file_prefix']
        self.file_prefix = self.file_prefix.replace('-', '_')
        self.file_suffix = IndalekoIngester.default_file_suffix
        if 'file_suffix' in kwargs:
            self.file_suffix = kwargs['file_suffix']
        self.file_suffix = self.file_suffix.replace('-', '_')
        self.machine_id = str(uuid.UUID('00000000-0000-0000-0000-000000000000').hex)
        if 'machine_id' in kwargs:
            self.machine_id = str(uuid.UUID(kwargs['machine_id']).hex)
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        if 'timestamp' in kwargs:
            self.timestamp = kwargs['timestamp']
        self.platform = 'unknown'
        if 'platform' in kwargs:
            self.platform = kwargs['platform']
        self.ingester = 'unknown'
        if 'ingester' in kwargs:
            self.ingester = kwargs['ingester']
        self.storage_description = None
        if 'storage_description' in kwargs:
            if kwargs['storage_description'] is None or \
                kwargs['storage_description'] == 'unknown':
                del kwargs['storage_description']
            else:
                self.storage_description = str(uuid.UUID(kwargs['storage_description']).hex)
        self.data_dir = kwargs.get('data_dir', Indaleko.default_data_dir)
        self.output_dir = kwargs.get('output_dir', self.data_dir)
        self.input_dir = kwargs.get('input_dir', self.data_dir)
        self.config_dir = kwargs.get('config_dir', Indaleko.default_config_dir)
        self.log_dir = kwargs.get('log_dir', Indaleko.default_log_dir)
        self.service_name = kwargs.get('Name', kwargs.get('service_name', None))
        assert self.service_name is not None, \
            f'Service name must be specified, kwargs={kwargs}'
        self.service_description = kwargs.get('Description',
                                              IndalekoIngester\
                                                .indaleko_generic_ingester_service_description)
        self.service_version = kwargs.get('Version',
                                          IndalekoIngester\
                                            .indaleko_generic_ingester_service_version)
        self.service_type = kwargs.get('Type', 'Ingester')
        self.service_identifier = kwargs.get('Identifier', kwargs.get('service_identifier', None))
        assert self.service_identifier is not None, \
            f'Service identifier must be specified\n{kwargs}'
        self.ingester_service = IndalekoServiceManager().register_service(
            service_name = self.service_name,
            service_description = self.service_description,
            service_version = self.service_version,
            service_type = self.service_type,
            service_id = self.service_identifier,
        )
        assert self.ingester_service is not None, 'Ingester service does not exist'
        for count in IndalekoIngester.counter_values:
            setattr(self, count, 0)

    def get_counts(self) -> dict:
        '''
        Retrieves counters about the ingester.
        '''
        return {x : getattr(self, x) for x in IndalekoIngester.counter_values}

    def generate_output_file_name(self, **kwargs) -> str:
        '''
        Given a set of parameters, generate a file name for the output
        file.
        '''
        output_dir = None
        if 'output_dir' in kwargs:
            output_dir = kwargs['output_dir']
            del kwargs['output_dir']
        if output_dir is None:
            output_dir = self.data_dir
        kwargs['ingester'] = self.ingester
        kwargs['machine'] = str(uuid.UUID(self.machine_id).hex)
        if self.storage_description is not None and \
            kwargs['storage'] != 'unknown':
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
        name = Indaleko.generate_file_name(**kwargs)
        return os.path.join(output_dir, name)

    def generate_file_name(self, target_dir : str = None, suffix = None) -> str:
        '''This will generate a file name for the ingester output file.'''
        if suffix is None:
            suffix = self.file_suffix
        kwargs = {
        'prefix' : self.file_prefix,
        'suffix' : suffix,
        'platform' : self.platform,
        'service' : 'ingest',
        'ingester' : self.ingester,
        'machine' : str(uuid.UUID(self.machine_id).hex),
        'collection' : 'Objects',
        'timestamp' : self.timestamp,
        'output_dir' : target_dir,
        }
        if self.storage_description is not None:
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
        return self.generate_output_file_name(**kwargs)

    @staticmethod
    def extract_metadata_from_ingester_file_name(file_name : str) -> dict:
        '''
        This will extract the metadata from the given file name.
        '''
        data = Indaleko.extract_keys_from_file_name(file_name)
        if 'machine' in data:
            data['machine'] = str(uuid.UUID(data['machine']))
        if 'storage' in data:
            data['storage'] = str(uuid.UUID(data['storage']))
        return data

    def write_data_to_file(self, data : list, file_name : str = None, jsonlines_output : bool = True) -> None:
        '''This will write the given data to the specified file.'''
        if data is None:
            raise ValueError('data must be specified')
        if file_name is None:
            raise ValueError('file_name must be specified')
        if jsonlines_output:
            with jsonlines.open(file_name, mode='w') as writer:
                for entry in data:
                    try:
                        writer.write(entry.to_dict())
                        self.output_count += 1
                    except TypeError as err:
                        logging.error('Error writing entry to JSONLines file: %s', err)
                        logging.error('Entry: %s', entry)
                        raise err
            logging.info('Wrote JSONLines data to %s', file_name)
        else:
            json.dump(data, file_name, indent=4)
            logging.info('Wrote JSON data to %s', file_name)

    @staticmethod
    def build_load_string(**kwargs) -> str:
        '''
        This will build the load string for the arangoimport command.
        '''
        db_config = IndalekoDBConfig()
        load_string = 'arangoimport'
        if 'collection' in kwargs:
            load_string += ' -collection ' + kwargs['collection']
        load_string += ' --server.username ' + db_config.get_user_name()
        load_string += ' --server.password ' + db_config.get_user_password()
        if db_config.get_ssl_state():
            load_string += ' --ssl.protocol 5'
            endpoint = 'http+ssl://'
        else:
            endpoint = 'http+tcp://'
        endpoint += db_config.get_hostname() + ':' + db_config.get_port()
        load_string += ' --server.endpoint ' + endpoint
        load_string += ' --server.database ' + kwargs.get('database', db_config.get_database_name())
        if 'file' in kwargs:
            load_string += ' ' + kwargs['file']
        return load_string
    ## arangoimport -collection Objects --server.username uiRXxRxF --server.password jDrcwy9VcAhhSmt --ssl.protocol 5
    ## .\indaleko-plt=Windows-svc=ingest-ingester=local_fs_ingester-machine=2e169bb700244dc193dc18b7d2d28190-storage=3397d97b2ca511edb2fcb40ede9a5a3c-collection=Objects-ts=2024_01_19T01#12#01.057294+00#00.jsonl
    ## --server.endpoint http+ssl://activitycontext.work:8529 --server.database Indaleko

    def load_indexer_data_from_file(self : 'IndalekoIngester') -> None:
        '''This function loads the indexer data from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            self.indexer_data = []
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.indexer_data.append(entry)
            ic(len(self.indexer_data))
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.indexer_data = json.load(file)
                ic(len(self.indexer_data))
        else:
            raise ValueError(f'Input file {self.input_file} is an unknown type')
        if not isinstance(self.indexer_data, list):
            raise ValueError('indexer_data is not a list')


def main():
    """Test code for IndalekoIngest.py"""
    # Now parse the arguments
    ingester = IndalekoIngester(test=True)
    assert ingester is not None, "Could not create ingester."
    fname = ingester.generate_file_name()
    print(fname)
    metadata = ingester.extract_metadata_from_ingester_file_name(fname)
    print(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    main()
