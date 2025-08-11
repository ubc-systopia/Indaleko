"""
This module defines the database statistics model for Indaleko.

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

# import uuid
# from datetime import datetime, timezone
# from typing import Dict, Any, Type, TypeVar, Union, Optional
# from typing import Union, List
from pydantic import BaseModel, Field  # , AwareDatetime, field_validator


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# T = TypeVar('T', bound='IndalekoPerformanceDataModel')

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


# pylint: enable=wrong-import-position


class IndalekoDBStatisticsDataModel(IndalekoBaseModel):
    """This class defines the data model for the Indaleko database statistics."""

    class __collection_attributes(BaseModel):
        """This defines the information for a given collection."""

        CollectionName: str
        Attributes: list[IndalekoSemanticAttributeDataModel]

    Record: IndalekoRecordDataModel = Field(
        ...,
        title="Record",
    )
    DataAttributes: list[IndalekoSemanticAttributeDataModel]
    CollectionAttributes: list[__collection_attributes]

    class Config:
        json_schema_extra = {
            "example": {
                "Record": {
                    "SourceIdentifier": {
                        "Identifier": "180a4fe8-cc30-4ed9-abab-bbf935e450f9",
                        "Version": "1.0",
                    },
                    "Timestamp": "2025-02-05T23:38:48.319654+00:00",
                    "Attributes": {},
                    "Data": "Base64EncodedData",
                },
                "DataAttributes": [
                    {
                        "Identifier": {
                            "Identifier": "f73abb61-858a-4949-9868-f1b82181f08d",
                            "Version": "1.0",
                            "Description": "Database Type and/or Name (MSSQL, ArangoDB, etc.)",
                        },
                        "Data": "ArangoDB",
                    },
                    {
                        "Identifier": {
                            "Identifier": "717efa63-f509-4961-9336-b6fa79c1a009",
                            "Version": "1.0",
                            "Description": "Database Name",
                        },
                        "Data": "Indaleko",
                    },
                ],
                "CollectionAttributes": {
                    "CollectionName": "Objects",
                    "Attributes": [
                        {
                            "Identifier": {
                                "Identifier": "ce008afa-356a-4f2d-ba35-ca3330abfea6",
                                "Version": "1.0",
                                "Description": "Statistics for the Collection",
                            },
                            "Data": {
                                "cache_in_use": False,
                                "cache_size": 0,
                                "cache_usage": 0,
                                "documents_size": 9173625741,
                                "indexes": {
                                    "count": 6,
                                    "size": 14386955476,
                                },
                            },
                        },
                        {
                            "Identifier": {
                                "Identifier": "f4fb9859-e132-471c-a34c-d48020e27bd5",
                                "Version": "1.0",
                                "Description": "Element count for the Collection",
                            },
                            "Data": 84759039,
                        },
                        {
                            "Identifier": {
                                "Identifier": "31b2b7ea-a934-4e34-bb66-1f199db79fdc",
                                "Version": "1.0",
                                "Description": "Properties for the collection",
                            },
                            "Data": {
                                "cache": False,
                                "edge": False,
                                "global_id": "h3BBE45331826/13362158",
                                "id": "13362158",
                                "internal_validator_type": 0,
                                "key_options": {
                                    "key_generator": "traditional",
                                    "key_last_value": 0,
                                    "user_keys": True,
                                },
                                "name": "PerformanceData",
                                "object_id": "13362157",
                                "rev_as_id": True,
                                "schema": None,
                                "smart_child": False,
                                "status": 3,
                                "status_string": "loaded",
                                "sync": False,
                                "sync_by_revision": True,
                                "system": False,
                                "type": 2,
                                "write_concern": 1,
                            },
                        },
                        {
                            "Identifier": {
                                "Identifier": "f4fb9859-e132-471c-a34c-d48020e27bd5",
                                "Version": "1.0",
                                "Description": "Collection Revision Number",
                            },
                            "Data": 547,
                        },
                    ],
                },
            },
        }


def main() -> None:
    """This allows testing the data model."""
    IndalekoDBStatisticsDataModel.test_model_main()


if __name__ == "__main__":
    main()
