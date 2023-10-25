#!/usr/bin/python3

import os
import configparser
import argparse
import secrets
import string
import subprocess
import datetime
import logging


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
    return run_command(cmd)

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

    @staticmethod
    def generate_random_password(length=15):
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for i in range(length))


    def __del__(self):
        if self.updated and self.config is not None:
            self.__save_config__()


    def __generate_new_config__(self):
        config = configparser.ConfigParser()
        print(type(config))
        assert type(config) == configparser.ConfigParser, 'ConfigParser not created'
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        config['database'] = {}
        config['database']['timestamp'] = timestamp
        config['database']['passwd'] = IndalekoDBConfig.generate_random_password()
        config['database']['container'] = 'arango-indaleko-' + timestamp
        config['database']['volume'] = 'indaleko-db-1-' + timestamp
        config['database']['host'] = 'localhost'
        config['database']['port'] = '8529'
        # config['database']['user'] = ''
        # config['database']['database'] = args.database
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

    def set_password(self, passwd : str):
        assert self.config is not None, 'No config found'
        assert passwd is not None, 'No password provided'
        self.config['database']['passwd'] = passwd
        self.updated = True

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
    passwd = config.config['database']['passwd']
    cmd += f'-e ARANGO_ROOT_PASSWORD="{passwd}" '
    cmd += "-d "
    cmd += f"-p {config.config['database']['port']}:8529 "
    cmd += f"--mount source={config.config['database']['volume']},target=/var/lib/arangodb3 "
    cmd += f"--name {config.config['database']['container']} "
    cmd += "arangodb"
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
    cmd = f"docker start {config.config['database']['container']}"
    logging.debug(f"Running command: {cmd}")
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
    args = parser.parse_args()
    logging.basicConfig(filename=args.log, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
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


if __name__ == '__main__':
    main()
