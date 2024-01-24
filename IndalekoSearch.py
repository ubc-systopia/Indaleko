'''
This module is used to perform specific searches in the Indaleko database.
'''
import argparse
import logging
import platform
import datetime
import os
import arango

from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig

class IndalekoSearch():
    '''
    This is a class object for performing specific searches in the Indaleko database.
    '''

    def __init__(self, **kwargs):
        '''Initialize a new instance of the IndalekoSearch class object.'''
        if 'db_config' in kwargs:
            self.db_config = kwargs['db_config']
        else:
            self.db_config = IndalekoDBConfig()
        self.view_name = None
        self.view_properties = None
        self.db_config.start()
        logging.info('IndalekoSearch initialized, Database connection instantiated.')

    def create_view(self, **kwargs):
        '''Create a view for searching the Indaleko database.'''
        if 'timestamp' in kwargs:
            timestamp = kwargs['timestamp']
            if not Indaleko.validate_iso_timestamp(timestamp):
                raise ValueError('Invalid timestamp: {}'.format(timestamp))
        else:
            timestamp = Indaleko.generate_iso_timestamp_for_file()
        # view names are limited to alpha numerics and _ and - are allowed
        # timestamps have : and +
        if 'view_name' in kwargs:
            logging.info('Reusing existing view %s', kwargs['view_name'])
            self.view_name = kwargs['view_name']
        else:
            self.view_name = 'search_{}'.format(timestamp)
            self.view_name = self.view_name.replace(':', '_').replace('+', '_').replace('.', '_')
            logging.info('Creating new view %s', self.view_name)
            result = self.db_config.db.create_arangosearch_view(
                name=self.view_name,
                properties=self.view_properties
            )
            print(result)
        if 'properties' not in kwargs:
            raise ValueError('No properties specified for view.')
        else:
            self.view_properties = kwargs['properties']
        logging.debug('Creating view %s with properties %s', self.view_name, self.view_properties)

    def delete_view(self) -> None:
        if self.view_name is not None:
            self.db_config.db.delete_arangosearch_view(
                name=self.view_name
            )
            self.view_name = None
            self.view_properties = None

    def search_by_name(self, name : str):
        if self.view_name is None:
            raise ValueError('No existing view to use.')
        query=f"FOR doc in {self.view_name} SEARCH ANALYZER(Objects.Record.Attributes.Name == @fileName, 'text_en') RETURN doc"
        bind_vars={'fileName': name}
        logging.debug('Executing query: %s, with bind_vars %s', query, bind_vars)
        result = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
        return result

    def create_oid_view(self) -> None:
        self.db_config.db.create_arangosearch_view(
            name='wam_oid_view',
            properties={
                'links' : {
                    'Objects' : {
                        'includeAllFields' : False,
                        'fields' : {
                            'ObjectIdentifier' : {
                                'analyzers' : ['identity'],
                            },
                        }
                    }
                }
            })

    def does_oid_view_exist(self) -> bool:
        existing_views = self.db_config.db.views()
        return any(view['name'] == 'wam_oid_view' for view in existing_views)

    def search_by_oid(self, oid : str) -> None:
        if not Indaleko.validate_uuid_string(oid):
            raise ValueError('Invalid OID: {}'.format(oid))
        if not self.does_oid_view_exist():
            self.create_oid_view()
        query=f"FOR doc in wam_oid_view SEARCH ANALYZER(Objects.ObjectIdentifier == @oid, 'identity') RETURN doc"
        bind_vars={'oid': oid}
        logging.debug('Executing query: %s, with bind_vars %s', query, bind_vars)
        result = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
        return result

def main() -> None:
    '''Main function for the IndalekoSearch module.'''
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_name = os.path.join(
        Indaleko.default_log_dir,
        Indaleko.generate_file_name(
            suffix='log',
            platform=platform.system(),
            service='IndalekoSearch',
            timestamp=timestamp
        )
    )
    logging.basicConfig(filename=log_name, level=logging.DEBUG)
    logging.debug('Starting IndalekoSearch')
    logging.debug(f'Logging to {log_name}')
    parser = argparse.ArgumentParser(description='Search the Indaleko database.')
    parser.add_argument('-l', '--limit', default=10, type=int, help='Limit the number of results.')
    subparsers = parser.add_subparsers(dest='command', required=True)
    parser_by_name = subparsers.add_parser('name', help='Search by name.')
    parser_by_name.add_argument('name', type=str, help='Name to search for.')
    parser_by_name.add_argument('-c', '--case-sensitive', action='store_true', help='Search case sensitively.')
    parser_by_name.add_argument('-r', '--regex', action='store_true', help='Search using regular expressions.')
    parser_by_date = subparsers.add_parser('date', help='Search by date.')
    parser_by_date.add_argument('date', type=str, help='Date to search for.')
    parser_by_oid = subparsers.add_parser('oid', help='Search by OID.')
    parser_by_oid.add_argument('oid', type=str, default='7376f876-3e2b-404b-9a70-338db6152523', help='OID to search for.')
    args = parser.parse_args()
    print(args)
    indaleko_search = IndalekoSearch()
    print('Search object created')
    if args.command == 'name':
        print('Searching by name')
        results = indaleko_search.search_by_name(args.name)
        print('Search results:')
        for result in results:
            print(result)
    elif args.command == 'date':
        print('Searching by date')
        assert False, 'Not implemented yet'
    elif args.command == 'oid':
        print('Searching by OID')
        results = indaleko_search.search_by_oid(args.oid)
        print('Search results:')
        for result in results:
            print(result)
    logging.debug('Ending IndalekoSearch')

if __name__ == '__main__':
    main()
