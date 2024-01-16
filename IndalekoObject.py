from IndalekoRecord import IndalekoRecord
import msgpack
import argparse
import os
import uuid
import json

from IndalekoObjectSchema import IndalekoObjectSchema

class IndalekoObject(IndalekoRecord):
    '''
    This defines the information that makes up an Indaleko Object (the
    things we store in the index)
    '''
    Schema = IndalekoObjectSchema.get_schema()

    '''UUIDs we associate with specific timestamps that we capture'''
    CREATION_TIMESTAMP = '6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6'
    MODIFICATION_TIMESTAMP = '434f7ac1-f71a-4cea-a830-e2ea9a47db5a'
    ACCESS_TIMESTAMP = '581b5332-4d37-49c7-892a-854824f5d66f'
    CHANGE_TIMESTAMP = '3bdc4130-774f-4e99-914e-0bec9ee47aab'

    def __init__(self, source:dict, raw_data:bytes, **kwargs):
        # the only _required_ field is the source
        assert isinstance(source, dict), 'source must be a dict'
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
        super().__init__(raw_data = msgpack.packb(raw_data),
                         attributes = attributes,
                         source = {
                             'Identifier' : source['Identifier'],
                              'Version' : source['Version']
                         })

    def to_dict(self):
        obj = {}
        obj['Record'] = super().to_dict()
        obj['_key'] = self.args['ObjectIdentifier']
        for key, value in self.args.items():
            obj[key] = value
        return obj


def main():
    """Test code for the IndalekoObject class."""
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
        'File': 'ms',
        'Path': 'D:\\dist',
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
    print(json.dumps(obj.to_dict(), indent=4))
    if IndalekoObjectSchema.is_valid_object(obj.to_dict()):
        print('Object is valid.')

if __name__ == "__main__":
    main()
