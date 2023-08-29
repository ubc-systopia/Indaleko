import argparse
import datetime
import json

class IndalekoIngest:
    '''
    Base class for all ingestors.  Provides a common interface for all
    ingestors.
    '''
    def __init__(self, basename : str, get_metadata):
        self.get_metadata = get_metadata
        assert type(get_metadata) == type(lambda: None), 'get_metadata must be a function that returns a list of metadata'
        self.output_file = f'data/{basename}-{datetime.datetime.utcnow()}-data.json'
        parser = argparse.ArgumentParser()
        parser.add_argument('--output', type=str, default=self.output_file,
                            help='Name and location of where to save the fetched metadata')

    def get_parser(self) -> argparse.ArgumentParser:
        '''Return default parser for all ingestors so they can augment it.'''
        return self.parser

    def capture_metadata(self, args):
        '''Capture metadata from the source and write it to the output file.'''
        self.metadata_list = self.get_metadata(args)
        self.output_file = args.output
        self.write_output()
        return self

    def write_output(self):
        with open(self.output_file, 'wt') as f:
            json.dump(self.metadata_list, f, indent=4)
        return self

def main():
    print('This is a library, do not invoke directly.')

if __name__ == "__main__":
    main()
