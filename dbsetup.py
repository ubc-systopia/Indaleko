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
    """Run a command, capture and process the output. Do not use shell=True"""
    assert isinstance(command, list), 'command is not a list'
    try:
        cmd = ' '.join(command)
        logging.debug('Running command: %s', cmd)
        output = subprocess.check_output(command, stderr = subprocess.STDOUT).decode('utf-8').strip()
        logging.debug("Command `%s` returned:\n%s", cmd, output)
        return output
    except subprocess.CalledProcessError as e:
        logging.debug("Command `%s` failed with error:\n%s",
                      command,
                      e.output.decode('utf-8').strip())
        raise e

def stop_container(container_name_or_id : str) -> None:
    """Stop the docker container for the database"""
    cmd = ['docker', 'ps',  '--all']
    containers = run_command(cmd)
    if container_name_or_id not in containers:
        # doesn't exist so we can't stop it
        return
    cmd = ['docker', 'ps']
    containers = run_command(cmd)
    if container_name_or_id not in containers:
        # not running so we can't stop it
        logging.info('Container %s not running', container_name_or_id)
        return
    cmd = ['docker', 'stop',  container_name_or_id]
    run_command(cmd)


def remove_container(container_name_or_id : str) -> None:
    """Remove the docker container for the database"""
    cmd = ['docker', 'ps']
    containers = run_command(cmd)
    if container_name_or_id in containers:
        logging.error('Cannot remove running container')
        logging.error('Aborting')
        exit(1)
    cmd = ['docker', 'ps',  '--all']
    containers = run_command(cmd)
    if container_name_or_id not in containers:
        # doesn't exist so we can't remove it
        logging.warning('Container %s does not exist, not removing', container_name_or_id)
        return
    cmd=['docker', 'rm', container_name_or_id]
    run_command(cmd)


def remove_volume(volume_name : str) -> None:
    """Remove the docker volume for the database"""
    cmd = ['docker', 'volume', 'ls']
    volumes = run_command(cmd)
    if volume_name not in volumes:
        # doesn't exist so we can't remove it
        return
    cmd = ['docker', 'volume', 'rm', volume_name]
    run_command(cmd)

def list_volumes() -> list:
    """List the docker volumes"""
    cmd = ['docker', 'volume', 'ls']
    response =  run_command(cmd)
    return [x for x in response.split('\n') if len(x) > 0 and 'indaleko' in x]

def list_containers(running_only : bool = False) -> list:
    """List the docker containers"""
    cmd = ['docker', 'ps']
    if not running_only:
        cmd.append('--all')
    response = run_command(cmd)
    containers = []
    for line in response.split('\n'):
        if 'indaleko' in line:
            containers.append([x for x in line.split(' ') if len(x) > 0][-1])
    return containers

def does_container_exist(container_name_or_id : str) -> bool:
    """Check if the container exists"""
    cmd = ['docker', 'ps', '--all']
    containers = run_command(cmd)
    return container_name_or_id in containers

def get_latest_image(image_name : str = 'arangodb/arangodb') -> None:
    """Get the latest docker image for the database"""
    cmd = ['docker', 'pull', f'{image_name}:latest']
    run_command(cmd)


def create_volume(config : IndalekoDBConfig = None) -> None:
    """Create the docker volume for the database"""
    assert config is not None, 'No config found'
    cmd = ['docker', 'volume', 'ls']
    volumes = run_command(cmd)
    if config.config['database']['volume'] in volumes:
        # already exists so we can't create it
        logging.error('Volume %s already exists', config.config['database']['volume'])
        logging.error('Aborting')
        exit(1)
    cmd = ['docker', 'volume', 'create', config.config['database']['volume']]
    run_command(cmd)

