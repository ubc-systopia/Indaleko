"""This module handles the Indaleko Activity Data class."""

import datetime
import json
import uuid

from IndalekoRecord import IndalekoRecord

class IndalekoActivityData(IndalekoRecord):
    """This defines the base class for the Indaleko Activity Data objects."""

    def __init__(self, **kwargs):
        """Initialize the object."""
        if 'raw_data' not in kwargs:
            kwargs['raw_data'] = b''
        super().__init__(**kwargs)
        self.activity_data_identifier = kwargs['ActivityDataIdentifier']
        self.timestamps = kwargs.get('Timestamps', {})
        self.activity_data = kwargs.get('ActivityData', {})
        self.activity_data_type = kwargs.get('ActivityDataType', 'Unknown Activity Data Type')
        self.activity_data_version = kwargs.get('ActivityDataVersion', '1.0')

    def add_timestamp(self, label: uuid.UUID, value: datetime.datetime = None):
        """Add a timestamp to the object."""
        assert isinstance(label, uuid.UUID), 'label must be a UUID'
        assert isinstance(value, datetime.datetime) or value is None, 'value must be a datetime'
        if value is None:
            value = datetime.datetime.now()
        self.timestamps[label] = value

    def to_dict(self):
        """Convert the object to a dictionary."""
        obj = super().to_dict()
        obj['ActivityDataIdentifier'] = self.activity_data_identifier
        obj['ActivityData'] = self.activity_data
        obj['ActivityDataType'] = self.activity_data_type
        obj['ActivityDataVersion'] = self.activity_data_version
        obj['Timestamps'] = []
        if len(self.timestamps) > 0:
            for key, value in self.timestamps.items():
                obj['Timestamps'].append({
                    'Label': str(key),
                    'Value': value.isoformat()
                })
        obj['_key'] = self.activity_data_identifier
        obj['Record'] = super().to_dict()

        return obj

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
        Timestamps = {
                '6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6' : datetime.datetime.now(datetime.timezone.utc),
        },
        ActivityData = {
            'Data': 'This is some activity data'
        },
        ActivityDataType = 'Test',
        ActivityDataVersion = '1.0'
    )
    print(json.dumps(data.to_dict(),indent=4))

if __name__ == '__main__':
    main()
