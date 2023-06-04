import os
import json
import uuid
import stat
from arango import ArangoClient
import arango
import argparse
import datetime


class IndalekoDB:

    def __init__(self, hostname='localhost', port=8529, username='root', password = None, database='Indaleko'):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = None
        self.database = database
        self.client = None
        self.db = None

    def set_hostname(self, hostname : str):
        self.hostname = hostname
        return self

    def set_port(self, port : int):
        assert port > 1023 and port < 65536, 'Invalid port number specified'
        self.port = port
        return self

    def set_username(self, username: str):
        self.username = username
        return self

    def set_password(self, password: str):
        self.password = password
        return self

    def set_database(self, database: str):
        self.database = database
        return self

    def connect(self):
        if self.client is None:
            url = 'http://{}:{}'.format(self.hostname, self.port)
            self.client = ArangoClient(hosts=url)
            assert self.client is not None
        if self.db is None:
            self.db = self.client.db(self.database, self.username, self.password, auth_method='basic')



class IndaelkoSchema:

    def __init__(self):
        pass

class IndalekoIndex:
    def __init__(self, collection: 'IndalekoCollection', index_type: str, fields: list, unique=False):
        self.collection = collection
        self.fields = fields
        self.unique = unique
        self.index_type = index_type
        assert index_type == 'persistent', 'Only support persistent indices'
        self.index = self.collection.add_persistent_index(fields=self.fields, unique=self.unique)

    def find_entries(self, **kwargs):
        return [document for document in self.collection.find(kwargs)]


class IndalekoCollection:

    def __init__(self, db, name: str, edge: bool = False, reset: bool = False) -> None:
        self.db = db
        self.name = name
        if reset and db.has_collection(name):
            db.delete_collection(name)
        if not db.has_collection(name):
            db.create_collection(name, edge=edge)
        self.collection = db.collection(self.name)
        self.indices = {}

    def create_index(self, name: str, index_type: str, fields: list, unique: bool) -> 'IndalekoCollection':
        self.indices[name] = IndalekoIndex(self.collection, index_type, fields, unique)
        return self

    def find_entries(self, **kwargs):
        return [document for document in self.collection.find(kwargs)]

    def insert(self, document: dict) -> 'IndalekoCollection':
        return self.collection.insert(document)


class ContainerRelationship:

    ContainsRelationshipSchema = {
        '_from_field' : {
            'type' : 'string',
            'rule' : {'type', 'uuid'}
        },
        '_to_field' : {
            'type' : 'string',
            'rule' : {'type', 'uuid'}
        }
    }

    def __init__(self, db, start, end, collection):
        self._from = start
        self._to = end
        db[collection].insert(self._dict_)

    def to_json(self):
        return json.dumps(self.__dict__)


class ContainedByRelationship:
    def __init__(self):
        pass

