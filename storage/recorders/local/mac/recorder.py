'''
This module handles recording metadata collected from the Mac local file system.

Indaleko Mac Local Storage Metadata Collector
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
import argparse
import datetime
import json
import logging
import os
import platform
import subprocess
import sys
import uuid

import jsonlines

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoDBCollections, IndalekoDBConfig, IndalekoServiceManager
from data_models import IndalekoSourceIdentifierDataModel
from platforms.mac.machine_config import IndalekoMacOSMachineConfig
from platforms.unix import UnixFileAttributes
from storage import IndalekoObject
from storage.recorders.base import BaseStorageRecorder
from storage.collectors.local.mac.collector import IndalekoMacLocalCollector
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
from utils.misc.file_name_management import indaleko_file_name_prefix
from utils.misc.data_management import encode_binary_data
from utils import IndalekoLogging
# pylint: enable=wrong-import-position

class IndalekoMacLocalStorageRecorder(BaseStorageRecorder):
    '''
    This class handles the processing of metadata from the Indaleko Mac local storage recorder service.
    '''

    mac_local_recorder_uuid = '07670255-1e82-4079-ad6f-f2bb39f44f8f'
    mac_local_recorder_service = {
        'service_name' : 'Mac Local Storage Recorder',
        'service_description' : 'This service records metadata collected from local filesystems of a Mac machine.',
        'service_version' : '1.0',
        'service_type' : IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier' : mac_local_recorder_uuid,
    }

    mac_platform = IndalekoMacLocalCollector.mac_platform
    mac_local_recorder = 'mac_local_recorder'

    def __init__(self, reset_collection=False, objects_file="", relations_file="", **kwargs) -> None:
        self.db_config = IndalekoDBConfig()
        if 'input_file' not in kwargs:
            raise ValueError('input_file must be specified')
        if 'machine_config' not in kwargs:
            raise ValueError('machine_config must be specified')
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        else:
            kwargs['machine_id'] = self.machine_config.machine_id
            if kwargs['machine_id'] != self.machine_config.machine_id:
                logging.warning('Warning: machine ID of collector file ' +
                                f'({kwargs["machine"]}) does not match machine ID of recorder ' +
                                f'({self.machine_config.machine_id}.)')
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.datetime.now(
                datetime.timezone.utc).isoformat()
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoMacLocalStorageRecorder.mac_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = IndalekoMacLocalStorageRecorder.mac_local_recorder
        if 'input_file' not in kwargs:
            kwargs['input_file'] = None
        for key, value in self.mac_local_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'Identifier' not in kwargs and 'service_id' not in kwargs:
            kwargs['Identifier'] = self.mac_local_recorder_uuid
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
            assert 'unknown' not in self.output_file, f'Output file should not have unknown in its name {self.output_file}'
        else:
            self.output_file = kwargs['output_file']
        self.collector_data = []
        self.source = {
            'Identifier': self.mac_local_recorder_uuid,
            'Version': '1.0'
        }
        self.docker_upload = kwargs.get('docker_upload', False)
        if not isinstance(self.docker_upload, bool):
            self.docker_upload = False
        self.reset_collection = reset_collection
        self.objects_file = objects_file
        self.relations_file = relations_file

    def find_recorder_files(self) -> list:
        '''This function finds the files to process:
            search_dir: path to the search directory
            prefix: prefix of the file to process
            suffix: suffix of the file to process (default is .json)
        '''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        return [x for x in super().find_collector_files(self.data_dir)
                if IndalekoMacLocalCollector.mac_platform in x and
                IndalekoMacLocalCollector.mac_local_collector_name in x]

    def load_collector_data_from_file(self: 'IndalekoMacLocalStorageRecorder') -> None:
        '''This function loads the collector metadata from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.collector_data.append(entry)
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.collector_data = json.load(file)
        else:
            raise ValueError(
                f'Input file {self.input_file} is of an unknown type')
        if not isinstance(self.collector_data, list):
            raise ValueError('collector_data is not a list')

    def normalize_collector_data(self, data: dict) -> IndalekoObject:
        '''
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        '''
        if data is None:
            raise ValueError('Data cannot be None')
        if not isinstance(data, dict):
            raise ValueError('Data must be a dictionary')
        if 'ObjectIdentifier' in data:
            oid = data['ObjectIdentifier']
        else:
            oid = str(uuid.uuid4())
        kwargs = {
            'source': self.source,
            'raw_data': encode_binary_data(bytes(json.dumps(data).encode('utf-8'))),
            'URI': data['URI'],
            'ObjectIdentifier': oid,
            'Timestamps': [
                {
                    'Label': IndalekoObject.CREATION_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_birthtime'],
                                                             datetime.timezone.utc).isoformat(),
                    'Description': 'Created',
                },
                {
                    'Label': IndalekoObject.MODIFICATION_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_mtime'],
                                                             datetime.timezone.utc).isoformat(),
                    'Description': 'Modified',
                },
                {
                    'Label': IndalekoObject.ACCESS_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_atime'],
                                                             datetime.timezone.utc).isoformat(),
                    'Description': 'Accessed',
                },
                {
                    'Label': IndalekoObject.CHANGE_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_ctime'],
                                                             datetime.timezone.utc).isoformat(),
                    'Description': 'Changed',
                },
            ],
            'Size': data['st_size'],
            'Attributes': data,
            'Machine': self.machine_config.machine_id,
        }

        if 'st_mode' in data:
            kwargs['UnixFileAttributes'] = UnixFileAttributes.map_file_attributes(
                data['st_mode'])

        return IndalekoObject(**kwargs)

    def record(self) -> None:
        '''
        This function processes the mac local storage collector metadata file
        and emits the data needed to upload to the database.
        '''

        # if the Objects and Relationships are provided, use them
        if len(self.objects_file) and len(self.relations_file):
            print(f'provided two paths for objects and relationships')
            assert os.path.isfile(self.objects_file), f'given objects file does not exist, got={
                self.objects_file}'
            assert os.path.isfile(self.relations_file), f'given objects file does not exits, got={
                self.relations_file}'

            print(f'importing objects and relations from:', f'Objects={
                  self.objects_file}', f'Relationships={self.relations_file}', sep='\n')
            self.arangoimport()
            return

        self.load_collector_data_from_file()
        dir_data_by_path = {}
        dir_data = []
        file_data = []
        # Step 1: build the normalized data
        for item in self.collector_data:
            try:
                obj = self.normalize_collector_data(item)
            except OSError as e:
                logging.error('Error normalizing data: %s', e)
                logging.error('Data: %s', item)
                self.error_count += 1
                continue
            if 'S_IFDIR' in obj.args['UnixFileAttributes']:
                if 'Path' not in obj:
                    logging.warning(
                        'Directory object does not have a path: %s', obj.to_json())
                    continue  # skip
                dir_data_by_path[obj['Path']] = obj
                dir_data.append(obj)
                self.dir_count += 1
            else:
                file_data.append(obj)
                self.file_count += 1
        # Step 2: build a table of paths to directory uuids
        dirmap = {}
        for item in dir_data:
            fqp = os.path.join(item['Path'], item['Name'])
            identifier = item.args['ObjectIdentifier']
            dirmap[fqp] = identifier
        # now, let's build a list of the edges, using our map.
        dir_edges = []
        source = {
            'Identifier': self.mac_local_recorder_uuid,
            'Version': '1.0',
        }
        source_id = IndalekoSourceIdentifierDataModel(**source)
        for item in dir_data + file_data:
            parent = item['Path']
            if parent not in dirmap:
                continue
            parent_id = dirmap[parent]
        for item in dir_data + file_data:
            parent = item['Path']
            if parent not in dirmap:
                continue
            parent_id = dirmap[parent]
            dir_edges.append(BaseStorageRecorder.build_dir_contains_relationship(
                parent_id, item.args['ObjectIdentifier'], source_id)
            )
            self.edge_count += 1
            dir_edges.append(BaseStorageRecorder.build_contained_by_dir_relationship(
                item.args['ObjectIdentifier'], parent_id, source_id)
            )
            self.edge_count += 1
            volume = item.args.get('Volume')
            if volume:
                dir_edges.append(BaseStorageRecorder.build_volume_contains_relationship(
                    volume, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                dir_edges.append(BaseStorageRecorder.build_contained_by_volume_relationship(
                    item.args['ObjectIdentifier'], volume, source_id)
                )
                self.edge_count += 1
            machine_id = item.args.get('machine_id')
            if machine_id:
                dir_edges.append(BaseStorageRecorder.build_machine_contains_relationship(
                    machine_id, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                dir_edges.append(BaseStorageRecorder.build_contained_by_machine_relationship(
                    item.args['ObjectIdentifier'], machine_id, source_id)
                )
                self.edge_count += 1
        # Save the data to the recorder output file
        self.write_data_to_file(dir_data + file_data, self.output_file)
        edge_file = self.generate_output_file_name(
            machine=self.machine_id,
            platform=self.platform,
            service='recorder',
            collection=IndalekoDBCollections.Indaleko_Relationship_Collection,
            timestamp=self.timestamp,
            output_dir=self.data_dir,
        )
        self.write_data_to_file(dir_edges, edge_file)

        # set the objects and relations file paths to these newly created ones
        self.objects_file = self.output_file
        self.relations_file = edge_file

        # import these using arangoimport tool
        if self.docker_upload:
            self.arangoimport()


    def arangoimport(self):
        print('{:-^20}'.format(""))
        print('using arangoimport to import objects')

        # check if the docker is up
        self.__run_docker_cmd('docker ps')

        # read the config file
        config = self.db_config.config

        dest = '/home'  # where in the container we copy the files; we use this for import to the database
        container_name = config['database']['container']
        server_username = config['database']['user_name']
        server_password = config['database']['user_password']
        server_database = config['database']['database']
        overwrite = str(self.reset_collection).lower()

        # copy the files first
        for filename, dest_filename in [
            (self.objects_file, "objects.jsonl"),
            (self.relations_file, "relations.jsonl")
        ]:
            self.__run_docker_cmd(f'docker cp {filename} {
                                  container_name}:{dest}/{dest_filename}')

        # run arangoimport on both of these files
        for filename, collection_name in [
            ("objects.jsonl", "Objects"),
            ("relations.jsonl", "Relationships")]:
            self.__run_docker_cmd(f'docker exec -t {container_name} arangoimport --file {dest}/{filename} --type "jsonl" --collection "{collection_name}" --server.username "{
                                  server_username}" --server.password "{server_password}" --server.database "{server_database}" --overwrite {overwrite}')

    def __run_docker_cmd(self, cmd):
        print('Running:', cmd)
        try:
            subprocess.run(cmd, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f'failed to run the command, got: {e}')


def main():
    '''
    This is the main handler for the Indaleko Mac Local Storage Recorder service.
    '''
    logging_levels = IndalekoLogging.get_logging_levels()

    # step 1: find the machine configuration file
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir', '-c',
                            help=f'Path to the config directory (default is {
                                indaleko_default_config_dir})',
                            default=indaleko_default_config_dir)
    pre_args, _ = pre_parser.parse_known_args()
    config_files = IndalekoMacOSMachineConfig.find_config_files(
        pre_args.configdir)
    assert isinstance(config_files, list), 'config_files must be a list'
    if len(config_files) == 0:
        print(f'No config files found in {pre_args.configdir}, exiting.')
        return
    default_config_file = IndalekoMacOSMachineConfig.get_most_recent_config_file(
        pre_args.configdir)
    pre_parser = argparse.ArgumentParser(add_help=False, parents=[pre_parser])
    pre_parser.add_argument('--config',
                            choices=config_files,
                            default=default_config_file,
                            help=f'Configuration file to use. (default: {default_config_file})')
    pre_parser.add_argument('--datadir',
                            help=f'Path to the data directory (default is {
                                indaleko_default_data_dir})',
                            type=str,
                            default=indaleko_default_data_dir)
    pre_args, _ = pre_parser.parse_known_args()
    machine_config = IndalekoMacOSMachineConfig.load_config_from_file(
        config_file=default_config_file)
    collector = IndalekoMacLocalCollector(
        search_dir=pre_args.datadir,
        prefix=IndalekoMacLocalCollector.mac_platform,
        suffix=IndalekoMacLocalCollector.mac_local_collector_name,
        machine_config=machine_config
    )
    collector_files = collector.find_collector_files(pre_args.datadir)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=collector_files,
                        default=collector_files[0],
                        help='Mac Local Storage Collector file to process.')
    parser.add_argument('--objects-file',
                        default="",
                        dest='objects_file',
                        help='path to the jsonl file that contains the documents for the Objects collection'
                        )
    parser.add_argument('--relations-file',
                        default="",
                        dest='relations_file',
                        help='path to the jsonl file that contains the documents for the Relationships collection'
                        )
    parser.add_argument('--reset', action='store_true',
                        help='Drop the collections before ingesting new data')
    parser.add_argument('--logdir',
                        help=f'Path to the log directory (default is {
                            indaleko_default_log_dir})',
                        default=indaleko_default_log_dir)
    parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    parser.add_argument('--docker_upload',
                        '-du',
                        default=False,
                        action='store_true',
                        help='copy into local docker container with arangodb for bulk uploading')
    args = parser.parse_args()
    metadata = IndalekoMacLocalCollector.extract_metadata_from_collector_file_name(
        args.input)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    machine_id = 'unknown'
    if 'machine' in metadata:
        if metadata['machine'] != machine_config.machine_id:
            print('Warning: machine ID of collector file ' +
                  f'({metadata["machine"]}) does not match machine ID of recorder ' +
                  f'({machine_config.machine_id})')
        machine_id = metadata['machine']
    if 'timestamp' in metadata:
        timestamp = metadata['timestamp']
    if 'platform' in metadata:
        collector_platform = metadata['platform']
        if collector_platform != IndalekoMacLocalStorageRecorder.mac_platform:
            print('Warning: platform of collector file ' +
                  f'({collector_platform}) name does not match platform of recorder ' +
                  f'({IndalekoMacLocalStorageRecorder.mac_platform}.)')
    storage = 'unknown'
    if 'storage' in metadata:
        storage = metadata['storage']
    file_prefix = indaleko_file_name_prefix
    if 'file_prefix' in metadata:
        file_prefix = metadata['file_prefix']
    file_suffix = BaseStorageRecorder.default_file_suffix
    if 'file_suffix' in metadata:
        file_suffix = metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    collector = IndalekoMacLocalStorageRecorder(
        reset_collection=args.reset,
        objects_file=args.objects_file,
        relations_file=args.relations_file,
        machine_config=machine_config,
        machine_id=machine_id,
        timestamp=timestamp,
        platform=IndalekoMacLocalCollector.mac_platform,
        collector=IndalekoMacLocalStorageRecorder.mac_local_recorder,
        storage_description=storage,
        file_prefix=file_prefix,
        file_suffix=file_suffix,
        data_dir=args.datadir,
        input_file=input_file,
        log_dir=args.logdir,
        docker_upload=args.docker_upload,
    )
    output_file = collector.generate_file_name()
    log_file_name = collector.generate_file_name(
        target_dir=args.logdir, suffix='.log')
    print(f"logging into {log_file_name}")
    logging.basicConfig(filename=os.path.join(log_file_name),
                        level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        force=True)
    logging.info('Found these collected metadata files: %s', collector_files)
    logging.info('Input file %s ', input_file)
    logging.info('Output file %s ', output_file)
    collector.record()
    counts = collector.get_counts()
    for count_type, count_value in counts.items():
        logging.info('%s: %d', count_type, count_value)
    logging.info('Done')


if __name__ == '__main__':
    main()
