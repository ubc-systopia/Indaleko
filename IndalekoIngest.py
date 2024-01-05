import os
import uuid


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


    def get_arg_parser(self, pre_parser : argparse.ArgumentParser = None) -> argparse.ArgumentParser:
        '''
        Returns an ArgumentParser object that can be used to parse the command
        line arguments for the ingestor.
        '''
        parser = argparse.ArgumentParser(parents=[pre_parser])
        parser.add_argument('--input', choices=self.get_input_file_list(), default=self.get_default_input_file(),
                            type=str, help = 'Input file to ingest')
        parser.add_argument('--version', action='version', version='%(prog)s 1.0')
        parser.add_argument('--reset', action='store_true', help='Reset the service collection for this ingester')
        return parser

    def get_ingester_machine_config(self : 'IndalekoIngest') -> dict:
        '''
        This method returns the machine configuration for the ingester. This
        method should be overridden by the derived class.
        '''
        assert False, "Do not call get_ingester_machine_config() on the base class - override it in the derived class."


    def ingest(self : 'IndalekoIngest') -> None:
        '''
        This method is the main entry point for the ingestor. It will drive the
        ingestion process, with specialization provided by the ingester implementation.
        '''
        assert False, "Not implemented (yet)"
        machine_config = self.get_ingester_machine_config()
        cfg = machine_config.get_config_data()

