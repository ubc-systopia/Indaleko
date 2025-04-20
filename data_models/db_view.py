"""
Indaleko Database View Data Model

This module defines the data model for ArangoDB views, particularly ArangoSearch views
for text search capabilities.

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
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.base import IndalekoBaseModel
from pydantic import Field


class IndalekoViewDefinition(IndalekoBaseModel):
    """
    Defines an ArangoDB view, particularly an ArangoSearch view for text search.
    
    ArangoSearch views provide high-performance full-text search capabilities in ArangoDB
    with features such as text analysis, ranking, and search-as-you-type functionality.
    
    Views are referenced in AQL queries using the FOR keyword similar to collections.
    """
    
    name: str = Field(..., description="Name of the view")
    type: str = Field("arangosearch", description="Type of view (arangosearch is the primary type)")
    collections: List[str] = Field(..., description="Collections to include in the view")
    fields: Union[Dict[str, List[str]], Dict[str, Dict[str, List[str]]]] = Field(
        ..., 
        description="Fields to include in the view by collection. Can be Dict[str, List[str]] or Dict[str, Dict[str, List[str]]]"
    )
    analyzers: Optional[List[str]] = Field(default=["text_en"], 
                             description="Default text analyzers to use (when not specified per field)")
    include_all_fields: bool = Field(default=False, description="Whether to include all fields in the view")
    primary_sort: Optional[List[Dict[str, str]]] = Field(default=None, description="Primary sort fields")
    stored_values: Optional[List[str]] = Field(default=None, description="Fields to store in the view for retrieval")
    view_id: Optional[str] = Field(default=None, description="ID of the created view")

    def get_creation_properties(self) -> Dict[str, Any]:
        """
        Generate the properties dictionary for view creation.
        
        Returns:
            Dict[str, Any]: The properties object for ArangoDB view creation.
        """
        # Build view links
        links = {}
        for collection in self.collections:
            links[collection] = {
                "analyzers": self.analyzers,
                "includeAllFields": self.include_all_fields,
                "fields": {}
            }
            
            # Add fields for this collection
            if collection in self.fields:
                collection_fields = self.fields[collection]
                
                # Check if we have field-specific analyzers
                if isinstance(collection_fields, dict):
                    # Format: {"field1": ["analyzer1", "analyzer2"], "field2": ["analyzer3"]}
                    for field, field_analyzers in collection_fields.items():
                        links[collection]["fields"][field] = {"analyzers": field_analyzers}
                else:
                    # Old format: list of fields using default analyzers
                    for field in collection_fields:
                        links[collection]["fields"][field] = {"analyzers": self.analyzers}
        
        # Build the properties object
        properties = {
            "links": links
        }
        
        # Add primary sort if specified
        if self.primary_sort:
            properties["primarySort"] = self.primary_sort
            
        # Add stored values if specified
        if self.stored_values:
            properties["storedValues"] = self.stored_values
            
        return properties

    class Config:
        """Configuration for IndalekoViewDefinition model."""
        json_schema_extra = {
            "example": {
                "name": "ObjectTextSearch",
                "type": "arangosearch",
                "collections": ["Objects"],
                "fields": {
                    "Objects": ["Label", "Record.Attributes.URI", "description"]
                },
                "analyzers": ["text_en"],
                "include_all_fields": False,
                "primary_sort": None,
                "stored_values": ["_key", "Label"],
                "view_id": None
            }
        }