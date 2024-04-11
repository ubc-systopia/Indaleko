'''Indaleko Activity Data Provider Location Data'''

from icecream import ic
import json
import uuid

from IndalekoActivityData import IndalekoActivityData

class IADPLocationData(IndalekoActivityData):
    '''This defines the class for location data.'''

    default_location_data_name = 'Location'
    default_location_data_source_uuid = '87d88169-d56d-472a-a7f7-fa18f8177d45'
    default_location_data_source = {
        'Identifier' : default_location_data_source_uuid,
        'Version' : '1.0',
        'Description' : 'Location data provider',
        'Name' : default_location_data_name,
    }

    def __init__(self, **kwargs):
        '''Initialize the object.'''
        ic(kwargs)
        self.name = kwargs.get('Name', self.default_location_data_name)
        self.data_identifier = kwargs.get('activity_data_id', str(uuid.uuid4()))
        self.source = kwargs.get('Source', self.default_location_data_source)
        if 'location' in kwargs:
            self.longitude = kwargs['location'].get('longitude', 0.0)
            self.latitude = kwargs['location'].get('latitude', 0.0)
        self.longitude = kwargs.get('Longitude', 0.0)
        self.latitude  = kwargs.get('Latitude', 0.0)
        if 'ActivityDataIdentifier' not in kwargs:
            kwargs['ActivityDataIdentifier'] = self.data_identifier
        if 'ActivityDataType' not in kwargs:
            kwargs['ActivityDataType'] = self.name
        if 'ActivityData' not in kwargs:
            kwargs['ActivityData'] = {
                'Longitude' : self.longitude,
                'Latitude' : self.latitude,
            }
        if 'source' not in kwargs:
            kwargs['source'] = self.source
        if 'attributes' not in kwargs:
            kwargs['attributes'] = {
                'Latitude' : self.latitude,
                'Longitude' : self.longitude,
            }
        super().__init__(**kwargs)

    def get_longitude(self):
        '''Return the longitude.'''
        return self.longitude

    def get_latitude(self):
        '''Return the latitude.'''
        return self.latitude

def main():
    '''Test the IADPLocationData class.'''
    print('Testing IADPLocationData')
    location_data = IADPLocationData()
    print(json.dumps(location_data.to_dict(),indent=2))

if __name__ == '__main__':
    main()
