import logging
import os
import json
from datetime import datetime

def setup_logging_indexing():
    logger = logging.getLogger('iCloudIndexLogger')
    logger.setLevel(logging.DEBUG)
    if not os.path.exists('logs'):
        os.makedirs('logs')
    log_filename = datetime.now().strftime('%Y%m%d-%H%M%S-metadata_index.log')
    file_handler = logging.FileHandler(os.path.join('logs', log_filename))
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    return logger

index_logger = setup_logging_indexing()

def list_top_level_contents(drive):
    """List the contents of the top level of the iCloud Drive."""
    index_logger.debug("Listing top level contents of iCloud Drive")
    items = drive.dir()  # Get all items at the top level
    index_logger.debug(f"Top level items: {items}")
    files_metadata = []
    for item_name in items:
        try:
            item = drive[item_name]
            if item.type == 'file':  # Only add metadata for files
                metadata = {
                    'name': item.name,
                    'size': item.size,
                    'path': f"/{item_name}",
                    'modified': item.date_modified.strftime('%Y-%m-%d %H:%M:%S') if item.date_modified else 'Unknown'
                }
                files_metadata.append(metadata)
                index_logger.debug(f"Indexed Item: {metadata}")
        except Exception as e:
            index_logger.error(f"Failed to process item: {item_name}, Error: {e}")
    return files_metadata

def index_to_jsonl(api):
    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')

    # Use the same datetime stamp as the log files
    datetime_stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    jsonl_output = os.path.join('data', f'{datetime_stamp}-topLevelSimpleMetadata.jsonl')
    
    try:
        # Get the root of the iCloud Drive
        drive = api.drive
        root_folder = drive.root  # Access it as a property, not a method

        # Get top-level files metadata
        files_metadata = list_top_level_contents(root_folder)

        # Write the file names and metadata to a JSONL file
        with open(jsonl_output, 'w', encoding='utf-8') as jsonlfile:
            for metadata in files_metadata:
                jsonlfile.write(json.dumps(metadata) + '\n')

        index_logger.info(f"Index of files and their metadata has been saved to {jsonl_output}")
    except Exception as e:
        index_logger.error(f"An error occurred during indexing to JSONL: {e}")

# This module should not run any main code