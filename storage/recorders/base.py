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

import datetime
import logging
import json
import jsonlines
import os
import uuid
import sys

from typing import Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.service_manager import IndalekoServiceManager
from utils.misc.directory_management import indaleko_default_data_dir, indaleko_default_config_dir, indaleko_default_log_dir
from utils.misc.file_name_management import generate_file_name, extract_keys_from_file_name
from data_models import IndalekoSemanticAttributeDataModel
from storage.i_relationship import IndalekoRelationship
# pylint: enable=wrong-import-position
class BaseStorageRecorder():
    '''
    IndalekoStorageRecorder is the generic class that we use for recording data from the
    various collectors that we have. Platform specific recorders are built on top
    of this class to handle platform-specific recording.
    '''

    default_file_prefix = 'indaleko'
    default_file_suffix = '.jsonl'

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



    def __init__(self : 'BaseStorageRecorder', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoStorageRecorder class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the recorder.
        '''
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
        self.data_dir = kwargs.get('data_dir', indaleko_default_data_dir)
        self.output_dir = kwargs.get('output_dir', self.data_dir)
        self.input_dir = kwargs.get('input_dir', self.data_dir)
        self.config_dir = kwargs.get('config_dir', indaleko_default_config_dir)
        self.log_dir = kwargs.get('log_dir', indaleko_default_log_dir)
        self.service_name = kwargs.get('Name', kwargs.get('service_name', None))
        assert self.service_name is not None, \
            f'Service name must be specified, kwargs={kwargs}'
        self.service_description = kwargs.get('Description',
                                              BaseStorageRecorder\
                                                .indaleko_generic_storage_recorder_service_description)
        self.service_version = kwargs.get('Version',
                                          BaseStorageRecorder\
                                            .indaleko_generic_storage_recorder_service_version)
        self.service_type = kwargs.get('Type', IndalekoServiceManager.service_type_storage_recorder)
        self.service_id = kwargs.get('Identifier', kwargs.get('service_id', kwargs.get('service_identifier', None)))
        assert self.service_id is not None, \
            f'Service identifier must be specified\n{kwargs}'
        self.recorder_service = IndalekoServiceManager().register_service(
            service_name = self.service_name,
            service_description = self.service_description,
            service_version = self.service_version,
            service_type = self.service_type,
            service_id = self.service_id,
        )
        assert self.recorder_service is not None, 'Recorder service does not exist'
        for count in BaseStorageRecorder.counter_values:
            setattr(self, count, 0)

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
        kwargs['recorder'] = self.recorder
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
        'service' : 'record',
        'recorder' : self.recorder,
        'machine' : str(uuid.UUID(self.machine_id).hex),
        'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
        'timestamp' : self.timestamp,
        'output_dir' : target_dir,
        }
        if self.storage_description is not None:
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
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
                        writer.write(entry.serialize())
                        self.output_count += 1
                    except TypeError as err:
                        logging.error('Error writing entry to JSONLines file: %s', err)
                        logging.error('Entry: %s', entry)
                        raise err
            logging.info('Wrote JSONLines data to %s', file_name)
            ic('Wrote JSON data to', file_name)
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

def main():
    """Test code for IndalekoStorageRecorder.py"""
    # Now parse the arguments
    recorder = BaseStorageRecorder(
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
