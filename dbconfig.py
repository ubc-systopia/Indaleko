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
import psutil
import os
import argparse
import datetime
import logging
from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollections
from IndalekoLogging import IndalekoLogging

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

def is_arangodb3_running():
    """Determine if ArangoDB is running on the local machine."""
    for proc in psutil.process_iter(['pid','name']):
        try:
            if 'arangod' in proc.info['name']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def main():
    """Main entry point for the program"""
    Indaleko.create_secure_directories()
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp=now.isoformat()
    print("This is the Indaleko Configuration File Builder")
    if not is_arangodb3_running():
        print('Note: ArangoDB is not running locally.')
        print('If you want to configure it with Docker, please use "dbsetup.py"')
    parser = argparse.ArgumentParser(description='Indaleko Config Builder')
    parser.add_argument('--database', type=str, default='Indaleko', help='This is the name of the database to create')
    parser.add_argument('--timestamp', type=str, default=now.strftime('%Y%m%d%H%M%S'), help='This is the timestamp to use')
    parser.add_argument('--admin', type=str, default='root', help='This is the name of the admin account')
    parser.add_argument('--password', type=str, required=True, help='Existing admin password for admin in the database')
    parser.add_argument('--host', type=str, default='localhost', help='Hostname or IP Address of database server')
    parser.add_argument('--port', type=str, default='8529', help="Port number to use when accessing the database")
    parser.add_argument('--user', type=str, default=None, help='Name of user to use for normal DB access')
    parser.add_argument('--upwd', type=str, default=None, help='Password of user')
    parser.add_argument('--log_dir',
                        help='Log directory to use',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--log', help='Log file to write')
    parser.add_argument('--loglevel', type=int, default=logging.DEBUG, help='Log level to use')
    parser.add_argument('--overwrite', default=False, action='store_true', help='Indicates the existing config file should be overwritten')
    args = parser.parse_args()
    if os.path.exists(IndalekoDBConfig.default_db_config_file) and not args.overwrite:
        print('Existing config file will not be overwritten, use "--ovewrite" if you want to overwrite it.')
        exit(1)
    admin_password = args.password
    delattr(args,'password')
    if args.log is None:
        args.log = Indaleko.generate_file_name(
                        suffix='log',
                        service='dbconfig',
                        timestamp=timestamp
                    )
    indaleko_logging = IndalekoLogging(service_name='dbconfig',
                                       log_dir=args.log_dir,
                                       log_file=args.log,
                                       log_level=args.loglevel)
    logging.info('Starting Indaleko database config')
    logging.debug(args)
    db_config = IndalekoDBConfig()
    # these keys aren't used because we aren't running it inside docker
    if 'container' in db_config.config:
        del db_config.config['database']['container']
    if 'volume' in db_config.config:
        del db_config.config['database']['volume']
    db_config.set_admin_password(admin_password)
    print('Admin password set')
    db_config.start()
    print('DB Configuration done')
    check_command(args)
    print('Done checking DB connection')
    logging.info('Ending Indaleko database config')
    return

if __name__ == '__main__':
    main()
