"""
This module provides an interface to managing the Docker components within
Indaleko.
"""

import os
import sys
import logging
import argparse
import docker
import json

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from Indaleko import Indaleko
from utils.i_logging import IndalekoLogging
import utils.misc.directory_management
import utils.misc.file_name_management

# pylint: enable=wrong-import-position


class IndalekoDocker:
    """Indaleko Class for managing Docker components."""

    def __init__(self, **kwargs):
        """Initialize a new instance of the IndalekoDocker class object."""
        self.container_name = None
        if "container_name" in kwargs:
            self.container_name = kwargs["container_name"]
        self.volume_name = None
        if "container_volume" in kwargs:
            self.volume_name = kwargs["container_name"]
        try:
            self.docker_client = docker.from_env()
        except docker.errors.DockerException as error:
            logging.error("Failed to connect to Docker: %s", error)
            print(f"Failed to connect to Docker: {error}")
            print(
                "Please make sure Docker is running and you have the correct permissions."
            )
            exit(1)
        self.docker_client.ping()
        logging.info("IndalekoDocker initialized, Docker connection instantiated.")

    def update_arango_image(self) -> bool:
        """Update the ArangoDB Docker image. Returns true if the image changed."""
        logging.info("Pulling latest ArangoDB image.")
        try:
            current_image = self.docker_client.images.get("arangodb/arangodb:latest")
            current_image_id = current_image.id
        except docker.errors.ImageNotFound:
            current_image_id = None
        # update the image
        self.docker_client.images.pull("arangodb/arangodb:latest")
        new_image = self.docker_client.images.get("arangodb/arangodb:latest")
        new_image_id = new_image.id
        if current_image_id == new_image_id:
            logging.info("ArangoDB image did not change.")
            return False
        else:
            logging.info("ArangoDB image updated.")
            return True

    def list_containers(self, all: bool = False) -> list:
        """List the Indaleko related Docker containers."""
        containers = self.docker_client.containers.list(all=all)
        return [
            container.name
            for container in containers
            if utils.misc.file_name_management.indaleko_file_name_prefix
            in container.name
        ]

    def list_volumes(self) -> list:
        """List the Indaleko related Docker volumes."""
        volumes = self.docker_client.volumes.list()
        return [
            volume.name
            for volume in volumes
            if utils.misc.file_name_management.indaleko_file_name_prefix in volume.name
        ]

    def create_container(
        self, container_name: str = None, volume_name: str = None, password: str = None
    ) -> None:
        """Add a new Indaleko related Docker container."""
        if container_name is not None:
            self.container_name = container_name
        if volume_name is not None:
            self.volume_name = volume_name
        if container_name is None:
            container_name = self.container_name
        else:
            self.container_name = container_name
        if volume_name is None:
            volume_name = self.volume_name
        else:
            self.volume_name = volume_name
        assert container_name is not None, "container_name must be provided"
        assert volume_name is not None, "volume_name must be provided"
        # Make sure the volume exists
        all_volumes = self.list_volumes()
        if volume_name not in all_volumes:
            self.create_volume(volume_name)
        all_containers = self.list_containers(all=True)
        if container_name in all_containers:
            logging.warning("Container %s already exists.", container_name)
            return
        self.update_arango_image()
        self.docker_client.containers.create(
            image="arangodb/arangodb:latest",
            name=container_name,
            ports={"8529/tcp": 8529},
            volumes={volume_name: {"bind": "/var/lib/arangodb3", "mode": "rw"}},
            environment={"ARANGO_ROOT_PASSWORD": password},
            restart_policy={self.container_name: "unless-stopped"},
            detach=True,
        )
        logging.debug("Created container %s", container_name)
        logging.debug("Created volume %s", volume_name)
        logging.debug("ARANGO_ROOT_PASSWORD is %s", password)

    def delete_volume(self, volume_name: str) -> None:
        """Delete an Indaleko related Docker volume."""
        if volume_name is None:
            raise ValueError("volume_name must be provided")
        if volume_name not in self.list_volumes():
            logging.warning("Volume %s does not exist, cannot delete", volume_name)
            print(f"Volume {volume_name} does not exist, cannot delete")
            return
        self.docker_client.volumes.get(volume_name).remove()
        logging.info("Deleted volume %s", volume_name)

    def delete_container(self, container_name: str, stop: bool = False) -> None:
        """Delete an Indaleko related Docker container."""
        if container_name is None:
            raise ValueError("container_name must be provided")
        if container_name not in self.list_containers(all=True):
            logging.warning(
                "Container %s does not exist, cannot delete", container_name
            )
            print(f"Container {container_name} does not exist, cannot delete")
            return
        if container_name in self.list_containers() and stop:
            logging.info("Stopping container %s (before deletion)", container_name)
            self.stop_container(container_name)
        if container_name in self.list_containers():
            logging.info(
                "Container %s is running, cannot stop, so cannot delete.",
                container_name,
            )
            print(
                f"Container {container_name} is running, cannot stop, so cannot delete."
            )
            return
        self.docker_client.containers.get(container_name).remove()
        logging.info("Deleted container %s", container_name)

    def stop_container(self, container_name: str) -> None:
        """Stop an Indaleko related Docker container."""
        if container_name is None:
            raise ValueError("container_name must be provided")
        logging.info("Stopping container %s", container_name)
        self.docker_client.containers.get(container_name).stop()

    def start_container(self, container_name: str) -> None:
        if container_name is None:
            raise ValueError("container_name must be provided")
        logging.info("Starting container %s", container_name)
        return self.docker_client.containers.get(container_name).start()

    def update_container(self, container_name: str) -> None:
        """Update the Indaleko ArangoDB container"""
        # First, find the info about the container
        if not self.update_arango_image():
            logging.info("ArangoDB image did not change, no need to update container.")
            print("ArangoDB image did not change, no need to update container.")
            return
        container = self.docker_client.containers.get(container_name)
        logging.debug(
            "Container %s: %s", container_name, json.dumps(container.attrs, indent=2)
        )
        mounts = container.attrs["HostConfig"]["Mounts"]
        db_mount = None
        for mount in mounts:
            if (
                mount["Type"] == "volume"
                and utils.misc.file_name_management.indaleko_file_name_prefix
                in mount["Source"]
            ):
                assert db_mount is None, "Found more than one Indaleko volume mount"
                db_mount = mount["Source"]
        assert db_mount is not None, "Could not find Indaleko volume mount"
        db_password = container.attrs["Config"]["Env"][0].split("=")[1]
        # Now, find the info about the volume
        logging.info("Found mount %s for container %s", db_mount, container_name)
        logging.warning(
            "Note: if this update is interrupted, "
            "you may need to manually rebuild the container and re-attach the volume."
        )
        logging.info("docker rm %s", container_name)
        logging.info("docker pull arangodb/arangodb:latest")
        create_cmd = f"docker create --name {container_name} "
        create_cmd += f"-p 8529:8529 -v {db_mount}:/var/lib/arangodb3"
        create_cmd += f"-e ARANGO_ROOT_PASSWORD={db_password} arangodb/arangodb:latest"
        logging.info(create_cmd)
        # delete the existing container
        self.delete_container(container_name=container_name, stop=True)
        # update the arango image
        self.update_arango_image()
        # create a new container (using updated image)
        self.create_container(
            container_name=container_name, volume_name=db_mount, password=db_password
        )
        print(f"Updated container {container_name} to latest image.")

    def create_volume(self, volume_name: str) -> None:
        """Add a new Indaleko related Docker volume."""
        assert volume_name is not None, "volume_name must be provided"
        all_volumes = self.list_volumes()
        if volume_name in all_volumes:
            logging.warning("Volume %s already exists.", volume_name)
            return
        self.docker_client.volumes.create(volume_name)
        logging.info("Created volume %s", volume_name)

    def reset_container_volume(self, container_name: str) -> None:
        """
        Delete the volume for an existing container.  This preserves the
        container information but uses a new volume.
        """
        if container_name is None:
            raise ValueError("container_name must be provided")
        if container_name not in self.list_containers(all=True):
            logging.warning(
                "Container %s does not exist, cannot reset volume", container_name
            )
            print(f"Container {container_name} does not exist, cannot reset volume")
            return
        container = self.docker_client.containers.get(container_name)
        logging.debug(
            "Container %s: %s", container_name, json.dumps(container.attrs, indent=2)
        )
        if "HostConfig" not in container.attrs:
            logging.warning(
                "Container %s has no HostConfig, cannot reset volume", container_name
            )
            print(f"Container {container_name} has no HostConfig, cannot reset volume")
            return
        if "Mounts" not in container.attrs["HostConfig"]:
            logging.warning(
                "Container %s has no mounts, cannot reset volume", container_name
            )
            print(f"Container {container_name} has no mounts, cannot reset volume")
            return
        mounts = container.attrs["HostConfig"]["Mounts"]
        db_mount = None
        for mount in mounts:
            if (
                mount["Type"] == "volume"
                and utils.misc.file_name_management.indaleko_file_name_prefix
                in mount["Source"]
            ):
                assert db_mount is None, "Found more than one Indaleko volume mount"
                db_mount = mount["Source"]
        assert db_mount is not None, "Could not find Indaleko volume mount"
        db_password = container.attrs["Config"]["Env"][0].split("=")[1]
        restart = False
        if container_name in self.list_containers():
            logging.info(
                "Stopping container %s (before resetting volume)", container_name
            )
            self.stop_container(container_name)
            restart = True
        logging.info("Deleting container %s (resetting volume)", container_name)
        self.delete_container(container_name=container_name)
        logging.info("Deleting volume %s (resetting volume)", db_mount)
        self.delete_volume(volume_name=db_mount)
        logging.info("Creating volume %s (reset volume)", db_mount)
        self.create_volume(volume_name=db_mount)
        logging.info("Creating container %s (reset volume)", container_name)
        self.create_container(
            container_name=container_name, volume_name=db_mount, password=db_password
        )
        if restart:
            logging.info("Starting container %s (reset volume)", container_name)
            self.start_container(container_name)


