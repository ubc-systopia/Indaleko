"""
This module defines the common data model for activity data providers
in the Indaleko project.

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

from pydantic import BaseModel, Field

# from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel  # noqa: E402
from data_models.db_index import IndalekoCollectionIndexDataModel  # noqa: E402
from data_models.named_entity import NamedEntityCollection  # noqa: E402
from query.query_processing.data_models.query_output import LLMIntentTypeEnum  # noqa: E402
# pylint: enable=wrong-import-position


class QueryFilter(BaseModel):
    field: str
    operation: str  # E.g., "=", ">", "<", "IN"
    value: str


class StructuredQuery(BaseModel):
    original_query: str = Field(
        ...,
        title='Original Query',
        description='The original (natural language) query from the user'
    )

    intent: LLMIntentTypeEnum = Field(
        ...,
        title='Intent',
        description='The intent of the query'
    )  # "search", "filter", etc.

    entities: NamedEntityCollection = Field(  # Extracted entities
        ...,
        title='Entities',
        description='The mapping of named entities in the query '
        'to their values in the NER collection (if any)'
    )

    db_info: list[IndalekoCollectionMetadataDataModel] = Field(
        ...,
        title='Database Information',
        description='The metadata for the database collections, '
        'including guidelines and schema'
    )

    db_indices: dict[str, list[IndalekoCollectionIndexDataModel]] = Field(
        ...,
        title='Database Indices',
        description='The indices for the database collections.'
        'Note that this does not include the primary key index, which is always present.'
    )
