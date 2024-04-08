'''
This module provides the IndalekoLocationDataProvider class,
which is used to provide location activity data for the Indaleko system.
'''

from IndalekoRecord import IndalekoRecord
from IndalekoActivityDataProvider import IndalekoActivityDataProvider
from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistration

class IndalekoLocationDataProvider(IndalekoRecord):
    '''This class is used to manage Indaleko Location Data.'''

    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoLocationDataProvider class.'''
        if 'provider' not in kwargs:
            raise ValueError('provider must be specified')
        self.provider_registration = self.get_provider_registration(kwargs['provider'])

    def get_provider_registration(self, provider_name : str) -> IndalekoActivityDataProviderRegistration:
        '''Return the provider for this location data.'''
        if hasattr(self, 'provider_registration') and self.provider_registration is not None:
            return self.provider_registration
        self.provider_registration = IndalekoActivityDataProviderRegistration(provider_name)
def main():
    '''Main entry point for IndalekoLocationDataProvider.'''
    print('Main called')

if __name__ == '__main__':
    main()
