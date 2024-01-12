"""
The purpose of this package is to create a common class structure for managing
Indaleko Services.

We have multiple sources of information that can be indexed by Indaleko.  Thus,
this provides a "registration mechanism" that allows a service to create a
registration endpoint and get back an object that it can use for interacting
with its service information.

The types of services envisioned here are:

* Indexers - these are component that gather data from storage locations.
* Ingesters - these are components that convert raw indexed information into a
  common format that is used when storing the actual data.

I expect there will be other kinds of services in the future, but that's the
list for now.
"""
import argparse
import uuid
import datetime
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollection
from IndalekoServicesSchema import IndalekoServicesSchema

class IndalekoService:
    """
    In Indaleko, a service is a component that provides some kind of
    functionality.  This class manages registration and lookup of services.
    """
    def __init__(self, name: str = None, id: str = None, description: str = None, version: str = None, service_type: str = 'Indexer'):
        assert name is not None or id is not None, 'Either name or id must be specified.'



class IndalekoServices:
    '''
    This class defines the service model for Indaleko.
    '''

    Schema = IndalekoServicesSchema.get_schema()

    indaleko_services = 'Services'

    service_types = (
        'Indexer',
        'Ingester',
        'SemanticTransducer',
        'ActivityContextGenerator',
        'ActivityDataCollector',
    )

    CollectionDefinition = {
        'schema' : Schema,
        'edge' : False,
        'indices' : {
            'name' : {
                'fields' : ['name'],
                'unique' : True,
                'type' : 'persistent'
            },
        },
    }

    def __init__(self, reset: bool = False) -> None:
        self.db_config = IndalekoDBConfig()
        self.db_config.start()
        self.service_collection = IndalekoCollection('Services',
                                                     self.CollectionDefinition,
                                                     self.db_config,
                                                     reset=reset)


    def create_indaleko_services_collection(self) -> IndalekoCollection:
        """
        This method creates the IndalekoServices collection in the database.
        """
        assert not self.db_config.db.has_collection(self.indaleko_services), \
         f'{self.indaleko_services} collection already exists, cannot create it.'
        self.service_collection = IndalekoCollection(self.db_config.db, self.indaleko_services)
        self.service_collection.add_schema(IndalekoServices.Schema)
        self.service_collection.create_index('name', 'persistent', ['name'], unique=True)
        return self.service_collection

    def lookup_service(self, name: str) -> dict:
        """
        This method is used to lookup a service by name.
        """
        entries = self.service_collection.find_entries(name =  name)
        assert len(entries) < 2, f'Multiple entries found for service {name}, not handle.'
        if len(entries) == 0:
            return None
        else:
            return entries[0]


    def register_service(self,
                         name: str,
                         description: str,
                         version: str,
                         service_type : str = 'Indexer',
                         service_id : str  = None) -> 'IndalekoServices':
        """
        This method registers a service with the given name, description, and
        version in the database.
        """
        assert service_type in IndalekoServices.service_types, f'Invalid service type {service_type} specified.'
        if service_id is None:
            service_id = str(uuid.uuid4())
        new_service = {
            'name': name,
            'description': description,
            'version': version,
            'identifier' : service_id,
            'created' : datetime.datetime.now(datetime.UTC).isoformat(),
            '_key' : service_id,
        }
        self.service_collection.insert(new_service)
        return self.lookup_service(name)

def main():
    """Test the IndalekoServices class."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    args = parser.parse_args()
    services = IndalekoServices(reset=args.reset)
    print(services)
    service = services.lookup_service('test')
    if len(service) == 0:
        print('Service not found, creating it')
        services.register_service('test', 'This is a test service.', '1.0')
    else:
        print(service)


if __name__ == "__main__":
    main()
