"""This module handles the Indaleko Activity Data class."""

import datetime
import json
import msgpack
import uuid

from IndalekoRecord import IndalekoRecord
from IndalekoActivityDataProvider import IndalekoActivityDataProvider
from Indaleko import Indaleko

class IndalekoActivityData(IndalekoRecord):
    """This defines the base class for the Indaleko Activity Data objects."""

    class ActivityTimestamp():
        '''This class defines the timestamp information for an activity data
        object.'''
        def __init__(self, **kwargs):
            '''Initialize the object.'''
            assert 'Label' in kwargs, 'Label must be specified'
            self.label = kwargs['Label']
            self.value = kwargs.get('Value', datetime.datetime.now(datetime.timezone.utc).isoformat())
            self.description = kwargs.get('Description', None)
            self.timestamp = {
                'Label' : self.label,
                'Value' : self.value,
            }
            if self.description is not None:
                self.timestamp['Description'] = self.description

        def to_dict(self):
            '''Convert the object to a dictionary.'''
            return self.timestamp

    def __init__(self, **kwargs):
        """Initialize the object."""
        self.activity_data_identifier = kwargs['ActivityDataIdentifier']
        self.timestamps = kwargs.get('ActivityTimestamps', [])
        assert isinstance(self.timestamps, list), 'Timestamps must be a list'
        self.activity_data = kwargs.get('ActivityData', {})
        assert isinstance(self.activity_data, dict), 'ActivityData must be a dict'
        self.activity_data_type = kwargs.get('ActivityDataType', 'Unknown Activity Data Type')
        assert isinstance(self.activity_data_type, str), 'ActivityDataType must be a string'
        self.activity_data_version = kwargs.get('ActivityDataVersion', '1.0')
        assert isinstance(self.activity_data_version, str), 'ActivityDataVersion must be a string'
        if 'CollectionTimestamp' not in kwargs:
            if IndalekoActivityDataProvider.collection_time_uuid_str in kwargs:
                self.collection_timestamp = \
                    kwargs[IndalekoActivityDataProvider.collection_time_uuid_str]
            else:
                self.collection_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        assert Indaleko.validate_iso_timestamp(self.collection_timestamp), \
            'CollectionTimestamp must be a valid ISO8601 timestamp'
        if 'Attributes' not in kwargs:
            kwargs['Attributes'] =  {
            'ActivityData': self.activity_data,
            'ActivityDataType': self.activity_data_type,
            'ActivityDataVersion': self.activity_data_version,
        }
        if 'raw_data' not in kwargs:
            kwargs['raw_data'] = msgpack.packb(kwargs['attributes'])
        super().__init__(**kwargs)

    def to_dict(self):
        """Convert the object to a dictionary."""
        obj = {}
        obj['ActivityDataIdentifier'] = self.activity_data_identifier
        obj['ActivityData'] = self.activity_data
        obj['ActivityDataType'] = self.activity_data_type
        obj['ActivityDataVersion'] = self.activity_data_version
        obj['ActivityTimestamps'] = self.timestamps
        obj['CollectionTimestamp'] = self.collection_timestamp
        obj['_key'] = self.activity_data_identifier
        obj['Record'] = super().to_dict()

        return obj

    @staticmethod
    def create_collection_timestamp(timestamp : datetime.datetime = None) -> dict:
        '''Create a collection timestamp.'''
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        return {
            'Label' : IndalekoActivityDataProvider.collection_time_uuid_str,
            'Value' : timestamp.isoformat(),
            'Description' : 'Collection Time',
        }

    @staticmethod
    def create_start_timestamp(timestamp : datetime.datetime = None) -> dict:
        '''Create a start timestamp.'''
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        return {
            'Label' : IndalekoActivityDataProvider.start_time_uuid_str,
            'Value' : timestamp.isoformat(),
            'Description' : 'Start Time',
        }

    @staticmethod
    def create_end_timestamp(timestamp : datetime.datetime = None) -> dict:
        '''Create an end timestamp.'''
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        return {
            'Label' : IndalekoActivityDataProvider.end_time_uuid_str,
            'Value' : timestamp.isoformat(),
            'Description' : 'End Time',
        }

def main():
    '''Test the IndalekoActivityData class.'''
    print('Testing IndalekoActivityData')
    data = IndalekoActivityData(
        source = {
            'Identifier': '6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6',
            'Version': '1.0',
            'Description': 'This is a test source.'
        },
        ActivityDataIdentifier = '6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6',
        ActivityTimestamps = [
            {
                'Label': str(uuid.uuid4()),
                'Value': '2022-01-09T17:49:00.665358+00:00',
            },
            {
                'Label' : IndalekoActivityDataProvider.collection_time_uuid_str,
                'Value' : datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'Description' : 'Collection Time',
            }
        ],
        ActivityData = {
            'Data': 'This is some activity data'
        },
        ActivityDataType = 'Test',
        ActivityDataVersion = '1.0'
    )
    print(json.dumps(data.to_dict(),indent=4))

if __name__ == '__main__':
    main()
