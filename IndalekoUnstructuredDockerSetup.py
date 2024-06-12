import os
import subprocess
import logging
from datetime import datetime

PathToUserDocumentLogFolder = input("Input full path directory to logs folder, where your log data will be stored...")
PathToIndalekoProjectDirectory = input("Input full path directory to Indaleko Project...")
PathToDownloads = input("Input path directory to User Downloads folder")
PathToTestFolder = input("Input path directory to Test Folder")

# Setup logging
log_file_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '-dockerSetup.log'
log_file_path = os.path.join(PathToUserDocumentLogFolder, log_file_name)
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())  # Log to both file and console

project_directory = PathToIndalekoProjectDirectory
logs_directory = PathToUserDocumentLogFolder
script_name = "IndalekoUnstructuredMetadata.py"
image_name = "downloads.unstructured.io/unstructured-io/unstructured"
image_tag = "latest"
container_base_name = "unstructured_io_latest"
volumes = [
    {"host": PathToDownloads, "container": "/app/downloads"},
    {"host": PathToTestFolder, "container": "/app/test"},
    {"host": PathToUserDocumentLogFolder, "container": "/app/logs"},
    {"host": os.path.join(project_directory, script_name), "container": f"/app/{script_name}"}
]

def get_local_image_version(image_name, image_tag):
    logger.info(f"Checking for local image version: {image_name}:{image_tag}")
    result = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        capture_output=True, text=True
    )
    images = result.stdout.splitlines()
    image_full_name = f"{image_name}:{image_tag}"
    if image_full_name in images:
        logger.info(f"Local image found: {image_full_name}")
        return image_tag
    logger.info(f"Local image not found: {image_full_name}")
    return None

def pull_docker_image(image_name, image_tag):
    logger.info(f"Pulling Docker image {image_name}:{image_tag}...")
    try:
        subprocess.run(["docker", "pull", f"{image_name}:{image_tag}"], check=True)
        logger.info(f"Successfully pulled Docker image {image_name}:{image_tag}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to pull Docker image {image_name}:{image_tag}: {e}")

def setup_directories_and_volumes():
    for volume in volumes:
        host_path = volume["host"]
        if not os.path.exists(host_path) and not os.path.isfile(host_path):
            logger.info(f"Creating directory or file {host_path}...")
            if os.path.splitext(host_path)[1]:  # If there's an extension, it's a file
                open(host_path, 'a').close()  # Create an empty file
            else:
                os.makedirs(host_path)  # Create a directory
            logger.info(f"Created {host_path}")
        else:
            logger.info(f"Already exists: {host_path}")

def run_docker_container(container_name, image_name, image_tag):
    logger.info(f"Running the Docker container '{container_name}' with necessary volume mounts...")
    volume_args = []
    for volume in volumes:
        volume_args.extend(["-v", f"{volume['host']}:{volume['container']}"])
    try:
        subprocess.run([
            "docker", "run", "-dt",
            "--memory", "20g",  # Limit memory usage to 20GB
            *volume_args,
            "--name", container_name,
            f"{image_name}:{image_tag}"
        ], check=True)
        logger.info(f"Successfully started Docker container '{container_name}'")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Docker container '{container_name}': {e}")

def execute_script(container_name):
    logger.info(f"Executing {script_name} inside the Docker container '{container_name}'...")
    try:
        subprocess.run(["docker", "exec", "-it", container_name, "python3", f"/app/{script_name}"], check=True)
        logger.info(f"Successfully executed {script_name} inside the Docker container '{container_name}'")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute {script_name} inside the Docker container '{container_name}': {e}")

def access_logs():
    logger.info("Displaying logs from the host machine...")
    log_file_path = os.path.join(logs_directory, "indexing.log")
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as log_file:
            logs = log_file.read()
            print(logs)
            logger.info("Log file content:")
            logger.info(logs)
    else:
        logger.error("Log file not found.")

def clean_up(container_name):
    logger.info(f"Stopping and removing the Docker container '{container_name}'...")
    try:
        subprocess.run(["docker", "stop", container_name], check=True)
        subprocess.run(["docker", "rm", container_name], check=True)
        logger.info(f"Successfully stopped and removed Docker container '{container_name}'")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to stop and remove Docker container '{container_name}': {e}")

if __name__ == "__main__":
    logger.info("Starting Docker setup script...")
    local_version = get_local_image_version(image_name, image_tag)
    if not local_version:
        pull_docker_image(image_name, image_tag)
    
    setup_directories_and_volumes()
    container_name = container_base_name
    try:
        run_docker_container(container_name, image_name, image_tag)
        execute_script(container_name)
        access_logs()  # Optional: Uncomment if you want to automatically display logs
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        clean_up(container_name)
    # clean_up(container_name)  # Uncomment if you want to automatically clean up after execution
    logger.info("Docker setup script finished.")