def create_container(config : IndalekoDBConfig = None):
    """Create the container for the database"""
    assert config is not None, 'No config found'
    cmd = [
        'docker',
        'run',
        '-e',
        f'ARANGO_ROOT_PASSWORD={config.config["database"]["admin_passwd"]}',
        '-d',
        '-p',
        f'{config.config["database"]["port"]}:8529',
        '--mount',
        f'source={config.config["database"]["volume"]},target=/var/lib/arangodb3',
        '--name',
        config.config['database']['container'],
        'arangodb'
    ]
    run_command(cmd)

def setup(config : IndalekoDBConfig = None):
    """Setup the container and volume for the database"""
    if config is None:
        config = IndalekoDBConfig()
    assert config is not None, 'No config found'
    logging.debug('Setup configuration for:\n%s', config['database']['container'])
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
    running_containers = run_command(['docker', 'ps'])
    logging.debug("Running containers (pre-stop):\n%s", running_containers)
    if config.config['database']['container'] in running_containers:
        logging.info('Database already running')
        return
    cmd = ['docker', 'start', config.config['database']['container']]
    results = run_command(cmd)
    running_containers = run_command(['docker',  'ps'])
    logging.debug("Running containers (post-stop):\n%s", running_containers)

def list_command(args : argparse.Namespace) -> None:
    """List the databases and/or containers"""
    logging.debug('list command: %s', args)
    if not args.volumes and not args.containers:
        args.all = True
    if args.volumes or args.all:
        print('Indaleko volumes:')
        volumes = list_volumes()
        if len(volumes) == 0:
            print('\t', 'None')
        else:
            for volume in volumes:
                print('\t', volume)
    if args.containers or args.all:
        containers = list_containers()
        running_containers = list_containers(running_only=True)
        print('Indaleko containers:')
        if len(containers) == 0:
            print('\t', 'None')
        else:
            for container in containers:
                suffix = ''
                if container in running_containers:
                    suffix = ' (running)'
                print('\t', container, suffix)


def cleanup_command(args : argparse.Namespace) -> None:
    """Cleanup the databases"""
    if args.timestamp is not None:
        logging.info('Cleaning up databases for timestamp %s', args.timestamp)
    assert False, 'Not implemented'

def delete_command(args : argparse.Namespace) -> None:
    """Delete a specific database"""
    # if they specified a timestamp, delete the volume and container for that
    # timestamp
    if args.timestamp is not None:
        assert args.config is None, 'Cannot specify both timestamp and config'
        logging.info('Deleting database for timestamp %s', args.timestamp)
        volumes = list_volumes()
        running_containers = list_containers(running_only=True)
        all_containers = list_containers()
        for container in running_containers:
            if args.timestamp == container:
                logging.warning('Container %s is running, not safe to delete')
                print('Container is running, not safe to delete')
                return
        for container in all_containers:
            if args.timestamp in container:
                logging.info('Removing container %s', container)
                remove_container(container)
        for volume in volumes:
            if args.timestamp in volume:
                volume = volume.split(' ')[-1]
                logging.info('Removing volume %s', volume)
                remove_volume(volume)
    if args.config is not None:
        assert os.path.exists(args.config), f'Config file {args.config} does not exist'
        config = IndalekoDBConfig(args.config)
    else:
        config = IndalekoDBConfig()
    if config is not None:
        cleanup(config)

def create_command(args : argparse.Namespace) -> None:
    """Create a new database"""
    logging.info
    if args.config is not None:
        if os.path.exists(args.config):
            logging.warning('Config file %s already exists')
            if not args.overwrite:
                logging.error('Config file %s already exists, not deleting', args.config)
                print('Config file already exists, not deleting')
                exit(1)
            try:
                old_config = IndalekoDBConfig(args.config)
                try:
                    os.rename(args.config, f'{args.config}-{old_config['database']['timestamp']}.bak')
                except KeyError:
                    logging.error('Invalid config file %s, deleting', args.config)
                    os.remove(args.config)
            except ValueError:
                os.remove(args.config)
        config = IndalekoDBConfig(args.config)
    else:
        config = IndalekoDBConfig()
    if config is not None:
        setup(config)
    if args.startup:
        startup(config)
    logging.info('Database setup complete, timestamp is %s', config['database']['timestamp'])


