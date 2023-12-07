#!/usr/bin/python3

import os
import configparser
import argparse
import secrets
import string
import subprocess
import datetime
import logging
from indaleko import *
from arango import ArangoClient
import arango.exceptions
import requests
import time


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
        self.collections = {'Objects' : {'schema' : IndalekoObject.Schema, 'collection' : None},
                            'Relationships' : {'schema' : IndalekoRelationship.Schema, 'collection' : None},
                            'Sources' : {'schema' : IndalekoSource.Schema, 'collection' : None},
        }


    def start(self):
        '''Once the container is running, this method will set up connections to
        the database and configure it if needed'''
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
        self.setup_collections()
        logging.info('Indaleko collections created')


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
        assert type(access) == list, 'Access must be a list'
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
            assert type(a) is dict, 'Access must be a list of dictionaries'
            perms = self.sys_db.permission(username=uname, database=a['database'])
            # TODO - figure out what is in perms
            # print(perms)
            self.sys_db.update_permission(uname, permission=a['permission'], database=a['database'])


    def setup_collections(self):
        assert self.collections is not None, 'No collections found'
        for collection in self.collections:
            try:
                self.collections[collection]['collection'] = self.db.create_collection(collection, schema=self.collections[collection]['schema'])
                logging.info('Created collection {collection} with schema {schema}, returned {object}'.format(collection=collection, schema=self.collections[collection]['schema'], object=self.collections[collection]['collection']))
            except arango.exceptions.CollectionCreateError as e:
                logging.error(f'Could not create collection {collection} with schema {self.collections[collection]['schema']}: {e}')
                self.collections[collection]['collection'] = self.db.create_collection(collection)
                logging.warning(f'Created collection {collection} without schema')


    def setup_database(self, dbname : str, reset: bool = False) -> bool:
        assert dbname is not None, 'No database name found'
        assert self.sys_db is not None, 'No system database found'
        if reset:
            if dbname in self.sys_db.databases():
                self.sys_db.delete_database(dbname)
        assert dbname not in self.sys_db.databases(), f'Database {dbname} already exists, reset not specified {self.sys_db.databases()}'
        assert self.sys_db.create_database(dbname), 'Database creation failed'
        return True



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
    parser.add_argument('--config', '-c', help='Path to the config file', default='./config/indaleko-db-config.ini')
    parser.add_argument('--passwd', '-p', help='Database password to use', default=None)
    parser.add_argument('--reset', '-r', help='Reset the database', action='store_true', default=False)
    parser.add_argument('--log', '-l', help='Log file to use', default=logfile)
    parser.add_argument('--logdir', help='Log directory to use', default='./logs')
    args = parser.parse_args()
    logging.basicConfig(filename=os.path.join(args.logdir, args.log), level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f'Begin run at {starttime}')
    if not os.path.exists(args.config):
        logging.info('No config file found, generating new one')
        new_config = True
    elif args.reset:
        logging.info('Resetting database')
        config = IndalekoDBConfig(args.config) # load existing
        logging.info('Cleanup previous database')
        cleanup(config)
        config.delete_config()
        new_config = True
    # load existing or generate new
    config = IndalekoDBConfig(args.config) # load config file if it exists
    if new_config:
        logging.info('Generated new config')
        setup(config)
    logging.info('Starting database')
    startup(config)
    logging.info('Configuring database')
    config.start()
    logging.info('Database setup and configuration complete')


if __name__ == '__main__':
    main()
