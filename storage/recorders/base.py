"""
This is the generic class for an Indaleko Storage Recorder.

An Indaleko storage recorder takes information about some (or all) of the data that is stored in
various storage repositories available to this machine.  It processes the output
from storage recorders and then generates additional metadata to associate with the
storage object (s) in the database.

Examples of recorders include:

* A file system specific metadata normalizer, which takes metadata information
  collected about one or more files and then converts that into a normalized
  form to be stored in the database. This includes common metadata such as
  length, label (the "name" of the file), timestamps, and so on.

* A semantic metadata generator, which takes the input from collectors and then
  performs operations on one or more files described by the collector to extract
  or compute metadata based upon the content of the file.  For example, this
  might include a "bag of words" from a text file, EXIF data from a JPEG
  file, or even commonly used checksums (e.g., MD5, SHA1, SHA256, etc.) that are
  computed from the file's contents.

* Environmental metadata generators, which take information about the
  environment in which the file is stored, such as the volume on which it is
  stored, additional non-standard metadata features that might be available,
  etc.


Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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
import datetime
import logging
import json
import jsonlines
import os
from pathlib import Path
import uuid
import sys
import tempfile

from typing import Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoCollection, IndalekoDBConfig, IndalekoDBCollections, IndalekoServiceManager
from utils.cli.base import IndalekoBaseCLI
from utils.decorators import type_check
from utils.misc.directory_management import indaleko_default_data_dir, indaleko_default_config_dir, indaleko_default_log_dir
from utils.misc.file_name_management import generate_file_name, extract_keys_from_file_name
from data_models import IndalekoSemanticAttributeDataModel
from storage import IndalekoObject
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.i_relationship import IndalekoRelationship
# pylint: enable=wrong-import-position
class BaseStorageRecorder:
    '''
    IndalekoStorageRecorder is the generic class that we use for recording data from the
    various collectors that we have. Platform specific recorders are built on top
    of this class to handle platform-specific recording.
    '''

    default_file_prefix = 'indaleko'
    default_file_suffix = '.jsonl'
    recorder_name = 'fs_recorder'


    indaleko_generic_storage_recorder_uuid_str = '526e0240-1ee4-46e9-9dac-3e557a8fb654'
    indaleko_generic_storage_recorder_uuid = uuid.UUID(indaleko_generic_storage_recorder_uuid_str)
    indaleko_generic_storage_recorder_service_name = 'Indaleko Generic Storage Recorder'
    indaleko_generic_storage_recorder_service_description = \
        'This is the base (non-specialized) Indaleko Storage Recorder. ' +\
        'You should not see it in the database.'
    indaleko_generic_storage_recorder_service_version = '1.0'
    counter_values = (
        'input_count',
        'output_count',
        'dir_count',
        'file_count',
        'error_count',
        'edge_count',
    )

    # Note: this defaults the platform and service type value(s);
    # recorder_data = IndalekoStorageRecorderDataModel(
    #    RecorderServiceName = indaleko_generic_storage_recorder_service_name,
    #    RecorderServiceUUID = indaleko_generic_storage_recorder_uuid,
    #    RecorderServiceVersion = indaleko_generic_storage_recorder_service_version,
    #    RecorderServiceDescription = indaleko_generic_storage_recorder_service_description,
    #)
    # This must come from the derived class: not a default value

    def __init__(self : 'BaseStorageRecorder', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoStorageRecorder class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the recorder.
        '''
        if 'recorder_data' in kwargs:
            self.recorder_data = kwargs['recorder_data']
        if 'args' in kwargs:
            self.args = kwargs['args']
            self.output_type = getattr(self.args, 'output_type', 'file')
            self.debug = getattr(self.args, 'debug', False)
        else:
            self.args = None
            self.output_type = 'file'
            self.debug = kwargs.get('debug', False)
        if 'storage' in kwargs:
            self.storage_description = kwargs['storage']
        self.file_prefix = BaseStorageRecorder.default_file_prefix
        if 'file_prefix' in kwargs:
            self.file_prefix = kwargs['file_prefix']
        self.file_prefix = self.file_prefix.replace('-', '_')
        self.file_suffix = BaseStorageRecorder.default_file_suffix
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
        self.recorder = 'unknown'
        if 'recorder' in kwargs:
            self.recorder = kwargs['recorder']
        self.storage_description = None
        if 'storage_description' in kwargs:
            if kwargs['storage_description'] is None or \
                kwargs['storage_description'] == 'unknown':
                del kwargs['storage_description']
            else:
                self.storage_description = str(uuid.UUID(kwargs['storage_description']).hex)
                if self.debug:
                    ic('Storage description: ', self.storage_description)
        self.data_dir = kwargs.get('data_dir', indaleko_default_data_dir)
        self.output_dir = kwargs.get('output_dir', self.data_dir)
        self.input_dir = kwargs.get('input_dir', self.data_dir)
        self.input_file = kwargs.get('input_file', None)
        self.config_dir = kwargs.get('config_dir', indaleko_default_config_dir)
        self.log_dir = kwargs.get('log_dir', indaleko_default_log_dir)
        self.recorder_service = IndalekoServiceManager().register_service(
            service_name = self.get_recorder_service_name(),
            service_id = str(self.get_recorder_service_uuid()),
            service_version = self.get_recorder_service_version(),
            service_description = self.get_recorder_service_description(),
            service_type = self.get_recorder_service_type(),
        )
        assert self.recorder_service is not None, 'Recorder service does not exist'
        for count in self.counter_values:
            setattr(self, count, 0)
        self.dir_data_by_path = {}
        self.dir_data = []
        self.file_data = []
        self.dirmap = {}
        self.dir_edges = []
        self.collector_data = []

    @classmethod
    def get_recorder_platform_name(cls : 'BaseStorageRecorder') -> str:
        '''This function returns the platform name for the recorder.'''
        if hasattr(cls, 'recorder_data'):
            return cls.recorder_data.RecorderPlatformName
        else:
            ic(f'Warning, no recorder_data, returning indaleko_recorder_platform')
            return 'indaleko_recorder_platform'

    @classmethod
    def get_recorder_service_name(cls) -> str:
        '''This function returns the service name for the recorder.'''
        if hasattr(cls, 'recorder_data'):
            return cls.recorder_data.RecorderServiceName
        else:
            ic(f'Warning, no recorder_data, returning indaleko_service_name')
            return 'indaleko_service_name'

    @classmethod
    def get_recorder_service_uuid(cls) -> uuid.UUID:
        '''This function returns the service UUID for the recorder.'''
        if hasattr(cls, 'recorder_data'):
            return cls.recorder_data.RecorderServiceUUID
        else:
            ic(f'Warning, no recorder_data, returning {uuid.UUID('00000000-0000-0000-0000-000000000000')}')
            return uuid.UUID('00000000-0000-0000-0000-000000000000')

    @classmethod
    def get_recorder_service_version(cls) -> str:
        '''This function returns the service version for the recorder.'''
        if hasattr(cls, 'recorder_data'):
            return cls.recorder_data.RecorderServiceVersion
        else:
            ic(f'Warning, no recorder_data, returning 1.0')
            return '1.0'

    @classmethod
    def get_recorder_service_description(cls) -> str:
        '''This function returns the service description for the recorder.'''
        if hasattr(cls, 'recorder_data'):
            return cls.recorder_data.RecorderServiceDescription
        else:
            ic(f'Warning, no recorder_data, returning indaleko_service_description')
            return 'indaleko_service_description'

    @classmethod
    def get_recorder_service_type(cls) -> str:
        '''This function returns the service type for the recorder.'''
        if hasattr(cls, 'recorder_data'):
            return cls.recorder_data.RecorderServiceType
        else:
            service_type = IndalekoServiceManager.service_type_storage_recorder
            ic(f'Warning, no recorder_data, returning {service_type}')
            return service_type

    def get_counts(self) -> dict:
        '''
        Retrieves counters about the recorder.
        '''
        return {x : getattr(self, x) for x in BaseStorageRecorder.counter_values}

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
        kwargs['machine'] = str(uuid.UUID(self.machine_id).hex)
        if self.storage_description is not None and \
            kwargs['storage'] != 'unknown':
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
        name = generate_file_name(**kwargs)
        return os.path.join(output_dir, name)

    def generate_file_name(self, target_dir : str = None, suffix = None) -> str:
        '''This will generate a file name for the recorder output file.'''
        if suffix is None:
            suffix = self.file_suffix
        kwargs = {
        'prefix' : self.file_prefix,
        'suffix' : suffix,
        'platform' : self.platform,
        'service' : self.recorder_name,
        'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
        'timestamp' : self.timestamp,
        'output_dir' : target_dir,
        }
        if hasattr(self, 'machine_id') and self.machine_id is not None:
            kwargs['machine'] = str(uuid.UUID(self.machine_id).hex)
        if hasattr(self, 'storage_description') and self.storage_description is not None:
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
        if hasattr(self, 'user_id') and self.user_id is not None:
            kwargs['user'] = str(uuid.UUID(self.user_id).hex)
        return self.generate_output_file_name(**kwargs)

    @staticmethod
    def extract_metadata_from_recorder_file_name(file_name : str) -> dict:
        '''
        This will extract the metadata from the given file name.
        '''
        data = extract_keys_from_file_name(file_name)
        if 'machine' in data:
            data['machine'] = str(uuid.UUID(data['machine']))
        if 'storage' in data:
            data['storage'] = str(uuid.UUID(data['storage']))
        return data

    @staticmethod
    def write_data_to_file(data : list, file_name : str = None, jsonlines_output : bool = True) -> int:
        '''
        This will write the given data to the specified file.

        Inputs:
            * data: the data to write
            * file_name: the name of the file to write to
            * jsonlines_output: whether to write the data in JSONLines format

        Returns:
            The number of records written to the file.
        '''
        if data is None:
            raise ValueError('data must be specified')
        if file_name is None:
            raise ValueError('file_name must be specified')
        output_count = 0
        if jsonlines_output:
            with jsonlines.open(file_name, mode='w') as writer:
                for entry in data:
                    try:
                        writer.write(entry.serialize())
                        output_count += 1
                    except TypeError as err:
                        logging.error('Error writing entry to JSONLines file: %s', err)
                        logging.error('Entry: %s', entry)
                        logging.error('Output count: %d', output_count)
                        logging.error('Data size %d', len(data))
                        raise err
            logging.info('Wrote JSONLines data to %s', file_name)
            ic('Wrote JSON data to', file_name)
        else:
            json.dump(data, file_name, indent=4)
            logging.info('Wrote JSON data to %s', file_name)
        return output_count

    @type_check
    def upload_data_to_database(self,
                                data : list,
                                collection : Union[IndalekoCollection, str] = 'Objects',
                                database : IndalekoDBConfig = IndalekoDBConfig(),
                                chunk_size : int = 5000) -> bool:
        '''
        This will upload the specified data to the database.

        Inputs:
            * data: list of data to upload (must be in the correct format, of course)
            * collection: the collection to which we should upload the data (defaults to 'Objects')
            * database: the database configuration object (uses default config if not specified)
            * chunk_size: the number of records to upload at a time (defaults to 5000)
        '''
        raise NotImplementedError('upload_data_to_database implementation is not complete.')
        if isinstance(collection, str):
            collection = IndalekoCollection(collection, db_config=database)
            assert isinstance(collection, IndalekoCollection), 'Collection is not an IndalekoCollection'
        count = 0
        while count < len(data):
            chunk = data[count:count + chunk_size]
            count += chunk_size

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

    def load_collector_data_from_file(self : 'BaseStorageRecorder') -> None:
        '''This function loads the collector data from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            self.collector_data = []
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.collector_data.append(entry)
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.collector_data = json.load(file)
        else:
            raise ValueError(f'Input file {self.input_file} is an unknown type')
        if not isinstance(self.collector_data, list):
            raise ValueError('collector_data is not a list')
        self.input_count = len(self.collector_data)

    @staticmethod
    def build_storage_relationship(
        id1 : Union[str, uuid.UUID],
        id2 : Union[str, uuid.UUID],
        relationship : Union[str, uuid.UUID],
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a storage relationship object between two objects.'''
        return IndalekoRelationship(
            objects = (
                {
                    'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
                    'object' : id1,
                },
                {
                    'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
                    'object' : id2,
                }
            ),
            relationships = [
                IndalekoSemanticAttributeDataModel(
                    Identifier=relationship
                )
            ],
            source_id=source_id
        )

    @staticmethod
    def build_dir_contains_relationship(
        parent : Union[str, uuid.UUID], # parent
        child : Union[str, uuid.UUID], # child
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a contains relationship object for a directory and a child.'''
        return BaseStorageRecorder.build_storage_relationship(
            parent, child, IndalekoRelationship.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR, source_id
        )

    @staticmethod
    def build_contained_by_dir_relationship(
        child : Union[str, uuid.UUID], # child
        parent : Union[str, uuid.UUID], # parent
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a contains relationship object for a directory and a child.'''
        return BaseStorageRecorder.build_storage_relationship(
            child, parent, IndalekoRelationship.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR, source_id
        )

    @staticmethod
    def build_volume_contains_relationship(
        volume : Union[str, uuid.UUID], # volume
        child : Union[str, uuid.UUID], # child
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a contains relationship object for a volume and a child.'''
        return BaseStorageRecorder.build_storage_relationship(
            volume, child, IndalekoRelationship.VOLUME_CONTAINS_RELATIONSHIP_UUID_STR, source_id
        )

    @staticmethod
    def build_contained_by_volume_relationship(
        child : Union[str, uuid.UUID], # child
        volume : Union[str, uuid.UUID], # volume
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a contains relationship object for a volume and a child.'''
        return BaseStorageRecorder.build_storage_relationship(
            child, volume, IndalekoRelationship.CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR, source_id
        )

    @staticmethod
    def build_machine_contains_relationship(
        machine : Union[str, uuid.UUID], # machine
        child : Union[str, uuid.UUID], # child
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a contains relationship object for a machine and a child.'''
        return BaseStorageRecorder.build_storage_relationship(
            machine, child, IndalekoRelationship.MACHINE_CONTAINS_RELATIONSHIP_UUID_STR, source_id
        )

    @staticmethod
    def build_contained_by_machine_relationship(
        child : Union[str, uuid.UUID], # child
        machine : Union[str, uuid.UUID], # machine
        source_id : Union[str, uuid.UUID]) -> IndalekoRelationship:
        '''This builds a contains relationship object for a machine and a child.'''
        return BaseStorageRecorder.build_storage_relationship(
            child, machine, IndalekoRelationship.CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR, source_id
        )


    def build_dirmap(self) -> None:
        '''This function builds the directory/file map'''
        for item in self.dir_data:
            fqp = os.path.join(item['Path'], item['Name'])
            identifier = item.args['ObjectIdentifier']
            self.dirmap[fqp] = identifier

    def build_edges(self) -> None:
        '''Build the edges between files and directories.'''
        # TODO: this should be abstracted out to allow
        # moving this into the base class.
        source_id = IndalekoSourceIdentifierDataModel(
            Identifier = str(self.recorder_data.RecorderServiceUUID),
            Version='1.0',
        )
        for item in self.dir_data + self.file_data:
            parent = item['Path']
            if parent not in self.dirmap:
                continue
            parent_id = self.dirmap[parent]
            self.dir_edges.append(BaseStorageRecorder.build_dir_contains_relationship(
                parent_id, item.args['ObjectIdentifier'], source_id)
            )
            self.edge_count += 1
            self.dir_edges.append(BaseStorageRecorder.build_contained_by_dir_relationship(
                item.args['ObjectIdentifier'], parent_id, source_id)
            )
            self.edge_count += 1
            volume = item.args.get('Volume')
            if volume:
                self.dir_edges.append(BaseStorageRecorder.build_volume_contains_relationship(
                    volume, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                self.dir_edges.append(BaseStorageRecorder.build_contained_by_volume_relationship(
                    item.args['ObjectIdentifier'], volume, source_id)
                )
                self.edge_count += 1
            machine_id = item.args.get('machine_id')
            if machine_id:
                self.dir_edges.append(BaseStorageRecorder.build_machine_contains_relationship(
                    machine_id, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                self.dir_edges.append(BaseStorageRecorder.build_contained_by_machine_relationship(
                    item.args['ObjectIdentifier'], machine_id, source_id)
                )
                self.edge_count += 1


    @staticmethod
    def arangoimport_object_data(recorder : 'BaseStorageRecorder') -> None:
        '''Import the object data into the database'''
        if recorder.object_data_load_string is None:
            raise ValueError('object_data_load_string must be set')
        recorder.execute_command(recorder.object_data_load_string)


    @staticmethod
    def arangoimport_relationship_data(recorder : 'BaseStorageRecorder') -> None:
        '''Import the relationship data into the database'''
        if recorder.relationship_data_load_string is None:
            raise ValueError('relationship_data_load_string must be set')
        recorder.execute_command(recorder.relationship_data_load_string)


    @staticmethod
    def bulk_upload_object_data(recorder : 'BaseStorageRecorder') -> None:
        '''Bulk upload the object data to the database'''
        raise NotImplementedError('bulk_upload_object_data must be implemented')


    @staticmethod
    def bulk_upload_relationship_data(recorder : 'BaseStorageRecorder') -> None:
        '''Bulk upload the relationship data to the database'''
        raise NotImplementedError('bulk_upload_relationship_data must be implemented')

    class base_recorder_mixin(IndalekoBaseCLI.default_handler_mixin):
        '''This is a mixin class for the base recorder.'''

        @staticmethod
        @type_check
        def get_additional_parameters(pre_parser : argparse.ArgumentParser) -> argparse.ArgumentParser:
            '''This function adds common switches for local storage recorders to a parser.'''
            default_output_type = 'file'
            output_type_choices = [default_output_type]
            output_type_help = 'Output type: file  = write to a file, '
            output_type_choices.append('incremental')
            output_type_help += 'incremental = add new entries, update changed entries in database, '
            output_type_choices.append('bulk')
            output_type_help += 'bulk = write all entries to the database using the bulk uploader interface, '
            output_type_choices.append('docker')
            output_type_help += 'docker = copy to the docker volume'
            output_type_help += f' (default={default_output_type})'
            pre_parser.add_argument('--output_type',
                                    choices=output_type_choices,
                                    default=default_output_type,
                                    help=output_type_help)
            pre_parser.add_argument('--arangoimport',
                                    default=False,
                                    help='Use arangoimport to load data (default=False)',
                                    action='store_true')
            pre_parser.add_argument('--bulk',
                                    default=False,
                                    help='Use bulk loader to load data (default=False)',
                                    action='store_true')
            return pre_parser

    @staticmethod
    def execute_command(command : str) -> None:
        '''Execute a command'''
        result = os.system(command)
        logging.info('Command %s result: %d', command, result)
        print(f'Command {command} result: {result}')


    @staticmethod
    def write_object_data_to_file(recorder : 'BaseStorageRecorder') -> None:
        '''Write the object data to a file'''
        data_file_name, count = recorder.record_data_in_file(
            recorder.dir_data + recorder.file_data,
            recorder.data_dir,
            recorder.output_object_file,
        )
        recorder.object_data_load_string = recorder.build_load_string(
            collection=IndalekoDBCollections.Indaleko_Object_Collection,
            file=data_file_name
        )
        logging.info('Load string: %s', recorder.object_data_load_string)
        print('Load string: ', recorder.object_data_load_string)
        if hasattr(recorder, 'output_count'): # should be there
            recorder.output_count += count

    @staticmethod
    def write_edge_data_to_file(recorder : 'BaseStorageRecorder') -> int:
        '''Write the edge data to a file'''
        data_file_name, count = recorder.record_data_in_file(
            recorder.dir_edges,
            recorder.data_dir,
            recorder.output_edge_file
        )
        recorder.relationship_data_load_string = recorder.build_load_string(
            collection=IndalekoDBCollections.Indaleko_Relationship_Collection,
            file=data_file_name
        )
        logging.info('Load string: %s', recorder.relationship_data_load_string)
        print('Load string: ', recorder.relationship_data_load_string)
        if hasattr(recorder, 'edge_count'):
            recorder.edge_count += count

    @staticmethod
    def record_data_in_file(
            data : list,
            dir_name : Union[Path, str],
            preferred_file_name : Union[Path, str, None] = None) -> tuple[str,int]:
        '''
        Record the specified data in a file.

        Inputs:
            - data: The data to record
            - preferred_file_name: The preferred file name (if any)

        Returns:
            - The name of the file where the data was recorded
            - The number of entries that were written to the file

        Notes:
            A temporary file is always created to hold the data, and then it is renamed to the
            preferred file name if it is provided.
        '''
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tf:
            temp_file_name = tf.name
        count = BaseStorageRecorder.write_data_to_file(data, temp_file_name)
        if preferred_file_name is None:
            return temp_file_name, count
        # try to rename the file
        try:
            if os.path.exists(preferred_file_name):
                os.remove(preferred_file_name)
            os.rename(temp_file_name, preferred_file_name)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.error(
                'Unable to rename temp file %s to output file %s',
                temp_file_name,
                preferred_file_name
            )
            print(f'Unable to rename temp file {temp_file_name} to output file {preferred_file_name}')
            print(f'Error: {e}')
            preferred_file_name=temp_file_name
        return preferred_file_name, count

    def get_object_path(self : 'BaseStorageRecorder', obj : IndalekoObject):
        '''Given an Indaleko object, return a valid local path to the object'''
        return obj['Path'] # default is no change

    def is_object_directory(self : 'BaseStorageRecorder', obj: IndalekoObject) -> bool:
        '''Return True if the object is a directory'''
        return 'S_IFDIR' in obj.args['PosixFileAttributes'] or \
               'FILE_ATTRIBUTE_DIRECTORY' in getattr(obj.args, 'WindowsFileAttributes', '')

    def normalize(self) -> None:
        '''Normalize the data from the collector'''
        self.load_collector_data_from_file()
        for item in self.collector_data:
            try:
                obj = self.normalize_collector_data(item)
            except OSError as e:
                logging.error('Error normalizing data: %s', e)
                logging.error('Data: %s', item)
                self.error_count += 1
                continue
            if self.is_object_directory(obj):
                if 'Path' not in obj.indaleko_object.Record.Attributes:
                    logging.warning('Directory object does not have a path: %s', obj.serialize())
                    continue # skip
                self.dir_data_by_path[self.get_object_path(obj)] = obj
                self.dir_data.append(obj)
                self.dir_count += 1
            else:
                self.file_data.append(obj)
                self.file_count += 1

    def record(self) -> None:
        '''
        This function processes and records the collector file and emits the data needed to
        upload to the database.
        '''
        self.normalize()
        assert len(self.dir_data) + len(self.file_data) > 0, 'No data to record'
        self.build_dirmap()
        self.build_edges()
        kwargs={
            'platform' : self.platform,
            'service' : self.recorder_data.RecorderServiceName,
            'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
            'timestamp' : self.timestamp,
            'output_dir' : self.data_dir,
        }
        if hasattr(self, 'machine_id') and self.machine_id is not None:
            kwargs['machine'] = str(uuid.UUID(self.machine_id).hex)
        if hasattr(self, 'storage_description') and self.storage_description:
            kwargs['storage'] = self.storage_description
        self.output_object_file = self.generate_output_file_name(**kwargs)
        kwargs['collection'] = IndalekoDBCollections.Indaleko_Relationship_Collection
        self.output_edge_file = self.generate_output_file_name(**kwargs)


def main():
    """Test code for IndalekoStorageRecorder.py"""
    # Now parse the arguments
    recorder = BaseStorageRecorder(
        recorder_data = IndalekoStorageRecorderDataModel(
            RecorderServiceName = BaseStorageRecorder.indaleko_generic_storage_recorder_service_name,
            RecorderServiceUUID = BaseStorageRecorder.indaleko_generic_storage_recorder_uuid,
            RecorderServiceVersion = BaseStorageRecorder.indaleko_generic_storage_recorder_service_version,
            RecorderServiceDescription = BaseStorageRecorder.indaleko_generic_storage_recorder_service_description,
        ),
        service_name=BaseStorageRecorder.indaleko_generic_storage_recorder_service_name,
        service_id=BaseStorageRecorder.indaleko_generic_storage_recorder_uuid_str,
        test=True
    )
    assert recorder is not None, "Could not create recorder."
    fname = recorder.generate_file_name()
    print(fname)
    metadata = recorder.extract_metadata_from_recorder_file_name(fname)
    print(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    main()
