'''
IndalekoActivityDataProvider --- this module provides
the data for the mechanisms for the activity data provider class.

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

from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistrationService

class IndalekoActivityDataProvider():
    '''This class is used to provide the data for the
    mechanisms for the activity data provider class.'''

    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoActivityDataProvider class.'''


def main():
    """Main function for the IndalekoActivityDataProvider class."""
    test_provider_uuid = '29872b82-af11-4b3a-bcb1-1ff2b6090d05'
    # backup_uuid = 'ddecdf14-ef7d-4537-abdb-da777dbe32fb'
    print("Welcome to Indaleko Activity Data Provider")
    registration = IndalekoActivityDataProviderRegistrationService()
    print(f'registration = {registration}')
    provider = registration.lookup_provider_by_identifier(test_provider_uuid)
    if len(provider) == 0:
        print(f'provider {test_provider_uuid} not found, creating')
        provider = registration.register_provider(
            Identifier = test_provider_uuid,
            Version = '1.0',
            Description = 'Test Activity Data Provider',
            Name = "Test Activity Data"
        )
    print(f'provider {provider}')
    print("Goodbye from Indaleko Activity Data Provider")

if __name__ == "__main__":
    main()