def list_volumes(args: argparse.Namespace) -> None:
    """List the Indaleko related Docker volumes."""
    assert hasattr(args, "indaleko_docker"), "args does not have indaleko_docker"
    volumes = args.indaleko_docker.list_volumes()
    print("Indaleko volumes:")
    for volume in volumes:
        print("  {}".format(volume))


def list_containers(args: argparse.Namespace) -> None:
    """List the Indaleko related Docker containers."""
    assert hasattr(args, "indaleko_docker"), "args does not have indaleko_docker"
    all_containers = args.indaleko_docker.list_containers(all=True)
    running_containers = args.indaleko_docker.list_containers()
    if not hasattr(args, "all"):
        args.all = False
    if args.all:
        containers = all_containers
    else:
        containers = running_containers
    print("Indaleko containers:")
    for container in containers:
        if container in running_containers:
            print("  {} (running)".format(container))
        else:
            print("  {} (stopped)".format(container))


def stop_command(args: argparse.Namespace) -> None:
    """Stop the Indaleko related Docker containers."""
    assert hasattr(args, "indaleko_docker"), "args does not have indaleko_docker"
    containers = args.indaleko_docker.list_containers()
    for container in containers:
        print("Stopping container {}".format(container))
        args.indaleko_docker.stop_container(container)


