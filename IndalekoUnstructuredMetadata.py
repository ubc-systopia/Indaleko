import os
import logging
from datetime import datetime
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_json

# Setup logging
log_file_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '-metadataExtraction.log'
log_file_path = os.path.join("/app/logs", log_file_name)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create file handler
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Create stream handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Add handlers to the logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Function to process files
def process_files(file_list, output_file):
    data = {}
    for file_path in file_list:
        try:
            # Partition the document and extract elements
            elements = partition(filename=file_path)
            # Save the extracted elements to JSON
            elements_to_json(elements, filename=os.path.join("/app/test", output_file))
            logger.info(f"Processed file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

# List all files
downloads_path = "/app/downloads"  # Adjust based on your Docker container setup
all_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(downloads_path) for f in filenames]

# Process in batches
batch_size = 20  # Adjust based on your needs
for i in range(0, len(all_files), batch_size):
    batch_files = all_files[i:i + batch_size]
    process_files(batch_files, "extracted_data4.json")