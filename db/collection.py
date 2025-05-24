"""
This module is used to manage specific collection objects in Indaleko.

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
import sys

from collections.abc import Sequence
from typing import Any

import arango
import arango.collection

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.insert(0,current_path)

# pylint: disable=wrong-import-position
from db.collection_index import IndalekoCollectionIndex
from db.db_config import IndalekoDBConfig
from utils.decorators import type_check


# pylint: enable=wrong-import-position


class IndalekoCollection:
    """IndalekoCollection wraps an ArangoDB collection."""

    def __init__(self, **kwargs: dict) -> None:
        if "ExistingCollection" in kwargs:
            self._arangodb_collection = kwargs["ExistingCollection"]
            assert isinstance(  # noqa: S101
                self._arangodb_collection,
                arango.collection.StandardCollection,
            ), f"self.collection is unexpected type {type(self._arangodb_collection)}"
            self.name = self._arangodb_collection.name
            self.definition = self._arangodb_collection.properties()
            self.db_config = kwargs.get("db", IndalekoDBConfig())
            self.collection_name = self.name
            self.indices = {}
            return
        if "name" not in kwargs:
            raise ValueError("name is a required parameter")
        self.name = kwargs["name"]
        self.definition = kwargs.get("definition")
        self.db_config = kwargs.get("db")
        self.db_config.start()
        self.reset = kwargs.get("reset", False)
        self.max_chunk_size = kwargs.get("max_chunk_size", 1000)
        self.collection_name = self.name
        self.indices = {}
        if self.definition is None:
            raise ValueError("Dynamic collection does not exist")
        assert isinstance(
            self.definition,
            dict,
        ), "Collection definition must be a dictionary"
        assert "schema" in self.definition, "Collection must have a schema"
        assert "edge" in self.definition, "Collection must have an edge flag"
        assert "indices" in self.definition, "Collection must have indices"
        assert isinstance(
            self.db_config,
            IndalekoDBConfig,
        ), "db must be None or an IndalekoDBConfig object"
        self.create_collection(self.collection_name, self.definition, reset=self.reset)

    @type_check
    def create_collection(
        self,
        name: str,
        config: dict,
        reset: bool = False,
    ) -> "IndalekoCollection":
        """
        Create a collection in the database. If the collection already exists,
        return the existing collection. If reset is True, delete the existing
        collection and create a new one.
        """
        if self.db_config.db.has_collection(name):
            if not reset:
                self._arangodb_collection = self.db_config.db.collection(name)
            else:
                raise NotImplementedError("delete existing collection not implemented")
        else:
            self._arangodb_collection = self.db_config.db.create_collection(
                name,
                edge=config["edge"],
            )
            if "schema" in config:
                try:
                    ic(config["schema"])
                    self._arangodb_collection.configure(schema=config["schema"])
                except arango.exceptions.CollectionConfigureError as error:  # pylint: disable=no-member
                    print(f"Failed to configure collection {name}")  # noqa: T201
                    print(error)    # noqa: T201
                    print("Schema:")    # noqa: T201
                    print(json.dumps(config["schema"], indent=2))    # noqa: T201
                    raise
        if "indices" in config:
            existing_indices = list(idx.get("name") for idx in self._arangodb_collection.indexes())
            for index in config["indices"]:
                if index in existing_indices:
                    ic(f"Index {index} already exists for collection {name}")
                    continue
                ic(f"Creating index {index} for collection {name}")
                self.create_index(index, **config["indices"][index])
        assert isinstance(  # noqa: S101
            self._arangodb_collection,
            arango.collection.StandardCollection,
        ), f"self.collection is unexpected type {type(self._arangodb_collection)}"
        return IndalekoCollection(ExistingCollection=self._arangodb_collection)

    def get_indices(self, name: str) -> list[IndalekoCollectionIndex]:
        """Return the index with the given name."""
        indices = []
        collection = self.db_config.db.collection(name)
        for index_data in collection.indexes():
            if index_data.get("type") == "primary":
                continue  # Skip the primary index
            type = index_data.get("type")
            del index_data["type"]
            index = IndalekoCollectionIndex(
                collection=collection,
                type=type,
                **index_data,
            )
            indices.append(index)
        sys.exit(0)
        return []

    @type_check
    def delete_collection(self, name: str) -> bool:
        """Delete the collection with the given name."""
        if not self.db_config.db.has_collection(name):
            return False
        self.db_config.db.delete_collection(name)
        return True

    def create_index(self, name, **kwargs: dict[str, Any]) -> "IndalekoCollection":
        """Create an index for the given collection."""
        self.indices[name] = IndalekoCollectionIndex(
            collection=self._arangodb_collection,
            **kwargs,
        )
        return self

    def find_entries(self, **kwargs):
        """Given a list of keyword arguments, return a list of documents that match the criteria."""
        return list(self._arangodb_collection.find(kwargs))

    def insert(self, document: dict, overwrite: bool = False) -> dict | bool:
        """
        Insert a document into the collection.

        Inputs:
            document (dict): The document to insert.
            overwrite (bool): If True, overwrite the document if it already exists.

        Returns:
            dict: The document that was inserted.
            None: If the document could not be inserted.

        Note: the python-arango library docs are ambiguous about the return type, suggesting
        Union[dict,None] and Union[dict,bool] in different places.  The way we use it here,
        this should return dict or None
        """
        try:
            return self._arangodb_collection.insert(document, overwrite=overwrite)
        except arango.exceptions.DocumentInsertError as e:
            ic(f"Insert failure for document into collection {self.name}")
            ic(document)
            ic(e)
            return None

    @type_check
    def bulk_insert(
        self,
        documents: Sequence[dict[str, Any]],
    ) -> None | list[dict[str, Any]]:
        """Insert a list of documents into the collection in batches."""
        errors = []
        for i in range(0, len(documents), self.max_chunk_size):
            batch = documents[i : i + self.max_chunk_size]
            try:
                result = self._arangodb_collection.insert_many(batch)
                batch_errors = [doc for doc in result if doc.get("error")]
                errors.extend(batch_errors)
            except arango.exceptions.DocumentInsertError as e:
                ic(f"Bulk insert failure for documents into collection {self.name}")
                ic(batch)
                ic(e)
                raise
        return errors if errors else None

    def add_schema(self, schema: dict) -> "IndalekoCollection":
        """Add a schema to the collection."""
        self._arangodb_collection.configure(schema=schema)
        return self

    def get_schema(self) -> dict:
        """Return the schema for the collection."""
        return self._arangodb_collection.properties().get("schema", {})

    def delete(self, key: str) -> "IndalekoCollection":
        """Delete the document with the given key."""
        return self._arangodb_collection.delete(key)

    def get_arangodb_collection(self) -> arango.collection.StandardCollection:
        """Return the underlying ArangoDB collection object."""
        return self._arangodb_collection


def main() -> None:
    """Test the IndalekoCollection class."""


if __name__ == "__main__":
    main()
