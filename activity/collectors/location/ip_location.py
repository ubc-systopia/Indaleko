'''This implements the IP Location Service'''

import datetime
import ipaddress
import os
import requests
import sys
import uuid

from typing import List, Dict, Any

from icecream import ic


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# now we can import modules from the project root
from activity.collectors.location import LocationCollector
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.location.data_models.ip_location_data_model import IPLocationDataModel
# pylint: enable=wrong-import-position


class IPLocation(LocationCollector):
    '''This is the IP Location Service'''
    def __init__(self):
        self.timeout = 10
        self._name = 'IP Location Service'
        self._location = ''
        self._provider_id = uuid.UUID('82ae879d-7280-4b5a-a98a-5ebc1bf61bbc')
        self.ip_address = self.capture_public_ip_address()
        self.ip_location_data = self.get_ip_location_data()
        self.location_data = self.map_ip_location_data_to_data_model(self.ip_location_data)

    @staticmethod
    def capture_public_ip_address(timeout: int = 10) -> str:
        '''Capture the public IP address'''
        response = requests.get('https://api.ipify.org?format=json', timeout=timeout)
        data = response.json()
        return data.get('ip')

    def map_ip_location_data_to_data_model(self, location_data: dict) -> IPLocationDataModel:
        '''Map the IP location data to the data model'''
        # start with the required fields
        if 'ip_address' in location_data:
            ip_address = location_data.get('ip_address')
        else:
            try:
                ip_address = ipaddress.IPv4Address(location_data.get('query'))
            except ipaddress.AddressValueError:
                ip_address = ipaddress.IPv6Address(location_data.get('query'))
        assert isinstance(ip_address, ipaddress.IPv4Address) \
            or isinstance(ip_address, ipaddress.IPv6Address), \
            f'The IP address is not a valid IP address. It is {type(ip_address)}'
        kwargs = {
            "latitude": location_data.get('lat'),
            "longitude": location_data.get('lon'),
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "source": "IP",
            "ip_address": ip_address,
        }
        # add the optional fields
        if 'altitude' in location_data:
            kwargs['altitude'] = location_data.get('altitude')
        if 'accuracy' in location_data:
            kwargs['accuracy'] = location_data.get('accuracy')
        if 'heading' in location_data:
            kwargs['heading'] = location_data.get('heading')
        if 'speed' in location_data:
            kwargs['speed'] = location_data.get('speed')
        if 'city' in location_data:
            kwargs['city'] = location_data.get('city')
        if 'country' in location_data:
            kwargs['country'] = location_data.get('country')
        if 'country_code' in location_data:
            kwargs['country_code'] = location_data.get('country_code')
        if 'region' in location_data:
            kwargs['region'] = location_data.get('region')
        if 'region_name' in location_data:
            kwargs['region_name'] = location_data.get('region_name')
        if 'postal_code' in location_data:
            kwargs['postal_code'] = location_data.get('postal_code')
        if 'isp' in location_data:
            kwargs['isp'] = location_data.get('isp')
        if 'org' in location_data:
            kwargs['org'] = location_data.get('org')
        if 'as_name' in location_data:
            kwargs['as_name'] = location_data.get('as_name')
        if 'timezone' in location_data:
            kwargs['timezone'] = location_data.get('timezone')
        return IPLocationDataModel(**kwargs)

    def get_ip_location_data(self) -> dict:
        '''Get the coordinates for the location'''
        if self.ip_address is None:
            return None
        url = f'http://ip-api.com/json/{self.ip_address}'
        response = requests.get(url, timeout=self.timeout)
        data = response.json()
        if data.get('status') == 'success':
            return data
        else:
            return None

    def get_collector_characteristics(self) -> List[ActivityDataCharacteristics]:
        '''Get the provider characteristics'''
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SPATIAL,
            ActivityDataCharacteristics.ACTIVITY_DATA_NETWORK,
            ActivityDataCharacteristics.PROVIDER_DEVICE_STATE_DATA,
        ]

    def get_collectorr_name(self) -> str:
        '''Get the provider name'''
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        '''Get the provider ID'''
        return self._provider_id

    def retrieve_data(self, data_type: str) -> str:
        '''Retrieve data from the provider'''
        raise NotImplementedError('This method is not implemented yet.')

    def retrieve_temporal_data(self,
                               reference_time: datetime.datetime,
                               prior_time_window: datetime.timedelta,
                               subsequent_time_window: datetime.timedelta,
                               max_entries: int = 0) -> List[Dict]:
        '''Retrieve temporal data from the provider'''
        raise NotImplementedError('This method is not implemented yet.')

    def get_cursor(self, activity_context: uuid. UUID) -> uuid.UUID:
        '''Retrieve the current cursor for this data provider
           Input:
                activity_context: the activity context into which this cursor is
                being used
            Output:
                The cursor for this data provider, which can be used to retrieve
                data from this provider (via the retrieve_data call).
        '''

    def cache_duration(self) -> datetime.timedelta:
        '''
        Retrieve the maximum duration that data from this provider may be
        cached
        '''
        return datetime.timedelta(minutes=10)

    def get_description(self) -> str:
        '''
        Retrieve a description of the data provider. Note: this is used for
        prompt construction, so please be concise and specific in your
        description.
        '''
        return '''
        This is a geolocation service that provides location data for
        the device.
        '''

    def get_json_schema(self) -> dict:
        '''Get the JSON schema for the provider'''
        return IPLocationDataModel.schema_json()

    def get_location_name(self) -> str:
        '''Get the location'''
        location = self._location
        if location is None:
            location = ''
        return location

    def get_coordinates(self) -> Dict[str, float]:
        '''Get the coordinates for the location'''
        return {'latitude': 0.0, 'longitude': 0.0}

    def get_location_history(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime
    ) -> List[Dict[str, Any]]:
        '''Get the location history for the location'''
        return []

    def get_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        '''Get the distance between two locations'''
        raise NotImplementedError('This method is not implemented yet.')


def main():
    '''This is the interface for testing the foo.py module.'''
    location = IPLocation()
    ic(location.get_collectorr_name())
    ic(location.get_provider_id())
    ic(location.get_collector_characteristics())
    ic(location.get_description())
    ic(location.get_json_schema())
    ic(location.get_location_name())
    ic(location.get_coordinates())
    ic(location.get_location_history(datetime.datetime.now(), datetime.datetime.now()))
    ic(location.ip_address)
    ic(location.ip_location_data)
    ic(location.location_data.json())


if __name__ == '__main__':
    main()
