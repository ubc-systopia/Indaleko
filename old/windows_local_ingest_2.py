'''This module implements the Windows local ingest process.  This is a test file.'''
from IndalekoIngest import IndalekoIngest
import argparse
from IndalekoIngest import IndalekoIngest
from windows_local_index import IndalekoWindowsLocalIndexer, IndalekoWindowsMachineConfig
import logging
import datetime
from IndalekoIndex import IndalekoIndex
from IndalekoWindowsMachineConfig import IndalekoWindowsMachineConfig

class IndalekoWindowsLocalIngest(IndalekoIngest):
    '''This is the specialization of the Indaleko ingester for Windows.'''

    WindowsMachineConfig_UUID = '3360a328-a6e9-41d7-8168-45518f85d73e'

    WindowsMachineConfigService = {
        'name': 'WindowsMachineConfig',
        'description': 'This service provides the configuration information for a Windows machine.',
        'version': '1.0',
        'identifier': WindowsMachineConfig_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Indexer',
    }

    WindowsLocalIndexer_UUID = '31315f6b-add4-4352-a1d5-f826d7d2a47c'

    WindowsLocalIndexerService = {
        'name': 'WindowsLocalIndexer',
        'description': 'This service indexes the local filesystems of a Windows machine.',
        'version': '1.0',
        'identifier': WindowsLocalIndexer_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Indexer',
    }

    WindowsLocalIngester_UUID = '429f1f3c-7a21-463f-b7aa-cd731bb202b1'

    WindowsLocalIngesterService = {
        'name': WindowsLocalIngester_UUID,
        'description': 'This service ingests captured index info from the local filesystems of a Windows machine.',
        'version': '1.0',
        'identifier': WindowsLocalIngester_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Ingester',
    }

    WindowsLocalDataFilePrefix = 'windows-local-ingest'
    WindowsLocalIngestLogPrefix = 'windows-local-ingest-log'

    def __init__(self : 'IndalekoWindowsLocalIngest', **kwargs):
        self.timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H%M%S")
        default_args = {
            'Indexer' : IndalekoWindowsLocalIngest.WindowsLocalIndexer_UUID,
            'MachineConfig' : IndalekoWindowsLocalIngest.WindowsMachineConfig_UUID,
            'Ingester' : IndalekoWindowsLocalIngest.WindowsLocalIngester_UUID,
            'MachineConfigService' : IndalekoWindowsLocalIngest.WindowsMachineConfigService,
            'IndexerService' : IndalekoWindowsLocalIngest.WindowsLocalIndexerService,
            'IngesterService' : IndalekoWindowsLocalIngest.WindowsLocalIngesterService,
            'log_level' : logging.DEBUG,
            'output_dir' : IndalekoWindowsLocalIngest.default_output_dir,
            'config_dir' : IndalekoWindowsLocalIngest.default_config_dir,
            'log_dir' : IndalekoWindowsLocalIngest.default_log_dir,
            'output_file_prefix' : IndalekoWindowsLocalIngest.WindowsLocalDataFilePrefix,
            'log_file_prefix' : IndalekoWindowsLocalIngest,
        }
        for key in kwargs:
            default_args[key] = kwargs[key]
        super().__init__(**default_args)


    @staticmethod
    def find_data_files(data_dir : str) -> list:
        '''This function finds the files to ingest:
            data_dir: path to the data directory
        '''
        assert data_dir is not None, 'data_dir must be a valid path'
        assert os.path.isdir(data_dir), 'data_dir must be a valid directory'
        df = [x for x in os.listdir(data_dir)
              if x.startswith(IndalekoWindowsLocalIndexer.WindowsLocalIndexFilePrefix)
              and x.endswith('.json')]
        return df

    @staticmethod
    def find_config_files(config_dir : str) -> list:
        '''This function finds the files to ingest:
            config_dir: path to the config directory
        '''
        assert config_dir is not None, 'config_dir must be a valid path'
        assert os.path.isdir(config_dir), 'config_dir must be a valid directory'
        return [x for x in os.listdir(config_dir)
                if x.startswith(IndalekoWindowsMachineConfig.windows_machine_config_file_prefix)
                and x.endswith('.json')]

    def set_default_input_file(self : 'IndalekoWindowsLocalIngest', filename : str) -> None:
        assert filename is not None, 'filename must be a valid string'
        self.default_input_file = os.path.join(self.output_dir, filename)
        assert os.path.isfile(self.default_input_file), 'default_input_file must be a valid file'

    def set_default_config_file(self : 'IndalekoWindowsLocalIngest', filename : str) -> None:
        assert filename is not None, 'filename must be a valid string'
        self.default_config_file = os.path.join(self.config_dir, filename)
        assert os.path.isfile(self.default_config_file), 'default_config_file must be a valid file'

    def get_default_input_file(self: 'IndalekoWindowsLocalIngest') -> str:
        return self.default_input_file

    def get_default_config_file(self: 'IndalekoWindowsLocalIngest') -> str:
        return self.default_config_file

    def get_default_logfile_name(self : 'IndalekoWindowsLocalIngest') -> str:
        return f'{self.WindowsLocalIngestLogPrefix}-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.log'

    def lookup_machine_config(self : 'IndalekoWindowsLocalIngest', machine_id : str) -> dict:
        '''
        This method uses the machine_id to see if the machine configuration
        is stored in the database.  If it is, it loads that and returns it to
        the caller.
        '''
        if hasattr(self, 'machine_config'):
            print('returning cached value of machine_config')
            return self.machine_config
        self.machine_config = IndalekoWindowsMachineConfig()
        print('returning newly loaded value of machine_config')
        return self.machine_config

    def get_machine_config(self : 'IndalekoWindowsLocalIngest',
                           machine_id : str = None,
                           config_dir : str = None,
                           config_file : str = None) -> IndalekoWindowsMachineConfig:
        '''
        This method loads th current machine configuration.  If the machine_id
        is provided, it will load the configuration from the database.  If not,
        it will find the most recent configuration file in the config_dir and
        load that.
        '''
        if not hasattr(self, 'machine_config'):
            if machine_id is not None:
                self.machine_config = IndalekoWindowsMachineConfig.load_config_from_db(machine_id)
            else:
                self.machine_config = IndalekoWindowsMachineConfig.load_config_from_file(config_dir = config_dir,
                                                                                         config_file = config_file)
                self.machine_config.write_config_to_db()
        return self.machine_config

    def ingest(self : 'IndalekoWindowsLocalIngest') -> None:
        logging.debug(f'Ingesting')
        logging.info(f'Ingesting file {self.default_input_file}, Step 1: get machine config')
        # Steps for ingestion:
        # 1. Make sure the machine config is in the database.  If not, capture
        #    it.  If it is, we just use it.  Might want to deal with checking to
        #    see if it has changed and, if so, capture it again. For now, we
        #    just capture it on first use.
        # 2. Make sure we have captured any local storage state (e.g., "volume"
        #    state) since this is important to have later.  Storage has this
        #    tendency to "move around" on device(s), such as with removable
        #    storage or even partial dismantling of an old computer system.
        # 3. Read the index file specified. This is where ingestion really
        #    starts:
        #    a. Process the data, splitting it into directory and file
        #    information.  I do this to minimize ordering dependencies between
        #    the two.  For directories, I can assert they never have two
        #    parents.  This restriction is _not_ valid for files.
        #    b. Normalize metadata into the common format. For Windows, this
        #    includes both the UNIX and Windows file attributes, while for
        #    non-Windows systems this is typically just the POSIX file
        #    attributes.  This may need to be generalized for other storage
        #    systems, where they have "rich" metadata.
        #    c. Construct the "relationships" between the various objects of the
        #    system.  This includes:
        #      (i) parent-child relationships between directories and files
        #      (both directions.)
        #      (ii) "volume" relationships between directories and files and
        #      the storage volumes they are on.
        #      (iii) capture the machine on which the given objects are located.
        #      (iv) associate the captured data with the source of the capture.
        #   Note that this list is likely to grow in the future.  To allow
        #   supporting storage silo specific features, this should have a
        #   generic base layer implementation and that can then be augmented by
        #   the platform specific ingester.
        # 4. Write the data for each _type_ of object into a set of jsonl files.
        #    We chose the jsonl format because it does not require loading and
        #    validating the entire file is json.  Rather it processes it one
        #    line at a time.  For debugging purposes, I also emit a json version
        #    of the data.
        # Note that the output of this process is just a set of files that still
        # need to be bulk uploaded to the database.  This _could_ be done via
        # the script interface.
        machine_config = self.get_machine_config()

    def start(self : 'IndalekoWindowsLocalIngest', args : argparse.Namespace) -> None:
        super().start(self.get_default_logfile_name(), args.loglevel)
        logging.debug(f'Starting Windows local ingest at {datetime.datetime.now(datetime.UTC).isoformat()}')
        logging.info(f'Ingesting file {args.input}')

