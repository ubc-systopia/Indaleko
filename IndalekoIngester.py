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
        self.machine_id = str(uuid.UUID('00000000-0000-0000-0000-000000000000').hex)
        if 'machine_id' in kwargs:
            self.machine_id = str(uuid.UUID(kwargs['machine_id']).hex)
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        if 'timestamp' in kwargs:
            self.timestamp = kwargs['timestamp']
        self.platform = 'unknown'
        if 'platform' in kwargs:
            self.platform = kwargs['platform']
        self.ingester = 'unknown'
        if 'ingester' in kwargs:
            self.ingester = kwargs['ingester']
        self.storage_description = str(uuid.UUID('00000000-0000-0000-0000-000000000000').hex)
        if 'storage_description' in kwargs:
            self.storage_description = str(uuid.UUID(kwargs['storage_description']).hex)
        self.data_dir = Indaleko.default_data_dir
        if 'data_dir' in kwargs:
            self.data_dir = kwargs['data_dir']
        self.output_dir = self.data_dir
        if 'output_dir' in kwargs:
            self.output_dir = kwargs['output_dir']
        self.input_dir = self.data_dir
        if 'input_dir' in kwargs:
            self.input_dir = kwargs['input_dir']
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

    def generate_output_file_name(self, **kwargs) -> str:
        '''
        Given a set of parameters, generate a file name for the output
        file.
        '''
        output_dir = None
        if 'output_dir' in kwargs:
            output_dir = kwargs['output_dir']
            del kwargs['output_dir']
        if output_dir is None:
            output_dir = self.data_dir
        kwargs['ingester'] = self.ingester
        kwargs['machine'] = self.machine_id.replace('-', '_')
        kwargs['storage'] = self.storage_description.replace('-', '_')
        name = Indaleko.generate_file_name(**kwargs)
        return os.path.join(output_dir, name)

    def generate_file_name(self, target_dir : str = None, suffix = None) -> str:
        '''This will generate a file name for the ingester output file.'''
        print('machine_id : %s', self.machine_id)
        print('storage_description : %s', self.storage_description)
        if suffix is None:
            suffix = self.file_suffix
        return self.generate_output_file_name(
            prefix = self.file_prefix,
            suffix = suffix,
            platform = self.platform,
            service= 'ingest',
            ingester = self.ingester,
            machine = str(uuid.UUID(self.machine_id).hex),
            storage = str(uuid.UUID(self.storage_description).hex),
            timestamp = self.timestamp,
            output_dir = target_dir,
        )

    @staticmethod
    def extract_metadata_from_ingester_file_name(file_name : str) -> dict:
        '''
        This will extract the metadata from the given file name.
        '''
        data = Indaleko.extract_keys_from_file_name(file_name)
        if 'machine' in data:
            data['machine'] = str(uuid.UUID(data['machine']))
        if 'storage' in data:
            data['storage'] = str(uuid.UUID(data['storage']))
        return data

    def write_data_to_file(self, data : list, file_name : str = None, jsonlines_output : bool = True) -> None:
        '''This will write the given data to the specified file.'''
        if data is None:
            raise ValueError('data must be specified')
        if file_name is None:
            raise ValueError('file_name must be specified')
        if jsonlines_output:
            with jsonlines.open(file_name, mode='w') as writer:
                for entry in data:
                    try:
                        writer.write(entry.to_dict())
                    except TypeError as err:
                        print('Error writing entry to JSONLines file: %s', err)
                        print('Entry: %s', entry)
                        logging.error('Error writing entry to JSONLines file: %s', err)
                        logging.error('Entry: %s', entry)
                        raise err
            logging.info('Wrote JSONLines data to %s', file_name)
        else:
            json.dump(data, file_name, indent=4)
            logging.info('Wrote JSON data to %s', file_name)

def main():
    """Test code for IndalekoIngest.py"""
    # Now parse the arguments
    ingester = IndalekoIngester(test=True)
    assert ingester is not None, "Could not create ingester."
    fname = ingester.generate_file_name()
    print(fname)
    metadata = ingester.extract_metadata_from_ingester_file_name(fname)
    print(json.dumps(metadata, indent=4))

if __name__ == "__main__":
    main()
