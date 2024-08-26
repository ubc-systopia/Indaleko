'''
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

'''
import argparse
import os
import uuid
import json
import datetime

from icecream import ic

from Indaleko import Indaleko
from IndalekoObjectDataSchema import IndalekoObjectDataSchema
from IndalekoObjectDataModel import IndalekoObjectDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel, IndalekoUUID

class IndalekoObject:
    '''
    An IndalekoObject represents a single object (file/directory) in the Indaleko system.
    '''
    Schema = IndalekoObjectDataSchema().get_json_schema()

    '''UUIDs we associate with specific timestamps that we capture'''
    CREATION_TIMESTAMP = '6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6'
    MODIFICATION_TIMESTAMP = '434f7ac1-f71a-4cea-a830-e2ea9a47db5a'
    ACCESS_TIMESTAMP = '581b5332-4d37-49c7-892a-854824f5d66f'
    CHANGE_TIMESTAMP = '3bdc4130-774f-4e99-914e-0bec9ee47aab'

    def __init__(self, **kwargs):
        '''Initialize the object.'''
        self.args = kwargs
        if 'Record' not in kwargs:
            self.legacy_constructor()
        else:
            self.indaleko_object = IndalekoObjectDataModel.IndalekoObject.deserialize(
                kwargs
            )

    def legacy_constructor(self):
        '''Create an object using the old format.'''
        kwargs = self.args
        record = IndalekoRecordDataModel.IndalekoRecord(
            Data=kwargs['raw_data'],
            Attributes=kwargs['Attributes'],
            SourceIdentifier=IndalekoDataModel.SourceIdentifier(
                Identifier=kwargs['source']['Identifier'],
                Version=kwargs['source']['Version'],
                Description=None
            ),
            Timestamp = kwargs.get('timestamp', datetime.datetime.now(datetime.UTC))
        )
        del kwargs['raw_data']
        del kwargs['Attributes']
        del kwargs['source']
        if 'timestamp' in kwargs:
            del kwargs['timestamp']
        assert 'Record' not in kwargs, 'Record is still in kwargs - new style constructor.'
        kwargs['Record'] = IndalekoRecordDataModel.IndalekoRecord.serialize(record)
        self.indaleko_object = IndalekoObjectDataModel.IndalekoObject.deserialize(kwargs)


    @staticmethod
    def deserialize(data: dict) -> 'IndalekoObject':
        '''Deserialize a dictionary to an object.'''
        return IndalekoObject(**data)

    def serialize(self) -> dict:
        '''Serialize the object to a dictionary.'''
        serialized_data = IndalekoObjectDataModel.IndalekoObject.serialize(self.indaleko_object)
        if isinstance(serialized_data, tuple):
            assert len(serialized_data) == 1, 'Serialized data is a multi-entry tuple.'
            serialized_data = serialized_data[0]
        if isinstance(serialized_data, dict):
            serialized_data['_key'] = self.args['ObjectIdentifier']
        return serialized_data

    def to_dict(self):
        '''Return a dictionary representation of this object.'''
        return self.serialize()

    @staticmethod
    def create_indaleko_object(**kwargs) -> 'IndalekoObject':
        '''Create an Indaleko Object from an old style description.'''
        raise NotImplementedError('This method is not implemented.')

    def __getitem__(self, key):
        '''Get an item from the object.'''
        return self.indaleko_object.Record.Attributes[key]

    def __contains__(self, key):
        '''Check if an item is in the object.'''
        return key in self.indaleko_object.Record.Attributes

