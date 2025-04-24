"""
This is a class for supporting builk upload to the database.

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

import os
import subprocess
import sys
from typing import Any

import jsonlines
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position

from db.db_config import IndalekoDBConfig
from utils.misc.file_name_management import extract_keys_from_file_name

# pylint: enable=wrong-import-position


class IndalekoDBUploader:
    """This class can be used when creating uploader(s) for the database."""

    def __init__(self, **kwargs: dict[str, Any]):
        """This is the constructor for the database uploader."""
        self.kwargs = kwargs

    @staticmethod
    def build_load_string(
        file_name: str, collection_name: str, db: IndalekoDBConfig | None = None,
    ) -> str:
        """
        This will build the load string for the arangoimport command.
        """
        if db is None:
            db = IndalekoDBConfig()
        load_string = f"arangoimport -collection {collection_name}"
        load_string += " --server.username " + db.get_user_name()
        load_string += " --server.password " + db.get_user_password()
        if db.get_ssl_state():
            load_string += " --ssl.protocol 5"
            endpoint = "http+ssl://"
        else:
            endpoint = "http+tcp://"
        endpoint += db.get_hostname() + ":" + db.get_port()
        load_string += " --server.endpoint " + endpoint
        load_string += " --server.database " + db.get_database_name()
        load_string += " " + file_name
        return load_string

    @staticmethod
    def bulk_upload(
        file_name: str, db: IndalekoDBConfig | None = None, chunk_size: int = 1000,
    ) -> bool:
        """This will use the bulk_import function of arango to upload the data to the database."""
        if db is None:
            db = IndalekoDBConfig()
        file_keys = extract_keys_from_file_name(file_name)
        if "collection" not in file_keys:
            print("Collection name not found in file name")
            return False
        collection = db.db_config.db.collection(file_keys["collection"])
        assert collection, f'Collection {file_keys["collection"]} not found'
        success = False
        try:
            with jsonlines.open(file_name) as reader:
                chunk = []
                for obj in reader:
                    chunk.append(obj)
                    if len(chunk) >= chunk_size:
                        collection.import_bulk(chunk)
                        chunk = []
                if chunk:
                    collection.import_bulk(chunk)
            success = True
        except Exception as e:
            print(f"Error during bulk upload: {e}")
        return success

    @staticmethod
    def external_upload(
        file_name: str, db: IndalekoDBConfig | None = None, chunk_size: int = 1000,
    ) -> bool:
        """
        This will upload the data to the database using arangoimport.
        """

    @staticmethod
    def external_upload(
        file_name: str, db: IndalekoDBConfig | None = None,
    ) -> bool:
        """
        This will upload the data to the database using arangoimport.
        """
        if db is None:
            db = IndalekoDBConfig()

        file_keys = extract_keys_from_file_name(file_name)
        if "collection" not in file_keys:
            print("Collection name not found in file name")
            return False

        success = False
        try:
            load_string = IndalekoDBUploader.build_load_string(
                file_name, file_keys["collection"], db,
            )
            process = subprocess.Popen(
                load_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"Error during external upload: {stderr.decode('utf-8')}")
            else:
                success = True
            print(stdout.decode("utf-8"))
        except Exception as e:
            print(f"Exception during external upload: {e}")
        return success

    @staticmethod
    def copy_to_docker(**kwargs) -> None:
        """
        This will copy data into the docker container for bulk uploading.
        Note: this was extracted from the Mac implementation and needs
        to be modified to work more generally.
        """

        def __run_docker_cmd(cmd: str) -> bool:
            print("Running:", cmd)
            result = False
            try:
                subprocess.run(cmd, check=True, shell=True)
                result = True
            except subprocess.CalledProcessError as e:
                print(f"failed to run the command, got: {e}")
            return result

        print("{:-^20}".format(""))
        print("using arangoimport to import objects")

        # check if the docker is up
        if not __run_docker_cmd("docker ps"):
            """The docker is not running, so we cannot upload the data."""
            print("The docker is not running, so we cannot upload the data.")
            exit(-1)

        # read the config file
        config = IndalekoDBConfig().config

        dest = "/home"  # where in the container we copy the files; we use this for import to the database
        container_name = config["database"]["container"]
        server_username = config["database"]["user_name"]
        server_password = config["database"]["user_password"]
        server_database = config["database"]["database"]
        overwrite = kwargs.get("reset_collection", False)

        # copy the files first
        for filename, dest_filename in [
            (kwargs.get("objects_file"), "objects.jsonl"),
            (kwargs.get("relations_file"), "relations.jsonl"),
        ]:
            __run_docker_cmd(
                f"docker cp {filename} {
                container_name}:{dest}/{dest_filename}",
            )

        # run arangoimport on both of these files
        for filename, collection_name in [
            ("objects.jsonl", "Objects"),
            ("relations.jsonl", "Relationships"),
        ]:
            __run_docker_cmd(
                f"docker exec -t {container_name} arangoimport --file {dest}/{filename} "
                + f'--type "jsonl" --collection "{collection_name}" --server.username "{server_username}" '
                f'--server.password "{server_password}" --server.database "{server_database}" --overwrite {overwrite}',
            )


def main():
    """This is the main function for the database uploader."""
    ic("Testing the database uploader.")


if __name__ == "__main__":
    main()
