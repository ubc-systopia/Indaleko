"""
This module defines the general data models for ambient music collection.

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
from typing import Optional, List, Dict
from pydantic import Field, field_validator, AwareDatetime

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.data_models.ambient_data_model import (
    BaseAmbientConditionDataModel,
)

# pylint: enable=wrong-import-position


class AmbientMusicData(BaseAmbientConditionDataModel):
    """
    Base model for ambient music data collection. This model captures
    the essential elements of music playback regardless of source.
    """

    # Track information
    track_name: str = Field(..., description="Name of the currently playing track")

    artist_name: str = Field(..., description="Name of the track's primary artist")

    album_name: Optional[str] = Field(
        None, description="Name of the album (if applicable)"
    )

    # Playback state
    is_playing: bool = Field(..., description="Whether music is currently playing")

    playback_position_ms: int = Field(
        ..., description="Current playback position in milliseconds", ge=0
    )

    track_duration_ms: int = Field(
        ..., description="Total track duration in milliseconds", gt=0
    )

    volume_percent: Optional[int] = Field(
        None, description="Current volume level as percentage", ge=0, le=100
    )

    # Additional track metadata
    genre: Optional[List[str]] = Field(
        None, description="Musical genres associated with the track"
    )

    release_date: Optional[str] = Field(None, description="Release date of the track")

    is_explicit: Optional[bool] = Field(
        None, description="Whether the track contains explicit content"
    )

    # Audio features
    tempo: Optional[float] = Field(None, description="Track tempo in BPM", ge=0, le=300)

    key: Optional[int] = Field(
        None,
        description="Musical key of the track (-1 to 11, where -1 represents no key detected)",
        ge=-1,
        le=11,
    )

    @field_validator("playback_position_ms")
    @classmethod
    def validate_position(cls, value: int, values: Dict) -> int:
        """Validate playback position is within track duration"""
        if "playback_position_ms" in values.data and value > values.data['track_duration_ms']:
            raise ValueError("Playback position cannot exceed track duration")
        return value


class SpotifyAmbientData(AmbientMusicData):
    """
    Spotify-specific implementation of the ambient music data model.
    Extends the base model with Spotify-specific attributes and features.
    """

    # Spotify-specific identifiers
    track_id: str = Field(
        ..., description="Spotify track URI", pattern="^spotify:track:[a-zA-Z0-9]{22}$"
    )

    artist_id: str = Field(
        ...,
        description="Spotify artist URI",
        pattern="^spotify:artist:[a-zA-Z0-9]{22}$",
    )

    album_id: Optional[str] = Field(
        None, description="Spotify album URI", pattern="^spotify:album:[a-zA-Z0-9]{22}$"
    )

    # Spotify-specific playback information
    device_name: str = Field(..., description="Name of the Spotify playback device")

    device_type: str = Field(
        ...,
        description="Type of Spotify playback device",
        pattern="^(Computer|Smartphone|Speaker|TV|Game_Console|Automobile|Unknown)$",
    )

    shuffle_state: bool = Field(False, description="Whether shuffle mode is enabled")

    repeat_state: str = Field(
        "off", description="Current repeat mode", pattern="^(track|context|off)$"
    )

    # Spotify-specific audio features
    danceability: Optional[float] = Field(
        None, description="Spotify danceability score", ge=0.0, le=1.0
    )

    energy: Optional[float] = Field(
        None, description="Spotify energy score", ge=0.0, le=1.0
    )

    valence: Optional[float] = Field(
        None, description="Spotify valence (positiveness) score", ge=0.0, le=1.0
    )

    instrumentalness: Optional[float] = Field(
        None, description="Spotify instrumentalness score", ge=0.0, le=1.0
    )

    acousticness: Optional[float] = Field(
        None, description="Spotify acousticness score", ge=0.0, le=1.0
    )

    # Context information
    context_type: Optional[str] = Field(
        None,
        description="Type of playback context",
        pattern="^(album|artist|playlist|collection)$",
    )

    context_id: Optional[str] = Field(
        None, description="Spotify URI of the playback context"
    )

    class Config:
        """Configuration and example data for the ambient music data model"""

        json_schema_extra = {
            "example": {
                # Include base model fields
                **BaseAmbientConditionDataModel.Config.json_schema_extra["example"],
                # Add music-specific fields
                "track_name": "Bohemian Rhapsody",
                "artist_name": "Queen",
                "album_name": "A Night at the Opera",
                "is_playing": True,
                "playback_position_ms": 120000,  # 2 minutes into the song
                "track_duration_ms": 354000,  # 5:54 total length
                "volume_percent": 65,
                "genre": ["Rock", "Progressive Rock"],
                "release_date": "1975-10-31",
                "is_explicit": False,
                "tempo": 72.5,
                "key": 0,  # C major
                "source": "music_player",
            }
        }


def main():
    """This allows testing the data models"""
    print("Testing base Ambient Music Data Model:")
    AmbientMusicData.test_model_main()


if __name__ == "__main__":
    main()