def reset_command(args : argparse.Namespace) -> None:
    """Reset a database to a clean state"""
    if args.timestamp is not None:
        logging.info('Cleaning up databases for timestamp %s', args.timestamp)
    assert False, 'Not implemented'

def start_command(args : argparse.Namespace) -> None:
    """Start an existing database"""
    if args.timestamp is not None:
        logging.info('Cleaning up databases for timestamp %s', args.timestamp)
    assert False, 'Not implemented'

def stop_command(args : argparse.Namespace) -> None:
    """Stop a running database"""
    existing_volumes =[x.split(' ')[-1] for x in list_volumes()]
    running_containers = [x.split(' ')[-1] for x in list_containers(running_only=True)]
    all_containers = [x.split(' ')[-1] for x in list_containers()]
    print(all_containers)
    print(running_containers)
    print(existing_volumes)
    if args.timestamp is not None:
        if args.timestamp not in all_containers:
            logging.warning('Container with timestamp %s does not exist', args.timestamp)
            print('Container with timestamp', args.timestamp, 'does not exist')
            return
        if args.timestamp in running_containers:
            for container in running_containers:
                if args.timestamp == container:
                    logging.info('Stopping container %s', container)
                    stop_container(container)
        if args.timestamp in all_containers:
            for container in all_containers:
                if args.timestamp == container:
                    logging.info('Removing container %s', container)
                    remove_container(container)
        if args.timestamp in existing_volumes:
            for volume in existing_volumes:
                if args.timestamp == volume:
                    logging.info('Removing volume %s', volume)
                    remove_volume(volume)
        logging.info('Cleaned up database for timestamp %s', args.timestamp)
        return
    config = IndalekoDBConfig()
    container_name = config['database']['container']
    found = False
    if container_name in running_containers:
        stop_container(args.name)
        found = True
    else:
        if container_name in all_containers:
            logging.warning('Container %s not running', args.name)
            found = True
    if found and args.delete:
        for container in all_containers:
            if container_name == container:
                logging.info('Removing container %s', container)
                remove_container(container)
    found = False
    volume_name = config['database']['volume']
    logging.info('Removing volume %s', volume_name)
    remove_volume(volume_name)

def setup_command(args : argparse.Namespace) -> None:
    """
    This provides the default behavior, which is to set up a clean instance
    of the database.
    """
    print('Set up a clean instance of the database')
    print('Not yet implemented')