def start_command(args: argparse.Namespace) -> None:
    """Start the Indaleko related Docker containers."""
    assert hasattr(args, "indaleko_docker"), "args does not have indaleko_docker"
    all_containers = args.indaleko_docker.list_containers(all=True)
    running_containers = args.indaleko_docker.list_containers()
    if len(running_containers) > 0:
        logging.warning("Indaleko containers already running: %s", running_containers)
        print("Indaleko containers already running:")
        for container in running_containers:
            print("  {}".format(container))
        return
    container = all_containers[-1]  # newest one
    print(
        "Starting container {} returns {}".format(
            container, args.indaleko_docker.start_container(container)
        )
    )


def update_command(args: argparse.Namespace) -> None:
    """Update the Indaleko related Docker containers."""
    print("Updating ArangoDB and containers depending upon it.")
    assert hasattr(args, "indaleko_docker"), "args does not have indaleko_docker"
    containers = args.indaleko_docker.list_containers(all=args.all)
    for container in containers:
        logging.info("Updating container %s", container)
        print("Updating container {}".format(container))
        args.indaleko_docker.update_container(container)


def reset_command(args: argparse.Namespace) -> None:
    """Reset the Indaleko related Docker containers."""
    print("Resetting ArangoDB and containers depending upon it.")
    assert hasattr(args, "indaleko_docker"), "args does not have indaleko_docker"
    if not hasattr(args, "all"):
        args.all = False
    containers = args.indaleko_docker.list_containers(all=args.all)
    for container in containers:
        logging.info("Resetting container %s", container)
        print("Resetting container {}".format(container))
        args.indaleko_docker.reset_container_volume(container)