def main():
    ingest_args = {
        'Indexer' : IndalekoWindowsLocalIngest.WindowsLocalIndexer_UUID,
        'MachineConfig' : IndalekoWindowsLocalIngest.WindowsMachineConfig_UUID,
        'Ingester' : IndalekoWindowsLocalIngest.WindowsLocalIngester_UUID,
        'MachineConfigService' : IndalekoWindowsLocalIngest.WindowsMachineConfigService,
        'IndexerService' : IndalekoWindowsLocalIngest.WindowsLocalIndexerService,
        'IngesterService' : IndalekoWindowsLocalIngest.WindowsLocalIngesterService,
        'log_level' : logging.DEBUG,
        'output_dir' : IndalekoWindowsLocalIngest.default_output_dir,
        'config_dir' : IndalekoWindowsLocalIngest.default_config_dir,
        'log_dir' : IndalekoWindowsLocalIngest.default_log_dir,
        'output_file_prefix' : IndalekoWindowsLocalIngest.WindowsLocalDataFilePrefix,
        'log_file_prefix' : IndalekoWindowsLocalIngest,
    }
    ingester = IndalekoWindowsLocalIngest(**ingest_args)


    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--data_dir', '-d',
                             help='Path to the data directory',
                             default=IndalekoIndex.default_data_dir)
    pre_parser.add_argument('--config_dir', '-c',
                            help='Path to the config directory',
                            default=IndalekoIndex.default_config_dir)
    # pre_parser.add_argument('--logdir', type=str, default=IndalekoIngest.DefaultLogDir, help='Directory to use for log file')
    # pre_parser.add_argument('--logfile', type=str, default=WindowsIngest.WindowsLocalIngestLogPrefix, help='Name of log file.')
    # pre_parser.add_argument('--log_level', '-l')
    pre_args, _ = pre_parser.parse_known_args()
    # logging.debug(f'first pass parser arguments are {pre_args}')

    # Step 2: find the possible data file(s)
    data_files = IndalekoWindowsLocalIngest.find_data_files(pre_args.data_dir)
    config_files = IndalekoWindowsLocalIngest.find_config_files(pre_args.config_dir)

    # Step 3: pick default files
    assert len(data_files) > 0, 'No data files found.'
    assert len(config_files) > 0, 'No config files found.'
    default_data_file = data_files[-1] # might want to date/time sort these or even iterate
    default_config_file = config_files[-1] # might want to date/time sort these or even iterate

    # Step 4: call the base ingester so it can finish parsing stuff.
    ingester.set_default_input_file(default_data_file)
    ingester.set_default_config_file(default_config_file)
    args = ingester.parse_args(pre_parser=pre_parser)
    ingester.start(args)
    logging.warning(f'Note the windows local ingester is currently NOT operational.')
    ingester.ingest()
    logging.info(f'Done with ingest at {datetime.datetime.now(datetime.UTC).isoformat()}')

if __name__ == "__main__":
    main()
