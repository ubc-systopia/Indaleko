"""
This module provides query output types for interaction with LLMs.

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
from enum import Enum
import os
import sys
from textwrap import dedent

from pydantic import BaseModel, Field, ConfigDict
from typing import Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-positionfrom data_models.collection_info import CollectionInfo
# pylint: enable=wrong-import-position


class LLMTranslateQueryResponse(BaseModel):
    aql_query: str = Field(..., title='AQL Query')
    rationale: str = Field(..., title='Rationale')
    alternatives_considered: list[dict[str, str]] = Field(..., title='Alternatives Considered')
    index_warnings: list[dict[str, str]] = Field(..., title='Index Warnings')

    model_config = ConfigDict(
        json_schema_extra={
            'required': [
                'aql_query',
                'rationale',
                'alternatives_considered',
                'index_warnings'
            ]
        }
    )


class LLMIntentTypeEnum(str, Enum):
    '''Enumeration of the different types of intents.'''
    SEARCH = 'search'
    FILTER = 'filter'
    SORT = 'sort'
    AGGREGATE = 'aggregate'
    COUNT = 'count'
    UNKNOWN = 'unknown'


class LLMIntentQueryResponse(BaseModel):
    intent: str = Field(
        ...,
        title='Intent',
        description=dedent(
            "The intent of the user query, with the following possible values:\n"
            f"{', '.join([intent.value for intent in LLMIntentTypeEnum])}"
        )
    )

    confidence: float = Field(
        ...,
        title='Confidence',
        description="The confidence score of the intent classification, ranging from 0 to 1"
    )

    rationale: str = Field(
        ...,
        title='Rationale',
        description='The rationale for why you chose this intent.'
    )

    alternatives_considered: list[dict[str, str]] = Field(
        ...,
        title='Alternatives Considered',
        description=dedent(
            'The alternatives considered for the intent classification (if any).'
            'This can include other intents that were considered, or other factors'
            'that were taken into account.'
            'If none were considered, this should be an empty list.'
        )
    )

    confidence: float = Field(
        ...,
        title='Confidence',
        description="The confidence score of the intent classification, ranging from 0 to 1"
    )

    suggestion: Union[str, None] = Field(
        None,
        title='Suggestion',
        description="Suggest ways to improve the intent classification process, "
        "such as by adding an additional class that might be useful, or a better prompt version.")

    model_config = ConfigDict(
        json_schema_extra={
            'required': [
                'intent',
                'rationale',
                'alternatives_considered',
                'confidence'
            ]
        }
    )


class LLMFilterConstraintQueryResponse(BaseModel):
    filter_constraints: list[dict[str, str]] = Field(..., title='Filter Constraints')
    rationale: str = Field(..., title='Rationale')
    alternatives_considered: list[dict[str, str]] = Field(..., title='Alternatives Considered')
    index_warnings: list[dict[str, str]] = Field(..., title='Index Warnings')

    class Config:
        json_schema_extra = {
            'example': {
                'filter_constraints': [
                    {
                        'field': 'name',
                        'operation': '=',
                        'value': 'Tony'
                    },
                    {
                        'field': 'creation time',
                        'operation': '>',
                        'value': '2022-01-01'
                    },
                    {
                        'field': 'creation time',
                        'operation': '<',
                        'value': '2022-01-02'
                    }
                ],
                'rationale': 'The user query indicated the directory name '
                             'must be Tony, and the creation time must be between '
                             '2022-01-01 and 2022-01-02',
                'alternatives_considered': [
                    {
                        'example': 'this is an example, so it is static and nothing else was considered'
                    }
                ],
                'index_warnings': [
                ]
            }
        }


class LLMCollectionCategoryEnum(str, Enum):
    '''Enumeration of the different types of collections.'''
    OBJECTS = 'objects'
    SEMANTIC = 'semantic'
    ACTIVITY = 'activity'


class LLMCollectionCategory(BaseModel):
    '''This labels a collection with a category.'''
    category: LLMCollectionCategoryEnum = Field(
        ...,
        title='Category',
        description=dedent(
            "The category of the collection, with the following possible values:\n"
            f"{', '.join([category.value for category in LLMCollectionCategoryEnum])}"
        )
    )

    collection: str = Field(
        ...,
        title='Collection',
        description='The name of the collection in ArangoDB.'
    )

    confidence: float = Field(
        ...,
        title='Confidence',
        description="The confidence score of the collection category classification, ranging from 0 to 1"
    )

    rationale: str = Field(
        ...,
        title='Rationale',
        description='The rationale for why you chose this collection category.'
    )

    alternatives_considered: list[dict[str, str]] = Field(
        ...,
        title='Alternatives Considered',
        description=dedent(
            'The alternatives considered for the collection category classification (if any).'
            'This can include other categories that were considered, or other factors'
            'that were taken into account.'
            'If none were considered, this should be an empty list.'
        )
    )

    suggestion: Union[str, None] = Field(
        None,
        title='Suggestion',
        description="Suggest ways to improve the collection category classification process, "
        "such as by adding an additional category that might be useful, or a better prompt version, "
        "or better descriptions within the collections.  Specificity is appreciated, as are examples.")

    class Config:

        json_schema_extra = {
            'required': [
                'category',
                'collection',
                'confidence',
                'rationale',
                'alternatives_considered'
            ],
            "example": {
                "category": "objects",
                "collection": "objects",
                "confidence": 0.95,
                "rationale": "The collection contains objects.",
                "alternatives_considered": [
                    {
                        "example": "this is an example, so it is static and nothing else was considered"
                    }
                ]
            }
        }


class LLMCollectionCategoryQueryResponse(BaseModel):
    '''Response for the collection category query.'''
    category_map: list[LLMCollectionCategory] = Field(
        ...,
        title='Category Map',
        description='This is the recommended mapping of collections to categories.'
    )

    feedback: Union[str, None] = Field(
        None,
        title='Feedback',
        description='General feedback on the collections.'
    )

    class Config:

        json_schema_extra = {
            "example": {
                "category_map": [
                    {
                        "category": "objects",
                        "collection": "objects",
                        "confidence": 0.95,
                        "rationale": "The collection contains objects.",
                        "alternatives_considered": [
                            {
                                "example": "this is an example, so it is static and nothing else was considered"
                            }
                        ]
                    }
                ],
                "feedback": "This is feedback."
            }
        }
