import argparse
from datetime import datetime, timezone
from icecream import ic
import logging
import os
import json
import jsonlines
import uuid


import IndalekoLogging
from Indaleko import Indaleko
from IndalekoICloudIndexer import IndalekoICloudIndexer
from IndalekoIngester import IndalekoIngester
from IndalekoObject import IndalekoObject
from IndalekoRelationshipContains import IndalekoRelationshipContains
from IndalekoRelationshipContained import IndalekoRelationshipContainedBy


class IndalekoICloudIngester(IndalekoIngester):
    '''
    This class handles ingestion of metadata from the Indaleko iCloud indexer.
    '''

    icloud_ingester_uuid = 'c2b887b3-2a2f-4fbf-83dd-062743f31477'
    icloud_ingester_service = {
        'service_name' : 'iCloud Ingester',
        'service_description' : 'This service ingests captured index info from iCloud.',
        'service_version' : '1.0',
        'service_type' : 'Ingester',
        'service_id' : icloud_ingester_uuid,
    }

    icloud_platform = IndalekoICloudIndexer.icloud_platform
    icloud_ingester = 'icloud_ingester'

    def __init__(self, **kwargs) -> None:
        if 'input_file' not in kwargs:
            raise ValueError('input_file must be specified')
        if 'timestamp' not in kwargs:
            raise ValueError('timestamp must be specified')
        if 'platform' not in kwargs:
            raise ValueError('platform must be specified')
        for key, value in self.icloud_ingester_service.items():
            if key not in kwargs:
                kwargs[key] = value
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'user_id' not in kwargs:
            raise ValueError('user_id must be specified')
        self.user_id = kwargs['user_id']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
        else:
            self.output_file = kwargs['output_file']
        self.indexer_data = []
        self.source = {
            'Identifier' : self.icloud_ingester_uuid,
            'Version' : '1.0',
        }

    def load_indexer_data_from_file(self) -> None:
        '''This function loads the indexer data from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.indexer_data.append(entry)
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.indexer_data = json.load(file)
        else:
            raise ValueError(f'Input file {self.input_file} is an unknown type')
        if not isinstance(self.indexer_data, list):
            raise ValueError('indexer_data is not a list')


    def normalize_index_data(self, data: dict) -> IndalekoObject:
        '''
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        '''
        if data is None:
            raise ValueError('Data cannot be None')
        if not isinstance(data, dict):
            raise ValueError('Data must be a dictionary')
        if 'ObjectIdentifier' not in data:
            raise ValueError('Data must contain an ObjectIdentifier')
        if 'user_id' not in data:
            data['user_id'] = self.user_id

        timestamps = []
        if 'date_created' in data:
            timestamps.append(
                {
                    'Label' : IndalekoObject.CREATION_TIMESTAMP,
                    'Value' : datetime.fromisoformat(data['date_created']).isoformat(),
                    'Description' : 'Date Created',
                }
            )
        if 'last_opened' in data:
            if isinstance(data['last_opened'], str):
                data['last_opened'] = datetime.fromisoformat(data['last_opened'])
            timestamps.append({
                'Label' : IndalekoObject.ACCESS_TIMESTAMP,
                'Value' : data['last_opened'].isoformat(),
                'Description' : 'Last Opened',
            })
        if 'date_changed' in data:
            if isinstance(data['date_changed'], str):
                data['date_changed'] = datetime.fromisoformat(data['date_changed'])
            timestamps.append({
                'Label' : IndalekoObject.ACCESS_TIMESTAMP,
                'Value' : data['date_changed'].isoformat(),
                'Description' : 'Changed',
            })

        # Ensure all datetime objects are converted to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        # Save debug information to a file
        debug_file_path = 'debug_data.jsonl'
        with open(debug_file_path, 'a') as debug_file:
            debug_file.write(json.dumps(data, indent=4, default=str) + '\n')

        try:
            raw_data = Indaleko.encode_binary_data(bytes(json.dumps(data).encode('utf-8')))
        except TypeError as e:
            with open(debug_file_path, 'a') as debug_file:
                debug_file.write("Failed to serialize the following data entry:\n")
                debug_file.write(json.dumps(data, indent=4, default=str) + '\n')
            raise e

        kwargs = {
            'source': self.source,
            'raw_data': raw_data,
            'URI': 'https://www.icloud.com/' + data['path_display'],
            'Path': data['path_display'],
            'ObjectIdentifier': data['ObjectIdentifier'],
            'Timestamps': timestamps,
            'Size': data.get('size', 0),
            'Attributes': data,
        }

        return IndalekoObject(**kwargs)

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
        'user_id' : self.user_id,
        'service' : 'ingest',
        'ingester' : self.ingester,
        'collection' : Indaleko.Indaleko_Object_Collection,
        'timestamp' : self.timestamp,
        'output_dir' : target_dir,
        }
        if self.storage_description is not None:
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
        return self.generate_output_file_name(**kwargs)

    def ingest(self) -> None:
        '''
        This method ingests the metadata from the iCloud indexer file and
        writes it to a JSONL file.
        '''
        self.load_indexer_data_from_file()
        dir_data_by_path = {}
        dir_data = []
        file_data = []

        # Create the icloud_root_dir object
        icloud_root_dir_obj = self.normalize_index_data(IndalekoICloudIndexer.icloud_root_folder)
        # Append icloud_root_dir object to file_data
        file_data.append(icloud_root_dir_obj)

        # Ensure root directory is in the dirmap
        dirmap = {'root': icloud_root_dir_obj.args['ObjectIdentifier']}

        # Now go into the Drive and create objects of every item
        for item in self.indexer_data:
            obj = self.normalize_index_data(item)
            assert 'Path' in obj.args
            path = obj.args['Path']

            if 'type' in item and item['type'] == 'folder':
                if path == "root/some_folder":
                    # Ignore the folder item with path "root/some_folder"
                    continue
                if 'path_display' not in item:
                    logging.warning('Directory object does not have a path: %s', item)
                    continue  # skip
                dir_data_by_path[item['path_display']] = obj
                dir_data.append(obj)
                self.dir_count += 1
            else:
                file_data.append(obj)
                self.file_count += 1

        for item in dir_data:
            dirmap[item.args['Path']] = item.args['ObjectIdentifier']

        dir_edges = []
        source = {
            'Identifier': self.icloud_ingester_uuid,
            'Version': '1.0',
        }

        # Add relationships for files in the root directory to the icloud_root_folder
        root_path = "root/"
        root_object_id = icloud_root_dir_obj.args['ObjectIdentifier']

        for item in file_data:
            path = item.args['Path']
            # Check if the file is directly under the root directory
            if path.startswith(root_path) and path.count('/') == 1:
                file_object_id = item.args['ObjectIdentifier']
                assert file_object_id != root_object_id, "Relationship built can not be self referential"

                dir_edge = IndalekoRelationshipContains(
                    relationship=IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                    object1={'collection': Indaleko.Indaleko_Object_Collection, 'object': file_object_id},
                    object2={'collection': Indaleko.Indaleko_Object_Collection, 'object': root_object_id},
                    source=source
                )
                dir_edges.append(dir_edge)
                self.edge_count += 1

                dir_edge = IndalekoRelationshipContainedBy(
                    relationship=IndalekoRelationshipContainedBy.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR,
                    object1={'collection': Indaleko.Indaleko_Object_Collection, 'object': root_object_id},
                    object2={'collection': Indaleko.Indaleko_Object_Collection, 'object': file_object_id},
                    source=source
                )
                dir_edges.append(dir_edge)
                self.edge_count += 1

        for item in dir_data:
            path = item.args['Path']
            # Skip the root folder itself
            if path == 'root':
                continue
            if 'Path' not in item.args:
                logging.warning('Path not found in item: %s', item.args)
                continue  # skip items without a path
            parent = os.path.dirname(path)
            if parent not in dirmap:
                logging.warning('Parent directory not found: %s', parent)
                continue  # skip if parent directory is unknown

            parent_id = dirmap[parent]
            object_id = item.args['ObjectIdentifier']

            # Ensure that object1 is not the same as object2 for folders
            assert object_id != parent_id, "Folder relationship built can not be self referential"

            dir_edge = IndalekoRelationshipContains(
                relationship=IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                object1={'collection': Indaleko.Indaleko_Object_Collection, 'object': object_id},
                object2={'collection': Indaleko.Indaleko_Object_Collection, 'object': parent_id},
                source=source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1

            dir_edge = IndalekoRelationshipContainedBy(
                relationship=IndalekoRelationshipContainedBy.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR,
                object1={'collection': Indaleko.Indaleko_Object_Collection, 'object': parent_id},
                object2={'collection': Indaleko.Indaleko_Object_Collection, 'object': object_id},
                source=source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1

        self.write_data_to_file(dir_data + file_data, self.output_file)
        load_string = self.build_load_string(collection=Indaleko.Indaleko_Object_Collection, file=self.output_file)
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)

        edge_file = self.generate_output_file_name(
            platform=self.platform,
            service='ingest',
            collection=Indaleko.Indaleko_Relationship_Collection,
            timestamp=self.timestamp,
            output_dir=self.data_dir,
        )
        self.write_data_to_file(dir_edges, edge_file)
        load_string = self.build_load_string(collection=Indaleko.Indaleko_Relationship_Collection, file=edge_file)
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        return

def main():
    '''This is the main handler for the iCloud ingester.'''
    logging_levels = Indaleko.get_logging_levels()
    timestamp = datetime.now(timezone.utc).isoformat()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--logdir', '-l',
                            help='Path to the log directory',
                            default=Indaleko.default_log_dir)
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
    pre_parser.add_argument('--datadir',
                            help='Path to the data directory',
                            default=Indaleko.default_data_dir,
                            type=str)
    pre_args , _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging.IndalekoLogging(
        platform=IndalekoICloudIngester.icloud_platform,
        service_name ='ingester',
        log_dir = pre_args.logdir,
        log_level = pre_args.loglevel,
        timestamp = timestamp,
        suffix = 'log'
    )


    indexer = IndalekoICloudIndexer()
    indexer_files = indexer.find_indexer_files(pre_args.datadir)

    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='iCloud index data file to ingest')
    args=parser.parse_args()
    input_metadata = IndalekoICloudIndexer.extract_metadata_from_indexer_file_name(args.input)

    input_timestamp = timestamp
    if 'timestamp' in input_metadata:
        input_timestamp = input_metadata['timestamp']
    input_platform = IndalekoICloudIngester.icloud_platform
    if 'platform' in input_metadata:
        input_platform = input_metadata['platform']
    if input_platform != IndalekoICloudIngester.icloud_platform:
        ic(f'Input platform {input_platform} does not match expected platform {IndalekoICloudIngester.icloud_platform}')
    file_prefix = IndalekoIngester.default_file_prefix
    if 'file_prefix' in input_metadata:
        file_prefix = input_metadata['file_prefix']
    file_suffix = IndalekoIngester.default_file_suffix
    if 'file_suffix' in input_metadata:
        file_suffix = input_metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    ingester = IndalekoICloudIngester(
        timestamp=input_timestamp,
        platform=input_platform,
        ingester=IndalekoICloudIngester.icloud_ingester,
        file_prefix=file_prefix,
        file_suffix=file_suffix,
        data_dir=args.datadir,
        input_file=input_file,
        log_dir=args.logdir,
        user_id=input_metadata['user_id']
    )
    output_file = ingester.generate_file_name()
    logging.info('Indaleko iCloud Ingester started.')
    logging.info(f'Input file: {input_file}')
    logging.info(f'Output file: {output_file}')
    logging.info(args)
    ingester.ingest()
    total=0
    for count_type, count_value in ingester.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        total += count_value
    logging.info('Total: %d', total)
    logging.info('Indaleko iCloud Ingester completed.')


if __name__ == '__main__':
    main()
