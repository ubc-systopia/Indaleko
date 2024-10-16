'''
This module defines the data model for the checksum data collector.

Project Indaleko
Copyright (C) 2024 Tony Mason

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
'''
# standard imports
import mimetypes
import os
import sys

from uuid import UUID, uuid4
from datetime import datetime, timezone

# third-party imports
from typing import Optional, List
from pydantic import Field, field_validator, AwareDatetime


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from semantic.data_models.base_data_model import BaseSemanticDataModel
# pylint: enable=wrong-import-position

class UnstructuredDataModel(BaseSemanticDataModel):
    '''
    This class defines the data model for the unstructured data collector.
    '''
    ElementId : UUID = Field(default_factory=uuid4,
                             description="The unique identifier for the unstructured data element.")
    FileUUID : UUID = Field(..., desdription = "The UUID for the file object in the database.")
    FileType : Optional[str]  = Field(..., description = "The MIME type of the file.")
    LastModified : AwareDatetime = Field(..., description = "The last modified time for the file.")
    PageNumber : Optional[int] = Field(..., description = "The page number where the element starts.")
    Languages : List[str] = Field(..., description = "The languages detected in the element.")
    EmphasizedTextContents : Optional[List[str]] =\
          Field(...,
                description = "The emphasized text contents.")
    EphasizedTextTags : Optional[List[str]] = \
        Field(...,
              description = "Tags corresponding (e.g,. bold, italic) for emphasized text.")
    Text : str = Field(..., description = "The text content of the element.")
    Type : str = \
        Field(...,
              description = "The type of the extracted element, such as 'Title' or 'UncagegorizedText'.")
    

    @classmethod
    @field_validator('FileType')
    def validate_file_type(cls, v):
        if v is None:
            return v
        if not mimetypes.guess_extension(v):
            raise ValueError(f"Invalid MIME type: {v}")
        return v


    @classmethod
    @field_validator('LastModified')
    def validate_last_modified(cls, value : datetime):
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    
