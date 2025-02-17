'''
This module defines the format of collection data for use by
the query processing system.

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
'''

import os
import sys

# from icecream import ic
from pydantic import BaseModel
from typing import Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.db_index import IndalekoCollectionIndexDataModel
# pylint: enable=wrong-import-position


class CollectionInfo(BaseModel):
    '''This class contains important information about a collection.'''
    Name: str
    Description: str
    Indices: list[IndalekoCollectionIndexDataModel]
    Schema: dict[str, Any]
    QueryGuidelines: list[str]
