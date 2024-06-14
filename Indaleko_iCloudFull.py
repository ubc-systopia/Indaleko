import logging
import os
import json
from datetime import datetime

def setup_logging_indexing():
    # Set up logger
    logger = logging.getLogger('iCloudIndexLogger')
    # Set up logger default level
    logger.setLevel(logging.DEBUG)
    # Sets up a log directory if one does not exist, then will place log file within
    if not os.path.exists('logs'):
        os.makedirs('logs')
    # Create the log file name - using datetime stamp at the start.
    log_filename = datetime.now().strftime('%Y%m%d-%H%M%S-smallMetadata_fullIndexing.log')
    file_handler = logging.FileHandler(os.path.join('logs', log_filename))
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    return logger

index_logger = setup_logging_indexing()

def get_folder_contents(folder, jsonlfile, path=''):
    """Recursively get the contents of a folder and write metadata to a JSON Lines file."""
    try:
        index_logger.info(f"Entering folder: {path or '/'}")
        for item_name in folder.dir():
            item = folder[item_name]
            item_path = f"{path}/{item_name}"

            if item.type == 'folder':
                # Recursively get the contents of this folder
                get_folder_contents(item, jsonlfile, item_path)
            else:
                metadata = {
                    'name': item.name,
                    'path': item_path,
                    'size': item.size,
                    'modified': item.date_modified.strftime('%Y-%m-%d %H:%M:%S') if item.date_modified else 'Unknown'
                }
                jsonlfile.write(json.dumps(metadata) + '\n')
                index_logger.debug(f"Indexed Item: {metadata}")
    except Exception as e:
        index_logger.error(f"Failed to process folder: {path}, Error: {e}")

def index_to_jsonl(api):
    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')

    # Use the same datetime stamp as the log files
    datetime_stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    jsonl_output = os.path.join('data', f'{datetime_stamp}-fullDirectorySmallMetadata.jsonl')
    
    try:
        # Get the root of the iCloud Drive
        drive = api.drive
        root_folder = drive.root  # Access it as a property, not a method

        # Write the file names and metadata to a JSONL file
        with open(jsonl_output, 'w', encoding='utf-8') as jsonlfile:
            get_folder_contents(root_folder, jsonlfile)

        index_logger.info(f"Index of files and their metadata has been saved to {jsonl_output}")
    except Exception as e:
        index_logger.error(f"An error occurred during indexing to JSONL: {e}")

# This module should not run any main code