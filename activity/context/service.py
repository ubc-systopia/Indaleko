"""
This module provides the implementation of the Indaleko Activity Context service.

This service is responsible for creating and managing activity contexts
to other components that seek to associate their own data with the activity
context.

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
import logging
import os
import sys
import uuid
from pathlib import Path

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# pylint: disable=wrong-import-position
from activity.context.data_models.activity_data import ActivityDataModel
from activity.context.data_models.context_data_model import (
    IndalekoActivityContextDataModel,
)
from constants import IndalekoConstants
from db import IndalekoCollections, IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from utils import IndalekoLogging, IndalekoSingleton
from utils.misc.file_name_management import generate_file_name

# pylint: enable=wrong-import-position


class IndalekoActivityContextService(IndalekoSingleton):
    """This class is the service interface for managing Activity Context."""

    def __init__(self, **kwargs: dict) -> None:
        """Create an instance of the IndalekoActivityContext class."""
        if self._initialized:
            return
        # initialize the object
        self._initialized = True
        if "db_config" in kwargs:
            self.db_config = kwargs["db_config"]
        else:
            self.db_config = IndalekoDBConfig()

        # Get the activity context collection
        activity_collection_name = (
            IndalekoDBCollections.Indaleko_ActivityContext_Collection
        )
        self._private_collection = IndalekoCollections.get_collection(
            activity_collection_name,
        )
        if self._private_collection is None:
            raise RuntimeError(
                f"Collection {activity_collection_name} not found in the database.",
            )

        self.handle = uuid.uuid4()
        self.timestamp = datetime.datetime.now(datetime.UTC)
        self.schema = IndalekoActivityContextDataModel.model_json_schema()
        self.arangodb_schema = {
            "rule": self.schema,
            "level": "strict",
            "message": "The document failed schema validation.  Sorry!",
        }
        self.cursors = {}
        self.updated = False
        self.referenced = False

    def update_cursor(
        self,
        provider: uuid.UUID,
        provider_reference: uuid.UUID,
        provider_data: str | None = None,
        provider_attributes: dict | None = None,
    ) -> bool:
        """
        Update the given provider's cursor.

        Inputs:
            provider : uuid.UUID : The provider of the activity data.
            provider_reference : uuid.UUID : The provider reference for the activity data.
            provider_data : str : The provider data (if any).
            provider_attributes : dict : The provider attributes (if any).

        Outputs:
            bool : True if the cursor was updated, False otherwise.

        Notes:
            If the cursor does not exist, it will be added. If the cursor
            exists, it will be updated **if and only if** the reference has
            changed.  We do not evaluate the data or attributes for changes.
        """
        if (
            provider in self.cursors
            and self.cursors[provider].ProviderReference == provider_reference
        ):
            return False
        # Otherwise, it either didn't exist, or it needs to be updated. Build
        # the new cursor.
        args = {
            "Provider": provider,
            "ProviderReference": provider_reference,
        }
        if provider_data is not None:
            args["ProviderData"] = provider_data
        if provider_attributes is not None:
            args["ProviderAttributes"] = provider_attributes
        cursor = ActivityDataModel(**args)
        self.cursors[provider] = cursor  # add/overwrite
        self.updated = True
        return True

    def get_activity_handle(self) -> uuid.UUID:
        """Get the activity handle for the context."""
        self.referenced = True
        return self.handle

    def get_activity_context_data(
        self,
        handle: uuid.UUID | None = None,
    ) -> IndalekoActivityContextDataModel | None:
        """
        Given an optional handle, retrieve the record from the database.

        Inputs:
            handle : uuid.UUID : The handle for the activity context.

        Outputs:
            IndalekoActivityContextDataModel : The activity context data from
            the database.
            None : If the activity context data is not found in the database.

        Notes:
            If the handle is None, the most recent activity context is returned.
            If there is no data in the database, None is returned.
        """
        if handle is None:
            return IndalekoActivityContextService.get_latest_db_update_dict()
        return handle

    @staticmethod
    def get_latest_db_update_dict() -> dict | None:
        """
        Get the most recent activity context data.

        Output:
            dict : The most recent activity context data.
            None : If there is no data in the database.

        Note: this implementation assumes the timestamp field is indexed.  Since
        it is staticmethod, it does not have access to the instance data.
        """
        query = """
            FOR doc IN @@collection
            SORT doc.Timestamp DESC
            LIMIT 1
            RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_ActivityContext_Collection,
        }
        results = (
            IndalekoDBConfig().get_arangodb().aql.execute(query, bind_vars=bind_vars)
        )
        entries = list(results)
        if len(entries) == 0:
            return None
        assert len(entries) == 1, f"Expected 1 entry, got {len(entries)}"
        return entries[0]

    def write_activity_context_to_database(self) -> bool:
        """
        Write the activity context to the database.

        Outputs:
            bool : True if the activity context was written to the database,
            False otherwise.

        Notes:
            This method will write the activity context to the database.  This
            will cause it to create a new handle and reset the cursor state.

            This **will not** write the activity context to the database if it
            has not changed since the last write, or if no references to it have
            been returned.
        """
        if not self.updated or not self.referenced:
            return False

        doc = IndalekoActivityContextDataModel(
            Handle=self.handle,
            Timestamp=self.timestamp,
            Cursors=list(self.cursors.values()),
        )
        self.handle = uuid.uuid4()
        data = doc.build_arangodb_doc(_key=self.handle)
        self._private_collection.insert(data)
        self.updated = False
        self.referenced = False
        return True


