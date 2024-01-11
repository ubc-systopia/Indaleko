"""
This is the generic class for an Indaleko Ingester.

An ingester takes information about some (or all) of the data that is stored in
various storage repositories available to this machine.  It processes the output
from indexers and then generates additional metadata to associate with the
storage object (s) in the database.

Examples of ingesters include:

* A file system specific metadata normalizer, which takes indexing information
  collected about one or more files and then converts that into a normalized
  form to be stored in the database. This includes common metadata such as
  length, label (the "name" of the file), timestamps, and so on.

* A semantic metadata generator, which takes the input from the indexer and then
  performs operations on one or more files described by the indexer to extract
  or compute metadata based upon the content of the file.  For example, this
  might include a "bag of words" from a text file, EXIF data from a JPEG
  file, or even commonly used checksums (e.g., MD5, SHA1, SHA256, etc.) that are
  computed from the file's contents.

* Environmental metadata generators, which take information about the
  environment in which the file is stored, such as the volume on which it is
  stored, additional non-standard metadata features that might be available,
  etc.

"""

import logging
import platform
import datetime
import os
import uuid
import argparse
from IndalekoServices import IndalekoServices
from IndalekoCollections import IndalekoCollections
from IndalekoMachineConfig import IndalekoMachineConfig

class IndalekoIngest():
    '''
    IndalekoIngest is the generic class that we use for ingesting data from the
    various indexers that we have. Platform specific ingesters are built on top
    of this class to handle platform-specific ingestion.
    '''

    indexer_uuid_str = None
    indexer_uuid = None
    machine_config_uuid_str = None
    machine_config_uuid = None
    ingester_uuid_str = None
    ingester_uuid = None

    machine_config_service = None
    indexer_service = None
    ingester_service = None

    default_output_dir = './data'
    default_config_dir = './config'
    default_log_dir = './logs'

    def __init__(self : 'IndalekoIngest', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoIngest class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the ingestor.
        '''
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        assert kwargs is not None, "Configuration object cannot be None"
        if 'test' in kwargs:
            self.test = kwargs['test']
        else:
            self.test = False
        if 'Indexer' in kwargs:
            self.indexer_uuid_str = kwargs['Indexer']
            self.indexer_uuid = uuid.UUID(self.indexer_uuid_str)
        if 'MachineConfig' in kwargs:
            self.machine_config_uuid_str = kwargs['MachineConfig']
            self.machine_config_uuid = uuid.UUID(self.machine_config_uuid_str)
        if 'Ingester' in kwargs:
            self.ingester_uuid_str = kwargs['Ingester']
            self.ingester_uuid = uuid.UUID(self.ingester_uuid_str)
        if 'MachineConfigService' in kwargs:
            self.machine_config_service = kwargs['MachineConfigService']
        if 'IndexerService' in kwargs:
            self.indexer_service = kwargs['IndexerService']
        if 'IngesterService' in kwargs:
            self.ingester_service = kwargs['IngesterService']
        if 'log_level' in kwargs:
            self.log_level = kwargs['log_level']
        else:
            self.log_level = logging.DEBUG
        if 'output_dir' in kwargs:
            self.output_dir = kwargs['output_dir']
        else:
            self.output_dir = self.default_output_dir
        if 'config_dir' in kwargs:
            self.config_dir = kwargs['config_dir']
        else:
            self.config_dir = self.default_config_dir
        if 'log_dir' in kwargs:
            self.log_dir = kwargs['log_dir']
        else:
            self.log_dir = self.default_log_dir
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
        self.indaleko_services = None
        self.collections = None
        self.indaleko_services = None
        self.parser = None
        self.config_data = None

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
        logging.info("Starting IndalekoIngest at %s", self.timestamp)
        self.indaleko_services = IndalekoServices()
        self.collections = IndalekoCollections()
        self.indaleko_services = IndalekoServices()


    def parse_args(self, pre_parser : argparse.ArgumentParser = None) -> argparse.Namespace:
        '''
        Returns an ArgumentParser object that can be used to parse the command
        line arguments for the ingester.
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

        self.parser.add_argument('--outdir',
                                 type=str,
                                 default=self.output_dir,
                                 help='Directory to use for output file')
        self.parser.add_argument('--output',
                                 type=str,
                                 default=self.output_file,
                                 help='Name to use for file into which the fetched metadata is saved.')
        self.parser.add_argument('--confdir',
                                 type=str,
                                 default=self.config_dir,
                                 help='Directory to use for config file')
        self.parser.add_argument('--config',
                                 type=str,
                                 default=self.config_file,
                                 help='Name to use for retrieving the database configuration file.')
        self.parser.add_argument('--loglevel',
                                 type=int,
                                 default=self.log_level,
                                 choices=logging_levels,
                                 help='Logging level to use (lower number = more logging)')
        self.parser.add_argument('--logdir',
                                 type=str,
                                 default=self.log_dir,
                                 help='Directory to use for log file')
        self.parser.add_argument('--logfile',
                                 type=str,
                                 default=self.log_file,
                                 help='Name of log file.')
        self.parser.add_argument('--input',
                                 type=str,
                                 default=self.get_default_input_file(),
                                 help='Name of input file.')
        args = self.parser.parse_args()
        return args

    def get_default_outfile_name(self : 'IndalekoIngest') -> str:
        """
        This method constructs a default output file name. Should be overridden
        in derived class.
        """
        return f'indaleko-ingest-output-{self.timestamp}.jsonl'

    def get_default_logfile_name(self : 'IndalekoIngest') -> str:
        """
        This method constructs a default log file name. Should be overridden in
        derived class.
        """
        return f'indaleko-ingest-log-{self.timestamp}.log'

    def get_default_config_file_name(self : 'IndalekoIngest') -> str:
        """
        This method constructs a default config file name. Should be overridden
        in derived class.
        """
        return 'indaleko-db-config.ini'

    def get_default_config_dir(self : 'IndalekoIngest') -> str:
        """
        This method returns the default configuration directory. Could be
        overridden in derived class.
        """
        return self.config_dir

    def register_service(self, service : dict) -> IndalekoServices:
        """Used to register a service provider in the database."""
        assert service is not None, 'Service cannot be None'
        assert 'name' in service, 'Service must have a name'
        assert 'description' in service, 'Service must have a description'
        assert 'version' in service, 'Service must have a version'
        assert 'identifier' in service, 'Service must have an identifier'
        existing_service = self.lookup_service(service['name'])
        if len(existing_service) > 0:
            # How do we want to deal with updates?  For now, just
            # assert these are the same
            assert existing_service[0]['version'] == service['version'], \
                f"Version for service {service['name']} does not match."
            assert existing_service[0]['identifier'] == service['identifier'], \
            f"Identifier for service {service['name']} does not match."
        logging.info("Registering service %s", service['name'])
        return self.indaleko_services.register_service(service['name'],
                                                       service['description'],
                                                       service['version'],
                                                       service['type'],
                                                       service['identifier'])

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
        assert service['name'] == service_name, \
            f"Service name {service_name} does not match service name {service['name']}"
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
        assert len(configs) == 1, \
            f"Found {len(configs)} machine configs for UUID {machine_uuid} (not expected)"
        self.config_data = configs[0]
        return self


    def get_ingester_machine_config(self : 'IndalekoIngest') -> dict:
        """
        This method returns the machine configuration for the ingester. This
        method should be overridden by the derived class.
        """
        raise AssertionError("Do not call get_ingester_machine_config() on the base class \
                             - override it in the derived class.")

    def get_indexer_output_file(self : 'IndalekoIngest') -> None:
        """
        This method should return the name of the output file that the
        ingester produces. Since this format varies by indexer, this method
        should be overridden by the derived class.
        """
        raise AssertionError("Do not call get_indexer_output_file() on the base class \
                                - override it in the derived class.")

    def get_input_file_list(self : 'IndalekoIngest') -> list:
        '''
        This method should return a list of files that could be ingested.
        Since this format varies by indexer, this method should be overridden by
        the derived class..
        '''
        raise AssertionError("Do not call get_input_file_list() on the base class \
                                - override it in the derived class.")

    def get_default_input_file(self : 'IndalekoIngest') -> str:
        '''
        This method should return the default file that should be ingested.
        Since this format varies by indexer, this method should be overridden by
        the derived class..
        '''
        raise AssertionError("Do not call get_default_input_file() on the base class \
                                - override it in the derived class.")

def main():
    """Test code for IndalekoIngest.py"""
    # Now parse the arguments
    ingest = IndalekoIngest(test=True)
    assert ingest is not None, "Could not create ingester."

if __name__ == "__main__":
    main()
