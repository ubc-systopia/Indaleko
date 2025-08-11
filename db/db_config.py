"""
Database Configuration Management.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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
"""

import argparse
import configparser
import datetime
import logging
import os
import secrets
import string
import sys
import time

from pathlib import Path

import requests

from arango import ArangoClient
from arango.collection import StandardCollection
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models.db_config import (
    IndalekoDBConfigDataModel,
    IndalekoDBConfigDockerConfigurationDataModel,
    IndalekoDBConfigUserDataModel,
)
from utils import IndalekoDocker, IndalekoLogging, IndalekoSingleton
from utils.data_validation import validate_hostname, validate_ip_address
from utils.misc.directory_management import (
    indaleko_default_config_dir,
    indaleko_default_log_dir,
)
from utils.misc.file_name_management import generate_file_name


# pylint: enable=wrong-import-position


class IndalekoDBConfig(IndalekoSingleton):
    """Read config file, connect to database."""

    default_db_config_file_name = IndalekoConstants.default_db_config_file_name
    default_db_config_file = Path(indaleko_default_config_dir) / default_db_config_file_name
    default_db_timeout = int(os.environ.get("INDALEKO_DB_TIMEOUT", "10"))
    default_db_aql_timeout = int(os.environ.get("INDALEKO_DB_AQL_TIMEOUT", "300"))

    def __init__(
        self,
        config_file: str = default_db_config_file,
        no_new_config: bool = False,  # noqa: FBT001, FBT002
        start: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize the database configuration object."""
        if self._initialized:
            return
        self._initialized = True
        self.config_file = config_file
        self.config = None
        if os.path.exists(config_file):
            try:
                self.__load_config__()
            except ValueError as e:
                logging.exception("Could not load config file %s: %s", config_file, e)
                self.config = {}
            if "database" not in self.config:
                assert not no_new_config, "No database section found in config file, but no new config set"
                logging.warning(
                    "No database section found in config file %s",
                    config_file,
                )
                logging.warning("Generating new config")
                self.config = self.__generate_new_config__()
        else:
            self.config = self.__generate_new_config__()
        self.started = False
        self.client = None
        self.sys_db = None
        self._arangodb = None
        self.db = None  # this is legacy and should be removed (but it'll break things)
        self.collections = {}
        if start:
            self.started = self.start()

    def get_arangodb(self) -> ArangoClient:
        """Get the ArangoDB client."""
        if not self._arangodb:
            raise ValueError("Database not connected")
        return self._arangodb

    def get_collection(self, collection_name: str) -> StandardCollection:
        """Get a collection from the database."""
        if not self._arangodb:
            raise ValueError("Database not connected")
        if not collection_name:
            raise ValueError("No collection name specified")
        if collection_name not in self.collections:
            collection = self._arangodb.collection(collection_name)
            if collection is None:

                raise ValueError(
                    f"Collection {collection_name} not found in database",
                )
            self.collections[collection_name] = collection
        return self.collections[collection_name]

    def start(self, timeout: int = 60) -> bool:
        """
        Start the database connection.

        Once the container is running, this method will set up connections to
        the database and configure it if needed
        """
        if self.started:
            return True
        web_service_name = "http"
        if "ssl" in self.config["database"] and self.config["database"]["ssl"] == "true":
            web_service_name = "https"
        url = f"{web_service_name}://{self.config['database']['host']}:"
        url += f"{self.config['database']['port']}"
        logging.debug("Connecting to %s", url)
        start_time = time.time()
        connected = False
        timedout = False
        while True:
            try:
                response = requests.get(url + "/_api/agency/readiness", timeout=5)
                logging.debug(
                    "Response from %s: %s",
                    url + "/_api/agency/readiness",
                    response.json(),
                )
                connected = True
                break  # this means the connection is now up - if it weren't, we'd get an exception
            except requests.RequestException as e:
                logging.debug(
                    "Exception from %s: %s %s",
                    url + "/_api/agency/readiness",
                    type(e),
                    e,
                )
            if time.time() - start_time > timeout:
                timedout = True
                break
            time.sleep(1)
        if timedout:
            logging.warning("Timed out waiting for database to start")
            return False
        connect_arg = f"{web_service_name}://{self.config['database']['host']}"
        connect_arg += ":"
        connect_arg += f"{self.config['database']['port']}"
        logging.debug("Connecting to %s", connect_arg)
        aql_timeout = self.config["database"].get(
            "timeout",
            IndalekoDBConfig.default_db_aql_timeout,
        )
        self.client = ArangoClient(connect_arg, request_timeout=aql_timeout)
        if "admin_user" not in self.config["database"]:
            self.config["database"]["admin_user"] = "root"
        if "admin_passwd" not in self.config["database"]:
            self.config["database"]["admin_passwd"] = self.config["database"]["passwd"]
        self.sys_db = self.client.db(
            "_system",
            username=self.config["database"]["admin_user"],
            password=self.config["database"]["admin_passwd"],
            auth_method="basic",
        )
        logging.debug("Ensuring Indaleko database is in ArangoDB")
        self.setup_database(self.config["database"]["database"])
        logging.debug(
            "Ensuring Indaleko user %s is in ArangoDB",
            self.config["database"]["user_name"],
        )
        self.setup_user(
            self.config["database"]["user_name"],
            self.config["database"]["user_password"],
            [{"database": "Indaleko", "permission": "rw"}],
        )
        # let's create the user's database access object
        self._arangodb = self.client.db(
            self.config["database"]["database"],
            username=self.config["database"]["user_name"],
            password=self.config["database"]["user_password"],
            auth_method="basic",
            verify=True,
        )
        self.db = self._arangodb
        assert self._arangodb is not None, "Could not connect to database"
        logging.info("Connected to database %s", self.config["database"]["database"])
        return connected

    @staticmethod
    def generate_random_password(length=15):
        """
        Generate a random password string of letters and digits. Omitted
        special characters due to issues with the db.
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for i in range(length))

    @staticmethod
    def generate_random_username(length=8) -> dict:
        """Generate a random user name string of letters and digits."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for i in range(length))

    def __generate_new_config__(self):
        config = configparser.ConfigParser()
        assert isinstance(config, configparser.ConfigParser), "ConfigParser not created"
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        config["database"] = {}
        config["database"]["database"] = "Indaleko"
        config["database"]["timestamp"] = timestamp
        config["database"]["admin_user"] = "root"
        config["database"]["admin_passwd"] = IndalekoDBConfig.generate_random_password()
        config["database"]["container"] = "arango-indaleko-" + timestamp
        config["database"]["volume"] = "indaleko-db-1-" + timestamp
        config["database"]["host"] = "localhost"
        config["database"]["port"] = "8529"
        config["database"]["user_name"] = self.generate_random_username()
        config["database"]["user_password"] = self.generate_random_password()
        self.config = config
        self.__save_config__()
        return config

    def __save_config__(self):
        """Save the config information in the object."""
        logging.debug("Saving config to %s", self.config_file)
        parent_dir = os.path.dirname(self.config_file)
        if not os.path.exists(parent_dir):
            logging.debug("folder %s doesn't exist. creating one ...", parent_dir)
            os.makedirs(parent_dir, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8-sig") as config_file:
            self.config.write(config_file)

    def __load_config__(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file, encoding="utf-8-sig")
        logging.debug("Loaded config from %s", self.config_file)
        parent_dir = os.path.dirname(self.config_file)
        if not os.path.exists(parent_dir):
            logging.debug("folder %s doesn't exist, creating one ... ", parent_dir)
            os.makedirs(parent_dir, exist_ok=True)
        if "database" not in self.config:
            logging.error(
                "No database section found in config file %s",
                self.config_file,
            )
            raise ValueError("No database section found in config file")

    def delete_config(self) -> None:
        """Delete the config information in the object."""
        if self.config is not None:
            self.config = None
            logging.debug("Deleting config %s", self.config_file)
            os.remove(self.config_file)

    def set_admin_password(self, passwd: str) -> None:
        """Set the admin password in the config object."""
        assert self.config is not None, "No config found"
        assert passwd is not None, "No password provided"
        self.config["database"]["admin_passwd"] = passwd
        self.__save_config__()

    def db_connect(self) -> bool:
        """Connect to the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["database"] is not None, "No database name found"
        assert self.config["database"]["user"] is not None, "No database user found"
        assert self.config["database"]["admin_passwd"] is not None, "No database password found"
        self._arangodb = self.client.db(
            self.config["database"]["database"],
            username=self.config["database"]["user"],
            password=self.config["database"]["admin_passwd"],
            auth_method="basic",
        )
        self.db = self._arangodb
        return True

    def setup_user(self, user_name: str, user_password: str, access: list) -> None:
        """Set up a user in the database."""
        assert user_name is not None, "No username provided"
        assert len(user_name) > 0, "Username must be at least one character"
        assert user_password is not None, "No password provided"
        assert len(user_password) > 0, "Password must be at least one character"
        assert access is not None, "No access list found"
        assert isinstance(access, list), "Access must be a list"
        assert self.sys_db is not None, "No system database found"
        user_list = self.sys_db.users()
        found = False
        for u in user_list:
            if u["username"] == user_name:
                found = True
                break
        if not found:
            self.sys_db.create_user(
                username=user_name,
                password=user_password,
                active=True,
            )
        for a in access:
            assert isinstance(a, dict), "Access must be a list of dictionaries"
            perms = self.sys_db.permission(username=user_name, database=a["database"])
            assert perms is not None, "Perms is None, which is unexpected."
            self.sys_db.update_permission(
                user_name,
                permission=a["permission"],
                database=a["database"],
            )

    def setup_database(self, dbname: str, reset: bool = False) -> bool:
        """Set up the database."""
        assert dbname is not None, "No database name found"
        assert self.sys_db is not None, "No system database found"
        if dbname in self.sys_db.databases():
            if reset:
                result = self.sys_db.delete_database(dbname)
                assert result, "Could not delete database"
            else:
                return True
        self.sys_db.create_database(dbname)
        if dbname not in self.sys_db.databases():
            raise ValueError(f"Database {dbname} not found - creation failed")
        return True

    def get_hostname(self) -> str:
        """Get the IP address of the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["host"] is not None, "No database host found"
        return self.config["database"]["host"]

    def get_port(self) -> str:
        """Get the port of the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["port"] is not None, "No database port found"
        return self.config["database"]["port"]

    def update_hostname(self, ipaddr: str) -> None:
        """
        Update the IP address in the config file.
        This is useful when moving the config to an additional machine.
        """
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert ipaddr is not None, "No IP address provided"
        assert validate_hostname(ipaddr) or validate_ip_address(
            ipaddr,
        ), f"Invalid IP address or host name: {ipaddr}"
        self.config["database"]["host"] = ipaddr
        self.__save_config__()

    def get_user_name(self) -> str:
        """Get the user name for the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["user_name"] is not None, "No user name found"
        return self.config["database"]["user_name"]

    def get_user_password(self) -> str:
        """Get the user password for the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["user_password"] is not None, "No user password found"
        return self.config["database"]["user_password"]

    def get_root_name(self) -> str:
        """Get the root/admin username for the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["admin_user"] is not None, "No admin username found"
        return self.config["database"]["admin_user"]

    def get_root_password(self) -> str:
        """Get the root/admin password for the database."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["admin_passwd"] is not None, "No admin password found"
        return self.config["database"]["admin_passwd"]

    def get_database_name(self) -> str:
        """Get the database name."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        assert self.config["database"]["database"] is not None, "No database name found"
        return self.config["database"]["database"]

    def get_ssl_state(self) -> str:
        """Get the SSL state."""
        assert self.config is not None, "No config found"
        assert self.config["database"] is not None, "No database config found"
        if "ssl" in self.config["database"]:
            return self.config["database"]["ssl"]
        return False

    @staticmethod
    def read_config_file(config_file: str | None) -> configparser.ConfigParser:
        """
        Read the config file.

        Inputs:
            * config_file: str: The name of the config file to read. (Optional)

        If the config file is not provided, the default config file and directory are used.
        If the config file is provided but does not exist as passed, the default directory is checked.

        Returns:
            * configparser.ConfigParser: The configuration file as parsed
            * None: If the file could not be read
        """
        config = configparser.ConfigParser()
        if config_file and not os.path.exists(config_file):
            alt_path = os.path.join(indaleko_default_config_dir, config_file)
            if os.path.exists(alt_path):
                config_file = alt_path
        if config_file is None:
            config_file = IndalekoDBConfig.default_db_config_file
        config.read(config_file, encoding="utf-8-sig")
        return config

    @staticmethod
    def config_parser_to_config_data(
        config_parser: configparser.ConfigParser,
    ) -> IndalekoDBConfigDataModel:
        """Convert the configuration parser object into a configuration data model."""
        inputs = {
            "Name": config_parser["database"]["database"],
            "Timestamp": config_parser["database"]["timestamp"],
            "AdminUser": IndalekoDBConfigUserDataModel(
                Name=config_parser["database"]["admin_user"],
                Password=config_parser["database"]["admin_passwd"],
            ),
            "DBUser": IndalekoDBConfigUserDataModel(
                Name=config_parser["database"]["user_name"],
                Password=config_parser["database"]["user_password"],
            ),
            "Hostname": config_parser["database"]["host"],
            "Port": config_parser["database"]["port"],
        }
        if "container" in config_parser["database"]:
            inputs["Docker"] = True
            inputs["Local"] = False
            inputs["DockerConfiguration"] = IndalekoDBConfigDockerConfigurationDataModel(
                ContainerName=config_parser["database"]["container"],
                VolumeName=config_parser["database"]["volume"],
            )
        else:
            inputs["Docker"] = False
            inputs["Local"] = True
        return IndalekoDBConfigDataModel(**inputs)

    @staticmethod
    def load_config_data(
        config_file: str | None = None,
    ) -> IndalekoDBConfigDataModel | None:
        """
        Load the configuration data from the file and convert it into the config data format.

        If the `config_file` is not provided, the default config file and directory are used (see
        read_config_file for details).

        Returns:
            * IndalekoDBConfigDataModel: The configuration data as a data model
            * None: If the file could not be read
        """
        config_parser = IndalekoDBConfig.read_config_file(config_file)
        if config_parser is None:
            return None
        return IndalekoDBConfig.config_parser_to_config_data(config_parser)

    @staticmethod
    def create_config_parser(
        config_data: IndalekoDBConfigDataModel,
    ) -> configparser.ConfigParser:
        """Given a configuration data model, create a configuration parser object."""
        config = configparser.ConfigParser()
        config["database"] = {}
        config["database"]["database"] = config_data.Name
        if isinstance(config_data.Timestamp, datetime.datetime):
            config["database"]["timestamp"] = config_data.Timestamp.strftime(
                "%Y%m%d%H%M%S",
            )
        else:
            config["database"]["timestamp"] = config_data.Timestamp
        config["database"]["admin_user"] = config_data.AdminUser.Name
        config["database"]["admin_passwd"] = config_data.AdminUser.Password
        config["database"]["user_name"] = config_data.DBUser.Name
        config["database"]["user_password"] = config_data.DBUser.Password
        config["database"]["host"] = config_data.Hostname
        config["database"]["port"] = str(config_data.Port)
        if config_data.Docker:
            config["database"]["container"] = config_data.DockerConfiguration.ContainerName
            config["database"]["volume"] = config_data.DockerConfiguration.VolumeName
        if config_data.SSL:
            config["database"]["ssl"] = "true"
        return config


def check_command(args: argparse.Namespace) -> None:
    """Check the database connection."""
    assert args is not None, "No args found"
    logging.debug("check_command invoked")
    db_config = IndalekoDBConfig()
    if db_config is None:
        logging.critical("Could not create IndalekoDBConfig object")
        sys.exit(1)
    started = db_config.start(timeout=10)
    if not started:
        logging.critical("Could not start database connection")
        return


def setup_command(args: argparse.Namespace) -> None:
    """Set up the database."""
    assert args is not None, "No args found"
    logging.info("Setting up new database configuration")
    db_config = IndalekoDBConfig()
    if db_config is None:
        logging.critical("Could not create IndalekoDBConfig object")
        sys.exit(1)
    if db_config.config["database"].get("container") and db_config.config["database"].get("volume"):
        logging.info("Initialize Docker ArangoDB")
        indaleko_docker = IndalekoDocker()
        logging.info(
            "Create container %s with volume %s",
            db_config.config["database"]["container"],
            db_config.config["database"]["volume"],
        )
        indaleko_docker.create_container(
            db_config.config["database"]["container"],
            db_config.config["database"]["volume"],
            db_config.config["database"]["admin_passwd"],
        )
        logging.info("Created container %s", db_config.config["database"]["container"])
        logging.info("Start container %s", db_config.config["database"]["container"])
        indaleko_docker.start_container(db_config.config["database"]["container"])
    logging.info("Connect to database")
    started = db_config.start()
    if not started:
        logging.critical("Could not start database connection")
        return
    logging.info("Database connection successful")

    def __setup_db() -> None:
        from i_collections import IndalekoCollections

        IndalekoCollections()

    __setup_db()


def docker_reset() -> None:
    """This resets the docker container and volume."""
    logging.info("Resetting database")
    indaleko_docker = IndalekoDocker()
    config = IndalekoDBConfig()
    # In either case we will delete the container and volume
    logging.warning(
        "DB Reset: stopping container %s",
        config.config["database"]["container"],
    )
    indaleko_docker.stop_container(config.config["database"]["container"])
    logging.warning(
        "DB Reset: deleting container %s",
        config.config["database"]["container"],
    )
    indaleko_docker.delete_container(config.config["database"]["container"])
    logging.warning("DB Reset: deleting volume %s", config.config["database"]["volume"])
    indaleko_docker.delete_volume(config.config["database"]["volume"])


def reset_command(args: argparse.Namespace) -> None:
    """Reset the database."""
    if not os.path.exists(IndalekoDBConfig.default_db_config_file):
        logging.critical("No config file found, cannot reset")
        return
    logging.info("Resetting database")
    indaleko_docker = IndalekoDocker()
    config = IndalekoDBConfig()
    # In either case we will delete the container and volume
    logging.warning(
        "DB Reset: stopping container %s",
        config.config["database"]["container"],
    )
    indaleko_docker.stop_container(config.config["database"]["container"])
    logging.warning(
        "DB Reset: deleting container %s",
        config.config["database"]["container"],
    )
    indaleko_docker.delete_container(config.config["database"]["container"])
    logging.warning("DB Reset: deleting volume %s", config.config["database"]["volume"])
    indaleko_docker.delete_volume(config.config["database"]["volume"])
    if args.rebuild:
        logging.info("DB Reset: Rebuild requested")
        logging.warning("DB Reset: deleting old config file")
        if os.path.exists(IndalekoDBConfig.default_db_config_file + ".bak"):
            os.remove(IndalekoDBConfig.default_db_config_file + ".bak")
        logging.warning("DB Reset: backing up old config file")
        os.rename(
            IndalekoDBConfig.default_db_config_file,
            IndalekoDBConfig.default_db_config_file + ".bak",
        )
        config = IndalekoDBConfig()
    setup_command(args)


def show_command(args: argparse.Namespace) -> None:
    """Show the database configuration."""
    assert args is not None, "No args found"
    logging.info("Show command starts")
    if not os.path.exists(IndalekoDBConfig.default_db_config_file):
        logging.critical("No config file found")
    config = IndalekoDBConfig()
    if config.config["database"].get("container"):
        pass
    if config.config["database"].get("volume"):
        pass
    logging.info("Show command complete")


def update_command(args: argparse.Namespace) -> None:
    """Update to most recent version of ArangoDB."""
    # Note: this is just a wrapper around the docker support for this.
    assert args is not None, "No args found"
    raise NotImplementedError("Not implemented yet")


def default_command_handler(args: argparse.Namespace) -> None:
    """Default command handler."""
    # Do we already have a config file?
    assert args is not None, "No args found"
    logging.debug("default_command_handler invoked")
    if os.path.exists(IndalekoDBConfig.default_db_config_file):
        check_command(args)
    else:
        setup_command(args)


def new_main() -> None:
    ic(IndalekoDBConfig.load_config_data())


def main() -> None:
    """This is the main function for the IndalekoDBConfig module."""
    now = datetime.datetime.now(datetime.UTC)
    timestamp = now.isoformat()
    parser = argparse.ArgumentParser(
        description="Indaleko DB Configuration Management.",
    )
    parser.add_argument(
        "--logdir",
        type=str,
        default=indaleko_default_log_dir,
        help="Log directory",
    )
    parser.add_argument("--log", type=str, default=None, help="Log file name")
    parser.add_argument(
        "--loglevel",
        type=int,
        default=logging.DEBUG,
        choices=IndalekoLogging.get_logging_levels(),
        help="Log level",
    )
    command_subparser = parser.add_subparsers(dest="command")
    parser_check = command_subparser.add_parser(
        "check",
        help="Check the database connection.",
    )
    parser_check.add_argument(
        "--ipaddr",
        type=str,
        default=None,
        help="IP address for database",
    )
    parser_check.set_defaults(func=check_command)
    parser_setup = command_subparser.add_parser("setup", help="Set up the database.")
    parser_setup.add_argument(
        "--ipaddr",
        type=str,
        default=None,
        help="IP address for database",
    )
    parser_setup.set_defaults(func=setup_command)
    parser_reset = command_subparser.add_parser("reset", help="Reset the database.")
    parser_reset.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the configuration (changes passwords).",
    )
    parser_reset.set_defaults(func=reset_command)
    parser_update = command_subparser.add_parser("update", help="Update the database.")
    parser_update.add_argument(
        "--ipaddr",
        type=str,
        default=None,
        help="IP address to update in database",
    )
    parser_update.set_defaults(func=update_command)
    parser_show = command_subparser.add_parser(
        "show",
        help="Show the database configuration.",
    )
    parser_show.set_defaults(func=show_command)
    parser.set_defaults(func=default_command_handler)
    args = parser.parse_args()
    if args.log is None:
        args.log = generate_file_name(
            suffix="log",
            service="IndalekoDBConfig",
            timestamp=timestamp,
        )
    indaleko_logging = IndalekoLogging(
        service_name="IndalekoDBConfig",
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir,
    )
    if indaleko_logging is None:
        sys.exit(1)
    logging.info("Starting IndalekoDBConfig")
    logging.debug(args)
    args.func(args)
    logging.info("IndalekoDBConfig: done processing.")


if __name__ == "__main__":
    main()
