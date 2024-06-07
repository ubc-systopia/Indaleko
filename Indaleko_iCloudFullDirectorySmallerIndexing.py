import logging
from Indaleko_iCloudSecureCreds import authenticate
import os
import json

def setup_logging(log_dir='logs'):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, 'metadata_index_recursive.log')
    
    # File handler for detailed debug logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Stream handler for critical logs only to the terminal
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.CRITICAL)
    
    logging.basicConfig(level=logging.DEBUG,  # Set to DEBUG to capture detailed information
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[file_handler, stream_handler])

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

def get_folder_contents(folder, jsonlfile, path=''):
    """Recursively get the contents of a folder and write metadata to a JSON Lines file."""
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
            logging.debug(f"Indexed Item: {metadata}")

def index_to_jsonl(api):
    jsonl_output = 'icl_full_index_meta.jsonl'  # Define the output JSON Lines file path
    try:
        # Get the root of the iCloud Drive
        drive = api.drive
        root_folder = drive.root  # Access it as a property, not a method

        # Open the JSON Lines file for writing
        with open(jsonl_output, 'w', encoding='utf-8') as jsonlfile:
            # Get all files metadata starting from the root
            get_folder_contents(root_folder, jsonlfile)

        logging.info(f"Index of files and their metadata has been saved to {jsonl_output}")
    except Exception as e:
        logging.critical(f"An error occurred during indexing to JSON Lines: {e}")

if __name__ == "__main__":
    setup_logging()
    try:
        api = authenticate()
        handle_two_factor(api)
        index_to_jsonl(api)
        logging.info("Metadata indexing completed.")
    except Exception as e:
        logging.critical(f"An error occurred: {e}")