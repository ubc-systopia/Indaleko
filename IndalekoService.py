"""
The purpose of this package is to create the information needed to track a
distinct Indaleko service class.  Registration and managemen is done in the
complementary IndalekoServices class.

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
"""

import argparse
import uuid
import datetime
import json

from icecream import ic

from IndalekoServiceDataModel import IndalekoServiceDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoService:
    """
    In Indaleko, a service is a component that provides some kind of
    functionality.  This class manages registration and lookup of services.
    """
    indaleko_service_uuid_str = '951724c8-9957-4455-8132-d786b7383b47'
    indaleko_service_version = '1.0'

    def __init__(self, **kwargs):
        '''
        This class takes the following optional arguments:
        * service_collection -the collection to use for service
            lookup/registration.  Note that if this is not specified the
            database configuration will be used and the default collection is
            used.
        * service_identifier - the identifier for the service.  This is used
            to look up an existing service.  If this is specified, the service
            will be looked up by its identifier.
        * service_name - the name of the service.  This is used to look up
            the service if the identifier is not specified.  If the service
            does not exist, it will be created.  See Indaleko.Collections for
            known services.

        Note: there are two sources for this data: one is from program callers,
        the other is from the database, that's why we check two different
        values.  Ugly, but it is what it is.
        '''
        self.record = kwargs.get('Record', kwargs.get('record', None))
        self.service_type = kwargs.get('service_type', kwargs.get('Type', None))
        self.service_identifier = kwargs.get('service_identifier', kwargs.get('Identifier', None))
        self.service_name = kwargs.get('service_name', kwargs.get('Name', None))
        self.service_description = kwargs.get('service_description', kwargs.get('Description', 'Unknown Service'))
        self.service_version = kwargs.get('service_version', kwargs.get('Version', '0.1'))
        self.creation_date = kwargs.get('creation_date',
                                        datetime.datetime.now(datetime.timezone.utc).isoformat())
        assert self.record is not None, 'Record is required for IndalekoService'
        assert self.service_type is not None, 'Type is required for IndalekoService'
        assert self.service_name is not None, 'Name is required for IndalekoService'
        assert self.service_version is not None, 'Version is required for IndalekoService'
        assert self.service_description is not None, 'Description is required for IndalekoService'
        assert self.service_identifier is not None, 'Identifier is required for IndalekoService'

        if type(self.record) is dict:
            ic(self.record)
            self.record = IndalekoRecordDataModel.IndalekoRecord.deserialize(self.record)
        self.service_object = IndalekoServiceDataModel.IndalekoService(
            Record = self.record,
            Identifier = self.service_identifier,
            Version = self.service_version,
            Name = self.service_name,
            Type = self.service_type
        )

    @staticmethod
    def deserialize(data : dict) -> 'IndalekoService':
        '''Deserialize the data into an IndalekoService object.'''
        return IndalekoService(**data)

    def serialize(self) -> dict:
        '''Serialize the object to a dictionary.'''
        serialized_data = IndalekoServiceDataModel.IndalekoService.serialize(self.service_object)
        serialized_data['_key'] = self.service_identifier
        return serialized_data

    def get_service_data(self) -> dict:
        """Return the data for this service."""
        return self.serialize()

    def to_dict(self) -> dict:
        """Return a dictionary representation of this object."""
        return self.serialize()

    def to_json(self, indent : int = 4) -> str:
        """Return a JSON representation of this object."""
        return json.dumps(self.to_dict(), indent=indent)

def main():
    '''Test code for IndalekoService'''
    print('No tests defined for IndalekoService yet.')

if __name__ == "__main__":
    main()
