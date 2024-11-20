'''
This is the docker support module for using Unstructured within Indaleko.

Project Indaleko
Copyright (C) 2024 Tony Mason

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


# standard imports
import argparse
import datetime
import docker
import logging
import os
import sys

# third-party imports
import docker.errors
from icecream import ic

# Indaleko imports

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from IndalekoDocker import IndalekoDocker
from IndalekoLogging import IndalekoLogging
# pylint: enable=wrong-import-position


class IndalekoUnstructuredDocker(IndalekoDocker):
    '''
    Support for running the Unstructured utility within a Docker container
    and exchanging data between the container and the host.
    '''
    default_image_name = 'downloads.unstructured.io/unstructured-io/unstructured'

    def __init__(self, **kwargs) -> None:
        '''Initialize the Docker support for Unstructured'''
        self.config_dir = kwargs.get('config_dir', Indaleko.default_config_dir)
        self.data_dir = kwargs.get('data_dir', Indaleko.default_data_dir)
        self.log_dir = kwargs.get('log_dir', Indaleko.default_log_dir)
        if not os.path.exists(self.config_dir)\
             or not os.path.exists(self.data_dir)\
                or not os.path.exists(self.log_dir):
              Indaleko.create_secure_directories([
                    self.config_dir,
                    self.data_dir,
                    self.log_dir
              ])
        if root_dir is None:
            root_dir = os.environ.get('INDALEKO_ROOT')
        self.root_dir = root_dir
        self.config_dir = os.path.join(self.root_dir, Indaleko.default_config_dir)


        super().__init__()
        assert hasattr(self, 'docker_client') and self.docker_client is not None, 'Docker client is not initialized'
        self.docker_client.ping()


    def get_image(self, image_name : str) -> dict:
        '''Get the Docker image by name'''
        try:
            current_image = self.docker_client.images.get(image_name)
        except docker.errors.ImageNotFound as ex:
            ic(ex)
        self.docker_client.images.pull(image_name)
        new_image = self.docker_client.images.get(image_name)
        return current_image.id == new_image.id

    def update_unstructured_image(self, image_name : str = default_image_name) -> bool:
        '''
        Update the Unstructured Docker image

        Returns:
            True - docker image wasa updated
            False - docker image was not updated
        '''

    @staticmethod
    def update_image(image_name : str) -> bool:
        '''Update the Docker image'''
        docker_client = docker.from_env()
        current_image = None
        try:
            current_image = docker_client.images.get(IndalekoUnstructuredDocker.default_image_name)
        except docker.errors.ImageNotFound as ex:
            ic(ex)
        if current_image is not None and not args.update:
            ic(f"Unstructured Docker image found: {current_image.id}")
            return False
        new_image = docker_client.images.pull(IndalekoUnstructuredDocker.default_image_name)
        if current_image is not None or current_image.id != new_image.id:
            ic(f"Unstructured Docker image is up to date: {new_image.id}")
            return True
        ic('Unstructured Docker image updated')
        return False


    @staticmethod
    def install_command(args : argparse.Namespace) -> None:
        '''Install the Unstructured Docker container'''
        updated = IndalekoUnstructuredDocker.update_image(args.image)
        if updated:
            ic(f'Updated Unstructured Docker image {args.image}')
        else:
            ic(f'Using existing Unstructured Docker image {args.image}')
        ic('Unstructured Docker image updated')


    @staticmethod
    def list_command(args : argparse.Namespace) -> None:
        '''List the Unstructured Docker container(s)'''
        docker_client = docker.from_env()
        try:
            count = 0
            for image in docker_client.images.list():
                if 'unstructured' not in image.tags:
                    continue
                ic(f"Image ID: {image.id}, Tags: {image.tags}")
                count += 1
            if count == 0:
                ic("No Unstructured Docker images found")
        except docker.errors.DockerException as ex:
            ic(f"Error listing Docker images: {ex}")

    @staticmethod
    def start_command(args : argparse.Namespace) -> None:
        '''Start the Unstructured Docker container'''
        raise NotImplementedError('Not yet implemented')

    @staticmethod
    def stop_command(args : argparse.Namespace) -> None:
        '''Stop the Unstructured Docker container'''
        raise NotImplementedError('Not yet implemented')

    @staticmethod
    def uninstall_command(args : argparse.Namespace) -> None:
        '''Uninstall the Unstructured Docker container'''
        raise NotImplementedError('Not yet implemented')

def main():
    '''This is the entry point for testing the docker/unstructured integration in Indaleko.'''
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()
    parser = argparse.ArgumentParser(description='Indaleko Unstructured Docker Support')
    parser.add_argument('--logdir' , type=str, default=Indaleko.default_log_dir, help='Log directory')
    parser.add_argument('--log', type=str, default=None, help='Log file name')
    parser.add_argument('--loglevel',
                        type=int,
                        default=logging.DEBUG,
                        choices=IndalekoLogging.get_logging_levels(),
                        help='Log level')
    parser.add_argument('--image', type=str,
                         default=IndalekoUnstructuredDocker.default_image_name,
                         help='Docker image name')
    command_subparser = parser.add_subparsers(dest='command', help='Command to execute')
    parser_install = command_subparser.add_parser('install',
                                                  help='Install the Unstructured Docker container')
    parser_install.add_argument('--update', action='store_true', help='Update the Unstructured Docker image')
    parser_install.set_defaults(func=IndalekoUnstructuredDocker.install_command)
    parser_list = command_subparser.add_parser('list',
                                               help='List the Unstructured Docker container(s)')
    parser_list.set_defaults(func=IndalekoUnstructuredDocker.list_command)
    parser_start = command_subparser.add_parser('start',
                                                help='Start the Unstructured Docker container')
    parser_start.set_defaults(func=IndalekoUnstructuredDocker.start_command)
    parser_stop = command_subparser.add_parser('stop',
                                               help='Stop the Unstructured Docker container')
    parser_stop.set_defaults(func=IndalekoUnstructuredDocker.stop_command)
    parser_uninstall = command_subparser.add_parser('uninstall',
                                                    help='Uninstall the Unstructured Docker container')
    parser_uninstall.set_defaults(func=IndalekoUnstructuredDocker.uninstall_command)
    parser.set_defaults(func=IndalekoUnstructuredDocker.list_command)
    args = parser.parse_args()
    ic(args)
    ic(timestamp)
    args.func(args)


if __name__ == '__main__':
    main()
