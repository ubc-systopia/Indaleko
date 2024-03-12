'''
IndalekoActivityRegistration is a class used to register activity data
providers for the Indaleko system.

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
import argparse
import datetime
import logging

from Indaleko import Indaleko
from IndalekoRecord import IndalekoRecord
from IndalekoLogging import IndalekoLogging
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollection, IndalekoCollections
from IndalekoActivityDataProviderRegistrationSchema \
    import IndalekoActivityDataProviderRegistrationSchema
from IndalekoServices import IndalekoService, IndalekoServices
from IndalekoSingleton import IndalekoSingleton

class IndalkeoActivityDataProviderRegistrationService(IndalekoSingleton):

    '''This class is used to implement and access
    the Indaleko Activity Data Provider Registration Service.'''

    UUID = '5ef4125d-4e46-4e35-bea5-f23a9fcb3f63'
    Version = '1.0'
    Description = 'Indaleko Activity Data Provider Registration Service'
    Name = 'IndalekoActivityDataProviderRegistrationService'

    activity_registration_service = IndalekoService.create_service_data(
        service_name = Name,
        service_description = Description,
        service_version = Version,
        service_type = IndalekoServices.service_type_activity_data_registrar,
        service_identifier = UUID
    )

    def __init__(self, **kwargs):
        '''Create an instance of the
        IndalekoActivityDataProviderRegistrationService class.'''
        if self._initialized:
            return
        if 'db_config' in kwargs:
            self.db_config = kwargs['db_config']
        else:
            self.db_config = IndalekoDBConfig()
        self.service = IndalekoService(
            service_name = Indaleko.Indaleko_ActivityDataProviders,
            service_description = self.Description,
            service_version = self.Version,
            service_type=IndalekoServices.service_type_activity_data_registrar,
            service_identifier = self.UUID
        )
        self._initialized = True




def main():
    '''Test the IndalekoActivityRegistration class.'''
    service = IndalkeoActivityDataProviderRegistrationService()
    print(service)


if __name__ == '__main__':
    main()
