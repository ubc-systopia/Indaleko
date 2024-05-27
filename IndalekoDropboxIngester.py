'''
IndalekoDropboxIngester.py

This script is used to ingest the files that have been indexed from Dropbox.  It
will create a JSONL file with the ingested metadata suitable for uploading to
the Indaleko database.

Project Indaleko
Copyright (C) 2024 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
import argparse
import datetime
from icecream import ic
import logging
import os
import json
import jsonlines

from IndalekoIngester import IndalekoIngester
from Indaleko import Indaleko
from IndalekoDropboxIndexer import IndalekoDropboxIndexer
from IndalekoServices import IndalekoService


class IndalekoDropboxIngester(IndalekoIngester):
    '''
    This class handles ingestion of metadata from the Indaleko Dropbox indexer.
    '''

    dropbox_ingester_uuid = '389ce9e0-3924-4cd1-be8d-5dc4b268e668'
    dropbox_ingester_service = IndalekoService.create_service_data(
        service_name = 'Dropbox Ingester',
        service_description = 'This service ingests captured index info from Dropbox.',
        service_version = '1.0',
        service_type = 'Ingester',
        service_identifier = dropbox_ingester_uuid,
    )

    dropbox_platform = 'Droppbox'
    dropbox_ingester = 'dropbox_ingester'

    def __init__(self, **kwargs) -> None:
        pass

def main():
    '''This is the main handler for the Dropbox ingester.'''
    logging_levels = Indaleko.get_logging_levels()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help='Path to the config directory',
                            default=Indaleko.default_config_dir)
    pre_parser.add_argument('--logdir', '-l',
                            help='Path to the log directory',
                            default=Indaleko.default_log_dir)
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
    pre_parser.add_argument('--datadir',
                            help='Path to the data directory',
                            default=Indaleko.default_data_dir,
                            type=str)
    pre_args , _ = pre_parser.parse_known_args()
    indexer = IndalekoDropboxIndexer()
    indexer_files = indexer.find_indexer_files(pre_args.datadir)
    ic(indexer_files)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='Dropbox index data file to ingest')
    args=parser.parse_args()
    ic(args)


if __name__ == '__main__':
    main()
