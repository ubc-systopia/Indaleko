'''
This defines the format of a "record" within Indaleko.  Other classes will
inherit from this base class.

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
import uuid
import base64
import json
import datetime
import argparse
import os
import random
import msgpack
from IndalekoRecordSchema import IndalekoRecordSchema
from Indaleko import Indaleko
class IndalekoRecord:
    '''
    This defines the format of a "record" within Indaleko.
    Other classes will inherit from this base class.
    '''
    keyword_map = (
        ('__raw_data__', 'Data'), # this is the raw captured data
        ('__attributes__', 'Attributes'),
        ('__source__', 'SourceIdentifier'), # this identifies the data source.
        ('__timestamp__', 'Timestamp'), # this is the timestamp for this record.
    )

    Schema = IndalekoRecordSchema().get_schema()

    @staticmethod
    def get_schema():
        """
        Return the schema for data managed by this class.
        """
        return IndalekoRecord.Schema

    @staticmethod
    def validate_uuid_string(uuid_string : str) -> bool:
        """Given a string, verify that it is in fact a valid uuid."""
        return Indaleko.validate_uuid_string(uuid_string)


    def __init__(self, **kwargs) -> None:
        if 'raw_data' not in kwargs:
            raise ValueError('raw_data must be specified')
        self.__raw_data__ = kwargs['raw_data']
        assert isinstance(self.__raw_data__, bytes), \
            f'raw_data must be bytes (is {type(self.__raw_data__)})'
        if isinstance(kwargs['raw_data'], str):
            self.set_base64_data(kwargs['raw_data'])
        else:
            self.set_data(kwargs['raw_data'])
        self.__attributes__ = {}
        if 'attributes' in kwargs:
            self.__attributes__ = kwargs['attributes']
        assert isinstance(self.__attributes__, dict), 'attributes must be a dict'
        if 'source' not in kwargs:
            raise ValueError('source must be specified')
        self.set_source(kwargs['source'])
        assert self.validate_source(self.__source__), f'source is not valid: {self.__source__}'
        if 'identifier' in kwargs:
            self.__identifier__ = kwargs['identifier']
            assert self.validate_uuid_string(self.__identifier__), 'identifier is not valid'
        else:
            self.__identifier__ = str(uuid.uuid4())
        self.__timestamp__ = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'timestamp' in kwargs:
            self.__timestamp__ = kwargs['timestamp']
            assert self.validate_iso_timestamp(self.__timestamp__), 'timestamp is not valid'

    def __setitem__(self, key, value):
        self.__attributes__[key] = value

    def __getitem__(self, key):
        if key not in self.__attributes__:
            raise KeyError(f'key {key} not found')
        return self.__attributes__[key]

    def __iter__(self):
        return iter(self.__attributes__)

    def __len__(self):
        return len(self.__attributes__)

    def __str__(self):
        return self.to_json(indent=0)

    def __delitem__(self, key):
        del self.__attributes__[key]

    def to_dict(self):
        """Return a dictionary representation of the record."""
        tmp = {}
        for field, keyword in self.keyword_map:
            if hasattr(self, field):
                tmp[keyword] = self.__dict__[field]
        return tmp

    def to_json(self, indent : int = 4):
        """Return a JSON representation of the record."""
        return json.dumps(self.to_dict(), indent=indent)

    def set_attributes(self, attributes : dict) -> 'IndalekoRecord':
        """Set the attributes for this record."""
        self.__attributes__ = attributes
        return self

    def get_attributes(self) -> dict:
        """Return the attributes for this record."""
        return self.__attributes__

    def set_source(self, source : dict) -> 'IndalekoRecord':
        """Set the source for this record."""
        assert self.validate_source(source), f'source is not valid: {source}'
        self.__source__ = {
            'Identifier' : source['Identifier'],
            'Version' : source['Version'],
            'Description' : None,
        }
        if 'Description' in source:
            self.__source__['Description'] = source['Description']
        if 'Name' in source:
            self.__source__['Name'] = source['Name']
        return self

    def get_source(self) -> dict:
        """Return the source for this record."""
        return self.__source__

    def set_data(self, raw_data : bytes) -> 'IndalekoRecord':
        """Set the raw data for this record. Note input is bytes and the data is
        stored as base64."""
        assert isinstance(raw_data, bytes), 'raw_data must be bytes'
        self.__raw_data__ = base64.b64encode(raw_data).decode('ascii')
        return self

    def set_base64_data(self, base64_data : str) -> 'IndalekoRecord':
        """Set the raw data for this record. Note input is base64 encoded."""
        assert isinstance(base64_data, str), 'base64_data must be a string'
        self.__raw_data__ = base64_data
        return self

    def get_data(self) -> str:
        """Return the raw data for this record. Note output is base64 encoded."""
        return self.__raw_data__

    def get_raw_data(self) -> bytes:
        """Return the raw data for this record. Note output is bytes."""
        return base64.b64decode(self.__raw_data__)

    def set_timestamp(self, timestamp : str) -> 'IndalekoRecord':
        """Set the timestamp for this record."""
        assert self.validate_iso_timestamp(timestamp), 'timestamp is not valid'
        self.__timestamp__ = timestamp
        return self

    @staticmethod
    def validate_source(source : dict) -> bool:
        """Given a source description as a dictionary, ensure it is valid."""
        valid = True
        if not isinstance(source, dict):
            print(f'source {source} is not a dict {type(source)}')
            valid = False
        elif 'Identifier' not in source:
            print('source does not contain an Identifier field')
            valid = False
        elif 'Version' not in source:
            print('source does not contain a Version field')
            valid = False
        elif not IndalekoRecord.validate_uuid_string(source['Identifier']):
            print('source Identifier is not a valid UUID')
            valid = False
        elif not isinstance(source['Version'], str):
            print('source Version is not a string')
            valid = False
        return valid

    @staticmethod
    def validate_iso_timestamp(source : str) -> bool:
        """Given a string, ensure it is a valid ISO timestamp."""
        return Indaleko.validate_iso_timestamp(source)

def main():
    """Test the IndalekoRecord class."""
    random_raw_data = msgpack.packb(os.urandom(64))
    source_uuid = str(uuid.uuid4())
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--source' ,
                        '-s',
                        type=str,
                        default=source_uuid, help='The source UUID of the data.')
    parser.add_argument('--raw-data',
                        '-r',
                        type=bytes,
                        default=random_raw_data,
                        help='The raw data to be stored.')
    args = parser.parse_args()
    attributes = {
        'field1' : random.randint(0, 100),
        'field2' : random.randint(101,200),
        'field3' : random.randint(201,300),
    }
    print(type(random_raw_data))
    record = IndalekoRecord(raw_data = random_raw_data,
                            attributes = attributes,
                            source = {
                                'Identifier' : args.source,
                                'Version' : '1.0'
                            })
    print(f'initial record :\n{record.to_json()}')
    for a in record:
        print(f'\tAttribute {a} has value {record[a]}')
    record['field4'] = random.randint(301,400)
    print(f'added field 4:\n{record.to_json()}')
    del record['field2']
    print(f'deleted field2 {record.to_json()}')
    IndalekoRecordSchema.is_valid_record(record.to_dict())

if __name__ == "__main__":
    main()
