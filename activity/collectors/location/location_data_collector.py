'''
This module defines a common base for location data collectors.

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
import json
import math
import os
import sys
import uuid

from datetime import datetime
from typing import Union, List, Dict
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollection import IndalekoCollection
from activity.provider_registration import IndalekoActivityDataProviderRegistration
from activity.provider_registration_service import IndalekoActivityDataProviderRegistrationService
from data_models.activity_data_provider_registration import IndalekoActivityDataProviderRegistrationDataModel
from data_models.indaleko_record_data_model import IndalekoRecordDataModel
from data_models.indaleko_source_identifier_data_model import IndalekoSourceIdentifierDataModel
from activity.providers.location.data_models.location_data_model import BaseLocationDataModel
from activity.data_model.activity_data_model import IndalekoActivityDataModel
from data_models.indaleko_semantic_attribute_data_model import IndalekoSemanticAttributeDataModel
from activity.provider_base import ProviderBase
from activity.provider_characteristics import ProviderCharacteristics
# pylint: enable=wrong-import-position

class BaseLocationDataCollector:
    '''This class provides a common base for location data collectors.'''

    default_min_movement_change_required = 500 # meters
    default_max_time_between_updates = 360 # seconds = 10 min

    def __init__(self, **kwargs):
        '''Initialize the base location data collector.'''
        self.min_movement_change_required = kwargs.get('min_movement_change_required',
                                                         self.default_min_movement_change_required)
        self.max_time_between_updates = kwargs.get('max_time_between_updates',
                                                    self.default_max_time_between_updates)
        self.provider = kwargs.get('provider', None)
        if self.provider is not None:
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'

    @staticmethod
    def compute_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        '''Compute the distance between two points.'''
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lon1_rad = math.radians(lon1)
        lon2_rad = math.radians(lon2)

        delta_lat = lat2_rad - lat1_rad
        delta_lon = lon2_rad - lon1_rad

        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = 6371 * 1000 * c # in meters
        ic(distance)
        return distance

    @staticmethod
    def compute_time_difference(time1: Union[datetime, str],
                                time2: Union[datetime, str]) -> float:
        '''Compute the time difference between two times.'''
        assert isinstance(time1, datetime) or isinstance(time1, str), 'time1 is not a datetime or string'
        assert isinstance(time2, datetime) or isinstance(time2, str), 'time2 is not a datetime or string'
        if isinstance(time1, str):
            time1 = datetime.fromisoformat(time1)
        if isinstance(time2, str):
            time2 = datetime.fromisoformat(time2)
        delta = time2 - time1
        return delta.total_seconds()

    def has_data_changed(self,
                         data1: BaseLocationDataModel,
                         data2: BaseLocationDataModel) -> bool:
        '''Check if the data has changed materially.

            Input:
                data1: the first data object
                data2: the second data object

            Output:
                True if the data has changed, False otherwise.

            Note: "changed" here means that the variation is more than the
            minimum allowed, based upon location (longitude, latitude) and time.
        '''
        if data1 is None or data2 is None:
            return True
        assert isinstance(data1, BaseLocationDataModel),\
            f'data1 is not a BaseLocationDataModel {type(data1)}'
        assert isinstance(data2, BaseLocationDataModel),\
            f'data2 is not a BaseLocationDataModel {type(data2)}'
        distance = BaseLocationDataCollector.compute_distance(data1.latitude, data1.longitude, data2.latitude, data2.longitude)
        time_delta = BaseLocationDataCollector.compute_time_difference(data1.timestamp, data2.timestamp)
        return distance > self.min_movement_change_required or\
               time_delta > self.max_time_between_updates

    @staticmethod
    def get_latest_db_update_dict(collection : IndalekoCollection) -> Union[dict, None]:
        '''Get the latest update from the database.'''
        assert isinstance(collection, IndalekoCollection),\
             f'collection is not an IndalekoCollection {type(collection)}'
        query = '''
            FOR doc IN @@collection
                SORT doc.timestamp DESC
                LIMIT 1
                RETURN doc
        '''
        bind_vars = {
            '@collection' : collection.name
        }
        results = IndalekoDBConfig().db.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]
        if len(entries) == 0:
            return None
        assert len(entries) == 1, f'Too many results {len(entries)}'
        return entries[0]

    @staticmethod
    def build_location_activity_document(
        source_data : Union[IndalekoSourceIdentifierDataModel, dict],
        location_data: Union[BaseLocationDataModel, dict],
        semantic_attributes : List[IndalekoSemanticAttributeDataModel]) -> dict:
        '''
        This builds a dictionary that can be used to generate the json
        required to insert the record into the database.

        Input:
            source_data: the source of this data.
            location_data: the location data.  Note that this is treated as
            transparent information and is simply stored in the database.

            semantic_attributes: the semantic attributes associated with the
            location data.  Note that this can be any combination of known and
            unknown semantic attributes.  These are indexed.
        '''
        assert isinstance(source_data, IndalekoSourceIdentifierDataModel) \
            or isinstance(source_data, dict),\
            f'source_data is not an IndalekoSourceIdentifierDataModel or dict {type(source_data)}'
        assert isinstance(location_data, BaseLocationDataModel) or isinstance(location_data, dict),\
            f'location_data is not a BaseLocationDataModel or dict {type(location_data)}'
        assert isinstance(semantic_attributes, List),\
            f'semantic_attributes is not a List {type(semantic_attributes)}'
        if isinstance(location_data, BaseLocationDataModel):
            location_data = json.loads(location_data.model_dump_json())
        assert len(semantic_attributes) > 0, 'No semantic attributes provided'
        timestamp = location_data['timestamp']
        ic(location_data)
        activity_data_args = {
            'Record' : IndalekoRecordDataModel(
                SourceIdentifier=source_data,
                Timestamp=timestamp,
                Attributes={},
                Data=Indaleko.encode_binary_data(location_data)
            ),
            'Timestamp' : timestamp,
            'SemanticAttributes' : semantic_attributes
        }
        ic(activity_data_args)
        activity_data = IndalekoActivityDataModel(**activity_data_args)
        return activity_data.model_dump_json()

    def retrieve_temporal_data(self,
                               reference_time : datetime.datetime,
                               prior_time_window : datetime.timedelta,
                               subsequent_time_window : datetime.timedelta,
                               max_entries : int = 0) -> Union[List[Dict],None]:
        '''
        This call retrieves temporal data available to the data provider within
        the specified time window.

        Args:
            reference_time (datetime.datetime): The reference time for the
            query.
            prior_time_window (datetime.timedelta): The time window before the
            reference time.
            subsequent_time_window (datetime.timedelta): The time window after
            the reference time.
            max_entries (int): The maximum number of entries to return.  If 0,
            then all entries are returned.

        Returns:
            List[Dict]: The data available within the specified time window.
        '''
        raise NotImplementedError('retrieve_temporal_data is not implemented')

    # Note: the following methods map to the abstract methods in the
    # ProviderBase.  Since many of them involve interacting with the database,
    # we can interact with the provider to interpret and handle the data, while
    # we handle the database interactions.
    def get_provider_characteristics(self) -> Union[List[ProviderCharacteristics],None]:
        '''
        This call returns the characteristics of the data provider.  This is
        intended to be used to help users understand the data provider and to
        help the system understand how to interact with the data provider.

        Returns:
            Dict: A dictionary containing the characteristics of the provider.
        '''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.get_provider_characteristics()
        return None

    def get_provider_name(self) -> Union[str, None]:
        '''
        Get the name of the provider

            Returns:
                str: The name of the provider
        '''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.get_provider_name()
        return None

    def get_provider_id(self) -> Union[uuid.UUID, None]:
        '''Get the UUID for the provider'''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.get_provider_id()
        return None

    def retrieve_data(self, data_id: uuid.UUID) -> Union[Dict, None]:
        '''
        This call retrieves the data associated with the provided data_id.

        Args:
            data_id (uuid.UUID): The UUID that represents the data to be
            retrieved.

        Returns:
            Dict: The data associated with the data_id.

        Note: this API may change (e.g., so that it includes both the activity
        context value as well as the provider value.)
        '''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.retrieve_data(data_id)
        return None

    def cache_duration(self) -> Union[datetime.timedelta, None]:
        '''
        Retrieve the maximum duration that data from this provider may be
        cached.
        '''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.cache_duration()
        return None

    def get_description(self) -> Union[str, None]:
        '''
        Retrieve a description of the data provider. Note: this is used for
        prompt construction, so please be concise and specific in your
        description.
        '''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.get_description()
        return None

    def get_json_schema(self) -> Union[dict, None]:
        '''
        Retrieve the JSON data schema to use for the database.
        '''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.get_json_schema()
        return None

    def get_cursor(self, activity_context : uuid.UUID) -> Union[uuid.UUID, None]:
        '''Retrieve the current cursor for this data provider'''
        if hasattr(self, 'provider'):
            assert isinstance(self.provider, ProviderBase),\
                f'provider is not an ProviderBase {type(self.provider)}'
            return self.provider.get_cursor(activity_context)
        return None
