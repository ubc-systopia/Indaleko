#!/usr/bin/python3

import os
import configparser
import argparse
import secrets
import string
import subprocess
import datetime
import logging
from Indaleko import *
from arango import ArangoClient
import arango.exceptions
import requests
import time
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
    parser.add_argument('--config', '-c', help='Path to the config file', default='./config/indaleko-db-config.ini')
    parser.add_argument('--passwd', '-p', help='Database password to use', default=None)
    parser.add_argument('--reset', '-r', help='Reset the database', action='store_true', default=False)
    parser.add_argument('--log', '-l', help='Log file to use', default=logfile)
    parser.add_argument('--logdir', help='Log directory to use', default='./logs')
    args = parser.parse_args()

    # make sure the following folders exist:
    #  1- `logs`: for the logs
    #  2- `config`: for the adb .ini configs
    list(map(lambda x: os.makedirs(x, exist_ok=True), [args.logdir, "./config"]))

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
    IndalekoCollections(config, args.reset)
    logging.info('Collection creation complete')
    logging.info('Database setup and configuration complete')


if __name__ == '__main__':
    main()