def main():
    """Main entry point for the program"""
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp=now.isoformat()
    starttime = now.strftime("%Y%m%d%H%M%S")
    parser = argparse.ArgumentParser(description='Manage Indaleko databases')
    parser.add_argument('--log_dir',
                        help='Log directory to use',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--log', help='Log file to write',
                        default=f'dbsetup-{starttime}.log')
    command_subparser = parser.add_subparsers(dest='command')
    parser_list = command_subparser.add_parser('list', help='List the databases')
    parser_list.add_argument('--volumes', action='store_true', help='List the volumes')
    parser_list.add_argument('--containers', action='store_true', help='List the containers')
    parser_list.add_argument('--all', action='store_true', help='List both volumes and containers')
    parser_list.set_defaults(func=list_command)
    parser_cleanup = command_subparser.add_parser('cleanup', help='Cleanup the databases')
    parser_cleanup.add_argument('--timestamp', type=str, help='Timestamp to delete')
    parser_cleanup.set_defaults(func=cleanup_command)
    parser_delete = command_subparser.add_parser('delete', help='Delete a specific database')
    parser_delete.add_argument('--config', type=str, help='Config file to use')
    parser_delete.add_argument('--timestamp', type=str, help='Timestamp to delete')
    parser_delete.set_defaults(func=delete_command)
    parser_create = command_subparser.add_parser('create', help='Create a new database')
    parser_create.add_argument('--config', type=str, help='Config file to use')
    parser_create.add_argument('--overwrite', action='store_true', help='Delete the configuration file if it exists')
    parser_create.add_argument('--startup', action='store_true', help='Start the database after creating it')
    parser_create.set_defaults(func=create_command)
    parser_reset = command_subparser.add_parser('reset', help='Reset a database to a clean state')
    parser_reset.add_argument('--config', type=str, help='Config file to use')
    parser_reset.set_defaults(func=reset_command)
    parser_start = command_subparser.add_parser('start', help='Start a database')
    parser_start.add_argument('--config', type=str, help='Config file to use')
    parser_start.add_argument('--create', action='store_true', help='Create the database if it does not exist')
    parser_start.set_defaults(func=start_command)
    parser_stop = command_subparser.add_parser('stop', help='Stop a database')
    parser_stop.add_argument('--config', type=str, help='Config file to use')
    parser_stop.add_argument('--timestamp', type=str, help='Timestamp to delete')
    parser_stop.add_argument('--delete', action='store_true', help='Delete the database after stopping it')
    parser_stop.set_defaults(func=stop_command)
    parser_setup = command_subparser.add_parser('setup', help='Set up a clean instance of the database')
    parser_setup.set_defaults(func=setup_command)
    parser.set_defaults(command='setup', func=setup_command)
    args = parser.parse_args()
    args.func(args)
    # set up logging
    if args.log is None:
        args.log = Indaleko.generate_file_name(
                        suffix='log',
                        service='dbsetup',
                        timestamp=timestamp
                    )
    log_name = os.path.join(args.log_dir, args.log)
    logging.basicConfig(filename=log_name, level=logging.DEBUG)
    logging.info('Starting Indaleko database setup')
    logging.info(f'Logging to {log_name}')
    print(args)
    dispatch = {
        'list': list_command,
        'cleanup': cleanup_command,
        'delete': delete_command,
        'create': create_command,
        'reset': reset_command,
        'start': start_command,
        'stop': stop_command,
        'setup': setup_command,
    }
    if args.command not in dispatch:
        print(f'Unknown command: {args.command}')
        exit(1)
    dispatch[args.command](args)
    return
    if args.command == 'list':
        if not args.volumes and not args.containers:
            args.all = True
        if args.volumes or args.all:
            print(list_volumes())
        if args.containers or args.all:
            print(list_containers())

    print(list_volumes())
    print(list_containers())
    return
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
        assert isinstance(config, IndalekoDBConfig), 'config is not an IndalekoDBConfig'
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
    new_config = False
    assert not (args.reset and args.regen), 'Cannot reset and regenerate at the same time'
    config = None
    if not os.path.exists(args.config):
        if args.regen:
            print('Cannot regenerate database without existing config file.  Terminating.')
            logging.error('Cannot regenerate database without existing config file')
            exit(1)
        logging.info('No config file found, generating new one')
        config = IndalekoDBConfig(args.config)
        new_config = True
    else:
        logging.info('Loading existing config')
        config = IndalekoDBConfig(args.config, no_new_config=args.regen)
        if not database_is_local(config):
            logging.error('Cannot reset or regenerate remote database')
            print('Cannot reset or regenerate remote database.  Terminating.')
            exit(1)
        logging.info('Resetting database')
        cleanup(config)
        if args.reset:
            logging.info('Deleting config file')
            config.delete_config()
            config = IndalekoDBConfig(args.config)
            new_config = True
        logging.info('Generated new config')
    if new_config:
        setup(config)
    logging.info('Starting database')
    startup(config)
    logging.info('Configuring database')
    IndalekoCollections(config, args.reset)
    logging.info('Collection creation complete')
    logging.info('Database setup and configuration complete')


if __name__ == '__main__':
    main()