def main():
    """Test code for the IndalekoObject class."""
    random_raw_data = Indaleko.encode_binary_data(os.urandom(64))
    source_uuid = str(uuid.uuid4())
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--source' , '-s', type=str, default=source_uuid, help='The source UUID of the data.')
    parser.add_argument('--raw-data', '-r', type=str, default=random_raw_data, help='The raw data to be stored.')
    args = parser.parse_args()
    data_object = {
        "Record": {
            "Data": "xQL6xQL3eyJzdF9hdGltZSI6IDE2OTMyMjM0NTYuMzMzNDI4MSwgInN0X2F0aW1lX25zIjogMTY5MzIyMzQ1NjMzMzQyODEwMCwgInN0X2JpcnRodGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2JpcnRodGltZV9ucyI6IDE2ODU4OTEyMjE1NTkxOTE3MDAsICJzdF9jdGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2N0aW1lX25zIjogMTY4NTg5MTIyMTU1OTE5MTcwMCwgInN0X2RldiI6IDI3NTYzNDcwOTQ5NTU2NDk1OTksICJzdF9maWxlX2F0dHJpYnV0ZXMiOiAzMiwgInN0X2dpZCI6IDAsICJzdF9pbm8iOiAxMTI1ODk5OTEwMTE5ODMyLCAic3RfbW9kZSI6IDMzMjc5LCAic3RfbXRpbWUiOiAxNjg1ODkxMjIxLjU1OTcxNTcsICJzdF9tdGltZV9ucyI6IDE2ODU4OTEyMjE1NTk3MTU3MDAsICJzdF9ubGluayI6IDEsICJzdF9yZXBhcnNlX3RhZyI6IDAsICJzdF9zaXplIjogMTQxMDEyMCwgInN0X3VpZCI6IDAsICJOYW1lIjogInJ1ZnVzLTQuMS5leGUiLCAiUGF0aCI6ICJkOlxcZGlzdCIsICJVUkkiOiAiXFxcXD9cXFZvbHVtZXszMzk3ZDk3Yi0yY2E1LTExZWQtYjJmYy1iNDBlZGU5YTVhM2N9XFxkaXN0XFxydWZ1cy00LjEuZXhlIiwgIkluZGV4ZXIiOiAiMDc5M2I0ZDUtZTU0OS00Y2I2LTgxNzctMDIwYTczOGI2NmI3IiwgIlZvbHVtZSBHVUlEIjogIjMzOTdkOTdiLTJjYTUtMTFlZC1iMmZjLWI0MGVkZTlhNWEzYyIsICJPYmplY3RJZGVudGlmaWVyIjogIjJjNzNkNmU1LWVhYmEtNGYwYS1hY2YzLWUwMmM1MjlmMDk3YSJ9",
            "Attributes": {
                "st_atime": 1693223456.3334281,
                "st_atime_ns": 1693223456333428100,
                "st_birthtime": 1685891221.5591917,
                "st_birthtime_ns": 1685891221559191700,
                "st_ctime": 1685891221.5591917,
                "st_ctime_ns": 1685891221559191700,
                "st_dev": 2756347094955649599,
                "st_file_attributes": 32,
                "st_gid": 0,
                "st_ino": 1125899910119832,
                "st_mode": 33279,
                "st_mtime": 1685891221.5597157,
                "st_mtime_ns": 1685891221559715700,
                "st_nlink": 1, "st_reparse_tag": 0,
                "st_size": 1410120,
                "st_uid": 0,
                "Name": "rufus-4.1.exe",
                "Path": "d:\\dist",
                "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\rufus-4.1.exe",
                "Indexer": "0793b4d5-e549-4cb6-8177-020a738b66b7",
                "Volume GUID": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
                "ObjectIdentifier": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a"
            },
            "SourceIdentifier": {
                "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                "Version": "1.0", "Description": None
            },
            "Timestamp": "2024-07-30T23:38:48.319654+00:00"
        },
        "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\rufus-4.1.exe",
        "ObjectIdentifier": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a",
        "Timestamps": [
            {
                "Label": "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6",
                "Value": "2023-06-04T15:07:01.559192+00:00",
                "Description": "Created"
            },
            {
                "Label": "434f7ac1-f71a-4cea-a830-e2ea9a47db5a",
                "Value": "2023-06-04T15:07:01.559716+00:00",
                "Description": "Modified"
            },
            {
                "Label": "581b5332-4d37-49c7-892a-854824f5d66f",
                "Value": "2023-08-28T11:50:56.333428+00:00",
                "Description": "Accessed"
            },
            {
                "Label": "3bdc4130-774f-4e99-914e-0bec9ee47aab",
                "Value": "2023-06-04T15:07:01.559192+00:00",
                "Description": "Changed"
            }
        ],
        "Size": 1410120,
        "Machine": "2e169bb7-0024-4dc1-93dc-18b7d2d28190",
        "Volume": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
        "UnixFileAttributes": "S_IFREG",
        "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE",
        "SemanticAttributes" : [],
        "Label" : None,
        "LocalIdentifier" : None
    }
    indaleko_object = IndalekoObject.deserialize(data_object)
    print(json.dumps(indaleko_object.serialize(), indent=2))
    assert IndalekoObjectDataSchema.is_valid_object(indaleko_object.serialize()),\
        'Object is not valid.'

if __name__ == "__main__":
    main()
