from IndalekoRecord import IndalekoRecord
import msgpack
import argparse
import os
import uuid

class IndalekoObject(IndalekoRecord):
    '''
    This defines the information that makes up an Indaleko Object (the
    things we store in the index)
    '''
    Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema#",
        "$id" : "https://activitycontext.work/schema/indaleko-object.json",
        "title": "Indaleko Object Schema",
        "description": "Schema for the JSON representation of an Indaleko Object, which is used for indexing storage content.",
        "type": "object",
        "rule" : {
            "type" : "object",
            "properties" : {
                "Label" : {
                    "type" : "string",
                    "description" : "The object label (like a file name)."
                },
                "URI" : {
                    "type" : "string",
                    "description" : "The URI of the object."
                },
                "ObjectIdentifier" : {
                    "type" : "string",
                    "description" : "The object identifier (UUID).",
                    "format" : "uuid",
                },
                "LocalIdentifier": {
                    "type" : "string",
                    "description" : "The local identifier used by the storage system to find this, such as a UUID or inode number."
                },
                "Timestamps" : {
                    "type" : "array",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" : "UUID representing the semantic meaning of this timestamp.",
                            "format": "uuid",
                        },
                        "Value" : {
                            "type" : "string",
                            "description" : "Timestamp in ISO date and time format.",
                            "format" : "date-time",
                        },
                        "Description" : {
                            "type" : "string",
                            "description" : "Description of the timestamp.",
                        },
                    },
                    "required" : [
                        "Label",
                        "Value"
                    ],
                    "description" : "List of timestamps with UUID-based semantic meanings associated with this object."
                },
                "Size" : {
                    "type" : "integer",
                    "description" : "Size of the object in bytes."
                },
                "RawData" : {
                    "type" : "string",
                    "description" : "Raw data captured for this object.",
                    "contentEncoding" : "base64",
                    "contentMediaType" : "application/octet-stream",
                },
                "SemanticAttributes" : {
                    "type" : "array",
                    "description" : "Semantic attributes associated with this object.",
                    "properties" : {
                        "UUID" : {
                            "type" : "string",
                            "description" : "The UUID for this attribute.",
                            "format" : "uuid",
                        },
                        "Data" : {
                            "type" : "string",
                            "description" : "The data associated with this attribute.",
                        },
                    },
                    "required" : [
                        "UUID",
                        "Data"
                    ]
                }
            },
            "required" : [
                "URI",
                "ObjectIdentifier",
                "Timestamps",
                "Size",
            ]
        }
    }

    '''UUIDs we associate with specific timestamps that we capture'''
    CREATION_TIMESTAMP = '6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6' # a/ka/ "birth time"
    MODIFICATION_TIMESTAMP = '434f7ac1-f71a-4cea-a830-e2ea9a47db5a' # last time data contents modified
    ACCESS_TIMESTAMP = '581b5332-4d37-49c7-892a-854824f5d66f' # last time file accessed (maybe)
    CHANGE_TIMESTAMP = '3bdc4130-774f-4e99-914e-0bec9ee47aab' # last time anything about the file changed

    def __init__(self, source:dict, raw_data:bytes, **kwargs):
        # the only _required_ field is the source
        assert type(source) is dict, 'source must be a dict'
        assert 'Identifier' in source, 'source must contain an Identifier field'
        assert 'Version' in source, 'source must contain a Version field'
        # there are four required object fields:
        assert 'URI' in kwargs, 'URI must be specified'
        assert 'ObjectIdentifier' in kwargs, 'ObjectIdentifier must be specified'
        assert 'Timestamps' in kwargs, 'Timestamps must be specified'
        assert 'Size' in kwargs, 'Size must be specified'
        args = {key : value for key, value in kwargs.items()}
        if 'Attributes' in args:
            attributes = args['Attributes']
            del args['Attributes']
        else:
            attributes = {}
        assert 'source' not in args, 'source is a separate parameter'
        assert '_key' not in args, '_key is a reserved parameter'
        assert 'Data' not in args, 'Data is a reserved parameter'
        self.args = args
        super().__init__(msgpack.packb(raw_data),
                         attributes,
                         {
                             'Identifier' : source['Identifier'],
                              'Version' : source['Version']
                         })

    def to_dict(self):
        obj = super().to_dict()
        obj['_key'] = self.args['ObjectIdentifier']
        for key, value in self.args.items():
            obj[key] = value
        return obj