class FileSystemObject:

    ObjectCount = 0
    RelationshipCount = 0

    DataObjectSchema = {
        'url_field': {
            'type': 'string',
            'rule': {'type': 'url'}
        },
        'uuid_field': {
            'type': 'string',
            'rule': {'type': 'uuid'}
        },
        # Define other fields in the schema
    }

    def __init__(self, collection: IndalekoCollection, path : str, root=False):
        self.root = root
        self.uuid = str(uuid.uuid4())
        self.url = 'file:///' + path
        self.stat_info = os.stat(path)
        self.size = self.stat_info.st_size
        self.timestamps = {
            'created': datetime.datetime.fromtimestamp(self.stat_info.st_ctime).isoformat(),
            'modified': datetime.datetime.fromtimestamp(self.stat_info.st_mtime).isoformat(),
            'accessed': datetime.datetime.fromtimestamp(self.stat_info.st_atime).isoformat(),
        }
        self.collection = collection
        '''Note: this is much faster than catching the exception and then doing
        the lookup, at least in the case where there are a lot of collisions.'''
        #if len(documents) > 0:
        #    self.dbinfo = documents[0]
        #else:
        #    self.dbinfo = collection.insert(self.to_dict())
        try:
            self.dbinfo = collection.insert(self.to_dict())
        except arango.exceptions.DocumentInsertError as e:
            documents = collection.find_entries(dev=self.stat_info.st_dev,
                                            inode=self.stat_info.st_ino)
            if len(documents) > 0:
                self.dbinfo = documents[0]
            else:
                print('Exception {} on file {}'.format(e, path))
                documents = collection.find_entries(url=self.url)
                if len(documents) > 0:
                    self.dbinfo = documents[0]
                else:
                    raise e
        FileSystemObject.ObjectCount += 1


    def add_contain_relationship(self, collections: dict, child_obj: 'FileSystemObject') -> 'FileSystemObject':
        assert stat.S_ISDIR(self.stat_info.st_mode), 'Should only add contain relationships from directories'
        parent_id = self.dbinfo['_id']
        child_id = child_obj.dbinfo['_id']
        collections['contains'].insert(json.dumps({'_from': parent_id, '_to': child_id, 'uuid1' : self.uuid, 'uuid2' : child_obj.uuid}))
        collections['contained_by'].insert(json.dumps({'_from': child_id, '_to': parent_id, 'uuid1' : child_obj.uuid, 'uuid2' : self.uuid}))
        FileSystemObject.RelationshipCount += 2
        return self

    def windows_attributes_to_data(self):
        attributes = self.stat_info.st_file_attributes
        data = {}
        prefix = 'FILE_ATTRIBUTE_'
        for attr in dir(stat):
            if attr.startswith(prefix):
                element_name = attr[len(prefix):]
                if attributes & getattr(stat, attr):
                    data[element_name] = True
                else:
                    data[element_name] = False
        return data

    def posix_attributes_to_data(self):
        attributes = self.stat_info.st_mode
        data = {}
        prefix = 'S_IS'
        for attr in dir(stat):
            if attr.startswith(prefix) and callable(getattr(stat,attr)):
                element_name = attr[len(prefix):]
                if getattr(stat,attr)(attributes):
                    data[element_name] = True
                else:
                    data[element_name] = False
        return data

    def to_dict(self):
        data = {
            'url': self.url,
            'timestamps': {
                'created': datetime.datetime.fromtimestamp(self.stat_info.st_ctime).isoformat(),
                'modified': datetime.datetime.fromtimestamp(self.stat_info.st_mtime).isoformat(),
                'accessed': datetime.datetime.fromtimestamp(self.stat_info.st_atime).isoformat(),
            },
            'size': self.size,
            'mode': self.stat_info.st_mode,
            'posix attributes' : self.posix_attributes_to_data(),
            'dev' : self.stat_info.st_dev,
            'inode' : self.stat_info.st_ino
        }
        if hasattr(self.stat_info, 'st_file_attributes'):
            # windows only
            data['Windows Attributes'] = self.windows_attributes_to_data()
        return json.dumps(data)

    def cloud_file_detector():
        '''
        import os
        import ctypes
        from ctypes import windll, wintypes, byref, POINTER, Structure

        # Define necessary constants and structures
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        FSCTL_GET_REPARSE_POINT = 0x900a8
        IO_REPARSE_TAG_CLOUD = 0x9000001
        IO_REPARSE_TAG_CLOUD_1 = 0x9000101
        IO_REPARSE_TAG_CLOUD_2 = 0x9000201
        IO_REPARSE_TAG_CLOUD_3 = 0x9000301
        IO_REPARSE_TAG_CLOUD_4 = 0x9000401
        IO_REPARSE_TAG_CLOUD_5 = 0x9000501
        IO_REPARSE_TAG_CLOUD_6 = 0x9000601
        IO_REPARSE_TAG_CLOUD_7 = 0x9000701
        IO_REPARSE_TAG_CLOUD_8 = 0x9000801
        IO_REPARSE_TAG_CLOUD_9 = 0x9000901
        IO_REPARSE_TAG_CLOUD_A = 0x9000A01
        IO_REPARSE_TAG_CLOUD_B = 0x9000B01
        IO_REPARSE_TAG_CLOUD_C = 0x9000C01
        IO_REPARSE_TAG_CLOUD_D = 0x9000D01
        IO_REPARSE_TAG_CLOUD_E = 0x9000E01
        IO_REPARSE_TAG_CLOUD_MASK = 0x0000F000
        MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16384
        INVALID_HANDLE_VALUE = -1

        class REPARSE_DATA_BUFFER(Structure):
            _fields_ = [
                ("ReparseTag", wintypes.DWORD),
                ("ReparseDataLength", wintypes.WORD),
                ("Reserved", wintypes.WORD),
                ("SubstituteNameOffset", wintypes.USHORT),
                ("SubstituteNameLength", wintypes.USHORT),
                ("PrintNameOffset", wintypes.USHORT),
                ("PrintNameLength", wintypes.USHORT),
                ("Flags", wintypes.ULONG),
                ("PathBuffer", wintypes.WCHAR * (MAXIMUM_REPARSE_DATA_BUFFER_SIZE//2))
            ]

            def is_cloud(self):
                return (self.ReparseTag & IO_REPARSE_TAG_CLOUD_MASK) == IO_REPARSE_TAG_CLOUD

        def is_cloud_file(path):
            file_attribute = windll.kernel32.GetFileAttributesW(path)
            if file_attribute == INVALID_HANDLE_VALUE or not file_attribute & FILE_ATTRIBUTE_REPARSE_POINT:
                return False

            hFile = windll.kernel32.CreateFileW(path, 0, 0, None, 3, FILE_ATTRIBUTE_REPARSE_POINT, None)
            if hFile == INVALID_HANDLE_VALUE:
                raise ctypes.WinError()

            buffer = REPARSE_DATA_BUFFER()
            bytesReturned = wintypes.DWORD()
            result = windll.kernel32.DeviceIoControl(hFile, FSCTL_GET_REPARSE_POINT, None, 0,
                                                    byref(buffer), ctypes.sizeof(buffer),
                                                    byref(bytesReturned), None)

            windll.kernel32.CloseHandle(hFile)
            if not result:
                raise ctypes.WinError()
            return buffer.is_cloud()

        # test
        file_path
    '''


