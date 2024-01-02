import argparse
from arango import ArangoClient
from indaleko import IndalekoObject, IndalekoRelationship, IndalekoSource
from dbsetup import IndalekoDBConfig
import logging
import datetime
import os

class IndalekoIndex:

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

    def __init__(self, db, name: str, edge: bool = False, reset: bool = False) -> None:
        '''Parameters:
            db: ArangoDB database object (with appropriate credentials)
            name: name of the collection
            edge: if True, the collection is an edge collection
            reset: if True, the collection is deleted and recreated
        '''
        self.db = db
        self.name = name
        self.edge = edge
        if reset and db.has_collection(name):
            db.delete_collection(name)
        if not db.has_collection(name):
            db.create_collection(name, edge=edge)
        self.collection = db.collection(self.name)
        self.indices = {}

    def create_index(self, name: str, index_type: str, fields: list, unique: bool) -> 'IndalekoCollection':
        self.indices[name] = IndalekoIndex(self.collection, index_type, fields, unique)
        return self

    def find_entries(self, **kwargs):
        return [document for document in self.collection.find(kwargs)]

    def insert(self, document: dict) -> 'IndalekoCollection':
        return self.collection.insert(document)

    def add_schema(self, schema: dict) -> 'IndalekoCollection':
        self.collection.configure(schema=schema)
        return self

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
                'local identity' : {
                    'fields' : ['LocalIdentifier'],
                    'unique' : True,
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
    }



def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    starttime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logfile = f'indalekocollections-test-{starttime}.log'
    parser = argparse.ArgumentParser(description='Set up and start the database(s) for Indaleko')
    parser.add_argument('--config', '-c', help='Path to the config file', default='./config/indaleko-db-config.ini')
    parser.add_argument('--log', '-l', help='Log file to use', default=logfile)
    parser.add_argument('--logdir', help='Log directory to use', default='./logs')
    args = parser.parse_args()
    logging.basicConfig(filename=os.path.join(args.logdir, args.log), level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f'Begin Indaleko Collections test at {starttime}')
    config = IndalekoDBConfig()
    config.start()
    collections = config.db.collections()
    logging.debug(f'Collections are {collections}')
    collections = {}
    for collection in Indaleko_Collections:
        c = config.db.collection(collection)
        if c is None:
            logging.warning(f'Collection {collection} not found in database!')
        else:
            collections[collection] = c
            logging.info(f'Found collection: {collection}')
    endtime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logging.info(f'End Indaleko Collections test at {endtime}')




if __name__ == "__main__":
    main()
