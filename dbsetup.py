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
    if os.path.exists(IndalekoDBConfig.default_db_config_file):
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
    logging.info('Check the database, args is %s', args)
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
    logging.info('Delete the database and volumes, args is %s', args)
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
    except Exception as e:
        logging.error('Could not delete container %s, Exception %s', container_name, e)
        print(f"Could not delete running container {container_name}, Exception {e}")
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
    if os.path.exists(IndalekoDBConfig.default_db_config_file):
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
    parser_setup = command_subparser.add_parser('setup',
                                                help='Set up a clean instance of the database')
    parser_setup.set_defaults(func=setup_command)
    parser_delete = command_subparser.add_parser('delete', help='Delete the database')
    parser_delete.set_defaults(func=delete_command)
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
    IndalekoLogging(service_name='dbsetup',
                    log_dir=args.log_dir,
                    log_file=args.log,
                    log_level=args.loglevel)
    logging.info('Starting Indaleko database setup')
    logging.debug(args)
    args.func(args)
    logging.info('Ending Indaleko database setup')
    return

if __name__ == '__main__':
    main()
