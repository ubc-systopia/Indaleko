import os
import json
import uuid
from arango import ArangoClient
import argparse
import datetime
from windows_local_index import IndalekoWindowsMachineConfig
from IndalekoCollections import *
from dbsetup import IndalekoDBConfig
from indaleko import *
import msgpack
import base64
from IndalekoServices import IndalekoServices
import jsonlines
import logging

class WindowsLocalIngest():

    WindowsMachineConfig_UUID = '3360a328-a6e9-41d7-8168-45518f85d73e'

    WindowsMachineConfigService = {
        'name': 'WindowsMachineConfig',
        'description': 'This service provides the configuration information for a Windows machine.',
        'version': '1.0',
        'identifier': WindowsMachineConfig_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Indexer',
    }

    WindowsLocalIndexer_UUID = '31315f6b-add4-4352-a1d5-f826d7d2a47c'

    WindowsLocalIndexerService = {
        'name': 'WindowsLocalIndexer',
        'description': 'This service indexes the local filesystems of a Windows machine.',
        'version': '1.0',
        'identifier': WindowsLocalIndexer_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Indexer',
    }

    WindowsLocalIngester_UUID = '429f1f3c-7a21-463f-b7aa-cd731bb202b1'

    WindowsLocalIngesterService = {
        'name': WindowsLocalIngester_UUID,
        'description': 'This service ingests captured index info from the local filesystems of a Windows machine.',
        'version': '1.0',
        'identifier': WindowsLocalIngester_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Ingester',
    }

    def register_service(self, service: dict) -> 'IndalekoServices':
        assert service is not None, 'Service cannot be None'
        assert 'name' in service, 'Service must have a name'
        assert 'description' in service, 'Service must have a description'
        assert 'version' in service, 'Service must have a version'
        assert 'identifier' in service, 'Service must have an identifier'
        return self.indaleko_services.register_service(service['name'], service['description'], service['version'], service['type'], service['identifier'])

    def lookup_service(self, name: str) -> dict:
        assert name is not None, 'Service name cannot be None'
        info = self.indaleko_services.lookup_service(name)
        return info

    def __init__(self, data_dir: str = './data', reset: bool = False) -> None:
        # Register our services
        self.indaleko_services = IndalekoServices(reset=reset)
        if len(self.lookup_service(self.WindowsMachineConfigService['name'])) == 0:
            self.register_service(self.WindowsMachineConfigService)
        if len(self.lookup_service(self.WindowsLocalIndexerService['name'])) == 0:
            self.register_service(self.WindowsLocalIndexerService)
        if len(self.lookup_service(self.WindowsLocalIngesterService['name'])) == 0:
            self.register_service(self.WindowsLocalIngesterService)
        self.sources = (
            self.WindowsMachineConfigService['name'],
            self.WindowsLocalIndexerService['name'],
            self.WindowsLocalIngesterService['name'],
        )
        self.collections = IndalekoCollections()
        self.set_data_dir(data_dir)


    def get_source(self, source_name: str) -> IndalekoSource:
        assert source_name is not None, 'Source name cannot be None'
        assert source_name in self.sources, f'Source name {source_name} is not valid.'
        source = self.lookup_service(source_name)[0]
        return IndalekoSource(uuid.UUID(source['identifier']), source['version'], source['description'])

    def add_record_to_collection(self, collection_name: str, record: dict) -> None:
        entries = self.collections.get_collection(collection_name).find_entries(_key=record['_key'])
        if len(entries) < 1:
            self.collections.get_collection(collection_name).insert(record)
            print(f'Inserted {record} into {collection_name}')

    def __find_data_files__(self: 'WindowsLocalIngest') -> None:
        self.data_files = [x for x in os.listdir(self.data_dir) if x.startswith('windows-local-fs-data') and x.endswith('.json')]
        return

    def set_data_dir(self : 'WindowsLocalIngest', data_dir : str) -> None:
        self.data_dir = data_dir
        self.__find_data_files__()
        return

    def set_data_file(self: 'WindowsLocalIngest', data_file: str) -> None:
        self.data_file = os.path.join(self.data_dir, data_file)
        self.data = {}
        with open(self.data_file, 'rt', encoding ='utf-8-sig') as fd:
            self.data = json.load(fd)
        return

    def load_data(self) -> None:
        self.__find_data_files__()
        for file in self.data_files:
            self.load_data_file(file)
        return

def find_data_files(dir: str ='./data'):
    return [x for x in os.listdir(dir) if x.startswith('windows-local-fs-data') and x.endswith('.json')]

def find_config_files(dir: str ='./config'):
    return [x for x in os.listdir(dir) if x.startswith('windows-hardware-info') and x.endswith('.json')]