class IndalekoActivityContextTest:
    """This class is used to test the IndalekoActivityContext class."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Create an instance of the IndalekoActivityContextTest class."""
        self.args = args

    def show_command(self) -> None:
        """Command to show the current activity context."""
        ic("show_command called")

    def check_command(self) -> None:
        """Check the activity context database connectivity."""
        ic("check_command called")

    def test_command(self) -> None:
        """Test the activity context data."""
        ic("test_command called")

    def schema_command(self) -> None:
        """Show the data schema."""
        ic("show schema")
        ic(IndalekoActivityContextDataModel.get_arangodb_schema())


def main() -> None:
    """Test the IndalekoActivityContext class."""
    ic("Testing IndalekoActivityContext")
    now = datetime.datetime.now(datetime.UTC)
    timestamp = now.isoformat()

    parser = argparse.ArgumentParser(
        description="Test the IndalekoActivityContext class",
    )
    parser.add_argument("--debug", action="store_true", help="Debug flag")
    parser.add_argument(
        "--logdir",
        type=str,
        default=IndalekoConstants.default_log_dir,
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
    command_subparsers = parser.add_subparsers(
        help="Command subparsers",
        dest="command",
    )
    parser_check = command_subparsers.add_parser(
        "check",
        help="Check the activity context database connectivity",
    )
    parser_check.set_defaults(func=IndalekoActivityContextTest.check_command)
    parser_show = command_subparsers.add_parser(
        "show",
        help="Show the current activity context",
    )
    parser_show.set_defaults(func=IndalekoActivityContextTest.show_command)
    parser_test = command_subparsers.add_parser(
        "test",
        help="Test the activity context data",
    )
    parser_test.set_defaults(func=IndalekoActivityContextTest.test_command)
    parser.set_defaults(func=IndalekoActivityContextTest.check_command)
    parser_schema = command_subparsers.add_parser(
        "schema",
        help="Display ArangoDB schema",
    )
    parser_schema.set_defaults(func=IndalekoActivityContextTest.schema_command)
    args = parser.parse_args()
    if args.debug:
        ic("Testing IndalekoActivityContext")
    if args.log is None:
        args.log = generate_file_name(
            suffix="log",
            service="IndalekoActivtyContext",
            timestamp=timestamp,
        )
    indaleko_logging = IndalekoLogging(
        service_name="IndalekoActivtyContext",
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir,
    )
    if indaleko_logging is None:
        ic("Failed to initialize logging")
        sys.exit(1)
    logging.info("Starting IndalekoActivityContext test.")
    logging.debug(args)
    test = IndalekoActivityContextTest(args)
    args.func(test)
    logging.info("Ending IndalekoActivityContext test.")
    args = parser.parse_args()


if __name__ == "__main__":
    main()
