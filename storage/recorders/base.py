"""
This is the generic class for an Indaleko Storage Recorder.

An Indaleko storage recorder takes information about some (or all) of the data that is stored in
various storage repositories available to this machine.  It processes the output
from storage recorders and then generates additional metadata to associate with the
storage object (s) in the database.

Examples of recorders include:

* A file system specific metadata normalizer, which takes metadata information
  collected about one or more files and then converts that into a normalized
  form to be stored in the database. This includes common metadata such as
  length, label (the "name" of the file), timestamps, and so on.

* A semantic metadata generator, which takes the input from collectors and then
  performs operations on one or more files described by the collector to extract
  or compute metadata based upon the content of the file.  For example, this
  might include a "bag of words" from a text file, EXIF data from a JPEG
  file, or even commonly used checksums (e.g., MD5, SHA1, SHA256, etc.) that are
  computed from the file's contents.

* Environmental metadata generators, which take information about the
  environment in which the file is stored, such as the volume on which it is
  stored, additional non-standard metadata features that might be available,
  etc.


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
import datetime
import json
import logging
import mimetypes
import os
import sys
import tempfile
import uuid
from pathlib import Path
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
from constants import IndalekoConstants
from data_models import (
    IndalekoSemanticAttributeDataModel,
    IndalekoSourceIdentifierDataModel,
)
from data_models.storage_semantic_attributes import StorageSemanticAttributes
from db import (
    IndalekoCollection,
    IndalekoDBCollections,
    IndalekoDBConfig,
    IndalekoServiceManager,
)
from storage.i_object import IndalekoObject
from storage.i_relationship import IndalekoRelationship
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from utils.cli.base import IndalekoBaseCLI
from utils.decorators import type_check
from utils.misc.directory_management import (
    indaleko_default_config_dir,
    indaleko_default_data_dir,
    indaleko_default_log_dir,
)
from utils.misc.file_name_management import (
    extract_keys_from_file_name,
    generate_file_name,
)

# pylint: enable=wrong-import-position


class BaseStorageRecorder:
    """
    IndalekoStorageRecorder is the generic class that we use for recording data from the
    various collectors that we have. Platform specific recorders are built on top
    of this class to handle platform-specific recording.
    """

    file_prefix = IndalekoConstants.default_prefix
    file_suffix = ".jsonl"

    recorder_platform = None  # This must be set by the derived class
    recorder_name = "recorder"

    storage_recorder_uuid = "526e0240-1ee4-46e9-9dac-3e557a8fb654"
    storage_recorder_service_name = "Indaleko Generic Storage Recorder"
    storage_recorder_service_description = (
        "This is the base (non-specialized) Indaleko Storage Recorder. " + "You should not see it in the database."
    )
    storage_recorder_service_version = "1.0"

    counter_values = (
        "input_count",
        "output_count",
        "dir_count",
        "file_count",
        "error_count",
        "edge_count",
    )

    recorder_data = IndalekoStorageRecorderDataModel(
        ServiceRegistrationName=storage_recorder_service_name,
        ServiceFileName=recorder_name,
        ServiceUUID=storage_recorder_uuid,
        ServiceVersion=storage_recorder_service_version,
        ServiceDescription=storage_recorder_service_description,
    )

    def __init__(self: "BaseStorageRecorder", **kwargs: dict) -> None:
        """
        Constructor for the IndalekoStorageRecorder class. Takes a configuration object
        as a parameter. The configuration object is a dictionary that contains
        all the configuration parameters for the recorder.
        """
        self.kwargs = kwargs
        if "recorder_data" in kwargs:
            self.recorder_data = kwargs["recorder_data"]
        if "args" in kwargs:
            self.args = kwargs["args"]
            self.output_type = getattr(self.args, "output_type", "file")
            self.debug = getattr(self.args, "debug", False)
        else:
            self.args = None
            self.output_type = "file"
            self.debug = kwargs.get("debug", False)
        if "storage" in kwargs:
            self.storage_description = kwargs["storage"]
        self.file_prefix = BaseStorageRecorder.file_prefix
        if "file_prefix" in kwargs:
            self.file_prefix = kwargs["file_prefix"]
        self.file_prefix = self.file_prefix.replace("-", "_")
        self.file_suffix = BaseStorageRecorder.file_suffix
        if "file_suffix" in kwargs:
            self.file_suffix = kwargs["file_suffix"]
        self.file_suffix = self.file_suffix.replace("-", "_")
        if "machine_id" in kwargs:
            self.machine_id = str(uuid.UUID(kwargs["machine_id"]).hex)
        self.timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        if "timestamp" in kwargs:
            self.timestamp = kwargs["timestamp"]
        self.recorder = "unknown"
        if "recorder" in kwargs:
            self.recorder = kwargs["recorder"]
        self.storage_description = None
        if "storage_description" in kwargs:
            if kwargs["storage_description"] is None or kwargs["storage_description"] == "unknown":
                del kwargs["storage_description"]
            else:
                self.storage_description = str(
                    uuid.UUID(kwargs["storage_description"]).hex,
                )
                if self.debug:
                    ic("Storage description: ", self.storage_description)
        self.data_dir = kwargs.get("data_dir", indaleko_default_data_dir)
        self.output_dir = kwargs.get("output_dir", self.data_dir)
        self.input_dir = kwargs.get("input_dir", self.data_dir)
        self.input_file = kwargs.get("input_file", None)
        self.config_dir = kwargs.get("config_dir", indaleko_default_config_dir)
        self.log_dir = kwargs.get("log_dir", indaleko_default_log_dir)
        self.recorder_service = IndalekoServiceManager().register_service(
            service_name=self.get_recorder_service_registration_name(),
            service_id=str(self.get_recorder_service_uuid()),
            service_version=self.get_recorder_service_version(),
            service_description=self.get_recorder_service_description(),
            service_type=self.get_recorder_service_type(),
        )
        assert self.recorder_service is not None, "Recorder service does not exist"
        for count in self.counter_values:
            setattr(self, count, 0)
        self.reset_data()

    def reset_data(self) -> None:
        """
        This function will reclaim any memory used by the recorder by
        resetting the data elements.
        """
        self.dir_data_by_path = {}
        self.dir_data = []
        self.file_data = []
        self.dirmap = {}
        self.dir_edges = []
        self.collector_data = []

    @classmethod
    def get_recorder_platform_name(cls: "BaseStorageRecorder") -> str:
        """This function returns the platform name for the recorder."""
        return cls.recorder_data.PlatformName

    @classmethod
    def get_recorder_service_registration_name(cls) -> str:
        """This function returns the service name for the recorder."""
        return cls.recorder_data.ServiceRegistrationName

    @classmethod
    def get_recorder_service_file_name(cls) -> str:
        return cls.recorder_data.ServiceFileName

    @classmethod
    def get_recorder_service_uuid(cls) -> uuid.UUID:
        """This function returns the service UUID for the recorder."""
        return cls.recorder_data.ServiceUUID

    @classmethod
    def get_recorder_service_version(cls) -> str:
        """This function returns the service version for the recorder."""
        return cls.recorder_data.ServiceVersion

    @classmethod
    def get_recorder_service_description(cls) -> str:
        """This function returns the service description for the recorder."""
        return cls.recorder_data.ServiceDescription

    @classmethod
    def get_recorder_service_type(cls) -> str:
        """This function returns the service type for the recorder."""
        return cls.recorder_data.ServiceType

    @classmethod
    def get_recorder_file_service_name(cls) -> str:
        """This function returns the service name to use in output file names."""
        return cls.recorder_name

    def get_counts(self) -> dict:
        """
        Retrieves counters about the recorder.
        """
        return {x: getattr(self, x) for x in BaseStorageRecorder.counter_values}

    def generate_output_file_name(self, **kwargs) -> str:
        """
        Given a set of parameters, generate a file name for the output
        file.
        """
        output_dir = None
        if "output_dir" in kwargs:
            output_dir = kwargs["output_dir"]
            del kwargs["output_dir"]
        if output_dir is None:
            output_dir = self.data_dir
        if hasattr(self, "machine_id") and self.machine_id is not None:
            kwargs["machine"] = str(uuid.UUID(self.machine_id).hex)
        if self.storage_description is not None and kwargs["storage"] != "unknown":
            kwargs["storage"] = str(uuid.UUID(self.storage_description).hex)
        name = generate_file_name(**kwargs)
        return os.path.join(output_dir, name)

    def generate_file_name(self, target_dir: str = None, suffix=None) -> str:
        """This will generate a file name for the recorder output file."""
        if suffix is None:
            suffix = self.file_suffix
        kwargs = {
            "prefix": self.file_prefix,
            "suffix": suffix,
            "platform": self.recorder_platform,
            "service": self.recorder_name,
            "collection": IndalekoDBCollections.Indaleko_Object_Collection,
            "timestamp": self.timestamp,
            "output_dir": target_dir,
        }
        if hasattr(self, "machine_id") and self.machine_id is not None:
            kwargs["machine"] = str(uuid.UUID(self.machine_id).hex)
        if hasattr(self, "storage_description") and self.storage_description is not None:
            kwargs["storage"] = str(uuid.UUID(self.storage_description).hex)
        if hasattr(self, "user_id") and self.user_id is not None:
            kwargs["user"] = self.user_id
        return self.generate_output_file_name(**kwargs)

    @staticmethod
    def extract_metadata_from_recorder_file_name(file_name: str) -> dict:
        """
        This will extract the metadata from the given file name.
        """
        data = extract_keys_from_file_name(file_name)
        if "machine" in data:
            data["machine"] = str(uuid.UUID(data["machine"]))
        if "storage" in data:
            data["storage"] = str(uuid.UUID(data["storage"]))
        return data

    @staticmethod
    def write_data_to_file(
        data: list,
        file_name: str = None,
        jsonlines_output: bool = True,
    ) -> int:
        """
        This will write the given data to the specified file.

        Inputs:
            * data: the data to write
            * file_name: the name of the file to write to
            * jsonlines_output: whether to write the data in JSONLines format

        Returns:
            The number of records written to the file.
        """
        if data is None:
            raise ValueError("data must be specified")
        if file_name is None:
            raise ValueError("file_name must be specified")
        output_count = 0
        if jsonlines_output:
            with jsonlines.open(file_name, mode="w") as writer:
                for entry in data:
                    try:
                        writer.write(entry.serialize())
                        output_count += 1
                    except TypeError as err:
                        logging.exception("Error writing entry to JSONLines file: %s", err)
                        logging.exception("Entry: %s", entry)
                        logging.exception("Output count: %d", output_count)
                        logging.exception("Data size %d", len(data))
                        raise err
            logging.info("Wrote JSONLines data to %s", file_name)
            ic("Wrote JSON data to", file_name)
        else:
            json.dump(data, file_name, indent=4)
            logging.info("Wrote JSON data to %s", file_name)
        return output_count

    @type_check
    def upload_data_to_database(
        self,
        data: list,
        collection: IndalekoCollection | str = "Objects",
        database: IndalekoDBConfig = IndalekoDBConfig(),
        chunk_size: int = 5000,
    ) -> bool:
        """
        This will upload the specified data to the database.

        Inputs:
            * data: list of data to upload (must be in the correct format, of course)
            * collection: the collection to which we should upload the data (defaults to 'Objects')
            * database: the database configuration object (uses default config if not specified)
            * chunk_size: the number of records to upload at a time (defaults to 5000)
        """
        raise NotImplementedError(
            "upload_data_to_database implementation is not complete.",
        )
        if isinstance(collection, str):
            collection = IndalekoCollection(collection, db_config=database)
            assert isinstance(
                collection,
                IndalekoCollection,
            ), "Collection is not an IndalekoCollection"
        count = 0
        while count < len(data):
            chunk = data[count : count + chunk_size]
            count += chunk_size
            assert chunk

    @staticmethod
    def build_load_string(**kwargs) -> str:
        """
        This will build the load string for the arangoimport command.
        """
        db_config = IndalekoDBConfig()
        load_string = "arangoimport"
        if "collection" in kwargs:
            load_string += " -collection " + kwargs["collection"]
        load_string += " --server.username " + db_config.get_user_name()
        load_string += " --server.password " + db_config.get_user_password()
        if db_config.get_ssl_state():
            load_string += " --ssl.protocol 5"
            endpoint = "http+ssl://"
        else:
            endpoint = "http+tcp://"
        endpoint += db_config.get_hostname() + ":" + db_config.get_port()
        load_string += " --server.endpoint " + endpoint
        load_string += " --server.database " + kwargs.get(
            "database",
            db_config.get_database_name(),
        )
        if "file" in kwargs:
            load_string += " " + kwargs["file"]
        return load_string

    def load_collector_data_from_file(self: "BaseStorageRecorder") -> None:
        """This function loads the collector data from the file."""
        if self.input_file is None:
            raise ValueError("input_file must be specified")
        if self.input_file.endswith(".jsonl"):
            self.collector_data = []
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.collector_data.append(entry)
        elif self.input_file.endswith(".json"):
            with open(self.input_file, encoding="utf-8-sig") as file:
                self.collector_data = json.load(file)
        else:
            raise ValueError(f"Input file {self.input_file} is an unknown type")
        if not isinstance(self.collector_data, list):
            raise ValueError("collector_data is not a list")
        self.input_count = len(self.collector_data)

    @staticmethod
    def map_suffix_to_mime_type(
        filename: str,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Maps a file's suffix to an estimated MIME type and returns it as a semantic attribute.

        This provides a quick estimation of file type without examining file contents.
        For more accurate MIME type detection, content-based analysis should be used.

        Args:
            filename: The filename (with extension) to analyze

        Returns:
            A list containing a semantic attribute with the estimated MIME type
        """
        # Extract file extension and convert to lowercase
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if not ext:
            # No extension, return application/octet-stream as default
            return [
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
                    Value="application/octet-stream",
                ),
            ]

        # Get MIME type from extension
        guessed_type, _ = mimetypes.guess_type(filename)

        # If we couldn't determine a type, use a generic default based on extension presence
        if guessed_type is None:
            guessed_type = "application/octet-stream"

        # Add both the detected MIME type and the raw suffix
        # (without the dot) as semantic attributes
        return [
            IndalekoSemanticAttributeDataModel(
                Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
                Value=guessed_type,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_SUFFIX,
                Value=ext[1:] if ext.startswith(".") else ext,
            ),
        ]

    @staticmethod
    def map_name_to_semantic_attributes(
        filename: str,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Maps a file's name to semantic attributes.

        Args:
            filename (str): _description_

        Raises:
            ValueError: _description_
            ValueError: _description_
            NotImplementedError: _description_
            NotImplementedError: _description_

        Returns:
            list[IndalekoSemanticAttributeDataModel]: _description_
        """
        assert isinstance(filename, str), "filename is not a string"
        return [
            {
                "Identifier": StorageSemanticAttributes.STORAGE_ATTRIBUTES_LOWERCASE_FILE_NAME,
                "Value": filename.lower(),
            },
        ]

    @staticmethod
    def build_storage_relationship(
        id1: str | uuid.UUID,
        id2: str | uuid.UUID,
        relationship: str | uuid.UUID,
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a storage relationship object between two objects."""
        return IndalekoRelationship(
            objects=(
                {
                    "collection": IndalekoDBCollections.Indaleko_Object_Collection,
                    "object": id1,
                },
                {
                    "collection": IndalekoDBCollections.Indaleko_Object_Collection,
                    "object": id2,
                },
            ),
            relationships=[IndalekoSemanticAttributeDataModel(Identifier=relationship)],
            source_id=source_id,
        )

    @staticmethod
    def build_dir_contains_relationship(
        parent: str | uuid.UUID,  # parent
        child: str | uuid.UUID,  # child
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a contains relationship object for a directory and a child."""
        return BaseStorageRecorder.build_storage_relationship(
            parent,
            child,
            IndalekoRelationship.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
            source_id,
        )

    @staticmethod
    def build_contained_by_dir_relationship(
        child: str | uuid.UUID,  # child
        parent: str | uuid.UUID,  # parent
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a contains relationship object for a directory and a child."""
        return BaseStorageRecorder.build_storage_relationship(
            child,
            parent,
            IndalekoRelationship.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR,
            source_id,
        )

    @staticmethod
    def build_volume_contains_relationship(
        volume: str | uuid.UUID,  # volume
        child: str | uuid.UUID,  # child
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a contains relationship object for a volume and a child."""
        return BaseStorageRecorder.build_storage_relationship(
            volume,
            child,
            IndalekoRelationship.VOLUME_CONTAINS_RELATIONSHIP_UUID_STR,
            source_id,
        )

    @staticmethod
    def build_contained_by_volume_relationship(
        child: str | uuid.UUID,  # child
        volume: str | uuid.UUID,  # volume
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a contains relationship object for a volume and a child."""
        return BaseStorageRecorder.build_storage_relationship(
            child,
            volume,
            IndalekoRelationship.CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR,
            source_id,
        )

    @staticmethod
    def build_machine_contains_relationship(
        machine: str | uuid.UUID,  # machine
        child: str | uuid.UUID,  # child
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a contains relationship object for a machine and a child."""
        return BaseStorageRecorder.build_storage_relationship(
            machine,
            child,
            IndalekoRelationship.MACHINE_CONTAINS_RELATIONSHIP_UUID_STR,
            source_id,
        )

    @staticmethod
    def build_contained_by_machine_relationship(
        child: str | uuid.UUID,  # child
        machine: str | uuid.UUID,  # machine
        source_id: str | uuid.UUID,
    ) -> IndalekoRelationship:
        """This builds a contains relationship object for a machine and a child."""
        return BaseStorageRecorder.build_storage_relationship(
            child,
            machine,
            IndalekoRelationship.CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR,
            source_id,
        )

    def build_dirmap(self) -> None:
        """This function builds the directory/file map"""
        for item in self.dir_data:
            fqp = os.path.join(item["LocalPath"], item["Label"])
            identifier = item.args["ObjectIdentifier"]
            self.dirmap[fqp] = identifier

    def build_edges(self) -> None:
        """Build the edges between files and directories."""
        source_id = IndalekoSourceIdentifierDataModel(
            Identifier=str(self.recorder_data.ServiceUUID),
            Version=self.recorder_data.ServiceVersion,
        )
        for item in self.dir_data + self.file_data:
            assert "LocalPath" in item, f"Path not in item: {item.indaleko_object}"
            parent = item["LocalPath"]
            if parent not in self.dirmap:
                # ic('Parent not in dirmap: ', parent)
                continue
            parent_id = self.dirmap[parent]
            self.dir_edges.append(
                BaseStorageRecorder.build_dir_contains_relationship(
                    parent_id,
                    item.args["ObjectIdentifier"],
                    source_id,
                ),
            )
            self.edge_count += 1
            self.dir_edges.append(
                BaseStorageRecorder.build_contained_by_dir_relationship(
                    item.args["ObjectIdentifier"],
                    parent_id,
                    source_id,
                ),
            )
            self.edge_count += 1
            volume = item.args.get("Volume")
            if volume:
                self.dir_edges.append(
                    BaseStorageRecorder.build_volume_contains_relationship(
                        volume,
                        item.args["ObjectIdentifier"],
                        source_id,
                    ),
                )
                self.edge_count += 1
                self.dir_edges.append(
                    BaseStorageRecorder.build_contained_by_volume_relationship(
                        item.args["ObjectIdentifier"],
                        volume,
                        source_id,
                    ),
                )
                self.edge_count += 1
            machine_id = item.args.get("machine_id")
            if machine_id:
                self.dir_edges.append(
                    BaseStorageRecorder.build_machine_contains_relationship(
                        machine_id,
                        item.args["ObjectIdentifier"],
                        source_id,
                    ),
                )
                self.edge_count += 1
                self.dir_edges.append(
                    BaseStorageRecorder.build_contained_by_machine_relationship(
                        item.args["ObjectIdentifier"],
                        machine_id,
                        source_id,
                    ),
                )
                self.edge_count += 1

    @staticmethod
    def arangoimport_object_data(recorder: "BaseStorageRecorder") -> None:
        """Import the object data into the database"""
        if recorder.object_data_load_string is None:
            raise ValueError("object_data_load_string must be set")
        recorder.execute_command(recorder.object_data_load_string)

    @staticmethod
    def arangoimport_relationship_data(recorder: "BaseStorageRecorder") -> None:
        """Import the relationship data into the database"""
        if recorder.relationship_data_load_string is None:
            raise ValueError("relationship_data_load_string must be set")
        recorder.execute_command(recorder.relationship_data_load_string)

    @staticmethod
    def bulk_upload_object_data(recorder: "BaseStorageRecorder") -> None:
        """Bulk upload the object data to the database"""
        assert isinstance(
            recorder,
            BaseStorageRecorder,
        ), "recorder is not a BaseStorageRecorder"
        raise NotImplementedError("bulk_upload_object_data must be implemented")

    @staticmethod
    def bulk_upload_relationship_data(recorder: "BaseStorageRecorder") -> None:
        """Bulk upload the relationship data to the database"""
        assert isinstance(
            recorder,
            BaseStorageRecorder,
        ), "recorder is not a BaseStorageRecorder"
        raise NotImplementedError("bulk_upload_relationship_data must be implemented")

    class base_recorder_mixin(IndalekoBaseCLI.default_handler_mixin):
        """This is a mixin class for the base recorder."""

        @staticmethod
        @type_check
        def get_additional_parameters(
            pre_parser: argparse.ArgumentParser,
        ) -> argparse.ArgumentParser:
            """This function adds common switches for local storage recorders to a parser."""
            default_output_type = "file"
            output_type_choices = [default_output_type]
            output_type_help = "Output type: file  = write to a file, "
            output_type_choices.append("incremental")
            output_type_help += "incremental = add new entries, update changed entries in database, "
            output_type_choices.append("bulk")
            output_type_help += "bulk = write all entries to the database using the bulk uploader interface, "
            output_type_choices.append("docker")
            output_type_help += "docker = copy to the docker volume"
            output_type_help += f" (default={default_output_type})"
            pre_parser.add_argument(
                "--output_type",
                choices=output_type_choices,
                default=default_output_type,
                help=output_type_help,
            )
            pre_parser.add_argument(
                "--arangoimport",
                default=False,
                help="Use arangoimport to load data (default=False)",
                action="store_true",
            )
            pre_parser.add_argument(
                "--bulk",
                default=False,
                help="Use bulk loader to load data (default=False)",
                action="store_true",
            )
            return pre_parser

    @staticmethod
    def execute_command(command: str) -> None:
        """Execute a command"""
        result = os.system(command)
        logging.info("Command %s result: %d", command, result)
        print(f"Command {command} result: {result}")

    @staticmethod
    def write_object_data_to_file(recorder: "BaseStorageRecorder", **kwargs) -> None:
        """Write the object data to a file"""
        output_file = kwargs.get("output_file")
        if not output_file and hasattr(recorder, "output_object_file"):
            output_file = recorder.output_object_file
        if not output_file:
            output_file = recorder.generate_file_name(target_dir=recorder.output_dir)
            ic(
                f"Warning: falling back to auto-generated output file name {output_file}",
            )
        output_file = str(Path(recorder.output_dir) / output_file)
        data_file_name, count = recorder.record_data_in_file(
            recorder.dir_data + recorder.file_data,
            recorder.data_dir,
            output_file,
        )
        recorder.object_data_load_string = recorder.build_load_string(
            collection=IndalekoDBCollections.Indaleko_Object_Collection,
            file=output_file,
        )
        logging.info("Load string: %s", recorder.object_data_load_string)
        print("Load string (objects): ", recorder.object_data_load_string)
        if hasattr(recorder, "output_count"):  # should be there
            recorder.output_count += count

    @staticmethod
    def write_edge_data_to_file(recorder: "BaseStorageRecorder", **kwargs) -> None:
        """Write the edge data to a file"""
        output_file = kwargs.get("output_file")
        if not output_file and hasattr(recorder, "output_object_file"):
            output_file = recorder.output_edge_file
        if output_file:
            output_file = str(Path(recorder.output_dir) / output_file)
        data_file_name, count = recorder.record_data_in_file(
            recorder.dir_edges,
            recorder.data_dir,
            output_file,
        )
        recorder.relationship_data_load_string = recorder.build_load_string(
            collection=IndalekoDBCollections.Indaleko_Relationship_Collection,
            file=data_file_name,
        )
        logging.info("Load string: %s", recorder.relationship_data_load_string)
        print("Load string (relationships): ", recorder.relationship_data_load_string)
        if hasattr(recorder, "edge_count"):
            recorder.edge_count += count

    @staticmethod
    def record_data_in_file(
        data: list,
        dir_name: Path | str,
        preferred_file_name: Path | str | None = None,
    ) -> tuple[str, int]:
        """
        Record the specified data in a file.

        Inputs:
            - data: The data to record
            - preferred_file_name: The preferred file name (if any)

        Returns:
            - The name of the file where the data was recorded
            - The number of entries that were written to the file

        Notes:
            A temporary file is always created to hold the data, and then it is renamed to the
            preferred file name if it is provided.
        """
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tf:
            temp_file_name = tf.name
        count = BaseStorageRecorder.write_data_to_file(data, temp_file_name)
        if preferred_file_name is None:
            return temp_file_name, count
        # try to rename the file
        try:
            if os.path.exists(preferred_file_name):
                os.remove(preferred_file_name)
            os.rename(temp_file_name, preferred_file_name)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.exception(
                "Unable to rename temp file %s to output file %s",
                temp_file_name,
                preferred_file_name,
            )
            print(
                f"Unable to rename temp file {temp_file_name} to output file {preferred_file_name}",
            )
            print(f"Error: {e}")
            preferred_file_name = temp_file_name
        return preferred_file_name, count

    def get_object_path(self: "BaseStorageRecorder", obj: IndalekoObject):
        """Given an Indaleko object, return a valid local path to the object"""
        return obj["LocalPath"]  # default is no change

    def is_object_directory(self: "BaseStorageRecorder", obj: IndalekoObject) -> bool:
        """Return True if the object is a directory"""
        assert isinstance(
            obj,
            IndalekoObject,
        ), f"obj is {type(obj)}, not an IndalekoObject"
        return "S_IFDIR" in obj.args["PosixFileAttributes"] or "FILE_ATTRIBUTE_DIRECTORY" in getattr(
            obj.args,
            "WindowsFileAttributes",
            "",
        )

    def normalize(self) -> None:
        """Normalize the data from the collector"""
        self.load_collector_data_from_file()
        for item in self.collector_data:
            try:
                obj = self.normalize_collector_data(item)
            except OSError as e:
                logging.exception("Error normalizing data: %s", e)
                logging.exception("Data: %s", item)
                ic(f"Error normalizing data: {e}")
                self.error_count += 1
                continue
            assert isinstance(
                obj,
                IndalekoObject,
            ), f"obj is {type(obj)}, not an IndalekoObject"
            if self.is_object_directory(obj):
                if "LocalPath" not in obj:
                    logging.warning(
                        "Directory object does not have a path: %s",
                        obj.serialize(),
                    )
                    ic(f"Directory object does not have a path: {obj.serialize()}")
                    continue  # skip
                self.dir_data_by_path[self.get_object_path(obj)] = obj
                self.dir_data.append(obj)
                self.dir_count += 1
                if self.dir_count % 1000 == 0:
                    ic("Processed", self.dir_count, "directories")
            else:
                self.file_data.append(obj)
                self.file_count += 1
                if self.file_count % 1000 == 0:
                    ic("Processed", self.file_count, "files")

    @staticmethod
    def map_posix_storage_attributes_to_semantic_attributes(
        posix_attributes: dict[str, Any],
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """Map POSIX storage attributes to semantic attributes"""
        semantic_attributes = []
        if "st_dev" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_DEVICE,
                    Value=posix_attributes["st_dev"],
                ),
            )
        if "st_gid" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_GID,
                    Value=posix_attributes["st_gid"],
                ),
            )
        if "st_mode" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_MODE,
                    Value=posix_attributes["st_mode"],
                ),
            )
        if "st_nlink" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_NLINK,
                    Value=posix_attributes["st_nlink"],
                ),
            )
        if "st_reparse_tag" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_REPARSE_TAG,
                    Value=posix_attributes["st_reparse_tag"],
                ),
            )
        if "st_uid" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_UID,
                    Value=posix_attributes["st_uid"],
                ),
            )
        if "st_inode" in posix_attributes:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=StorageSemanticAttributes.STORAGE_ATTRIBUTES_INODE,
                    Value=posix_attributes["st_inode"],
                ),
            )
        file_name = posix_attributes.get("Name")
        if file_name:
            semantic_attributes.extend(
                BaseStorageRecorder.map_name_to_semantic_attributes(file_name),
            )
            if "st_mode" in posix_attributes:
                semantic_attributes.extend(
                    BaseStorageRecorder.map_suffix_to_mime_type(file_name),
                )
        return semantic_attributes

    def record(self) -> None:
        """
        This function processes and records the collector file and emits the data needed to
        upload to the database.
        """
        self.normalize()
        assert len(self.dir_data) + len(self.file_data) > 0, "No data to record"
        self.build_dirmap()
        self.build_edges()
        assert self.recorder_platform
        kwargs = {
            "platform": self.recorder_platform,
            "service": self.get_recorder_file_service_name(),
            "collection": IndalekoDBCollections.Indaleko_Object_Collection,
            "timestamp": self.timestamp,
            "output_dir": self.data_dir,
        }
        if hasattr(self, "machine_id") and self.machine_id is not None:
            kwargs["machine"] = str(uuid.UUID(self.machine_id).hex)
        if hasattr(self, "storage_description") and self.storage_description:
            kwargs["storage"] = self.storage_description
        self.output_object_file = self.generate_output_file_name(**kwargs)
        kwargs["collection"] = IndalekoDBCollections.Indaleko_Relationship_Collection
        self.output_edge_file = self.generate_output_file_name(**kwargs)


def main():
    """Test code for IndalekoStorageRecorder.py"""
    # Now parse the arguments
    recorder = BaseStorageRecorder(
        recorder_data=IndalekoStorageRecorderDataModel(
            ServiceName=BaseStorageRecorder.indaleko_generic_storage_recorder_service_name,
            ServiceUUID=BaseStorageRecorder.indaleko_generic_storage_recorder_uuid,
            ServiceVersion=BaseStorageRecorder.indaleko_generic_storage_recorder_service_version,
            ServiceDescription=BaseStorageRecorder.indaleko_generic_storage_recorder_service_description,
        ),
        service_name=BaseStorageRecorder.indaleko_generic_storage_recorder_service_name,
        service_id=BaseStorageRecorder.indaleko_generic_storage_recorder_uuid_str,
        test=True,
    )
    assert recorder is not None, "Could not create recorder."
    fname = recorder.generate_file_name()
    print(fname)
    metadata = recorder.extract_metadata_from_recorder_file_name(fname)
    print(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    main()