class WindowsFileAttributes:

    FILE_ATTRIBUTES = {
        'FILE_ATTRIBUTE_READONLY' : 0x00000001,
        'FILE_ATTRIBUTE_HIDDEN' : 0x00000002,
        'FILE_ATTRIBUTE_SYSTEM' : 0x00000004,
        'FILE_ATTRIBUTE_DIRECTORY' : 0x00000010,
        'FILE_ATTRIBUTE_ARCHIVE' : 0x00000020,
        'FILE_ATTRIBUTE_DEVICE' : 0x00000040,
        'FILE_ATTRIBUTE_NORMAL' : 0x00000080,
        'FILE_ATTRIBUTE_TEMPORARY' : 0x00000100,
        'FILE_ATTRIBUTE_SPARSE_FILE' : 0x00000200,
        'FILE_ATTRIBUTE_REPARSE_POINT' : 0x00000400,
        'FILE_ATTRIBUTE_COMPRESSED' : 0x00000800,
        'FILE_ATTRIBUTE_OFFLINE' : 0x00001000,
        'FILE_ATTRIBUTE_NOT_CONTENT_INDEXED' : 0x00002000,
        'FILE_ATTRIBUTE_ENCRYPTED' : 0x00004000,
        'FILE_ATTRIBUTE_INTEGRITY_STREAM' : 0x00008000,
        'FILE_ATTRIBUTE_VIRTUAL' : 0x00010000,
        'FILE_ATTRIBUTE_NO_SCRUB_DATA' : 0x00020000,
        'FILE_ATTRIBUTE_EA' : 0x00040000,
        'FILE_ATTRIBUTE_PINNED' : 0x00080000,
        'FILE_ATTRIBUTE_UNPINNED' : 0x00100000,
        'FILE_ATTRIBUTE_RECALL_ON_OPEN' : 0x00040000,
        'FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS' : 0x00400000,
        'FILE_ATTRIBUTE_STRICTLY_SEQUENTIAL' : 0x20000000,
        'FILE_ATTRIBUTE_OPEN_REPARSE_POINT' : 0x00200000,
        'FILE_ATTRIBUTE_OPEN_NO_RECALL' : 0x00100000,
        'FILE_ATTRIBUTE_FIRST_PIPE_INSTANCE' : 0x00080000,
    }

    @staticmethod
    def map_file_attributes(attributes : int):
        fattrs = []
        if (0 == attributes):
            fattrs = ['FILE_ATTRIBUTE_NORMAL']
        for attr in WindowsFileAttributes.FILE_ATTRIBUTES:
            if attributes & WindowsFileAttributes.FILE_ATTRIBUTES[attr] == WindowsFileAttributes.FILE_ATTRIBUTES[attr]:
                fattrs.append(attr)
        return ' | '.join(fattrs)

def normalize_index_data(data: dict, cfg : IndalekoWindowsMachineConfig) -> dict:
    '''
    Given some metadata, this will create a record that can be inserted into the
    Object collection.
    '''
    assert cfg is not None, 'cfg cannot be None'
    assert data is not None, 'Data cannot be None'
    assert type(data) is dict, 'Data must be a dictionary'
    oid = str(uuid.uuid4())
    object = {
        '_key' : oid,
        'Label' : data['file'],
        'Path' : data['path'],
        'URI' : data['URI'],
        'ObjectIdentifier' : oid,
        'LocalIdentifier' : str(data['st_ino']),
        'Timestamps' : [
            {
                'Label' : IndalekoObject.CREATION_TIMESTAMP,
                'Value' : datetime.datetime.fromtimestamp(data['st_birthtime'], datetime.timezone.utc).isoformat(),
                'Description' : 'Created'
            },
        ],
        'Size' : data['st_size'],
        'FileId' : str(data['st_ino']),
        # these are the data fields for the "record" format
        'RawData' : base64.b64encode(msgpack.packb(data)).decode('ascii'),
        'Attributes' : data, # at least for now, I just keep all of the original data as attributes.
        'source' : {
           'identifier' : WindowsLocalIngest.WindowsLocalIngesterService['identifier'],
           'version' : WindowsLocalIngest.WindowsLocalIngesterService['version'],
        },
        'Machine' : cfg.get_config_data()['MachineGuid'],
        # TODO: there are likely other things of interest here, such as the
        # containing device (volume).
    }
    if 'st_mode' in data:
        object['UnixFileAttributes'] = UnixFileAttributes.map_file_attributes(data['st_mode'])
    if 'st_file_attributes' in data:
        object['WindowsFileAttributes'] = WindowsFileAttributes.map_file_attributes(data['st_file_attributes'])
    if data['URI'].startswith('\\\\?\\Volume{'):
        object['Volume'] = data['URI'][11:47]
    return object


