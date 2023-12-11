import argparse
import json
import os
import logging
import uuid
import datetime
import datetime
import platform


class ContainerRelationship:

    ContainsRelationshipSchema = {
        '_from_field' : {
            'type' : 'string',
            'rule' : {'type', 'uuid'}
        },
        '_to_field' : {
            'type' : 'string',
            'rule' : {'type', 'uuid'}
        }
    }

    def __init__(self, db, start, end, collection):
        self._from = start
        self._to = end
        db[collection].insert(self._dict_)

    def to_json(self):
        return json.dumps(self.__dict__)


class FileSystemObject:
    '''
    This class represents a file system object's meta-data
    '''
    ObjectCount = 0 # track how many
    RelationshipCount = 0 # track how many

    def __init__(self, path : str, root = False):
        self.root = root
        self.uuid = str(uuid.uuid4())
        self.url = 'file:///' + path
        self.stat_info = os.stat(path)
        self.size = self.stat_info.st_size
        self.timestamps = {
            'created': datetime.datetime.fromtimestamp(self.stat_info.st_ctime).isoformat(),
            'modified': datetime.datetime.fromtimestamp(self.stat_info.st_mtime).isoformat(),
            'accessed': datetime.datetime.fromtimestamp(self.stat_info.st_atime).isoformat(),
        }
        FileSystemObject += 1


class LocalFileSystemMetadata:

    def __init__(self):
        pass

    def get_output_file_name(self):
        assert False, 'get_output_file_name not implemented in base class: please override'

    def get_uri_for_file(self, file_name: str) -> str:
        assert False, 'get_uri_for_file not implemented in base class: please override'


class LocalIngest:

    DefaultOutputDir = './data'
    DefaultConfigDir = './config'
    DefaultOutputFile = 'output.json'
    DefaultConfigFile = 'config.ini'

    def __init__(self, parser : argparse.ArgumentParser = None):
        if parser is not None:
            self.parser = parser
        else:
            self.parser = argparse.ArgumentParser()
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
        self.__setup_defaults__()
        logging.basicConfig(level=logging.WARNING)
        self.logger = logging.getLogger(__name__)
        self.parser.add_argument('--loglevel', type=int, default=logging.WARNING, choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
        self.parser.add_argument('--outdir', type=str, default=self.DefaultOutputDir, help='Directory to use for output file')
        self.parser.add_argument('--output', type=str, default=self.DefaultOutputFile,
                            help='Name and location of where to save the fetched metadata')
        self.parser.add_argument('--confdir', type=str, default=self.DefaultConfigDir, help='Directory to use for config file')
        self.parser.add_argument('--config', type=str, default=self.DefaultConfigFile,
                            help='Name and location from whence to retrieve the Microsoft Graph Config info')

    def __setup_defaults__(self) -> 'LocalIngest':
        self.set_output_dir(LocalIngest.DefaultOutputDir).set_output_file(LocalIngest.DefaultOutputFile)
        self.set_config_dir(LocalIngest.DefaultConfigDir).set_config_file(LocalIngest.DefaultConfigFile)
        return self

    def parse_args(self) -> argparse.Namespace:
        self.args = self.parser.parse_args()
        logging.basicConfig(level=self.args.loglevel)
        self.logger = logging.getLogger(__name__)
        self.logger.debug(self.args)
        self.logger.debug(f"Log level set to {self.args.loglevel}")
        self.logger.debug(f"Output file set to {self.args.output}")
        self.logger.debug(f"Config file set to {self.args.config}")
        return self.args


    def add_arguments(self, *args, **kwargs) -> 'LocalIngest':
        self.parser.add_argument(*args, **kwargs)
        return self


    def set_output_dir(self, dir_name : str) -> 'LocalIngest':
        self.output_dir = dir_name
        for action in self.parser._actions:
            if 'outdir' == action.dest:
                self.logger.debug(f"Setting default for {action.dest} to {self.output_file}")
                action.default = self.output_dir
                break
        return self

    def set_output_file(self, file_name : str) -> 'LocalIngest':
        self.output_file = file_name
        for action in self.parser._actions:
            if 'output' == action.dest:
                self.logger.debug(f"Setting default for {action.dest} to {self.output_file}")
                action.default = self.output_file
                break
        return self

    def set_config_dir(self, dir_name : str) -> 'LocalIngest':
        self.config_dir = dir_name
        for action in self.parser._actions:
            if 'confdir' == action.dest:
                self.logger.debug(f"Setting default for {action.dest} to {self.output_file}")
                action.default = self.config_dir
                break
        return self

    def set_config_file(self, file_name : str) -> 'LocalIngest':
        self.config_file = file_name
        for action in self.parser._actions:
            if 'config' == action.dest:
                self.logger.debug(f"Setting default for {action.dest} to {self.output_file}")
                action.default = self.config_file
                break
        return self

def main():
    # Note that this script is designed to be a class library, so if someone
    # runs it directly, I'll point them at the correct version to run.
    # We _could_ change it so that it runs the correct version, but that
    # seems unnecessary.
    print('This script is a general library used by platform specific ingesters.')
    print('You are running on ' + platform.system())
    print(f'The ingester script should be called something like {platform.system().lower()}_local_ingest.py')
    print('Please run that script instead.')

if __name__ == "__main__":
    main()
