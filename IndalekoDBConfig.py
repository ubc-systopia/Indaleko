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
import logging
import os
import configparser
import secrets
import string
import datetime
from arango import ArangoClient
import requests
import time


class IndalekoDBConfig:
    """
    Class used to read a configuration file, connect to, and set-up (if
    needed) the database.
    """
    def __init__(self, config_file: str = './config/indaleko-db-config.ini'):
        self.config_file = config_file
        self.config = None
        self.updated = False
        if os.path.exists(config_file):
            self.__load_config__()
        else:
            self.config = self.__generate_new_config__()
            self.updated = True
        self.started = False
        self.client = None
        self.sys_db = None
        self.db = None
        self.collections = {}

    def start(self):
        '''Once the container is running, this method will set up connections to
        the database and configure it if needed'''
        if self.started:
            return
        url = f"http://{self.config['database']['host']}:{self.config['database']['port']}"
        logging.debug('Connecting to %s', url)
        while True:
            try:
                response = requests.get(url + '/_api/agency/readiness', timeout=5)
                logging.debug("Response from %s: %s",
                              url + '/_api/agency/readiness',
                              response.json())
                break # this means the connection is now up - if it weren't, we'd get an exception
            except requests.RequestException as e:
                logging.debug("Exception from %s: %s %s",
                              url + '/_api/agency/readiness',
                              type(e),
                              e)
            time.sleep(2)
        connect_arg = f"http://{self.config['database']['host']}"
        connect_arg += ':'
        connect_arg += f"{self.config['database']['port']}"
        logging.debug('Connecting to %s', connect_arg)
        self.client = ArangoClient(connect_arg)
        if 'admin_user' not in self.config['database']:
            self.config['database']['admin_user'] = 'root'
        if 'admin_passwd' not in self.config['database']:
            self.config['database']['admin_passwd'] = self.config['database']['passwd']
        self.sys_db = self.client.db('_system',
                                     username=self.config['database']['admin_user'],
                                     password=self.config['database']['admin_passwd'],
                                     auth_method='basic')
        if self.updated:
            # This is a new config, so we need to set up the user and then the
            # database
            self.setup_database(self.config['database']['database'])
            self.setup_user(self.config['database']['user_name'],
                            self.config['database']['user_password'],
                            [{'database': 'Indaleko', 'permission': 'rw'}])
        # let's create the user's database access object
        self.db = self.client.db(self.config['database']['database'],
                                 username=self.config['database']['user_name'],
                                 password=self.config['database']['user_password'],
                                 auth_method='basic',
                                 verify=True)
        assert self.db is not None, 'Could not connect to database'
        logging.info('Connected to database %s', self.config['database']['database'])


    @staticmethod
    def generate_random_password(length=15):
        """
        Generate a random password string of letters and digits. Omitted
        special characters due to issues with the db.
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))

    @staticmethod
    def generate_random_username(length=8) -> dict:
        """
        Generate a random user name string of letters and digits.
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))


    def __del__(self):
        if self.updated and self.config is not None:
            self.__save_config__()


    def __generate_new_config__(self):
        config = configparser.ConfigParser()
        assert isinstance(config, configparser.ConfigParser), 'ConfigParser not created'
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        config['database'] = {}
        config['database']['database'] = 'Indaleko'
        config['database']['timestamp'] = timestamp
        config['database']['admin_user'] = 'root'
        config['database']['admin_passwd'] = IndalekoDBConfig.generate_random_password()
        config['database']['container'] = 'arango-indaleko-' + timestamp
        config['database']['volume'] = 'indaleko-db-1-' + timestamp
        config['database']['host'] = 'localhost'
        config['database']['port'] = '8529'
        config['database']['user_name'] = self.generate_random_username()
        config['database']['user_password'] = self.generate_random_password()
        self.updated = True
        return config


    def __save_config__(self):
        with open(self.config_file, 'wt', encoding='utf-8-sig') as config_file:
            self.config.write(config_file)


    def __load_config__(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file, encoding='utf-8-sig')


    def delete_config(self):
        """Delete the config information in the object."""
        if self.config is not None:
            self.config = None
            self.updated = False
            os.remove(self.config_file)

    def set_admin_password(self, passwd : str):
        """Set the admin password in the config object."""
        assert self.config is not None, 'No config found'
        assert passwd is not None, 'No password provided'
        self.config['database']['admin_passwd'] = passwd
        self.updated = True

    def db_connect(self) -> bool:
        """Connect to the database."""
        assert self.config is not None, 'No config found'
        assert self.config['database'] is not None, 'No database config found'
        assert self.config['database']['database'] is not None, 'No database name found'
        assert self.config['database']['user'] is not None, 'No database user found'
        assert self.config['database']['admin_passwd'] is not None, 'No database password found'
        self.db = self.client.db(self.config['database']['database'],
                                    username=self.config['database']['user'],
                                    password=self.config['database']['admin_passwd'],
                                    auth_method='basic')
        return True


    def setup_user(self, user_name : str, user_password : str, access: list):
        """Set up a user in the database."""
        assert user_name is not None, 'No username provided'
        assert len(user_name) > 0, 'Username must be at least one character'
        assert user_password is not None, 'No password provided'
        assert len(user_password) > 0, 'Password must be at least one character'
        assert access is not None, 'No access list found'
        assert isinstance(access, list), 'Access must be a list'
        assert self.sys_db is not None, 'No system database found'
        user_list = self.sys_db.users()
        found = False
        for u in user_list:
            if u['username'] == user_name:
                found = True
                break
        if not found:
            self.sys_db.create_user(username=user_name, password=user_password, active=True)
        for a in access:
            assert isinstance(a, dict), 'Access must be a list of dictionaries'
            perms = self.sys_db.permission(username=user_name, database=a['database'])
            assert perms is not None, 'Perms is None, which is unexpected.'
            self.sys_db.update_permission(user_name,
                                          permission=a['permission'],
                                          database=a['database'])



    def setup_database(self, dbname : str, reset: bool = False) -> bool:
        """Set up the database."""
        assert dbname is not None, 'No database name found'
        assert self.sys_db is not None, 'No system database found'
        if reset:
            if dbname in self.sys_db.databases():
                self.sys_db.delete_database(dbname)
        assert dbname not in self.sys_db.databases(), \
            f'Database {dbname} already exists, reset not specified {self.sys_db.databases()}'
        assert self.sys_db.create_database(dbname), 'Database creation failed'
        return True

def main():
    print('Currently there is no test code for this module.')

if __name__ == "__main__":
    main()