def main():
    """Main function for the IndalekoDocker class."""
    print("Welcome to Indaleko Docker Management")
    parser = argparse.ArgumentParser(description="Indaleko docker management")
    parser.add_argument(
        "--log-level", default=logging.INFO, help="Set the logging level."
    )
    parser.add_argument(
        "--log-file",
        default=IndalekoLogging.generate_log_file_name(service_name="IndalekoDocker"),
        help="Set the logging file.",
    )
    parser.add_argument(
        "--log-dir",
        default=utils.misc.directory_management.indaleko_default_log_dir,
        help="Set the logging directory.",
    )
    subparser = parser.add_subparsers(
        dest="command", title="command", help="command to execute"
    )
    list_parser = subparser.add_parser(
        "list",
        help=f"List all {utils.misc.file_name_management.indaleko_file_name_prefix} containers.",
    )
    list_parser.add_argument(
        "--all", default=False, action="store_true", help="List all containers."
    )
    parser.set_defaults(func=list_containers)
    listvol_parser = subparser.add_parser(
        "listvol",
        help=f"List all {utils.misc.file_name_management.indaleko_file_name_prefix} volumes.",
    )
    listvol_parser.set_defaults(func=list_volumes)
    start_parser = subparser.add_parser(
        "start",
        help=f"Start the {utils.misc.file_name_management.indaleko_file_name_prefix} containers.",
    )
    start_parser.set_defaults(func=start_command)
    stop_parser = subparser.add_parser(
        "stop",
        help=f"Stop the {utils.misc.file_name_management.indaleko_file_name_prefix} containers.",
    )
    stop_parser.set_defaults(func=stop_command)
    update_parser = subparser.add_parser(
        "update",
        help=f"Update the {utils.misc.file_name_management.indaleko_file_name_prefix} containers.",
    )
    update_parser.add_argument(
        "--all", default=False, action="store_true", help="Update all containers."
    )
    update_parser.set_defaults(func=update_command)
    reset_parser = subparser.add_parser(
        "reset",
        help=f"Reset the {utils.misc.file_name_management.indaleko_file_name_prefix} container volumes.",
    )
    reset_parser.add_argument(
        "--all", default=False, action="store_true", help="Reset all containers."
    )
    reset_parser.set_defaults(func=reset_command)
    args = parser.parse_args()
    indaleko_logging = IndalekoLogging(
        service_name="IndalekoDocker",
        log_level=args.log_level,
        log_file=args.log_file,
        log_dir=args.log_dir,
    )
    # Logging must start before docker is initialized.
    logging.info(args)
    indaleko_docker = IndalekoDocker()
    logging.info("IndalekoDocker initialized, Docker connection instantiated.")
    args.indaleko_docker = indaleko_docker
    args.indaleko_logging = indaleko_logging
    args.func(args)
    logging.info("IndalekoDocker exiting...")


if __name__ == "__main__":
    main()
