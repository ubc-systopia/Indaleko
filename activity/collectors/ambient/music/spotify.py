"""
This module defines a utility for acquiring Spotify data.

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
from typing import Any, Dict
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.music.music_data_model import SpotifyAmbientData
from activity.collectors.ambient.base import AmbientCollector
# pylint: enable=wrong-import-position


class SpotifyMusicCollector(AmbientCollector):
    """
    This class provides a utility for acquiring Spotify data.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, **kwargs):
        """Initialize the object."""
        super().__init__(**kwargs)
        self.data = SpotifyAmbientData()
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                            client_secret=client_secret,
                                                            redirect_uri=redirect_uri,
                                                            scope="user-read-playback-state"))
        self.authenticate()

    def authenticate(self) -> None:
        """Authenticate with the Spotify API."""
        ic('Authenticating with Spotify API')
        self.sp.current_user()

    def collect_data(self) -> None:
        """
        Collect Spotify data.
        """
        ic('Collecting Spotify data')
        playback = self.sp.current_playback()
        if playback:
            raw_data = {
                "track_name": playback['item']['name'],
                "artist_name": playback['item']['artists'][0]['name'],
                "album_name": playback['item']['album']['name'],
                "is_playing": playback['is_playing'],
                "playback_position_ms": playback['progress_ms'],
                "track_duration_ms": playback['item']['duration_ms'],
                "volume_percent": playback['device']['volume_percent'],
                "track_id": playback['item']['uri'],
                "artist_id": playback['item']['artists'][0]['uri'],
                "album_id": playback['item']['album']['uri'],
                "device_name": playback['device']['name'],
                "device_type": playback['device']['type'],
                "shuffle_state": playback['shuffle_state'],
                "repeat_state": playback['repeat_state'],
                "context_type": playback['context']['type'] if playback['context'] else None,
                "context_id": playback['context']['uri'] if playback['context'] else None
            }
            self.data.process_spotify_data(raw_data)

    def process_data(self, data: Any) -> Dict[str, Any]:
        """
        Process the collected data.
        """
        ic('Processing Spotify data')
        return self.data.dict()

    def store_data(self, data: Dict[str, Any]) -> None:
        """
        Store the processed data.
        """
        ic('Storing Spotify data')
        print("Storing data:", data)

    def get_latest_db_update(self) -> Dict[str, Any]:
        """
        Get the latest data update from the database.
        """
        ic('Getting latest Spotify data update from the database')
        return {
            "track_name": "Bohemian Rhapsody",
            "artist_name": "Queen",
            "album_name": "A Night at the Opera",
            "is_playing": True,
            "playback_position_ms": 120000,
            "track_duration_ms": 354000,
            "volume_percent": 65,
            "track_id": "spotify:track:123ABC456DEF",
            "artist_id": "spotify:artist:123ABC456DEF",
            "album_id": "spotify:album:123ABC456DEF",
            "device_name": "My Computer",
            "device_type": "Computer",
            "shuffle_state": False,
            "repeat_state": "off",
            "context_type": "playlist",
            "context_id": "spotify:playlist:123ABC456DEF"
        }

    def update_data(self) -> None:
        """
        Update the data in the database.
        """
        ic('Updating Spotify data in the database')
        latest_data = self.get_latest_db_update()
        self.store_data(latest_data)


def main():
    """Main entry point for the Spotify Music Collector."""
    ic('Starting Spotify Music Collector')
    client_id = "YOUR_SPOTIFY_CLIENT_ID"
    client_secret = "YOUR_SPOTIFY_CLIENT_SECRET"
    redirect_uri = "YOUR_SPOTIFY_REDIRECT_URI"
    collector = SpotifyMusicCollector(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
    collector.collect_data()
    latest = collector.get_latest_db_update()
    ic(latest)
    ic(collector.get_description())
    ic('Finished Spotify Music Collector')


if __name__ == '__main__':
    main()
