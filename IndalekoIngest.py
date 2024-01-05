import os
import uuid
import argparse
from dbsetup import IndalekoDBConfig
from IndalekoServices import IndalekoServices
from IndalekoCollections import *
import logging
import jsonlines
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
            self.log_level = logging.WARNING
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
            self.log_file = self.DefaultLogDir
        if 'output_file' in kwargs:
            self.output_file = kwargs['output_file']
        else:
            self.output_file = self.get_default_outfile_name()
        if 'config_file' in kwargs:
            self.config_file = kwargs['config_file']
        else:
            self.config_file = self.get_default_config_file_name()
        if 'log_level' in kwargs:
            self.log_level = kwargs['log_level']
        else:
            self.log_level = logging.WARNING
        print(self.log_dir)

    def parse_args(self, pre_parser : argparse.ArgumentParser = None) -> argparse.Namespace:
        '''
        Returns an ArgumentParser object that can be used to parse the command
        line arguments for the ingestor.dir
        '''
        self.parser = argparse.ArgumentParser(parents=[pre_parser], add_help=False)
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
            logging_levels = sorted(set([l for l in logging.getLevelNamesMapping()]))

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
        args = self.parser.parse_args()
        logging.basicConfig(
            filename = os.path.join(args.logdir, args.logfile),
            level=self.log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        return args

    def get_default_outfile_name(self : 'IndalekoIngest') -> str:
        return f'indaleko-ingest-output-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.jsonl'

    def get_default_config_file_name(self : 'IndalekoIngest') -> str:
        return 'indaleko-db-config.ini'

    def ingest(self : 'IndalekoIngest') -> None:
        '''
        This method is the main entry point for the ingestor. It will drive the
        ingestion process, with specialization provided by the ingester implementation.
        '''
        assert False, "Not implemented (yet)"
        machine_config = self.get_ingester_machine_config()
        cfg = machine_config.get_config_data()

    def register_service(self, service : dict) -> IndalekoServices:
        pass

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
    args = ingest.parse_args(parser)
    print(args)

if __name__ == "__main__":
    main()

