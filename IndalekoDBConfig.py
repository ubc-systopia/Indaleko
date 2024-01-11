import logging
import os
import configparser
import secrets
import string
import datetime
from arango import ArangoClient
from IndalekoCollections import IndalekoCollections
import requests
import time


class IndalekoDBConfig:
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


    def start(self):
        '''Once the container is running, this method will set up connections to
        the database and configure it if needed'''
        if self.started:
            return
        url = f"http://{self.config['database']['host']}:{self.config['database']['port']}"
        while True:
            try:
                response = requests.get(url + '/_api/agency/readiness')
                logging.debug(f"Response from {url + '/_api/agency/readiness'}: {response.json()}")
                break # this means the connection is now up - if it weren't, we'd get an exception
            except Exception as e:
                logging.debug(f"Exception from {url + '/_api/agency/readiness'}: {type(e)} {e}")
            time.sleep(2)
        self.client = ArangoClient(f"http://{self.config['database']['host']}:{self.config['database']['port']}")
        if 'admin_user' not in self.config['database']:
            self.config['database']['admin_user'] = 'root'
        if 'admin_passwd' not in self.config['database']:
            self.config['database']['admin_passwd'] = self.config['database']['passwd']
        self.sys_db = self.client.db('_system', username=self.config['database']['admin_user'],
                                     password=self.config['database']['admin_passwd'], auth_method='basic')
        if self.updated:
            # This is a new config, so we need to set up the user and then the
            # database
            self.setup_database(self.config['database']['database'])
            self.setup_user(self.config['database']['user_name'], self.config['database']['user_password'], [{'database': 'Indaleko', 'permission': 'rw'}])
        # let's create the user's database access object
        self.db = self.client.db(self.config['database']['database'],
                                 username=self.config['database']['user_name'],
                                 password=self.config['database']['user_password'],
                                 auth_method='basic',
                                 verify=True)
        assert self.db is not None, 'Could not connect to database'
        logging.info(f'Connected to database {self.config["database"]["database"]}')


    @staticmethod
    def generate_random_password(length=15):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))

    @staticmethod
    def generate_random_username(length=8) -> dict:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))


    def __del__(self):
        if self.updated and self.config is not None:
            self.__save_config__()


    def __generate_new_config__(self):
        config = configparser.ConfigParser()
        assert type(config) == configparser.ConfigParser, 'ConfigParser not created'
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
        with open(self.config_file, 'wt') as configfile:
            self.config.write(configfile)


    def __load_config__(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)


    def delete_config(self):
        if self.config is not None:
            self.config = None
            self.updated = False
            os.remove(self.config_file)

    def set_admin_password(self, passwd : str):
        assert self.config is not None, 'No config found'
        assert passwd is not None, 'No password provided'
        self.config['database']['admin_passwd'] = passwd
        self.updated = True

    def db_connect(self) -> bool:
        assert self.config is not None, 'No config found'
        assert self.config['database'] is not None, 'No database config found'
        assert self.config['database']['database'] is not None, 'No database name found'
        assert self.config['database']['user'] is not None, 'No database user found'
        assert self.config['database']['admin_passwd'] is not None, 'No database password found'
        try:
            self.db = self.client.db(self.config['database']['database'], username=self.config['database']['user'],
                                     password=self.config['database']['admin_passwd'], auth_method='basic')
            return True
        except Exception as e:
            logging.error(f'Could not connect to database: {e}')
            return False

    def setup_collection(self, collection_name : str, schema : dict = None):
        if self.db is None:
            result = self.db.create_collection(collection_name, schema=schema)
            logging.debug(f'Created collection {collection_name}: {result}')

    def setup_user(self, uname : str, upwd : str, access: list):
        assert uname is not None, 'No username provided'
        assert len(uname) > 0, 'Username must be at least one character'
        assert upwd is not None, 'No password provided'
        assert len(upwd) > 0, 'Password must be at least one character'
        assert access is not None, 'No access list found'
        assert isinstance(access, list), 'Access must be a list'
        assert self.sys_db is not None, 'No system database found'
        ulist = self.sys_db.users()
        found = False
        for u in ulist:
            if u['username'] == uname:
                found = True
                break
        if not found:
            self.sys_db.create_user(username=uname, password=upwd, active=True)
        for a in access:
            assert isinstance(a, dict), 'Access must be a list of dictionaries'
            perms = self.sys_db.permission(username=uname, database=a['database'])
            # TODO - figure out what is in perms
            assert perms is not None, 'Perms is None, which is unexpected.'
            self.sys_db.update_permission(uname, permission=a['permission'], database=a['database'])


    def setup_collections(self, reset: bool = False) -> None:
        self.collections = IndalekoCollections()


    def setup_database(self, dbname : str, reset: bool = False) -> bool:
        assert dbname is not None, 'No database name found'
        assert self.sys_db is not None, 'No system database found'
        if reset:
            if dbname in self.sys_db.databases():
                self.sys_db.delete_database(dbname)
        assert dbname not in self.sys_db.databases(), f'Database {dbname} already exists, reset not specified {self.sys_db.databases()}'
        assert self.sys_db.create_database(dbname), 'Database creation failed'
        return True


