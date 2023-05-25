import os
import json
import uuid
import stat
from arango import ArangoClient

class FileSystemObject:

    ObjectCount = 0
    RelationshipCount = 0

    def __init__(self, path, root=False):
        self.root = root
        self.uuid = str(uuid.uuid4())
        self.url = path
        self.stat_info = os.stat(path)
        self.size = self.stat_info.st_size
        self.timestamps = {
            'created': self.stat_info.st_ctime,
            'modified': self.stat_info.st_mtime,
            'accessed': self.stat_info.st_atime
        }
        self.attributes = os.stat_result(self.stat_info).st_file_attributes
        db['DataObjects'].insert(self.__dict__)
        FileSystemObject.ObjectCount += 1


    def add_contain_relationship(self, db, child_obj):
        assert stat.S_ISDIR(self.stat_info.st_mode), 'Should only add contain relationships from directories'
        db['contains'].insert({'_from': self.uuid, '_to': child_obj.uuid})
        db['contained_by'].insert({'_from': child_obj.uuid, '_to': self.uuid})
        FileSystemObject.RelationshipCount += 2


    def to_json(self):
        return json.dumps(self.__dict__)

def process_directory(db, path, root_obj=None):
    LastCount = 0
    if None is root_obj:
        root_obj = FileSystemObject(path, True)
    for root, dirs, files in os.walk(path):
        if LastCount + 5000 < FileSystemObject.ObjectCount:
            print('Object Count now ', FileSystemObject.ObjectCount)
            LastCount = FileSystemObject.ObjectCount
        for name in files:
            file_path = os.path.join(root, name)
            file_obj = FileSystemObject(file_path)
            root_obj.add_contain_relationship(db, file_obj)
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                dir_obj = FileSystemObject(dir_path)
            except FileNotFoundError:
                # transient file
                continue
            root_obj.add_contain_relationship(db, dir_obj)

def process_file(path, db):
    stat_info = os.stat(path)
    size = stat_info.st_size
    timestamps = {
        'created': stat_info.st_ctime,
        'modified': stat_info.st_mtime,
        'accessed': stat_info.st_atime
    }
    attributes = os.stat_result(stat_info).st_file_attributes
    file_obj = FileSystemObject(path)
    db['DataObjects'].insert(file_obj.__dict__)
    return file_obj

# ArangoDB connection settings
arango_url = "http://localhost:8529"
arango_username = "tony"
arango_password = None
arango_db_name = 'Indaleko'

# Initialize the ArangoDB client
client = ArangoClient()

# Connect to the database
db = client.db(arango_db_name, username=arango_username,
                password=arango_password, auth_method='basic')

# Replace 'volume_path' with the path of the Windows volume you want to scan
volume_path='C:\\'
process_directory(db, volume_path)

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
