'''
This extracts the metadata of files to be processed from ArangoDB and parses
them into an input suitable for the Unstructured Docker Containers.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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

# standard library imports
import configparser
import logging
import os
import sys
import re
import json

# third-party imports
from icecream import ic
from arango import ArangoClient

#  Find Indaleko Root
if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# Indaleko Imports
from Indaleko import Indaleko
from storage.i_object import IndalekoObject

class UnstructuredLookup():
    '''This class retrieves the metadata of files to be processed from ArangoDB
        and parses them into an input as a jsonl file that is suitable for Unstructured Docker.
        
        Steps involved:

        1. Connect to DB
        2. Retrieve all file objects in Object
        3. Converts retrieved Objects into IndalekoObject
        4. Get volume GUID path to file in local.
        5. Convert the local paths to a unix path

        TODO:
        - Add logging
        - More error handling
        - Checksums
        - Filter out incompatible file types
        
        '''
    arango_config_file_name = "indaleko-db-config.ini"
    unstructured_config_file_name = 'unstructured_config.ini'

    # Query to retrieve files wanted for unstructured processing
    # query_string = 'FOR doc IN Object \
    #                     FILTER doc.WindowsFileAttributes == @val \
    #                     SORT doc.URI \
    #                     RETURN doc'

    # Query that returns a smaller result. 
    # Make sure to edit variables in perform_query()
    query_string = 'FOR doc IN Object \
                        FILTER doc.WindowsFileAttributes == @val \
                            AND doc.Label == @essay \
                        SORT doc.URI \
                        RETURN doc'

    def __init__(self):
        unstructured_config_file = os.path.join(Indaleko.default_config_dir, self.unstructured_config_file_name)
        unstructured_config = configparser.ConfigParser()
        unstructured_config.read(unstructured_config_file, encoding='utf-8-sig')

        self.host_drive_mount = unstructured_config['VOLUMES']['HostDriveMount']
        self.unstructured_data_dir = unstructured_config['DATA']['UnstructuredDataDir']
        self.output_name = unstructured_config['DATA']['InputFileName']


    def windows_to_unix_path(self, windows_path):
        '''Converts the given windows path of a file to a unix one. With
        the root directory set to the host drive's Bind Mount in Docker'''
        normalized_path = os.path.normpath(windows_path)
        linux_path = normalized_path.replace("\\", "/")
        match = re.split(r"//\?/Volume{.+}", linux_path)
        if len(match) > 1:
            linux_path = self.host_drive_mount + match[1]
        return linux_path
    
    def connect_db(self):
        '''Returns a StandardDatabase object after connecting to ArangoDB
        using information specified in the DB configuration file'''
        arango_config_file = os.path.join(Indaleko.default_config_dir, self.arango_config_file_name)
        config = configparser.ConfigParser()
        config.read(arango_config_file, encoding='utf-8-sig')

        ARANGO_USER_NAME = config['database']['user_name']
        ARANGO_USER_PASSWORD = config['database']['user_password']
        ARANGO_HOST = config['database']['host']
        ARANGO_PORT = config['database']['port']

        host = f"http://{ARANGO_HOST}:{ARANGO_PORT}"
        client = ArangoClient(hosts = host)
        db = client.db("Indaleko", ARANGO_USER_NAME, ARANGO_USER_PASSWORD)

        assert db.has_collection('Object')
        ic(f'Connected to ArangoDB: {host}')
        return db

    def perform_query(self):
        '''Returns a Cursor to the results of the query.'''
        db = self.connect_db()
        cursor = db.aql.execute(self.query_string,
                                    bind_vars = {'val': 'FILE_ATTRIBUTE_ARCHIVE', 'essay' : 'Essay.docx'},
                                    batch_size=10,
                                    count=True)
        ic('Query Successful')
        return cursor
    
    def generate_input(self):
        '''Creates a jsonl file in the Data directory with a set of inputs to be sent to Unstructured for processing. Each row contains a unique ObjectIdentifier and unix-base URI converted from the original Windows one. 

        Additional feature to be added later: Checksums'''
        cursor = self.perform_query()
        if not os.path.exists(self.unstructured_data_dir):
            os.mkdir(self.unstructured_data_dir)
        with open(os.path.join(self.unstructured_data_dir, 
                               self.output_name), 'w') as jsonl_file:
            for doc in cursor:
                indaleko_object = IndalekoObject.deserialize(doc)
                ## Add more code here to filter out unknown file types, or files that have been processed already
                object_uri = indaleko_object.__getitem__('URI')
                object_uuid = indaleko_object.__getitem__('ObjectIdentifier')
                jsonl_file.write(json.dumps({'ObjectIdentifier': object_uuid,
                                            'URI': self.windows_to_unix_path(object_uri)}) + '\n')
        
        

    
