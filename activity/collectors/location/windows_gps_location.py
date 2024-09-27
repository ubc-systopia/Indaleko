'''
This module defines a utility for acquiring GPS data for a windows system and
recording it in the database.

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

from typing import Union
from datetime import datetime
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
from activity.providers.known_semantic_attributes import KnownSemanticAttributes
from activity.provider_registration_service import IndalekoActivityDataProviderRegistrationService
from activity.providers.location.windows_gps_location import WindowsGPSLocation
from activity.providers.location.data_models.windows_gps_location_data_model\
        import WindowsGPSLocationDataModel
from data_models.indaleko_record_data_model import IndalekoRecordDataModel
from data_models.indaleko_source_identifier_data_model import IndalekoSourceIdentifierDataModel
from data_models.indaleko_uuid_data_model import IndalekoUUIDDataModel
from activity.collectors.location.location_data_collector import BaseLocationDataCollector
from data_models.indaleko_semantic_attribute_data_model import IndalekoSemanticAttributeDataModel
# pylint: enable=wrong-import-position

class WindowsGPSLocationCollector(BaseLocationDataCollector):
    '''This class provides a utility for acquiring GPS data for a windows system
    and recording it in the database.'''

    identifier = uuid.UUID('7e85669b-ecc7-4d57-8b51-8d325ea84930')
    version = '1.0.0'
    description = 'Windows GPS Location Collector'

    def __init__(self, **kwargs):
        '''Initialize the Windows GPS Location Collector.'''
        self.min_movement_change_required = kwargs.get('min_movement_change_required',
                                                         self.default_min_movement_change_required)
        self.max_time_between_updates = kwargs.get('max_time_between_updates',
                                                    self.default_max_time_between_updates)
        self.db_config = IndalekoDBConfig()
        assert self.db_config is not None, 'Failed to get the database configuration'
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description
        )
        ic(source_identifier.serialize())
        record_kwargs = {
            'Identifier' : str(self.identifier),
            'Version' : self.version,
            'Description' : self.description,
            'Record' : IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(),
                Attributes={},
                Data=''
            )
        }
        self.provider_registrar = IndalekoActivityDataProviderRegistrationService()
        assert self.provider_registrar is not None, 'Failed to get the provider registrar'
        provider = self.provider_registrar.lookup_provider_by_identifier(str(self.identifier))
        if provider is None:
            ic('Registering the provider')
            provider, collection = self.provider_registrar.register_provider(**record_kwargs)
        else:
            ic('Provider already registered')
            collection = IndalekoActivityDataProviderRegistrationService\
                .lookup_activity_provider_collection(str(self.identifier))
        ic(provider)
        ic(collection)
        self.provider = provider
        self.collection = collection

    def get_latest_db_update(self) -> Union[WindowsGPSLocation, None]:
        '''Get the latest update from the database.'''
        doc = BaseLocationDataCollector.get_latest_db_update_dict(self.collection)
        if doc is None:
            return None
        current_data = Indaleko.decode_binary_data(doc['Record']['Data'])
        ic(current_data)
        return WindowsGPSLocationDataModel.deserialize(current_data)

    def update_data(self) -> Union[WindowsGPSLocationDataModel, None]:
        '''Update the data in the database.'''
        ksa = KnownSemanticAttributes()
        current_data = WindowsGPSLocation().get_coords()
        ic(type(current_data))
        assert isinstance(current_data, WindowsGPSLocationDataModel),\
            f'current_data is not a WindowsGPSLocationDataModel {type(current_data)}'
        ic(type(current_data))
        latest_db_data = self.get_latest_db_update()
        if not self.has_data_changed(current_data, latest_db_data):
            ic('Data has not changed, return last DB record')
            return latest_db_data
        # the data has changed enough for us to record it.
        ic('Data has changed, record in the database')
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description
        )
        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(
                Identifier = IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_PROVIDER_LOCATION_LATITUDE,
                    Version='1',
                    Description='Latitude'
                ),
                Data=current_data.latitude,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier= IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_PROVIDER_LOCATION_LONGITUDE,
                    Version='1',
                    Description='Longitude'
                ),
                Data=current_data.longitude,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier = IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_PROVIDER_LOCATION_ACCURACY,
                    Version='1',
                    Description='Accuracy'
                ),
                Data=current_data.accuracy,
            )
        ]
        ic(type(current_data))
        doc = BaseLocationDataCollector.build_location_activity_document(
            source_data=source_identifier,
            location_data=current_data,
            semantic_attributes=semantic_attributes
        )
        # doc = current_data.model_dump_json()
        ic(doc)
        data = json.loads(doc)
        data['_key'] = str(uuid.uuid4())
        doc = json.dumps(data)
        self.collection.insert(doc)
        return ic(current_data)


def main():
    '''Main entry point for the Windows GPS Location Collector.'''
    ic('Starting Windows GPS Location Collector')
    collector = WindowsGPSLocationCollector()
    collector.update_data()
    latest = collector.get_latest_db_update()
    ic(latest)
    ic('Finished Windows GPS Location Collector')

if __name__ == '__main__':
    main()
