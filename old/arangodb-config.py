import argparse
import json
import os


class ArangoDBConfig:

    DefaultConfigFile = "config.json"
    DefaultHost = "127.0.0.1"
    DefaultPort = 8529
    DefaultUser = "tony"
    DefaultPassword = "pa$$w0rd"
    DefaultDatabase = "Indaleko"

    def __init__(self) -> None:
        self.config = self.DefaultConfigFile
        self.host = self.DefaultHost
        self.port = self.DefaultPort
        self.user = self.DefaultUser
        self.password = self.DefaultPassword
        self.database = self.DefaultDatabase

    def set_config(self, config_name: str):
        self.config = config_name
        return self

    def set_host(self, host_name_addr: str):
        self.host = host_name_addr
        return self

    def set_port(self, port: int):
        assert port > 1023 and port < 65536, "Invalid port number"
        self.port = port
        return self

    def set_user(self, user: str):
        self.user = user
        return self

    def set_password(self, password: str):
        self.password = password
        return self

    def set_database(self, database: str):
        self.database = database
        return self

    def to_dict(self):
        return {
            "config": self.config,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
        }

    def write_config(self):
        self.verify_config_in_gitignore()
        with open(self.config, "w") as fd:
            json.dump(self.to_dict(), fd)
        return self

    def verify_config_in_gitignore(self) -> None:
        if not os.path.exists(".gitignore"):
            with open(".gitignore", "w") as fd:
                fd.write(f"{self.config}\n")
        else:
            found = False
            with open(".gitignore") as fd:
                for line in fd:
                    if line.strip() == self.config:
                        found = True
                    else:
                        pass
            if not found:
                with open(".gitignore", "a") as fd:
                    fd.write(f"{self.config}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Name of the configuration file to generate",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Name or IP address of database",
    )
    parser.add_argument(
        "--port",
        type=str,
        default=8529,
        help="Port to use for accessing database",
    )
    parser.add_argument(
        "--user",
        type=str,
        default="tony",
        help="User name for credentials",
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Password to use for logging into database",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="Indaleko",
        help="Name of database to use",
    )
    args = parser.parse_args()
    assert args.port > 1023 and args.port < 65536, "Invalid port number"

    config = ArangoDBConfig()
    config.set_config(args.config).set_host(args.host).set_port(args.port).set_user(
        args.user,
    ).set_password(
        args.password,
    ).set_database(args.database)
    config.write_config()


if __name__ == "__main__":
    main()
