import logging
from Indaleko_iCloudSecureCreds import authenticate
import os
import json

def setup_logging(log_dir='logs'):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, 'metadata_index.log')
    logging.basicConfig(level=logging.DEBUG,  # Set to DEBUG to capture detailed information
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler(log_file),
                                  logging.StreamHandler()])

def handle_two_factor(api):
    if api.requires_2fa:
        logging.info("Two-factor authentication required.")
        code = input("Enter the code you received on one of your approved devices: ")
        result = api.validate_2fa_code(code)
        logging.info(f"Code validation result: {result}")
        if not result:
            raise ValueError("Failed to verify security code")
        if not api.is_trusted_session:
            logging.info("Session is not trusted. Requesting trust...")
            result = api.trust_session()
            logging.info(f"Session trust result: {result}")
            if not result:
                raise ValueError("Failed to request trust. You will likely be prompted for the code again in the coming weeks")

def list_top_level_contents(drive):
    """List the contents of the top level of the iCloud Drive."""
    items = drive.dir()  # Get all items at the top level
    logging.debug(f"Top level items: {items}")
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
                logging.debug(f"Indexed Item: {metadata}")
        except Exception as e:
            logging.error(f"Failed to process item: {item_name}, Error: {e}")
    return files_metadata

def index_to_json(api):
    json_output = 'icl_top_level_meta.json'  # Define the output JSON file path
    try:
        # Get the root of the iCloud Drive
        drive = api.drive
        root_folder = drive.root  # Access it as a property, not a method

        # Get top-level files metadata
        files_metadata = list_top_level_contents(root_folder)

        # Write the file names and metadata to a JSON file
        with open(json_output, 'w', encoding='utf-8') as jsonfile:
            json.dump(files_metadata, jsonfile, ensure_ascii=False, indent=4)

        logging.info(f"Index of files and their metadata has been saved to {json_output}")
    except Exception as e:
        logging.error(f"An error occurred during indexing to JSON: {e}")

if __name__ == "__main__":
    setup_logging()
    try:
        api = authenticate()
        handle_two_factor(api)
        index_to_json(api)
        logging.info("Metadata indexing completed.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")