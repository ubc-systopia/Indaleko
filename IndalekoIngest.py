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
from Indaleko import Indaleko

class IndalekoIngest():
    '''
    IndalekoIngest is the generic class that we use for ingesting data from the
    various indexers that we have. Platform specific ingesters are built on top
    of this class to handle platform-specific ingestion.
    '''

    default_file_prefix = 'indaleko'
    default_file_suffix = '.jsonl'

    indexer_uuid_str = None
    indexer_uuid = None
    machine_config_uuid_str = None
    machine_config_uuid = None
    ingester_uuid_str = None
    ingester_uuid = None

    machine_config_service = None
    indexer_service = None
    ingester_service = None

    default_output_dir = Indaleko.default_data_dir
    default_config_dir = Indaleko.default_config_dir
    default_log_dir = Indaleko.default_log_dir

    def __init__(self : 'IndalekoIngest', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoIngest class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the ingestor.
        '''
        if 'file_prefix' in kwargs:
            self.file_prefix = kwargs['file_prefix']
        else:
            self.file_prefix = IndalekoIngest.default_file_prefix
        self.file_prefix = self.file_prefix.replace('-', '_')
        if 'file_suffix' in kwargs:
            self.file_suffix = kwargs['file_suffix'].replace('-', '_')
        else:
            self.file_suffix = IndalekoIngest.default_file_suffix
        self.file_suffix = self.file_suffix.replace('-', '_')
        if 'machine_id' in kwargs:
            self.machine_id = kwargs['machine_id']
        if 'timestamp' in kwargs:
            self.timestamp = kwargs['timestamp']
        else:
            self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        if 'platform' in kwargs:
            self.platform = kwargs['platform']
        if 'ingester' in kwargs:
            self.ingester = kwargs['ingester']
        if 'output_dir' in kwargs:
            self.output_dir = kwargs['output_dir']
        else:
            self.output_dir = self.default_output_dir
        if 'input_file' in kwargs:
            self.input_file = kwargs['input_file']
        if 'log_dir' in kwargs:
            self.log_dir = kwargs['log_dir']
        else:
            self.log_dir = self.default_log_dir
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

    def get_default_outfile_name(self : 'IndalekoIngest', target_dir : str = None) -> str:
        """
        This method constructs a default output file name. Should be overridden
        in derived class.
        """
        if hasattr(self, 'platform'):
            ingest_platform = self.platform
        else:
            ingest_platform = 'unknown'
        ingest_platform = ingest_platform.replace('-', '_')
        if hasattr(self, 'ingester'):
            ingester = self.ingester
        else:
            ingester = 'unknown_ingester'
        ingester = ingester.replace('-', '_')
        if hasattr(self, 'machine_id'):
            machine_id = self.machine_id
        else:
            machine_id = 'unknown_machine_id'
        machine_id = machine_id.replace('-', '_')
        if hasattr(self, 'timestamp'):
            timestamp = self.timestamp
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if target_dir is None:
            target_dir = self.output_dir
        return os.path.join(
            target_dir,
            f'{self.file_prefix}-\
              platform={ingest_platform}-\
              ingester={ingester}-\
              machine={machine_id}-\
              timestamp={timestamp}\
              {self.file_suffix}'.replace(' ', ''))

    def get_default_logfile_name(self : 'IndalekoIngest') -> str:
        """
        This method constructs a default log file name. Should be overridden in
        derived class.
        """
        return self.get_default_outfile_name(target_dir=self.log_dir).replace('.jsonl', '.log')


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
    ingester = IndalekoIngest(test=True)
    assert ingester is not None, "Could not create ingester."
    print(ingester.get_default_outfile_name())

if __name__ == "__main__":
    main()
