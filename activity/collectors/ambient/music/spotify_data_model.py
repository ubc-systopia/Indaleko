"""
This module defines the data models for
a Spotify-specific implementation.

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

from pydantic import Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.music.music_data_model import AmbientMusicData


# pylint: enable=wrong-import-position


class SpotifyAmbientData(AmbientMusicData):
    """
    Spotify-specific implementation of the ambient music data model.
    Extends the base model with Spotify-specific attributes and features.
    """

    # Spotify-specific identifiers
    track_id: str = Field(
        ...,
        description="Spotify track URI",
        pattern="^spotify:track:[a-zA-Z0-9]{22}$",
    )

    artist_id: str = Field(
        ...,
        description="Spotify artist URI",
        pattern="^spotify:artist:[a-zA-Z0-9]{22}$",
    )

    album_id: str | None = Field(
        None,
        description="Spotify album URI",
        pattern="^spotify:album:[a-zA-Z0-9]{22}$",
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
        "off",
        description="Current repeat mode",
        pattern="^(track|context|off)$",
    )

    # Spotify-specific audio features
    danceability: float | None = Field(
        None,
        description="Spotify danceability score",
        ge=0.0,
        le=1.0,
    )

    energy: float | None = Field(
        None,
        description="Spotify energy score",
        ge=0.0,
        le=1.0,
    )

    valence: float | None = Field(
        None,
        description="Spotify valence (positiveness) score",
        ge=0.0,
        le=1.0,
    )

    instrumentalness: float | None = Field(
        None,
        description="Spotify instrumentalness score",
        ge=0.0,
        le=1.0,
    )

    acousticness: float | None = Field(
        None,
        description="Spotify acousticness score",
        ge=0.0,
        le=1.0,
    )

    # Context information
    context_type: str | None = Field(
        None,
        description="Type of playback context",
        pattern="^(album|artist|playlist|collection)$",
    )

    context_id: str | None = Field(
        None,
        description="Spotify URI of the playback context",
    )

    class Config:
        """Configuration and example data for the Spotify ambient data model."""

        json_schema_extra = {
            "example": {
                **AmbientMusicData.Config.json_schema_extra["example"],
                "track_id": "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
                "artist_id": "spotify:artist:0OdUWJ0sBjDrqHygGUXeCF",
                "album_id": "spotify:album:2noRn2Aes5aoNVsU6iWThc",
                "device_name": "My Speaker",
                "device_type": "Speaker",
                "shuffle_state": False,
                "repeat_state": "off",
                "danceability": 0.735,
                "energy": 0.578,
                "valence": 0.624,
                "instrumentalness": 0.0902,
                "acousticness": 0.0264,
                "context_type": "playlist",
                "context_id": "spotify:playlist:37i9dQZF1DX5",
                "source": "spotify",
            },
        }


def main() -> None:
    """This allows testing the data models."""
    SpotifyAmbientData.test_model_main()


if __name__ == "__main__":
    main()
