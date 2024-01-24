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
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollections


def resetdb(args : argparse.Namespace) -> None:
    """Reset the database"""
    assert args.reset is True, 'resetdb called without --reset'

def run_command(command : str) -> None:
    """Run a command, capture and process the output"""
    try:
        logging.debug('Running command: %s', command)
        output = subprocess.check_output(command, stderr = subprocess.STDOUT, shell=True)
        logging.debug("Command `%s` returned:\n%s", command, output.decode('utf-8').strip())
        return output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        logging.debug("Command `%s` failed with error:\n%s",
                      command,
                      e.output.decode('utf-8').strip())
        raise e

def stop_container(container_name_or_id : str) -> None:
    """Stop the docker container for the database"""
    cmd = f"docker stop {container_name_or_id}"
    run_command(cmd)


def remove_container(container_name_or_id : str) -> None:
    """Remove the docker container for the database"""
    cmd=f"docker rm {container_name_or_id}"
    run_command(cmd)


def remove_volume(volume_name : str) -> None:
    """Remove the docker volume for the database"""
    cmd = f"docker volume rm {volume_name}"
    run_command(cmd)


def get_latest_image(image_name : str = 'arangodb/arangodb') -> None:
    """Get the latest docker image for the database"""
    run_command(f"docker pull {image_name}:latest")


def create_volume(config : IndalekoDBConfig = None) -> None:
    """Create the docker volume for the database"""
    assert config is not None, 'No config found'
    cmd = f"docker volume create {config.config['database']['volume']}"
    run_command(cmd)

def create_container(config : IndalekoDBConfig = None):
    """Create the container for the database"""
    assert config is not None, 'No config found'
    cmd = "docker run "
    passwd = config.config['database']['admin_passwd']
    cmd += f'-e ARANGO_ROOT_PASSWORD="{passwd}" '
    cmd += "-d "
    cmd += f"-p {config.config['database']['port']}:8529 "
    cmd += f"--mount source={config.config['database']['volume']},target=/var/lib/arangodb3 "
    cmd += f"--name {config.config['database']['container']} "
    cmd += "arangodb"
    run_command(cmd)

def create_user(config : IndalekoDBConfig = None):
    """Create the user (not root) account in the database"""
    assert config is not None, 'No config found'
    assert config.config['database']['user'] is not None, 'No database user found'
    cmd = f"docker exec -it {config.config['database']['container']} "
    cmd += f"arangosh --server.password {config.config['database']['admin_passwd']} "
    cmd += "--javascript.execute-string "
    cmd += f"'require(\"@arangodb/users\").save(\"{config.config['database']['user']}\", "
    cmd += f"\"{config.config['database']['admin_passwd']}\")'"
    run_command(cmd)

def setup(config : IndalekoDBConfig = None):
    """Setup the container and volume for the database"""
    if config is None:
        config = IndalekoDBConfig()
    assert config is not None, 'No config found'
    get_latest_image()
    create_volume(config)
    create_container(config)


def cleanup(config :IndalekoDBConfig):
    """Cleanup the database and associated resources"""
    assert config is not None, 'No config found'
    if 'database' in config.config:
        if 'container' in config.config['database']:
            stop_container(config.config['database']['container'])
            remove_container(config.config['database']['container'])
        if 'volume' in config.config['database']:
            remove_volume(config.config['database']['volume'])

def startup(config: IndalekoDBConfig):
    """Start the database"""
    running_containers = run_command('docker ps')
    logging.debug("Running containers (pre-stop):\n%s", running_containers)
    cmd = f"docker start {config.config['database']['container']}"
    logging.debug("Running command: %s", cmd)
    running_containers = run_command('docker ps')
    logging.debug("Running containers (post-stop):\n%s", running_containers)
    return run_command(cmd)


def main():
    """Main entry point for the program"""
    new_config = False
    starttime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logfile = f'dbsetup-{starttime}.log'
    parser = argparse.ArgumentParser(description='Set up and start the database(s) for Indaleko')
    parser.add_argument('--config_dir',
                        default=Indaleko.default_config_dir,
                        help='Directory where the config file is stored')
    parser.add_argument('--data_dir',
                        default=Indaleko.default_data_dir,
                        help='Directory where the database data is stored')
    parser.add_argument('--config',
                        help='Config file to use',
                        default=os.path.join(Indaleko.default_config_dir, 'indaleko-db-config.ini'))
    parser.add_argument('--log_dir',
                        help='Log directory to use',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--passwd',
                        help='Database password to use',
                        default=None)
    parser.add_argument('--reset',
                        help='Delete the existing database,' +
                        ' generate a new config file, build new database',
                        action='store_true',
                        default=False)
    parser.add_argument('--regen',
                        help='Regenerate the database using the same config file.',
                        action='store_true', default=False)
    parser.add_argument('--log',
                        help='Log file to use',
                        default=logfile)
    args = parser.parse_args()

    def create_secure_directory(directory : str) -> None:
        """Create a directory with secure permissions"""
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o700)

    def database_is_local(config : IndalekoDBConfig) -> bool:
        """Check if the database is local or remote."""
        return config.get_ipaddr() == 'localhost' \
            or config.get_ipaddr() == '127.0.0.1' \
            or config.get_ipaddr() == '::1'

    create_secure_directory(args.log_dir)
    create_secure_directory(args.config_dir)
    create_secure_directory(args.data_dir)

    logging.basicConfig(filename=os.path.join(args.log_dir, args.log),
                        level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info('Begin run at %s', starttime)
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
        # we could probably delete the collections
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
