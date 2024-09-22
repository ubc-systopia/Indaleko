'''This implements the IP Location Service'''




import asyncio
import configparser
import datetime
import os
import platform
import requests
import sys
import uuid

from typing import List, Dict, Any

from icecream import ic
from pytile import async_login
from aiohttp import ClientSession

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from activity.providers.location import LocationProvider
from activity import ProviderCharacteristics
from activity.providers.location.data_models.tile_location_data_model import TileLocationDataModel

class TileLocation(LocationProvider):
    '''This is the Tile Location Service'''
    def __init__(self):
        self.timeout = 10
        self._name = 'Tile Location Service'
        self._location = 'Tile Location'
        self._provider_id = uuid.UUID('83496cc6-c3d8-4941-b5ab-ad064c345ebe')
        self.tile_config = self.get_tile_config()
        self.tile_data = self.get_tile_data()

    def get_tile_config(self, config_file : str = None) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        if config_file is None:
            config_file = os.path.join(os.environ['INDALEKO_ROOT'], 'config', 'tile.ini')
        config.read(config_file)
        return config

    def get_tile_data(self) -> dict:
        async def get_tile_data_async(email : str, password : str) -> dict:
            async with ClientSession() as session:
                api = await async_login(email, password, session)
                tiles = await api.async_get_tiles()
                return tiles
        return asyncio.run(
            get_tile_data_async(
                self.tile_config['tile']['email'],
                self.tile_config['tile']['password']
                )
            )

    def get_provider_characteristics(self) -> List[ProviderCharacteristics]:
        '''Get the provider characteristics'''
        return [
            ProviderCharacteristics.PROVIDER_SPATIAL_DATA,
            ProviderCharacteristics.PROVIDER_NETWORK_DATA,
            ProviderCharacteristics.PROVIDER_DEVICE_STATE_DATA,
        ]

    def get_provider_name(self) -> str:
        '''Get the provider name'''
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        '''Get the provider ID'''
        return self._provider_id

    def retrieve_data(self, data_type: str) -> str:
        '''Retrieve data from the provider'''
        raise NotImplementedError('This method is not implemented yet.')

    def retrieve_temporal_data(self,
                               reference_time : datetime.datetime,
                               prior_time_window : datetime.timedelta,
                               subsequent_time_window : datetime.timedelta,
                               max_entries : int = 0) -> List[Dict]:
        '''Retrieve temporal data from the provider'''
        raise NotImplementedError('This method is not implemented yet.')

    def get_cursor(self, activity_context : uuid. UUID) -> uuid.UUID:
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
        This is a service that retrieves Tile tracking information for the user.
        '''

    def get_json_schema(self) -> dict:
        '''Get the JSON schema for the provider'''
        return {}

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
        start_time : datetime.datetime,
        end_time : datetime.datetime) -> List[Dict[str, Any]]:
        '''Get the location history for the location'''
        return []

    def get_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        '''Get the distance between two locations'''
        raise NotImplementedError('This method is not implemented yet.')

def main():
    '''This is the interface for testing the foo.py module.'''

if __name__ == '__main__':
    main()
