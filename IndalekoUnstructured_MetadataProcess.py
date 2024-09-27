import os
import logging
from datetime import datetime
from unstructured.partition.auto import partition  # type: ignore
from unstructured.staging.base import elements_to_json  # type: ignore
import json

# Paths (ensure these match the paths in IndalekoUnstructured_Main.py)
LOGS_PATH = "/app/logs"
TEST_PATH = "/app/test"

# Ask the user for the output file name
output_file_name = input("Enter the desired output file name (without extension): ")
output_file_json = output_file_name + ".json"
output_file_jsonl = output_file_name + ".jsonl"

# Setup logging
log_file_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '-metadataExtraction.log'
log_file_path = os.path.join(LOGS_PATH, log_file_name)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create file handler
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
)

# Create stream handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
)

# Add handlers to the logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Function to process files
def process_files(file_list, output_file_json):
    all_elements = []
    for file_path in file_list:
        try:
            # Partition the document and extract elements
            elements = partition(filename=file_path)
            all_elements.extend(elements)
            logger.info(f"Processed file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    # Save the extracted elements to JSON
    elements_to_json(all_elements, filename=os.path.join(TEST_PATH, output_file_json))

    # Convert JSON to JSONL
    json_file_path = os.path.join(TEST_PATH, output_file_json)
    jsonl_file_path = os.path.join(TEST_PATH, output_file_jsonl)

    try:
        with open(json_file_path, 'r') as json_file, open(jsonl_file_path, 'w') as jsonl_file:
            data = json.load(json_file)
            for entry in data:
                jsonl_file.write(json.dumps(entry) + '\n')
        logger.info(f"Converted {output_file_json} to {output_file_jsonl}")
    except Exception as e:
        logger.error(f"Failed to convert JSON to JSONL: {e}")

# List all files
downloads_path = "/app/downloads"  # Adjust based on your Docker container setup
all_files = [
    os.path.join(dp, f) for dp, dn, filenames in os.walk(downloads_path) for f in filenames
]

# Process in batches
batch_size = 20  # Adjust based on your needs
for i in range(0, len(all_files), batch_size):
    batch_files = all_files[i:i + batch_size]
    process_files(batch_files, output_file_json)