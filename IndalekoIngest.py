import argparse
import datetime
import json
import logging

class IndalekoIngest:
    '''
    Base class for all ingestors.  Provides a common interface for all
    ingestors.
    '''
    config_dir = 'config/'
    data_dir = 'data/'
    timestamp = datetime.datetime.utcnow()

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        logging_levels = sorted(
            set([l for l in logging.getLevelNamesMapping()]))
        self.parser.add_argument('--loglevel', type=int, default=logging.WARNING, choices=logging_levels,
                                 help='Logging level to use (lower number = more logging)')
        self.parser.add_argument('--output', type=str, default=None, help='Name of output file for captured data')
        self.args = None
        self.output_file = None
        self.metadata = []

    def get_metadata(self):
        assert False, 'get_metadata must be overridden by a subclass'

    def main(self):
        '''This is the entry point for all ingestors'''
        if self.args is None:
            self.args = self.parser.parse_args()
        self.start = datetime.datetime.utcnow()
        self.metadata = self.get_metadata()
        self.end = datetime.datetime.utcnow()
        self.get_output_file()
        self.record_metadata()

    def _get_output_file(self) -> str:
        '''Override this in derived classes if needed.'''
        return self.output_file

    def get_output_file(self) -> str:
        '''This is used to get the output file. Note that a derived class should
        override _get_output_file as this will preserve the override from the
        command line.'''
        if self.output_file is None and self.args.output is not None:
            self.output_file = self.args.output.replace(' ', '_').replace(':', '-')
        else:
            self.output_file = self._get_output_file()
        return self.output_file


    def record_metadata(self):
        if self.output_file is not None and len(self.metadata) > 0:
            with open(self.output_file, 'wt') as output_file:
                json.dump(self.metadata, output_file, indent=4)
            elapsed = self.end - self.start
            print(
                f'Saved {len(self.metadata)} records to {self.output_file} in {elapsed} seconds ({elapsed/len(self.metadata)} seconds per record)')
        return self

    def get_metadata(self):
        assert False, 'get_metadata must be overridden by a subclass'
