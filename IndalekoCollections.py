import argparse
from IndalekoObject import IndalekoObject
from IndalekoRelationship import IndalekoRelationship
from IndalekoSource import IndalekoSource
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
import logging
import datetime
import os
from IndalekoDBConfig import IndalekoDBConfig
class IndalekoCollectionIndex:

    def __init__(self, collection: 'IndalekoCollection', index_type: str, fields: list, unique=False):
        '''Parameters:
            This class is used to create indices for IndalekoCollection objects.

            collection: this points to the ArangoDB collection object to use for
                        this index.

            index_type: 'persistent' or 'hash'

            fields: list of fields to be indexed

            unique: if True, the index is unique
        '''
        self.collection = collection
        self.fields = fields
        self.unique = unique
        self.index_type = index_type
        self.index = self.collection.add_persistent_index(fields=self.fields, unique=self.unique)

    def find_entries(self, **kwargs):
        return [document for document in self.collection.find(kwargs)]


class IndalekoCollection:

    def __init__(self, name : str, definition : dict, db : IndalekoDBConfig = None, reset : bool = False) -> None:
        self.name = name
        self.definition = definition
        assert isinstance(definition, dict), 'Collection definition must be a dictionary'
        assert 'schema' in definition, 'Collection must have a schema'
        assert 'edge' in definition, 'Collection must have an edge flag'
        assert 'indices' in definition, 'Collection must have indices'
        assert db is None or type(db) is IndalekoDBConfig, 'db must be None or an IndalekoDBConfig object'
        if db is None:
            self.db_config = IndalekoDBConfig()
            self.db_config.start()
        else:
            self.db_config = db
        assert db is not None, 'db must be a valid IndalekoDBConfig object'
        self.collection_name = self.name
        self.indices = {}
        self.create_collection(self.collection_name, definition, reset=reset)

    def create_collection(self, name : str, config : dict, reset : bool = False) -> 'IndalekoCollection':
        if self.db_config.db.has_collection(name) and not reset:
            self.collection = self.db_config.db.collection(name)
        else:
            self.collection = self.db_config.db.create_collection(name, edge=config['edge'])
            if 'schema' in config:
                self.collection.configure(schema=config['schema'])
            if 'indices' in config:
                for index in config['indices']:
                    self.create_index(index, config['indices'][index]['type'], config['indices'][index]['fields'], config['indices'][index]['unique'])
        return self.collection

    def create_index(self, name: str, index_type: str, fields: list, unique: bool) -> 'IndalekoCollection':
        self.indices[name] = IndalekoCollectionIndex(self.collection, index_type, fields, unique)
        return self

    def find_entries(self, **kwargs):
        return [document for document in self.collection.find(kwargs)]

    def insert(self, document: dict) -> 'IndalekoCollection':
        return self.collection.insert(document)

    def add_schema(self, schema: dict) -> 'IndalekoCollection':
        self.collection.configure(schema=schema)
        return self


class IndalekoCollections:
    '''
    This class is used to manage the collections in the Indaleko database.
    '''
    Indaleko_Collections = {
            'Objects': {
                'schema' : IndalekoObject.Schema,
                'edge' : False,
                'indices' : {
                    'URI' : {
                        'fields' : ['URI'],
                        'unique' : True,
                        'type' : 'persistent'
                    },
                    'file identity' : {
                        'fields' : ['ObjectIdentifier'],
                        'unique' : True,
                        'type' : 'persistent'
                    },
                    'local identity' : { # Question: should this be combined with other info to allow uniqueness?
                        'fields' : ['LocalIdentifier'],
                        'unique' : False,
                        'type' : 'persistent'
                    },
                },
            },
            'Relationships' : {
                'schema' : IndalekoRelationship.Schema,
                'edge' : True,
                'indices' : {
                    'relationship' : {
                        'fields' : ['relationship'],
                        'unique' : False,
                        'type' : 'persistent'
                    },
                    'vertex1' : {
                        'fields' : ['object1'],
                        'unique' : False,
                        'type' : 'persistent'
                    },
                    'vertex2' : {
                        'fields' : ['object2'],
                        'unique' : False,
                        'type' : 'persistent'
                    },
                    'edge' : {
                        'fields' : ['object1', 'object2'],
                        'unique' : False,
                        'type' : 'persistent'
                    },
                }
            },
            'Sources' : {
                'schema' : IndalekoSource.Schema,
                'edge' : False,
                'indices' : {
                    'identifier' : {
                        'fields' : ['identifier'],
                        'unique' : False,
                        'type' : 'persistent'
                    },
                },
            },
            'MachineConfig' : {
                'schema' : IndalekoMachineConfigSchema,
                'edge' : False,
                'indices' : { },
            }
        }

    def __init__(self, db_config: IndalekoDBConfig = None, reset: bool = False) -> None:
        if db_config is None:
            self.db_config = IndalekoDBConfig()
        else:
            self.db_config = db_config
        self.db_config.start()
        self.collections = {}
        for name in self.Indaleko_Collections:
            self.collections[name] = IndalekoCollection(name, self.Indaleko_Collections[name], self.db_config, reset)

    def get_collection(self, name: str) -> IndalekoCollection:
        assert name in self.collections, f'Collection {name} does not exist.'
        return self.collections[name]


def main():
    starttime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    parser = argparse.ArgumentParser()
    logfile = f'indalekocollections-test-{starttime}.log'
    parser = argparse.ArgumentParser(description='Set up and create the collections for the Indaleko database.')
    parser.add_argument('--reset', '-r', help='Reset the database', action='store_true')
    parser.add_argument('--config', '-c', help='Path to the config file', default='./config/indaleko-db-config.ini')
    parser.add_argument('--log', '-l', help='Log file to use', default=logfile)
    parser.add_argument('--logdir', help='Log directory to use', default='./logs')
    args = parser.parse_args()
    logging.basicConfig(filename=os.path.join(args.logdir, args.log), level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f'Begin Indaleko Collections test at {starttime}')
    collections = IndalekoCollections()
    endtime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logging.info(f'End Indaleko Collections test at {endtime}')
    assert collections is not None, 'Collections object should not be None'



if __name__ == "__main__":
    main()
