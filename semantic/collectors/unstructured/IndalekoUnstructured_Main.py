import os
import subprocess
import logging
import sys  # Added to use sys.exit()
from datetime import datetime

# Prompt the user for the necessary paths
PathToWhereLogFileWillBeStored = input(
    "Type path where you want the log file for this process to be stored: \n"
)
PathToIndalekoProjectDirectory = input(
    "Please input path to directory where project is: \n"
)
PathToUserDefinedFolder = input(
    "Input the directory you want to have indexed by Unstructured: \n"
)
PathToOutputFileWillBeSaved = input(
    "Please specify where you want the resulting JSONL file to be stored: \n"
)

# Ask the user for the output file name
output_file_name = input("Enter the desired output file name (without extension): ")

# Setup logging
log_file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "-dockerSetup.log"
log_file_path = os.path.join(PathToWhereLogFileWillBeStored, log_file_name)

logger = logging.getLogger()
# uncomment below if I want the logs printed out to Terminal.
# StreamHandler outputs logs to the console
# logger.addHandler(logging.StreamHandler())  # Log to both file and console

# Variables
project_directory = PathToIndalekoProjectDirectory
logs_directory = PathToWhereLogFileWillBeStored
script_name = "IndalekoUnstructured_MetadataProcess.py"
image_name = "downloads.unstructured.io/unstructured-io/unstructured"
image_tag = "latest"
container_base_name = "unstructured_io_latest"

# Mount the entire project directory
volumes = [
    {"host": PathToUserDefinedFolder, "container": "/app/downloads"},
    {"host": PathToOutputFileWillBeSaved, "container": "/app/test"},
    {"host": PathToWhereLogFileWillBeStored, "container": "/app/logs"},
    {"host": project_directory, "container": "/app/Indaleko"},
    {
        "host": os.path.join(project_directory, "processed"),
        "container": "/app/processed",
    },
]


def get_local_image_version(image_name, image_tag):
    logger.info(f"Checking for local image version: {image_name}:{image_tag}")
    result = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        capture_output=True,
        text=True,
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
        sys.exit(1)  # Exit the script if the image pull fails


def setup_directories_and_volumes():
    for volume in volumes:
        host_path = volume["host"]
        if not os.path.exists(host_path):
            logger.info(f"Creating directory or file {host_path}...")
            if os.path.splitext(host_path)[1]:  # If there's an extension, it's a file
                open(host_path, "a").close()  # Create an empty file
            else:
                os.makedirs(host_path)  # Create a directory
            logger.info(f"Created {host_path}")
        else:
            logger.info(f"Already exists: {host_path}")


# Check if a container exists
def container_exists(container_name):
    result = subprocess.run(
        ["docker", "ps", "-aq", "-f", f"name=^{container_name}$"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def run_docker_container(container_name, image_name, image_tag, output_file_name):
    logger.info(
        f"Running the Docker container '{container_name}' with necessary volume mounts..."
    )
    volume_args = []
    for volume in volumes:
        volume_args.extend(["-v", f"{volume['host']}:{volume['container']}"])

    # Remove existing container if it exists
    if container_exists(container_name):
        logger.info(f"Container with name '{container_name}' already exists.")
        logger.info(f"Removing existing container '{container_name}'")
        try:
            subprocess.run(["docker", "rm", "-f", container_name], check=True)
            logger.info(f"Successfully removed existing container '{container_name}'")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove existing container '{container_name}': {e}")
            raise  # Stop execution if the container cannot be removed

    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--memory",
                "20g",
                "--rm",
                "--name",
                container_name,
                "-i",  # Keep STDIN open
                *volume_args,
                f"{image_name}:{image_tag}",
                "python3",
                f"/app/Indaleko/{script_name}",
                output_file_name,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(
            f"Successfully ran Docker container '{container_name}' and executed '{script_name}'"
        )
        logger.info(f"Container stdout:\n{result.stdout}")
        logger.info(f"Container stderr:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run Docker container '{container_name}': {e}")
        logger.error(f"Error output:\n{e.stderr}")
        raise


"""The following function is not necessary atm. It would require creating a 
temporary file to pass it back to the main script via a shared volume or another method.
Since the second script -MetadataProcess- runs inside the Docker container created here, 
sharing this information back to the main script can be complex. 

This is not necessary as I can access the full log file in the log directory.

Leaving it here to serve as a reminder to potentially work on"""


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
        logger.info(
            f"Successfully stopped and removed Docker container '{container_name}'"
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to stop and remove Docker container '{container_name}': {e}"
        )


if __name__ == "__main__":
    logger.info("Starting Docker setup script...")
    local_version = get_local_image_version(image_name, image_tag)
    if not local_version:
        pull_docker_image(image_name, image_tag)

    setup_directories_and_volumes()
    container_name = container_base_name
    try:
        run_docker_container(container_name, image_name, image_tag, output_file_name)
        # access_logs()  # Optional: Uncomment if you want to automatically display logs
    except subprocess.CalledProcessError as e:
        logger.error(f"An error occurred during execution: {e}")
        sys.exit(1)  # Exit the script with a non-zero status code
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)  # Exit the script with a non-zero status code
    logger.info(
        f"Docker Unstructured script finished on: {PathToUserDefinedFolder}.\nSaved to: {PathToOutputFileWillBeSaved}"
    )
