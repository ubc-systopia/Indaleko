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
from IndalekoLogging import IndalekoLogging
from IndalekoDocker import IndalekoDocker

def setup_command(args : argparse.Namespace) -> None:
    """
    This sets up a clean instance of the database.
    """
    logging.info('Setup new database configuration')
    print('Setup new database configuration')
    if os.path.exists(IndalekoDBConfig.IndalekoDBConfig_default_db_config_file):
        logging.info('Default config file already exists')
        print('Default config file already exists: checking database')
        check_command(args)
        return
    db_config = IndalekoDBConfig()
    if db_config is None:
        logging.critical('Could not create IndalekoDBConfig object')
        exit(1)
    logging.info('Initialize Docker ArangoDB')
    print('Initialize Docker ArangoDB')
    indaleko_docker = IndalekoDocker()
    logging.info('Create container %s with volume %s',
                 db_config.config['database']['container'],
                 db_config.config['database']['volume'])
    print(f"Create container {db_config.config['database']['container']}" +\
          f"with volume {db_config.config['database']['volume']}")
    indaleko_docker.create_container(
        db_config.config['database']['container'],
        db_config.config['database']['volume'],
        db_config.config['database']['admin_passwd'])
    logging.info('Created container %s', db_config.config['database']['container'])
    print(f"Created container {db_config.config['database']['container']}" +\
          f"with volume {db_config.config['database']['volume']}")
    logging.info('Start container %s', db_config.config['database']['container'])
    print(f"Start container {db_config.config['database']['container']}")
    indaleko_docker.start_container(db_config.config['database']['container'])
    logging.info('Connect to database')
    print('Connect to database')
    started = db_config.start()
    if not started:
        logging.critical('Could not start database connection')
        print('Could not start DB connection.  Confirm the docker image is running.')
        return
    logging.info('Database connection successful')

def check_command(args : argparse.Namespace) -> None:
    """Check the database"""
    logging.info('Check the database')
    db_config = IndalekoDBConfig()
    if db_config is None:
        logging.critical('Could not create IndalekoDBConfig object')
        return
    started = db_config.start(timeout=10)
    if not started:
        logging.critical('Could not start the database')
        print('Database is not reachable, check failed')
        return
    logging.info('Database connection successful.')
    print('Database connection successful.')
    # make sure the collections exist
    IndalekoCollections(db_config)


def delete_command(args : argparse.Namespace) -> None:
    """Delete the database"""
    print('Delete the database')
    logging.info('Delete the database and volumes')
    db_config = IndalekoDBConfig()
    if db_config is None:
        logging.critical('Could not create IndalekoDBConfig object')
        return
    container_name = db_config.config['database']['container']
    volume_name = db_config.config['database']['volume']
    logging.info('Delete container %s', container_name)
    print(f"Delete container {container_name}")
    indaleko_docker = IndalekoDocker()
    stop=False
    if hasattr(args, 'force') and args.force:
        stop=True
    try:
        indaleko_docker.delete_container(container_name, stop=stop)
    except:
        logging.error('Could not delete container %s', container_name)
        print(f"Could not delete running container {container_name}")
        return
    logging.info('Delete volume %s', volume_name)
    indaleko_docker.delete_volume(volume_name)
    logging.info('Delete config file %s', db_config.config_file)
    db_config.delete_config()
    logging.info('Database deleted')
    print(f'Database {container_name} deleted')


def default_command(args : argparse.Namespace) -> None:
    """Default command"""
    logging.debug('DBSetup: default command handler invoked')
    if os.path.exists(IndalekoDBConfig.IndalekoDBConfig_default_db_config_file):
        check_command(args)
    else:
        setup_command(args)
    return

def main():
    """Main entry point for the program"""
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp=now.isoformat()
    parser = argparse.ArgumentParser(description='Indaleko DB Setup')
    parser.add_argument('--log_dir',
                        help='Log directory to use',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--log', help='Log file to write')
    parser.add_argument('--loglevel', type=int, default=logging.DEBUG, help='Log level to use')
    command_subparser = parser.add_subparsers(dest='command')
    parser_check = command_subparser.add_parser('check', help='Check the database')
    parser_check.set_defaults(func=check_command)
    parser_setup = command_subparser.add_parser('setup', help='Set up a clean instance of the database')
    parser_setup.set_defaults(func=setup_command)
    parser_delete = command_subparser.add_parser('delete', help='Delete the database')
    parser_setup.set_defaults(func=delete_command)
    parser.set_defaults(func=default_command)
    args = parser.parse_args()
    if args.log is None:
        args.log = Indaleko.generate_file_name(
                        suffix='log',
                        service='dbsetup',
                        timestamp=timestamp
                    )
    print(args)
    indaleko_logging = IndalekoLogging(service_name='dbsetup',
                                       log_dir=args.log_dir,
                                       log_file=args.log,
                                       log_level=args.loglevel)
    logging.info('Starting Indaleko database setup')
    logging.debug(args)
    args.func(args)
    logging.info('Ending Indaleko database setup')
    return

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
