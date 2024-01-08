from IndalekoIngest import *
import argparse
from IndalekoIngest import IndalekoIngest
from windows_local_index import IndalekoWindowsLocalIndexer, IndalekoWindowsMachineConfig
import logging
import datetime
from IndalekoIndex import IndalekoIndex

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

    def __init__(self, **kwargs):
        self.timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H%M%S")
        default_args = {
            'Indexer' : IndalekoWindowsLocalIngest.WindowsLocalIndexer_UUID,
            'MachineConfig' : IndalekoWindowsLocalIngest.WindowsMachineConfig_UUID,
            'Ingester' : IndalekoWindowsLocalIngest.WindowsLocalIngester_UUID,
            'MachineConfigService' : IndalekoWindowsLocalIngest.WindowsMachineConfigService,
            'IndexerService' : IndalekoWindowsLocalIngest.WindowsLocalIndexerService,
            'IngesterService' : IndalekoWindowsLocalIngest.WindowsLocalIngesterService,
            'log_level' : logging.DEBUG,
            'output_dir' : IndalekoWindowsLocalIngest.DefaultOutputDir,
            'config_dir' : IndalekoWindowsLocalIngest.DefaultConfigDir,
            'log_dir' : IndalekoWindowsLocalIngest.DefaultLogDir,
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
                if x.startswith(IndalekoWindowsMachineConfig.WindowsMachineConfigFilePrefix)
                and x.endswith('.json')]

    def set_default_input_file(self, filename : str) -> None:
        assert filename is not None, 'filename must be a valid string'
        self.default_input_file = os.path.join(self.output_dir, filename)
        assert os.path.isfile(self.default_input_file), 'default_input_file must be a valid file'

    def set_default_config_file(self, filename : str) -> None:
        assert filename is not None, 'filename must be a valid string'
        self.default_config_file = os.path.join(self.config_dir, filename)
        assert os.path.isfile(self.default_config_file), 'default_config_file must be a valid file'

    def get_default_input_file(self: IndalekoIngest) -> str:
        return self.default_input_file

    def get_default_config_file(self: IndalekoIngest) -> str:
        return self.default_config_file

    def get_default_logfile_name(self : 'IndalekoIngest') -> str:
        return f'{self.WindowsLocalIngestLogPrefix}-{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.log'


def main():
    ingest_args = {
        'Indexer' : IndalekoWindowsLocalIngest.WindowsLocalIndexer_UUID,
        'MachineConfig' : IndalekoWindowsLocalIngest.WindowsMachineConfig_UUID,
        'Ingester' : IndalekoWindowsLocalIngest.WindowsLocalIngester_UUID,
        'MachineConfigService' : IndalekoWindowsLocalIngest.WindowsMachineConfigService,
        'IndexerService' : IndalekoWindowsLocalIngest.WindowsLocalIndexerService,
        'IngesterService' : IndalekoWindowsLocalIngest.WindowsLocalIngesterService,
        'log_level' : logging.DEBUG,
        'output_dir' : IndalekoWindowsLocalIngest.DefaultOutputDir,
        'config_dir' : IndalekoWindowsLocalIngest.DefaultConfigDir,
        'log_dir' : IndalekoWindowsLocalIngest.DefaultLogDir,
        'output_file_prefix' : IndalekoWindowsLocalIngest.WindowsLocalDataFilePrefix,
        'log_file_prefix' : IndalekoWindowsLocalIngest,
    }
    ingester = IndalekoWindowsLocalIngest(**ingest_args)


    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--data_dir', '-d',
                             help='Path to the data directory',
                             default=IndalekoIndex.DefaultDataDir)
    pre_parser.add_argument('--config_dir', '-c',
                            help='Path to the config directory',
                            default=IndalekoIndex.DefaultConfigDir)
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
    ingester.start(ingester.get_default_logfile_name(), args.loglevel)
    logging.info(f'Done with ingest at {datetime.datetime.now(datetime.UTC).isoformat()}')

if __name__ == "__main__":
    main()
