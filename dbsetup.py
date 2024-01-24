#!/usr/bin/python3
'''
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

import os
import argparse
import subprocess
import datetime
import logging
from Indaleko import Indaleko
from arango import ArangoClient
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollections


def resetdb(args : argparse.Namespace) -> None:
    assert args.reset is True, 'resetdb called without --reset'

def run_command(command : str) -> None:
    try:
        output = subprocess.check_output(command, stderr = subprocess.STDOUT, shell=True)
        logging.debug(f"Command `{command}` returned:\n{output.decode('utf-8').strip()}")
        return output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        logging.debug(f"Command `{command}` failed with error:\n{e.output.decode('utf-8').strip()}")
        return None

def stop_container(container_name_or_id : str) -> None:
    cmd = f"docker stop {container_name_or_id}"
    logging.debug(f"Running command: {cmd}")
    res = run_command(cmd)
    assert res is not None, f"Could not stop container {container_name_or_id}"


def remove_container(container_name_or_id : str) -> None:
    cmd=f"docker rm {container_name_or_id}"
    logging.debug(f"Running command: {cmd}")
    return run_command(cmd)

def remove_volume(volume_name : str) -> None:
    cmd = f"docker volume rm {volume_name}"
    logging.debug(f"Running command: {cmd}")
    return run_command(f"docker volume rm {volume_name}")

def get_latest_image(image_name : str = 'arangodb/arangodb') -> str:
    return run_command(f"docker pull {image_name}:latest")


def create_volume(config : IndalekoDBConfig = None):
    assert config is not None, 'No config found'
    # return run_command(f"docker volume create {volume_name}")
    cmd = f"docker volume create {config.config['database']['volume']}"
    logging.debug(f"Running command: {cmd}")
    # return run_command(cmd)

def create_container(config : IndalekoDBConfig = None):
    # docker run -e ARANGO_ROOT_PASSWORD=Kwishut22 -d -p 8529:8529 --mount source=ArangoDB-wam-db-1,target=/var/lib/arangodb3 --name arangodb-instance arangodb
    assert config is not None, 'No config found'
    cmd = "docker run "
    passwd = config.config['database']['admin_passwd']
    cmd += f'-e ARANGO_ROOT_PASSWORD="{passwd}" '
    cmd += "-d "
    cmd += f"-p {config.config['database']['port']}:8529 "
    cmd += f"--mount source={config.config['database']['volume']},target=/var/lib/arangodb3 "
    cmd += f"--name {config.config['database']['container']} "
    cmd += "arangodb"
    logging.debug(f"Running command: {cmd}")
    return run_command(cmd)

def create_user(config : IndalekoDBConfig = None):
    assert config is not None, 'No config found'
    assert config.config['database']['user'] is not None, 'No database user found'
    cmd = f"docker exec -it {config.config['database']['container']} arangosh --server.password {config.config['database']['admin_passwd']} --javascript.execute-string 'require(\"@arangodb/users\").save(\"{config.config['database']['user']}\", \"{config.config['database']['admin_passwd']}\")'"
    logging.debug(f"Running command: {cmd}")
    return run_command(cmd)

def setup(config : IndalekoDBConfig = None):
    if config is None:
        config = IndalekoDBConfig()
    assert config is not None, 'No config found'
    get_latest_image()
    create_volume(config)
    create_container(config)


def cleanup(config :IndalekoDBConfig):
    assert config is not None, 'No config found'
    if 'database' in config.config:
        if 'container' in config.config['database']:
            stop_container(config.config['database']['container'])
            remove_container(config.config['database']['container'])
        if 'volume' in config.config['database']:
            remove_volume(config.config['database']['volume'])

def startup(config: IndalekoDBConfig):
    running_containers = run_command('docker ps')
    logging.debug(f"Running containers (pre-stop):\n{running_containers}")
    cmd = f"docker start {config.config['database']['container']}"
    logging.debug(f"Running command: {cmd}")
    running_containers = run_command('docker ps')
    logging.debug(f"Running containers (post-stop):\n{running_containers}")
    return run_command(cmd)

def main():
    new_config = False
    starttime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logfile = f'dbsetup-{starttime}.log'
    parser = argparse.ArgumentParser(description='Set up and start the database(s) for Indaleko')
    parser.add_argument('--config_dir', default=Indaleko.default_config_dir, help='Directory where the config file is stored')
    parser.add_argument('--data_dir', default=Indaleko.default_data_dir, help='Directory where the database data is stored')
    parser.add_argument('--log_dir', help='Log directory to use', default=Indaleko.default_log_dir)
    parser.add_argument('--passwd', '-p', help='Database password to use', default=None)
    parser.add_argument('--reset', '-r', help='Delete the existing database, generate a new config file, build new database', action='store_true', default=False)
    parser.add_argument('--regen', help='Regenerate the database using the same config file.', action='store_true', default=False)
    parser.add_argument('--log', '-l', help='Log file to use', default=logfile)
    args = parser.parse_args()

    def create_secure_directory(directory : str) -> None:
        """Create a directory with secure permissions"""
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o700)

    def database_is_local(config : IndalekoDBConfig) -> bool:
        """Check if the database is local or remote."""
        return config.get_ipaddr() == 'localhost' or config.get_ipaddr() == '127.0.0.1' or config.get_ipaddr() == '::1'

    # make sure the following folders exist:
    #  1- `logs`: for the logs
    #  2- `config`: for the adb .ini configs
    list(map(lambda x: create_secure_directory(x), [args.log_dir, args.config_dir, args.data_dir]))

    logging.basicConfig(filename=os.path.join(args.logdir, args.log), level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f'Begin run at {starttime}')
    assert not (args.reset and args.regen), 'Cannot reset and regenerate at the same time'
    if not os.path.exists(args.config):
        logging.info('No config file found, generating new one')
        new_config = True
    elif args.reset or args.regen:
        if not database_is_local(config):
            logging.error('Cannot reset or regenerate remote database')
            print('Cannot reset or regenerate remote database.  Terminating.')
            exit(1)
        if args.reset:
            logging.info('Resetting database')
        else:
            logging.info('Regenerating database')
        config = IndalekoDBConfig(args.config) # load existing
        logging.info('Cleanup previous database')
        cleanup(config)
        if args.reset:
            logging.info('Deleting config file')
            config.delete_config()
            new_config = True
        # TODO: we could probably delete the collections
        # and re-create them from a remote if that would be useful.
    else:
        logging.info('Loading existing config')
        config = IndalekoDBConfig(args.config)
    # load existing or generate new
    config = IndalekoDBConfig(args.config) # load config file if it exists
    if new_config:
        logging.info('Generated new config')
        setup(config)
    logging.info('Starting database')
    startup(config)
    logging.info('Configuring database')
    IndalekoCollections(config, args.reset)
    logging.info('Collection creation complete')
    logging.info('Database setup and configuration complete')


if __name__ == '__main__':
    main()
