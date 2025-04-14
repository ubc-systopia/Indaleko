"""
This module defines the classification model for activities in the Indaleko project.

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
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import Field, validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from activity.data_model.activity import IndalekoActivityDataModel

# pylint: enable=wrong-import-position


class IndalekoActivityClassification(IndalekoBaseModel):
    """
    Classification weights for different activity dimensions.
    
    Each activity can be classified along multiple dimensions with weights
    from 0.0 to 1.0, allowing for nuanced categorization of activities
    that may span multiple types.
    """
    ambient: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Activity serves as background or passive content"
    )
    consumption: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0,
        description="Activity involves consuming media or content"
    ) 
    productivity: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0,
        description="Activity related to work or task completion"
    )
    research: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0,
        description="Activity involves learning or information gathering"
    )
    social: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0,
        description="Activity involves social interaction or sharing"
    )
    creation: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0,
        description="Activity involves creating new content"
    )

    class Config:
        """Sample configuration data for the classification model."""
        json_schema_extra = {
            "example": {
                "ambient": 0.3,
                "consumption": 0.8,
                "productivity": 0.1,
                "research": 0.4,
                "social": 0.2,
                "creation": 0.0
            }
        }


class IndalekoMultiClassifiedActivityDataModel(IndalekoActivityDataModel):
    """
    Extended activity data model that supports multi-dimensional classification.
    
    This model enhances the base activity model with classification weights
    across multiple dimensions, allowing activities to be categorized in a 
    more nuanced way than simple single-category classification.
    """
    Classification: IndalekoActivityClassification = Field(
        default_factory=IndalekoActivityClassification,
        title="Classification",
        description="Multi-dimensional classification of this activity"
    )
    
    Duration: Optional[int] = Field(
        default=None,
        title="Duration",
        description="Duration of the activity in seconds"
    )
    
    Source: str = Field(
        ...,
        title="Source",
        description="The source system that generated this activity (e.g., 'youtube', 'spotify')"
    )
    
    ActivityType: str = Field(
        ...,
        title="ActivityType",
        description="Specific type of this activity (e.g., 'video_watch', 'music_listen')"
    )
    
    AdditionalMetadata: Dict[str, Any] = Field(
        default_factory=dict,
        title="AdditionalMetadata",
        description="Additional metadata specific to this activity type"
    )

    def get_primary_classification(self) -> str:
        """Returns the primary classification based on highest weight."""
        classifications = self.Classification.dict()
        primary = max(classifications.items(), key=lambda x: x[1])
        return primary[0]
    
    class Config:
        """Sample configuration data for the multi-classified activity model."""
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.get_json_example(),
                "Timestamp": "2024-01-01T00:00:00Z",
                "SemanticAttributes": [
                    IndalekoSemanticAttributeDataModel.get_json_example()
                ],
                "Classification": IndalekoActivityClassification.get_json_example(),
                "Duration": 300,
                "Source": "youtube",
                "ActivityType": "video_watch",
                "AdditionalMetadata": {
                    "video_id": "dQw4w9WgXcQ",
                    "title": "Sample Video Title",
                    "channel": "Sample Channel",
                    "watch_percentage": 0.85
                }
            }
        }


def main():
    """This allows testing the data model"""
    IndalekoMultiClassifiedActivityDataModel.test_model_main()


if __name__ == "__main__":
    main()