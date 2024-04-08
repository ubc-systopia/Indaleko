'''This is the Indaleko module for managing Activity Context.'''

from IndalekoActivityContextSchema import IndalekoActivityContextSchema
from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistrationService
from IndalekoSingleton import IndalekoSingleton
from IndalekoDBConfig import IndalekoDBConfig

class IndalekoActivityContext(IndalekoSingleton):
    '''This class is used to manage Indaleko Activity Context.'''

    Schema = IndalekoActivityContextSchema.get_schema()

    ActivityContext_UUID = '6c65350c-1dd5-4675-b17a-4dd409349a40' # REPLACE
    ActivityContext_Version = '1.0'
    ActivityContext_Description = 'Activity Context'

    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoActivityContext class.'''
        if self._initialized:
            return
        # initialize the object
        print('initialize the object')
        self._initialized = True
        if 'db_config' in kwargs:
            self.db_config = kwargs['db_config']
        else:
            self.db_config = IndalekoDBConfig()
        if 'activity_provider_registration' in kwargs:
            self.activity_provider_registration = kwargs['activity_provider_registration']
        else:
            self.activity_provider_registration = \
                IndalekoActivityDataProviderRegistrationService(
                    DBConfig=self.db_config
                )
            raise NotImplementedError('activity_provider_registration is required') # REPLACE

def main():
    '''Test the IndalekoActivityContext class.'''
    instance1 = IndalekoActivityContext()
    instance2 = IndalekoActivityContext()
    assert instance1 == instance2, 'IndalekoActivityContext is not a singleton.'
    print('IndalekoActivityContext is a singleton.')
    activity_registration_collection = \
        instance1.activity_provider_registration.get_activity_registration_collection()
    print(activity_registration_collection)

if __name__ == '__main__':
    main()