Indaleko_Collections = {
        'DataObjects': {
            'schema' : FileSystemObject.DataObjectSchema,
            'edge' : False,
            'indices' : {
                'url' : {
                    'fields' : ['url'],
                    'unique' : True,
                    'type' : 'persistent'
                },
                'file identity' : {
                    'fields' : ['dev', 'inode'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            },
        },
        'contains' : {
            'schema' : ContainerRelationship.ContainsRelationshipSchema,
            'edge' : True,
            'indices' : {
                'container' : {
                    'fields' : ['uuid1', 'uuid2'],
                    'unique' : True,
                    'type' : 'persistent',
                }
            }
        },
        'contained_by' : {
            'schema' : ContainerRelationship.ContainsRelationshipSchema,
            'edge' : True,
            'indices' : {
                'contained_by' : {
                    'fields' : ['uuid1', 'uuid2'],
                    'unique' : True,
                    'type' : 'persistent',
                },
            },
        },
    }

def process_directory(collections: dict, path: str, root_obj=None) -> int:
    LastCount = 0
    count = 0
    if None is root_obj:
        root_obj = FileSystemObject(collections['DataObjects'], path, True)
    for root, dirs, files in os.walk(path):
        count = FileSystemObject.ObjectCount
        if LastCount + 5000 < FileSystemObject.ObjectCount:
            print('Object Count now ', FileSystemObject.ObjectCount)
            LastCount = FileSystemObject.ObjectCount
        for name in files:
            file_path = os.path.join(root, name)
            try:
                file_obj = FileSystemObject(
                    collections['DataObjects'], file_path)
            except FileNotFoundError:
                # transient file
                continue
            except Exception as e:
                # not sure what triggers this.
                print('Processing File {}, exception {}\n**Ignored**'.format(file_path, e))
                continue
            root_obj.add_contain_relationship(collections, file_obj)
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                dir_obj = FileSystemObject(
                    collections['DataObjects'], dir_path)
            except FileNotFoundError:
                # transient file
                continue
            except Exception as e:
                # not sure what triggers this.
                print(
                    'Processing File {}, exception {}\n**Ignored**'.format(file_path, e))
                continue
            root_obj.add_contain_relationship(collections, dir_obj)
    return count


def setup_collections(db, collection_names, reset=False) -> dict:
    collections = {}
    for name in collection_names:
        assert name not in collections, 'Duplicate collection name'
        edge = False
        if 'edge' in collection_names[name]:
            assert type(collection_names[name]['edge']) is bool
            edge = collection_names[name]['edge']
        edge = False
        collections[name] = IndalekoCollection(db, name, edge, reset)
        if 'indices' in collection_names[name]:
            for index in collection_names[name]['indices']:
                e = collection_names[name]['indices'][index]
                assert e['type'] == 'persistent', 'Only support persistent'
                collections[name].create_index(index, e['type'], e['fields'], e['unique'])
    return collections

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-host', type=str, default='localhost', help='URL to use for ArangoDB')
    parser.add_argument('-port', type=int, default=8529, help='port number to use')
    parser.add_argument('-user', type=str, default='tony', help='user name')
    parser.add_argument('-password', type=str, required=True, help='user password')
    parser.add_argument('-database', type=str, default='Indaleko', help='Name of the database to use')
    parser.add_argument('-path', type=str, default='C:\\', help='the path where indexing should start')
    parser.add_argument('-reset', action='store_true', default=False, help='Clean database before running')
    args = parser.parse_args()
    assert args.port > 1023 and args.port < 65536, 'Invalid port number'

    print(args)

    # ArangoDB connection settings
    arango_url = 'http://{}:{}'.format(args.host, args.port)
    arango_username = args.user
    arango_password = args.password
    arango_db_name = args.database

    # Initialize the ArangoDB client
    client = ArangoClient(hosts=arango_url)

    # Connect to the database
    db = client.db(arango_db_name, username=arango_username,
                password=arango_password, auth_method='basic')

    collections = setup_collections(db, Indaleko_Collections, args.reset)

    start = datetime.datetime.utcnow()
    # Replace 'volume_path' with the path of the Windows volume you want to scan
    count = process_directory(collections, args.path)
    end = datetime.datetime.utcnow()
    execution_time = end - start
    if count > 0:
        print('Added {} in {} time ({} seconds per entry)'.format(count, execution_time, execution_time.total_seconds() / count))

if __name__ == "__main__":
    main()
