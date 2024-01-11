'''
The IndalekoIndex class is a base class for common elements of storage indexing
operations.
'''
import os

class IndalekoIndex:

    DefaultDataDir = './data'
    DefaultConfigDir = './config'

    def __init__(self, collection, index_type: str, fields: list, unique: bool) -> None:
        pass

    @staticmethod
    def find_files(search_dir : str, prefix : str, suffix : str = '.json') -> list:
        '''This function finds the files to ingest:
            search_dir: path to the search directory
            prefix: prefix of the file to ingest
            suffix: suffix of the file to ingest (default is .json)
        '''
        assert search_dir is not None, 'search_dir must be a valid path'
        assert os.path.isdir(search_dir), 'search_dir must be a valid directory'
        assert prefix is not None, 'prefix must be a valid string'
        assert suffix is not None, 'suffix must be a valid string'
        return [x for x in os.listdir(search_dir)
                if x.startswith(prefix)
                and x.endswith(suffix)]