def main():
    data_files = find_data_files()
    assert len(data_files) > 0, 'At least one data file should exist'
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--datadir', '-d', help='Path to the data directory', default='./data')
    pre_parser.add_argument('--configdir', '-c', help='Path to the config directory', default='./config')
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.datadir != './data':
        data_files = find_data_files(pre_args.datadir)
    default_data_file = data_files[-1] # TODO: date/time sort this.
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input', choices=data_files, default=default_data_file, help='Windows Local Indexer file to ingest.')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    args = parser.parse_args()
    ingester = WindowsLocalIngest(data_dir=args.datadir, reset=args.reset)
    machine_config = IndalekoWindowsMachineConfig(args.configdir)
    cfg = machine_config.get_config_data()
    config_data = base64.b64encode(msgpack.packb(cfg))
    # config_record = IndalekoRecord(msgpack.packb(cfg), cfg, ingester.get_source(ingester.WindowsMachineConfigService['name']).get_source_identifier())
    config_info = {
        'platform' : {
            'software' : {
                'OS' : cfg['OperatingSystem']['Caption'],
                'Architecture' : cfg['OperatingSystem']['OSArchitecture'],
                'Version' : cfg['OperatingSystem']['Version']
            },
            'hardware' : {
                'CPU' : cfg['CPU']['Name'],
                'Version' : cfg['CPU']['Name'],
                'Cores' : cfg['CPU']['Cores'],
            },
        },
        'source' : WindowsLocalIngest.WindowsMachineConfigService['identifier'],
        'version' : WindowsLocalIngest.WindowsMachineConfigService['version'],
        'captured' : {
            'Label' : 'Timestamp',
            'Value' : datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        'Attributes' : cfg,
        'Data' : config_data.decode('ascii'),
        '_key' : cfg['MachineGuid']
    }
    # looks ready to save to the database
    ingester.add_record_to_collection('MachineConfig', config_info)
    volinfo = machine_config.get_volume_info()
    # Note: I'm saving this information in the configuration database, but it is
    # distinctly possible that we need a different spot for it.  TBD
    for vol in volinfo:
        vol_record = {
            'volume' : volinfo[vol].get_vol_guid(),
            'source' : IndalekoWindowsMachineConfig.WindowsDriveInfo.WindowsDriveInfo_UUID_str,
            'version' : IndalekoWindowsMachineConfig.WindowsDriveInfo.WindowsDriveInfo_Version,
            'captured' : {
                'Label' : 'Timestamp',
                'Value' : datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            'Attributes' : volinfo[vol].get_attributes(),
            'Data' : volinfo[vol].get_raw_data(),
            'Machine' : cfg['MachineGuid'], # TODO - should we have a relationship?
            '_key' : volinfo[vol].get_vol_guid(),
        }
        ingester.add_record_to_collection('MachineConfig', vol_record)
    logging.debug(f'Start processing {args.input}')
    ingester.set_data_file(args.input)
    logging.debug(f'Finish processing {args.input}')
    print(len(ingester.data))
    ## Now we have data that we can parse, isn't this exciting?
    dir_data_by_path = {}
    dir_data = []
    file_data = []
    for item in ingester.data:
        item = normalize_index_data(item, machine_config)
        if 'S_IFDIR' in item['UnixFileAttributes'] or \
            'FILE_ATTRIBUTE_DIRECTORY' in item['WindowsFileAttributes']:
            if 'Path' not in item:
                print(item)
            dir_data_by_path[os.path.join(item['Path'],item['Label'] )] = item
            dir_data.append(item)
        else:
            file_data.append(item)
    for item in dir_data:
        assert 'Container' not in item, 'directories should not have multiple links'
        if item['Path'] in dir_data_by_path:
            item['Container'] = [dir_data_by_path[item['Path']]['ObjectIdentifier']]
    for item in file_data:
        assert not 'S_IFDIR' in item['UnixFileAttributes'], 'directories should not be in file_data'
        assert not 'FILE_ATTRIBUTE_DIRECTORY' in item['WindowsFileAttributes'], 'directories should not be in file_data'
        if item['Path'] in dir_data_by_path:
            if 'Container' not in item:
                item['Container'] = []
            assert type(item['Container']) is list, f'{item['Container']} must be a list'
            item['Container'].append(dir_data_by_path[item['Path']]['ObjectIdentifier'])
    # Next I need to capture some relationships that will go into edge
    # collection(s).
    contained_by_relationship_uuid = '3d4b772d-b4b0-4203-a410-ecac5dc6dafa'
    containing_relationship_uuid = 'cde81295-f171-45be-8607-8100f4611430'
    machine_relationship_uuid = 'f3dde8a2-cff5-41b9-bd00-0f41330895e1'
    volume_relationship_uuid = 'db1a48c0-91d9-4f16-bd65-845433e6cba9'
    source_relationship_uuid = 'c7c72ead-7705-4421-8bb4-2d6bd9502f58'
    contained_by_edges = []
    containing_edges = []
    machine_edges = []
    volume_edges = []
    source_edges = []
    for item in dir_data + file_data:
        if 'Container' not in item:
            print(f'Skipping item {item['ObjectIdentifier']} because it has no container')
            continue
        for c in item['Container']:
            edge = {
                '_from' : 'Objects/' + item['ObjectIdentifier'],
                '_to' : 'Objects/' + c,
                'object1' : item['ObjectIdentifier'],
                'object2' : c,
                'relationship' : contained_by_relationship_uuid
            }
            contained_by_edges.append(edge)
            edge = {
                '_from' : 'Objects/' + c,
                '_to' : 'Objects/' + item['ObjectIdentifier'],
                'object1' : c,
                'object2' : item['ObjectIdentifier'],
                'relationship' : containing_relationship_uuid
            }
            containing_edges.append(edge)
            edge = {
                '_from' : 'MachineConfig/' + cfg['MachineGuid'],
                '_to' : 'Objects/' + item['ObjectIdentifier'],
                'relationship' : machine_relationship_uuid,
                'object1' : cfg['MachineGuid'],
                'object2' : item['ObjectIdentifier'],
            }
            machine_edges.append(edge)
            edge = {
                '_from' : 'MachineConfig/' + item['Volume'],
                '_to' : 'Objects/' + item['ObjectIdentifier'],
                'object1' : item['Volume'],
                'object2' : item['ObjectIdentifier'],
                'relationship' : volume_relationship_uuid
            }
            volume_edges.append(edge)
            edge = {
                '_from' : 'Services/' + WindowsLocalIngest.WindowsLocalIngesterService['identifier'],
                '_to' : 'Objects/' + item['ObjectIdentifier'],
                'object1' : WindowsLocalIngest.WindowsLocalIngesterService['identifier'],
                'object2' : item['ObjectIdentifier'],
                'relationship' : source_relationship_uuid
            }
            source_edges.append(edge)

    # This is some ragged code at this point, but it demonstrates
    # how to ingest the data and put it into a format that will allow bulk
    # uploading into ArangoDB, which is the **entire point** of this extra
    # activity - after all, I had already done the work of capturing the data
    # and sticking it into Arango previously.  It was just quite slow.
    print(f'Number of directories: {len(dir_data)}')
    print(f'Number of files: {len(file_data)}')
    print(f'Number of contained_by edges: {len(contained_by_edges)}')
    print(f'Number of containing edges: {len(containing_edges)}')
    print(f'Number of machine edges: {len(machine_edges)}')
    print(f'Number of volume edges: {len(volume_edges)}')
    print(f'Number of source edges: {len(source_edges)}')

    with jsonlines.open('./data/dir_data.jsonl', mode='w') as fd:
        for item in dir_data:
            fd.write(item)
    with jsonlines.open('./data/file_data.jsonl', mode='w') as fd:
        for item in file_data:
            fd.write(item)
    with jsonlines.open('./data/contained_by_edges.jsonl', mode='w') as fd:
        for item in contained_by_edges:
            fd.write(item)
    with jsonlines.open('./data/containing_edges.jsonl', mode='w') as fd:
        for item in containing_edges:
            fd.write(item)
    with jsonlines.open('./data/machine_edges.jsonl', mode='w') as fd:
        for item in machine_edges:
            fd.write(item)
    with jsonlines.open('./data/volume_edges.jsonl', mode='w') as fd:
        for item in volume_edges:
            fd.write(item)
    with jsonlines.open('./data/source_edges.jsonl', mode='w') as fd:
        for item in source_edges:
            fd.write(item)

    with open('./data/dir_data.json', 'wt', encoding='utf-8') as fd:
        json.dump(dir_data, fd, indent=4)
    with open('./data/file_data.json', 'wt', encoding='utf-8') as fd:
        json.dump(file_data, fd, indent=4)
    with open('./data/contained_by_edges.json', 'wt', encoding='utf-8') as fd:
        json.dump(contained_by_edges, fd, indent=4)
    with open('./data/containing_edges.json', 'wt', encoding='utf-8') as fd:
        json.dump(containing_edges, fd, indent=4)
    with open('./data/machine_edges.json', 'wt', encoding='utf-8') as fd:
        json.dump(machine_edges, fd, indent=4)
    with open('./data/volume_edges.json', 'wt', encoding='utf-8') as fd:
        json.dump(volume_edges, fd, indent=4)
    with open('./data/source_edges.json', 'wt', encoding='utf-8') as fd:
        json.dump(source_edges, fd, indent=4)



if __name__ == "__main__":
    main()
