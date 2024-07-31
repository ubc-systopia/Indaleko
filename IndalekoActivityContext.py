'''This is the Indaleko module for managing Activity Context.'''

import argparse
import datetime
from icecream import ic
import logging
import sys
import uuid

from IndalekoActivityContextSchema import IndalekoActivityContextSchema
from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistrationService
from IndalekoSingleton import IndalekoSingleton
from IndalekoDBConfig import IndalekoDBConfig
from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging
from IndalekoCollections import IndalekoCollections

class IndalekoActivityContext(IndalekoSingleton):
    '''This class is used to manage Indaleko Activity Context.'''

    Schema = IndalekoActivityContextSchema().get_json_schema()

    class ActivityContextData:
        '''This defines the format of an activity context record.'''

        activity_context_name = 'ActivityContext'
        activity_context_uuid = '588fcca9-aad5-41c2-b2fd-7588d91cfafd'
        activity_context_source = {
            'Identifier' : activity_context_uuid,
            'Version' : '1.0',
            'Description' : 'Activity Context',
            'Name' : activity_context_name,
        }

        def __init__(self, **kwargs):
            '''
            Initialize the activity context.
            '''
            self.attributes = {}
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.attributes['ContextHandle'] = kwargs.get('ContextHandle', uuid.uuid4().hex)
            self.attributes['SemanticCursors'] = {}
            self.attributes['SemanticCursors']['ContextTimestamp'] = \
                kwargs.get('ContextTimestamp', self.timestamp)
            if 'raw_data' not in kwargs:
                kwargs['raw_data'] = b''
            if 'source' not in kwargs:
                kwargs['source'] = self.activity_context_source
            if 'attributes' not in kwargs:
                kwargs['attributes'] = self.attributes
            super().__init__(**kwargs)

        def to_dict(self) -> dict:
            '''Capture activity context record as a dictionary.'''
            raise NotImplementedError('This method needs to be switched to data model.')
            record = { key : value for key, value in self.attributes.items()}
            record['Record'] = super().to_dict()
            return record


    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoActivityContext class.'''
        if self._initialized:
            return
        # initialize the object
        self._initialized = True
        if 'db_config' in kwargs:
            self.db_config = kwargs['db_config']
        else:
            self.db_config = IndalekoDBConfig()
        self.collection = IndalekoCollections.get_collection(Indaleko.Indaleko_ActivityContext)
        assert self.collection is not None, 'Collection must be pre-defined'

    def get_current_activity_context(self) -> uuid.UUID:
        '''Return a handle to the current activity context.'''
        return uuid.uuid4()

    def write_activity_context_to_database(self) -> bool:
        '''Write the activity context to the database.'''
        ic('write_activity_context_to_database called')
        return False

class IndalekoActivityContextTest:
    '''This class is used to test the IndalekoActivityContext class.'''

    def __init__(self, args : argparse.Namespace):
        '''Create an instance of the IndalekoActivityContextTest class.'''
        self.args = args

    def show_command(self):
        '''Command to show the current activity context.'''
        ic('show_command called')

    def check_command(self):
        '''Check the activity context database connectivity.'''
        ic('check_command called')
        context = IndalekoActivityContext()
        ic(context.get_current_activity_context())

    def test_command(self):
        '''Test the activity context data.'''
        ic('test_command called')
        data = IndalekoActivityContext.ActivityContextData()
        ic(data.to_dict())

def main():
    '''Test the IndalekoActivityContext class.'''
    ic('Testing IndalekoActivityContext')
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()

    parser = argparse.ArgumentParser(description='Test the IndalekoActivityContext class')
    parser.add_argument('--debug',
                        action='store_true',
                        help='Debug flag')
    parser.add_argument('--logdir' ,
                        type=str,
                        default=Indaleko.default_log_dir,
                        help='Log directory')
    parser.add_argument('--log',
                        type=str,
                        default=None,
                        help='Log file name')
    parser.add_argument('--loglevel',
                        type=int,
                        default=logging.DEBUG,
                        choices=IndalekoLogging.get_logging_levels(),
                        help='Log level')
    command_subparsers = parser.add_subparsers(help='Command subparsers', dest='command')
    parser_check = command_subparsers.add_parser('check', help='Check the activity context database connectivity')
    parser_check.set_defaults(func=IndalekoActivityContextTest.check_command)
    parser_show = command_subparsers.add_parser('show', help='Show the current activity context')
    parser_show.set_defaults(func=IndalekoActivityContextTest.show_command)
    parser_test = command_subparsers.add_parser('test', help='Test the activity context data')
    parser_test.set_defaults(func=IndalekoActivityContextTest.test_command)
    parser.set_defaults(func=IndalekoActivityContextTest.check_command)
    args = parser.parse_args()
    if args.debug:
        ic('Testing IndalekoActivityContext')
    if args.log is None:
        args.log = Indaleko.generate_file_name(
            suffix='log',
            service='IndalekoActivtyContext',
            timestamp=timestamp
        )
    indaleko_logging = IndalekoLogging(
        service_name='IndalekoActivtyContext',
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir
    )
    if indaleko_logging is None:
        ic('Failed to initialize logging')
        sys.exit(1)
    logging.info('Starting IndalekoActivityContext test.')
    logging.debug(args)
    test = IndalekoActivityContextTest(args)
    args.func(test)
    logging.info('Ending IndalekoActivityContext test.')
    args = parser.parse_args()
if __name__ == '__main__':
    main()
