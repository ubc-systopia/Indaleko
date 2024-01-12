
import uuid
import base64
import json
import datetime
import argparse
import os
import random
import msgpack
from IndalekoRecordSchema import IndalekoRecordSchema
class IndalekoRecord:
    '''
    This defines the format of a "record" within Indaleko.
    Other classes will inherit from this base class.
    '''
    keyword_map = (
        ('__raw_data__', 'Data'), # this is the raw captured data
        ('__attributes__', 'Attributes'),
        ('__source__', 'Source'), # this identifies the data source.
        ('__identifier__', 'RecordIdentifier'), # this identifies this specific record.
        ('__timestamp__', 'RecordTimestamp'), # this is the timestamp for this record.
    )

    Schema = IndalekoRecordSchema.get_schema()

    @staticmethod
    def get_schema():
        """
        Return the schema for data managed by this class.
        """
        return IndalekoRecord.Schema

    @staticmethod
    def validate_uuid_string(uuid_string : str) -> bool:
        """Given a string, verify that it is in fact a valid uuid."""
        if not isinstance(uuid_string, str):
            print(f'uuid is not a string it is a {type(uuid)}')
            return False
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            print('uuid is not valid')
            return False


    def __init__(self, raw_data : bytes, attributes : dict, source : dict) -> None:
        assert isinstance(raw_data, bytes), 'raw_data must be bytes'
        assert isinstance(attributes, dict), f'attributes must be a dict (not {type(attributes)})'
        assert isinstance(source, dict), 'source must be a dict'
        assert 'Identifier' in source, 'source must contain an Identifier field'
        assert 'Version' in source, 'source must contain a Version field'

        self.__raw_data__ = base64.b64encode(raw_data).decode('ascii')
        self.__attributes__ = attributes
        self.__source__ = {
            'Identifier' : source['Identifier'],
            'Version' : source['Version'],
        }
        self.__identifier__ = str(uuid.uuid4())
        self.__timestamp__ = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def __setitem__(self, key, value):
        self.__attributes__[key] = value

    def __getitem__(self, key):
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

    def set_attributes(self, attributes : dict) -> None:
        """Set the attributes for this record."""
        self.__attributes__ = attributes

    def get_attributes(self) -> dict:
        """Return the attributes for this record."""
        return self.__attributes__

    def set_source(self, source : dict):
        """Set the source for this record."""
        assert self.validate_source(source), 'source is not valid'
        self.__source__ = {
            'Identifier' : source['Identifier'],
            'Version' : source['Version'],
        }

    def get_source(self) -> dict:
        """Return the source for this record."""
        return self.__source__

    def set_data(self, raw_data : bytes) -> None:
        """Set the raw data for this record. Note input is bytes and the data is
        stored as base64."""
        assert isinstance(raw_data, bytes), 'raw_data must be bytes'
        self.__raw_data__ = base64.b64encode(raw_data).decode('ascii')

    def set_base64_data(self, base64_data : str) -> None:
        """Set the raw data for this record. Note input is base64 encoded."""
        assert isinstance(base64_data, str), 'base64_data must be a string'
        self.__raw_data__ = base64_data

    def get_data(self) -> str:
        """Return the raw data for this record. Note output is base64 encoded."""
        return self.__raw_data__

    def get_raw_data(self) -> bytes:
        """Return the raw data for this record. Note output is bytes."""
        return base64.b64decode(self.__raw_data__)

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
        valid = True
        if not isinstance(source, str):
            valid = False
        else:
            try:
                datetime.datetime.fromisoformat(source)
            except ValueError:
                valid = False
        return valid


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
                        type=str,
                        default=random_raw_data,
                        help='The raw data to be stored.')
    args = parser.parse_args()
    attributes = {
        'field1' : random.randint(0, 100),
        'field2' : random.randint(101,200),
        'field3' : random.randint(201,300),
    }
    record = IndalekoRecord(args.raw_data,
                            attributes,
                            {
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
