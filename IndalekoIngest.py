import os
import uuid
import argparse
from IndalekoServices import IndalekoServices
from IndalekoCollections import IndalekoCollections
from IndalekoMachineConfig import IndalekoMachineConfig
import logging
import platform
import datetime

class IndalekoIngest():
    '''
    IndalekoIngest is the generic class that we use for ingesting data from the
    various indexers that we have. Platform specific ingesters are built on top
    of this class to handle platform-specific ingestion.
    '''

    Indexer_UUID_str = None
    Indexer_UUID = None
    MachineConfig_UUID_str = None
    MachineConfig_UUID = None
    Ingester_UUID_str = None
    Ingester_UUID = None

    MachineConfigService = None
    IndexerService = None
    IngesterService = None

    DefaultOutputDir = './data'
    DefaultConfigDir = './config'
    DefaultLogDir = './logs'

    def __init__(self : 'IndalekoIngest', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoIngest class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the ingestor.
        '''
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        assert kwargs is not None, "Configuration object cannot be None"
        if 'Indexer' in kwargs:
            self.Indexer_UUID_str = kwargs['Indexer']
            self.Indexer_UUID = uuid.UUID(self.Indexer_UUID_str)
        if 'MachineConfig' in kwargs:
            self.MachineConfig_UUID_str = kwargs['MachineConfig']
            self.MachineConfig_UUID = uuid.UUID(self.MachineConfig_UUID_str)
        if 'Ingester' in kwargs:
            self.Ingester_UUID_str = kwargs['Ingester']
            self.Ingester_UUID = uuid.UUID(self.Ingester_UUID_str)
        if 'MachineConfigService' in kwargs:
            self.MachineConfigService = kwargs['MachineConfigService']
        if 'IndexerService' in kwargs:
            self.IndexerService = kwargs['IndexerService']
        if 'IngesterService' in kwargs:
            self.IngesterService = kwargs['IngesterService']
        if 'log_level' in kwargs:
            self.log_level = kwargs['log_level']
        else:
            self.log_level = logging.DEBUG
        if 'output_dir' in kwargs:
            self.output_dir = kwargs['output_dir']
        else:
            self.output_dir = self.DefaultOutputDir
        if 'config_dir' in kwargs:
            self.config_dir = kwargs['config_dir']
        else:
            self.config_dir = self.DefaultConfigDir
        if 'log_dir' in kwargs:
            self.log_dir = kwargs['log_dir']
        else:
            self.log_dir = self.DefaultLogDir
        if 'log_file' in kwargs:
            self.log_file = kwargs['log_file']
        else:
            self.log_file = self.get_default_logfile_name()
        if 'output_file' in kwargs:
            self.output_file = kwargs['output_file']
        else:
            self.output_file = self.get_default_outfile_name()
        if 'config_file' in kwargs:
            self.config_file = kwargs['config_file']
        else:
            self.config_file = self.get_default_config_file_name()
        if 'input_file' in kwargs:
            self.input_file = kwargs['input_file']

    def start(self, logfile : str = None, loglevel = logging.DEBUG) -> None:
        '''This will start up the various services required for ingestion.'''
        if logfile is None:
            logfile = self.get_default_logfile_name()
        if logfile is None:
            logging.basicConfig(level=loglevel, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            logging.basicConfig(filename=os.path.join(self.log_dir, logfile),
                                level=loglevel,
                                format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"Starting IndalekoIngest at {self.timestamp}")
        self.indaleko_services = IndalekoServices()
        self.collections = IndalekoCollections()
        self.indaleko_services = IndalekoServices()

    def ingest(self : 'IndalekoIngest') -> None:
        '''
        This method is the main entry point for the ingestor. It will drive the
        ingestion process, with specialization provided by the ingester implementation.
        '''
        assert False, "Not implemented in the base class - needs a specialized class for the platform."


    def parse_args(self, pre_parser : argparse.ArgumentParser = None) -> argparse.Namespace:
        '''
        Returns an ArgumentParser object that can be used to parse the command
        line arguments for the ingestor.dir
        '''
        self.parser = argparse.ArgumentParser(parents=[pre_parser])
        if platform.python_version() < '3.12':
            logging_levels = []
            if hasattr(logging, 'CRITICAL'):
                logging_levels.append('CRITICAL')
            if hasattr(logging, 'ERROR'):
                logging_levels.append('ERROR')
            if hasattr(logging, 'WARNING'):
                logging_levels.append('WARNING')
            if hasattr(logging, 'WARN'):
                logging_levels.append('WARN')
            if hasattr(logging, 'INFO'):
                logging_levels.append('INFO')
            if hasattr(logging, 'DEBUG'):
                logging_levels.append('DEBUG')
            if hasattr(logging, 'NOTSET'):
                logging_levels.append('NOTSET')
            if hasattr(logging, 'FATAL'):
                logging_levels.append('FATAL')
        else:
            logging_levels = sorted(set([level for level in logging.getLevelNamesMapping()]))

        self.parser.add_argument('--outdir', type=str, default=self.output_dir, help='Directory to use for output file')
        self.parser.add_argument('--output', type=str, default=self.output_file,
                            help='Name to use for file into which the fetched metadata is saved.')
        self.parser.add_argument('--confdir', type=str, default=self.config_dir, help='Directory to use for config file')
        self.parser.add_argument('--config', type=str, default=self.config_file,
                            help='Name to use for retrieving the database configuration file.')
        self.parser.add_argument('--loglevel', type=int, default=self.log_level, choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
        self.parser.add_argument('--logdir', type=str, default=self.log_dir, help='Directory to use for log file')
        self.parser.add_argument('--logfile', type=str, default=self.log_file, help='Name of log file.')
        self.parser.add_argument('--input', type=str, default=self.get_default_input_file(), help='Name of input file.')
        args = self.parser.parse_args()
        return args

    def get_default_outfile_name(self : 'IndalekoIngest') -> str:
        return f'indaleko-ingest-output-{self.timestamp}.jsonl'

    def get_default_logfile_name(self : 'IndalekoIngest') -> str:
        return f'indaleko-ingest-log-{self.timestamp}.log'

    def get_default_config_file_name(self : 'IndalekoIngest') -> str:
        return 'indaleko-db-config.ini'

    def get_default_config_dir(self : 'IndalekoIngest') -> str:
        return self.config_dir

    def register_service(self, service : dict) -> IndalekoServices:
        assert service is not None, 'Service cannot be None'
        assert 'name' in service, 'Service must have a name'
        assert 'description' in service, 'Service must have a description'
        assert 'version' in service, 'Service must have a version'
        assert 'identifier' in service, 'Service must have an identifier'
        existing_service = self.lookup_service(service['name'])
        if len(existing_service) > 0:
            # TODO - how do we want to deal with updates?  For now, just
            # assert these are the same
            assert existing_service[0]['version'] == service['version'], f"Version for service {service['name']} does not match."
            assert existing_service[0]['identifier'] == service['identifier'], f"Identifier for service {service['name']} does not match."
        logging.info(f"Registering service {service['name']}")
        return self.indaleko_services.register_service(service['name'], service['description'], service['version'], service['type'], service['identifier'])

    def lookup_service(self, service_name : str) -> list:
        '''
        Given a name, this method will lookup the service in the database.
        If it does not exist an empty list is returned.
        '''
        assert service_name is not None, 'Service name cannot be None'
        service = self.indaleko_services.lookup_service(service_name)
        if service is None:
            return service
        assert 'name' in service, 'Service must have a name'
        assert service['name'] == service_name, f"Service name {service_name} does not match service name {service['name']}"
        assert 'version' in service, 'Service must have a version'
        assert 'identifier' in service, 'Service must have an identifier'
        return service

    def lookup_machine_config(self : 'IndalekoIngest', machine_uuid : str) -> IndalekoMachineConfig:
        '''
        This method will lookup the machine configuration, based upon the
        passed-in UUID.
        '''
        try:
            _ = uuid.UUID(machine_uuid)
        except ValueError:
            assert False, f"Invalid UUID: {machine_uuid}"
        collection = self.collections.get_collection('MachineConfig')
        configs = collection.find_entries(_key = machine_uuid)
        # configs = self.collections.get_collection('MachineConfig').find_entries({'_key' : m_uuid})
        if len(configs) < 1:
            return None
        # there should be only one entry since the key has to be unique
        assert len(configs) == 1, f"Found {len(configs)} machine configs for UUID {machine_uuid} (not expected)"
        self.config_data = configs[0]
        return self


    '''
    Beyond this point are the methods that should be overriden in the derived class.
    '''

    def get_ingester_machine_config(self : 'IndalekoIngest') -> dict:
        '''
        This method returns the machine configuration for the ingester. This
        method should be overridden by the derived class.
        '''
        assert False, "Do not call get_ingester_machine_config() on the base class - override it in the derived class."

    def get_indexer_output_file(self : 'IndalekoIngest') -> None:
        '''
        This method should return the name of the output file that the
        ingester produces. Since this format varies by indexer, this method
        should be overridden by the derived class.
        '''
        assert False, "Do not call get_indexer_output_file() on the base class - override it in the derived class."

    def get_input_file_list(self : 'IndalekoIngest') -> list:
        '''
        This method should return a list of files that could be ingested.
        Since this format varies by indexer, this method should be overridden by
        the derived class..
        '''
        assert False, "Do not call get_input_file_list() on the base class - override it in the derived class."

    def get_default_input_file(self : 'IndalekoIngest') -> str:
        '''
        This method should return the default file that should be ingested.
        Since this format varies by indexer, this method should be overridden by
        the derived class..
        '''
        assert False, "Do not call get_default_input_file() on the base class - override it in the derived class."

def main():
    # Now parse the arguments
    ingest = IndalekoIngest(test=True)
    assert ingest is not None, "Could not create ingester."
    parser = argparse.ArgumentParser(description='Test the IndalekoIngester class.')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    _ = ingest.parse_args(parser)
    logging.info('Testing the machine configuration lookup (using the UUID for my Windows machine.)')
    mcfg = ingest.lookup_machine_config('2e169bb7-0024-4dc1-93dc-18b7d2d28190')
    print(mcfg.config_data)

if __name__ == "__main__":
    main()