'''
This is the format of an object as it should appear in the database.

{
        "_key": "ea8ebe41-461a-4481-b77f-b83f8f2ea7dd",
        "Label": "ms",
        "Path": "D:\\dist",
        "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\ms",
        "ObjectIdentifier": "ea8ebe41-461a-4481-b77f-b83f8f2ea7dd",
        "LocalIdentifier": "844424930132312",
        "Timestamps": [
            {
                "Label": "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6",
                "Value": "2022-01-09T17:49:00.665358+00:00",
                "Description": "Created"
            }
        ],
        "Size": 4096,
        "FileId": "844424930132312",
        "RawData": "3gAUqHN0X2F0aW1ly0HZZXOPjyLpq3N0X2F0aW1lX25zzxem8s6eIbZkrHN0X2JpcnRodGltZctB2HbIAyqVOK9zdF9iaXJ0aHRpbWVfbnPPFsiraxoqBSCoc3RfY3RpbWXLQdh2
yAMqlTirc3RfY3RpbWVfbnPPFsiraxoqBSCmc3RfZGV2zyZAgxRAguo/snN0X2ZpbGVfYXR0cmlidXRlcxCmc3RfZ2lkAKZzdF9pbm/PAAMAAAAAAVinc3RfbW9kZc1B/6hzdF9tdGltZctB2Lyx36/oJ6tz
dF9tdGltZV9uc88XCcgZydNN9KhzdF9ubGluawGuc3RfcmVwYXJzZV90YWcAp3N0X3NpemXNEACmc3RfdWlkAKRmaWxlom1zpHBhdGinRDpcZGlzdKNVUknZOFxcP1xWb2x1bWV7MzM5N2Q5N2ItMmNhNS0x
MWVkLWIyZmMtYjQwZWRlOWE1YTNjfVxkaXN0XG1z",
        "Attributes": {
            "st_atime": 1704316478.2365057,
            "st_atime_ns": 1704316478236505700,
            "st_birthtime": 1641750540.6653576,
            "st_birthtime_ns": 1641750540665357600,
            "st_ctime": 1641750540.6653576,
            "st_ctime_ns": 1641750540665357600,
            "st_dev": 2756347094955649599,
            "st_file_attributes": 16,
            "st_gid": 0,
            "st_ino": 844424930132312,
            "st_mode": 16895,
            "st_mtime": 1660077950.7485445,
            "st_mtime_ns": 1660077950748544500,
            "st_nlink": 1,
            "st_reparse_tag": 0,
            "st_size": 4096,
            "st_uid": 0,
            "file": "ms",
            "path": "D:\\dist",
            "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\ms"
        },
        "source": {
            "identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
            "version": "1.0"
        },
        "Machine": "2e169bb7-0024-4dc1-93dc-18b7d2d28190",
        "UnixFileAttributes": "S_IFDIR",
        "WindowsFileAttributes": "FILE_ATTRIBUTE_DIRECTORY",
        "Volume": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c"
    },
'''


def main():
    random_raw_data = msgpack.packb(os.urandom(64))
    source_uuid = str(uuid.uuid4())
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--source' , '-s', type=str, default=source_uuid, help='The source UUID of the data.')
    parser.add_argument('--raw-data', '-r', type=str, default=random_raw_data, help='The raw data to be stored.')
    args = parser.parse_args()
    fattrs = {
        'st_atime': 1704316478.2365057,
        'st_atime_ns': 1704316478236505700,
        'st_birthtime': 1641750540.6653576,
        'st_birthtime_ns': 1641750540665357600,
        'st_ctime': 1641750540.6653576,
        'st_ctime_ns': 1641750540665357600,
        'st_dev': 2756347094955649599,
        'st_file_attributes': 16,
        'st_gid': 0,
        'st_ino': 844424930132312,
        'st_mode': 16895,
        'st_mtime': 1660077950.7485445,
        'st_mtime_ns': 1660077950748544500,
        'st_nlink': 1,
        'st_reparse_tag': 0,
        'st_size': 4096,
        'st_uid': 0,
        'file': 'ms',
        'path': 'D:\\dist',
        'URI': '\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\ms'
    }
    objattrs = {
        "Label": "ms",
        "Path": "D:\\dist",
        "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\ms",
        "ObjectIdentifier": "ea8ebe41-461a-4481-b77f-b83f8f2ea7dd",
        "LocalIdentifier": "844424930132312",
        "Timestamps": [
            {
                "Label": "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6",
                "Value": "2022-01-09T17:49:00.665358+00:00",
                "Description": "Created"
            }
        ],
        "Size": 4096,
        "FileId": "844424930132312",
        "Machine": "2e169bb7-0024-4dc1-93dc-18b7d2d28190",
        "UnixFileAttributes": "S_IFDIR",
        "WindowsFileAttributes": "FILE_ATTRIBUTE_DIRECTORY",
        "Volume": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c"
    }
    objattrs['Attributes'] = fattrs
    obj = IndalekoObject({'Identifier' : args.source, 'Version' : '1.0'}, args.raw_data, **objattrs)
    print(obj)

if __name__ == "__main__":
    main()

