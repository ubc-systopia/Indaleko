"""Semantic attribute utilities for the ablation framework."""

from typing import Any, Dict, Optional, Union
from uuid import UUID

from ..utils.uuid_utils import generate_uuid_for_entity


def create_semantic_attribute(attribute_name: str, value: Any) -> Dict:
    """Create a semantic attribute for use in activity data.
    
    Args:
        attribute_name: The name of the attribute.
        value: The value of the attribute.
        
    Returns:
        Dict: A semantic attribute dictionary.
    """
    attribute_id = generate_uuid_for_entity("semantic_attribute", attribute_name)
    
    return {
        "Identifier": {
            "Identifier": str(attribute_id),
            "Label": attribute_name
        },
        "Value": value
    }


class SemanticAttributeRegistry:
    """Registry of common semantic attributes used in ablation testing."""
    
    # Music activity semantic attributes
    MUSIC_ARTIST = "music.artist"
    MUSIC_TRACK = "music.track"
    MUSIC_ALBUM = "music.album"
    MUSIC_GENRE = "music.genre"
    MUSIC_DURATION = "music.duration"
    MUSIC_SOURCE = "music.source"
    
    # Location activity semantic attributes
    LOCATION_NAME = "location.name"
    LOCATION_COORDINATES = "location.coordinates"
    LOCATION_TYPE = "location.type"
    LOCATION_DEVICE = "location.device"
    LOCATION_WIFI_SSID = "location.wifi_ssid"
    LOCATION_SOURCE = "location.source"
    
    # Task activity semantic attributes
    TASK_NAME = "task.name"
    TASK_APPLICATION = "task.application"
    TASK_WINDOW_TITLE = "task.window_title"
    TASK_DURATION = "task.duration"
    TASK_ACTIVE = "task.active"
    TASK_SOURCE = "task.source"
    
    # Collaboration activity semantic attributes
    COLLAB_PLATFORM = "collaboration.platform"
    COLLAB_TYPE = "collaboration.type"
    COLLAB_PARTICIPANTS = "collaboration.participants"
    COLLAB_CONTENT = "collaboration.content"
    COLLAB_DURATION = "collaboration.duration"
    COLLAB_SOURCE = "collaboration.source"
    
    # Storage activity semantic attributes
    STORAGE_PATH = "storage.path"
    STORAGE_FILE_TYPE = "storage.file_type"
    STORAGE_SIZE = "storage.size"
    STORAGE_OPERATION = "storage.operation"
    STORAGE_TIMESTAMP = "storage.timestamp"
    STORAGE_SOURCE = "storage.source"
    
    # Media activity semantic attributes
    MEDIA_TYPE = "media.type"
    MEDIA_TITLE = "media.title"
    MEDIA_PLATFORM = "media.platform"
    MEDIA_DURATION = "media.duration"
    MEDIA_CREATOR = "media.creator"
    MEDIA_SOURCE = "media.source"
    
    @staticmethod
    def create_attribute(attribute_name: str, value: Any) -> Dict:
        """Create a semantic attribute from the registry.
        
        Args:
            attribute_name: The name of the attribute from the registry.
            value: The value of the attribute.
            
        Returns:
            Dict: A semantic attribute dictionary.
        """
        return create_semantic_attribute(attribute_name, value)
