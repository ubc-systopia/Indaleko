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
import json
import jsonlines
import datetime
import os
import uuid
from IndalekoServices import IndalekoService
from Indaleko import Indaleko

class IndalekoIngester():
    '''
    IndalekoIngest is the generic class that we use for ingesting data from the
    various indexers that we have. Platform specific ingesters are built on top
    of this class to handle platform-specific ingestion.
    '''

    default_file_prefix = 'indaleko'
    default_file_suffix = '.jsonl'

    indaleko_generic_ingester_uuid_str = '526e0240-1ee4-46e9-9dac-3e557a8fb654'
    indaleko_generic_ingester_uuid = uuid.UUID(indaleko_generic_ingester_uuid_str)
    indaleko_generic_ingester_service_name = 'Indaleko Generic Ingester'
    indaleko_generic_ingester_service_description = \
        'This is the base (non-specialized) Indaleko Ingester. ' +\
        'You should not see it in the database.'
    indaleko_generic_ingester_service_version = '1.0'

    def __init__(self : 'IndalekoIngester', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoIngest class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the ingester.
        '''
        self.file_prefix = IndalekoIngester.default_file_prefix
        if 'file_prefix' in kwargs:
            self.file_prefix = kwargs['file_prefix']
        self.file_prefix = self.file_prefix.replace('-', '_')
        self.file_suffix = IndalekoIngester.default_file_suffix
        if 'file_suffix' in kwargs:
            self.file_suffix = kwargs['file_suffix']
        self.file_suffix = self.file_suffix.replace('-', '_')
        self.machine_id = 'unknown'
        if 'machine_id' in kwargs:
            self.machine_id = kwargs['machine_id']
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        if 'timestamp' in kwargs:
            self.timestamp = kwargs['timestamp']
        self.platform = 'unknown'
        if 'platform' in kwargs:
            self.platform = kwargs['platform']
        self.ingester = 'unknown'
        if 'ingester' in kwargs:
            self.ingester = kwargs['ingester']
        self.storage_description = 'unknown'
        if 'storage_description' in kwargs:
            self.storage_description = kwargs['storage_description']
        self.data_dir = Indaleko.default_data_dir
        if 'data_dir' in kwargs:
            self.data_dir = kwargs['data_dir']
        assert self.data_dir is not None, 'data_dir must be specified'
        self.config_dir = Indaleko.default_config_dir
        if 'config_dir' in kwargs:
            self.config_dir = kwargs['config_dir']
        self.log_dir = Indaleko.default_log_dir
        if 'log_dir' in kwargs:
            self.log_dir = kwargs['log_dir']
        self.service_name = IndalekoIngester.indaleko_generic_ingester_service_name
        if 'service_name' in kwargs:
            self.service_name = kwargs['service_name']
        self.service_description = IndalekoIngester.indaleko_generic_ingester_service_description
        if 'service_description' in kwargs:
            self.service_description = kwargs['service_description']
        self.service_version = IndalekoIngester.indaleko_generic_ingester_service_version
        if 'service_version' in kwargs:
            self.service_version = kwargs['service_version']
        self.service_type = 'Ingester'
        if 'service_type' in kwargs:
            self.service_type = kwargs['service_type']
        self.service_identifier = IndalekoIngester.indaleko_generic_ingester_uuid_str
        if 'service_identifier' in kwargs:
            self.service_identifier = kwargs['service_identifier']
        self.ingester_service = IndalekoService(
            service_name = self.service_name,
            service_description = self.service_description,
            service_version = self.service_version,
            service_type = self.service_type,
            service_identifier = self.service_identifier,
        )
        assert self.ingester_service is not None, 'Ingester service does not exist'


    def generate_ingester_file_name(self, target_dir : str = None) -> str:
        '''This will generate a file name for the ingester output file.'''
        if target_dir is None:
            target_dir = self.data_dir
        return os.path.join(
                target_dir,
                f'{self.file_prefix}-\
                   platform={self.platform}-\
                   ingester={self.ingester}-\
                   machine={self.machine_id}-\
                   storage={self.storage_description}-\
                   timestamp={self.timestamp}\
                   {self.file_suffix}'.replace(' ', '')
        )

    def write_data_to_file(self, data : list, file_name : str = None, jsonlines_output : bool = True) -> None:
        '''This will write the given data to the specified file.'''
        if data is None:
            raise ValueError('data must be specified')
        if file_name is None:
            raise ValueError('file_name must be specified')
        if jsonlines_output:
            with jsonlines.open(file_name, mode='w') as writer:
                for entry in data:
                    writer.write(entry)
            logging.info('Wrote JSONLines data to %s', file_name)
        else:
            json.dump(data, file_name, indent=4)
            logging.info('Wrote JSON data to %s', file_name)

def main():
    """Test code for IndalekoIngest.py"""
    # Now parse the arguments
    ingester = IndalekoIngester(test=True)
    assert ingester is not None, "Could not create ingester."
    print(ingester.generate_ingester_file_name())

if __name__ == "__main__":
    main()
