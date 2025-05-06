"""
Music Activity Generator Tool for simulating Spotify-like music listening activity.

This tool generates realistic music listening patterns with temporal consistency,
artist preferences, genre distributions, and proper integration with location data.

The tool follows the established data models from Indaleko's ambient music collectors
and produces properly formatted activity records for database integration.

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

import json
import os
import random
import string
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import faker

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.collectors.ambient.music.music_data_model import AmbientMusicData
from activity.collectors.ambient.music.spotify_data_model import SpotifyAmbientData
from activity.collectors.ambient.semantic_attributes import (
    ADP_AMBIENT_SPOTIFY_ALBUM_NAME,
    ADP_AMBIENT_SPOTIFY_ARTIST_NAME,
    ADP_AMBIENT_SPOTIFY_DEVICE_TYPE,
    ADP_AMBIENT_SPOTIFY_TRACK_DURATION,
    ADP_AMBIENT_SPOTIFY_TRACK_NAME,
)
from activity.data_model.activity import IndalekoActivityDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections


class MusicActivityGenerator:
    """
    Generator for music listening activity data that simulates realistic
    music consumption patterns with Spotify-specific details.
    """

    def __init__(self):
        """Initialize the music activity generator."""
        self.faker = faker.Faker()
        
        # Source identifier for Spotify music data
        self.source_data = {
            "Identifier": uuid.UUID("6ea66ced-5a54-4cba-a421-50d5671021cb"),
            "Version": "1.0.0",
            "Description": "Spotify Ambient Music Generator",
        }
        
        # Define genres and typical attributes
        self.music_genres = [
            "Pop", "Rock", "Hip Hop", "Electronic", "Classical", 
            "Jazz", "Country", "R&B", "Metal", "Indie", "Folk",
            "Ambient", "Reggae", "Blues", "Soul", "Funk", "Disco",
            "Techno", "House", "Trap", "Latin", "K-Pop"
        ]
        
        # Device types
        self.device_types = [
            "Computer", "Smartphone", "Speaker", "TV", 
            "Game_Console", "Automobile", "Unknown"
        ]
        
        # Repeat states
        self.repeat_states = ["track", "context", "off"]
        
        # Map semantic attributes to model field names
        self.semantic_attributes_map = {
            ADP_AMBIENT_SPOTIFY_TRACK_NAME: "track_name",
            ADP_AMBIENT_SPOTIFY_ARTIST_NAME: "artist_name",
            ADP_AMBIENT_SPOTIFY_ALBUM_NAME: "album_name",
            ADP_AMBIENT_SPOTIFY_TRACK_DURATION: "track_duration_ms",
            ADP_AMBIENT_SPOTIFY_DEVICE_TYPE: "device_type",
        }
        
        # Time patterns for music listening (hours with higher probability)
        self.listening_time_weights = {
            "weekday": {
                # Morning commute
                7: 0.6, 8: 0.7, 9: 0.5,
                # Work hours (background music)
                10: 0.3, 11: 0.3, 12: 0.4, 13: 0.4, 14: 0.3, 15: 0.3, 16: 0.4,
                # Evening commute and after work
                17: 0.8, 18: 0.9, 19: 0.8, 20: 0.7, 21: 0.6, 22: 0.4, 23: 0.2,
            },
            "weekend": {
                # Later morning starts
                9: 0.3, 10: 0.5, 11: 0.7, 12: 0.8,
                # Afternoon activities
                13: 0.7, 14: 0.6, 15: 0.6, 16: 0.7,
                # Evening entertainment
                17: 0.8, 18: 0.9, 19: 0.9, 20: 1.0, 21: 0.8, 22: 0.7, 23: 0.5,
            }
        }
        
        # Genre preferences (to create realistic user taste profiles)
        self.user_genre_preferences = self._generate_user_genre_preferences()
        
        # Artist catalog - mapping artists to their typical genres and song durations
        self.artist_catalog = self._generate_artist_catalog()
        
    def _generate_user_genre_preferences(self) -> Dict[str, float]:
        """
        Generate user genre preferences with weighted probabilities.
        Users typically have 2-4 favorite genres and occasionally listen to others.
        """
        preferences = {}
        
        # Pick 2-4 favorite genres with high weights
        favorite_genres = random.sample(self.music_genres, random.randint(2, 4))
        for genre in favorite_genres:
            preferences[genre] = random.uniform(0.7, 1.0)
            
        # Add some secondary genres with medium weights
        secondary_count = random.randint(3, 5)
        remaining_genres = [g for g in self.music_genres if g not in favorite_genres]
        secondary_genres = random.sample(remaining_genres, min(secondary_count, len(remaining_genres)))
        
        for genre in secondary_genres:
            preferences[genre] = random.uniform(0.3, 0.6)
            
        # Add all remaining genres with low weights
        for genre in self.music_genres:
            if genre not in preferences:
                preferences[genre] = random.uniform(0.05, 0.2)
                
        return preferences
    
    def _generate_artist_catalog(self, artist_count: int = 50) -> Dict[str, Dict[str, Any]]:
        """
        Generate a catalog of artists with their typical genres and song attributes.
        """
        catalog = {}
        
        for _ in range(artist_count):
            artist_name = self.faker.name()
            
            # Each artist has 1-3 primary genres
            primary_genres = random.sample(self.music_genres, random.randint(1, 3))
            
            # Generate some albums for this artist
            album_count = random.randint(2, 8)
            albums = {}
            
            for _ in range(album_count):
                album_name = self._generate_album_name()
                track_count = random.randint(8, 15)
                albums[album_name] = {
                    "release_date": self.faker.date_between(start_date="-10y", end_date="today").strftime("%Y-%m-%d"),
                    "tracks": self._generate_tracks(track_count)
                }
            
            # Each artist has their typical song duration range
            avg_duration = random.randint(180000, 300000)  # 3-5 minutes in milliseconds
            duration_variance = random.randint(30000, 60000)  # 30s-1m variance
            
            catalog[artist_name] = {
                "genres": primary_genres,
                "albums": albums,
                "avg_duration": avg_duration,
                "duration_variance": duration_variance,
                # Create Spotify artist ID
                "artist_id": f"spotify:artist:{''.join(random.choices(string.ascii_lowercase + string.digits, k=22))}"
            }
            
        return catalog
    
    def _generate_album_name(self) -> str:
        """Generate a plausible album name."""
        patterns = [
            lambda: self.faker.word().title(),
            lambda: f"The {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} of {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} {self.faker.word().title()} {self.faker.word().title()}",
            lambda: f"The {self.faker.word().title()} of {self.faker.word().title()}",
        ]
        return random.choice(patterns)()
    
    def _generate_tracks(self, count: int) -> Dict[str, Dict[str, Any]]:
        """Generate track names and details for an album."""
        tracks = {}
        for _ in range(count):
            track_name = self._generate_track_name()
            tracks[track_name] = {
                "track_id": f"spotify:track:{''.join(random.choices(string.ascii_lowercase + string.digits, k=22))}"
            }
        return tracks
    
    def _generate_track_name(self) -> str:
        """Generate a plausible track name."""
        patterns = [
            lambda: self.faker.word().title(),
            lambda: f"The {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} of {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} in the {self.faker.word().title()}",
            lambda: f"{self.faker.word().title()} {self.faker.word().title()} {self.faker.word().title()}",
        ]
        return random.choice(patterns)()
    
    def _create_spotify_id(self, prefix: str) -> str:
        """Generate a Spotify ID with the correct format."""
        return f"spotify:{prefix}:{''.join(random.choices(string.ascii_lowercase + string.digits, k=22))}"
    
    def _generate_listening_sessions(
        self, 
        start_date: datetime,
        end_date: datetime,
        location_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate listening sessions with temporal patterns based on time of day and day of week.
        
        If location_data is provided, correlate music listening with location context.
        """
        sessions = []
        current_date = start_date
        
        # Map location types to device preferences
        location_device_map = {
            "home": ["Speaker", "Computer", "Smartphone", "TV"],
            "work": ["Computer", "Smartphone"],
            "commute": ["Smartphone", "Automobile"],
            "gym": ["Smartphone"],
            "coffee_shop": ["Smartphone"],
            "restaurant": ["Smartphone"],
            "shopping": ["Smartphone"],
            "outdoors": ["Smartphone"],
            "unknown": ["Smartphone"]
        }
        
        while current_date < end_date:
            # Determine if it's a weekday or weekend
            is_weekend = current_date.weekday() >= 5
            pattern_key = "weekend" if is_weekend else "weekday"
            time_weights = self.listening_time_weights[pattern_key]
            
            # For each hour of the day
            for hour in range(24):
                # Skip hours not in our probability map
                if hour not in time_weights:
                    continue
                    
                # Determine if user listens during this hour based on probability
                if random.random() <= time_weights.get(hour, 0):
                    # Determine number of tracks in this session (1-8)
                    track_count = random.randint(1, 8)
                    session_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
                    
                    # Find user's location at this time if available
                    current_location = None
                    location_type = "unknown"
                    if location_data:
                        for loc in location_data:
                            loc_time = datetime.fromisoformat(loc["timestamp"])
                            # Find closest location data point within 1 hour
                            if abs((session_time - loc_time).total_seconds()) < 3600:
                                current_location = loc
                                location_type = loc.get("location_type", "unknown")
                                break
                    
                    # Choose device based on location
                    if location_type in location_device_map:
                        device_type = random.choice(location_device_map[location_type])
                    else:
                        device_type = random.choice(self.device_types)
                    
                    # Generate sequential tracks for this session
                    session_tracks = []
                    
                    # Choose an artist for this session (often listen to same artist)
                    # bias toward favorite genres based on time of day
                    if hour < 10:  # Morning
                        # Morning tends to be energetic music
                        preferred_genres = ["Pop", "Electronic", "Rock"]
                    elif hour < 17:  # Work day
                        # Work day tends to be focus music
                        preferred_genres = ["Classical", "Ambient", "Jazz", "Electronic"]
                    else:  # Evening
                        # Evening varies more
                        preferred_genres = list(self.music_genres)
                    
                    # Filter artists by preferred genres for this time period
                    matching_artists = []
                    for artist, details in self.artist_catalog.items():
                        if any(genre in preferred_genres for genre in details["genres"]):
                            matching_artists.append(artist)
                    
                    # If no matches, use any artist
                    if not matching_artists:
                        matching_artists = list(self.artist_catalog.keys())
                    
                    # Choose an artist
                    session_artist = random.choice(matching_artists)
                    artist_details = self.artist_catalog[session_artist]
                    
                    # Choose an album for this session (80% chance)
                    if random.random() < 0.8 and artist_details["albums"]:
                        session_album = random.choice(list(artist_details["albums"].keys()))
                        album_tracks = list(artist_details["albums"][session_album]["tracks"].keys())
                        
                        # Choose random tracks from this album
                        track_sample = random.sample(
                            album_tracks, 
                            min(track_count, len(album_tracks))
                        )
                        
                        current_time = session_time
                        for track_name in track_sample:
                            track_id = artist_details["albums"][session_album]["tracks"][track_name]["track_id"]
                            
                            # Generate duration based on artist's typical duration
                            duration = max(
                                60000,  # Minimum 1 minute
                                random.randint(
                                    artist_details["avg_duration"] - artist_details["duration_variance"],
                                    artist_details["avg_duration"] + artist_details["duration_variance"]
                                )
                            )
                            
                            # Generate playback position (usually listen to most of song)
                            if random.random() < 0.8:  # 80% chance of listening to most of song
                                playback_position = int(duration * random.uniform(0.7, 1.0))
                            else:  # 20% chance of partial listen
                                playback_position = int(duration * random.uniform(0.1, 0.6))
                            
                            # Create track data
                            track_data = {
                                "timestamp": current_time.isoformat(),
                                "track_name": track_name,
                                "artist_name": session_artist,
                                "album_name": session_album,
                                "track_id": track_id,
                                "artist_id": artist_details["artist_id"],
                                "album_id": f"spotify:album:{''.join(random.choices(string.ascii_lowercase + string.digits, k=22))}",
                                "is_playing": True,
                                "playback_position_ms": playback_position,
                                "track_duration_ms": duration,
                                "device_type": device_type,
                                "device_name": f"My {device_type}",
                                "shuffle_state": random.random() < 0.3,  # 30% chance shuffle is on
                                "repeat_state": random.choices(
                                    self.repeat_states, 
                                    weights=[0.1, 0.2, 0.7]  # Mostly off
                                )[0],
                                "volume_percent": random.randint(40, 100),
                                "genres": artist_details["genres"],
                                "location": current_location,
                                # Add audio features
                                "danceability": round(random.uniform(0, 1.0), 3),
                                "energy": round(random.uniform(0, 1.0), 3),
                                "valence": round(random.uniform(0, 1.0), 3),
                                "instrumentalness": round(random.uniform(0, 1.0), 3),
                                "acousticness": round(random.uniform(0, 1.0), 3),
                            }
                            
                            session_tracks.append(track_data)
                            
                            # Advance time by the playback duration
                            advance_seconds = playback_position / 1000
                            current_time += timedelta(seconds=advance_seconds)
                    
                    else:
                        # Mixed tracks from different artists/albums
                        current_time = session_time
                        for _ in range(track_count):
                            # Sometimes switch artists between tracks
                            if random.random() < 0.3:  # 30% chance to switch artist
                                session_artist = random.choice(list(self.artist_catalog.keys()))
                                artist_details = self.artist_catalog[session_artist]
                            
                            if artist_details["albums"]:
                                session_album = random.choice(list(artist_details["albums"].keys()))
                                album_tracks = list(artist_details["albums"][session_album]["tracks"].keys())
                                track_name = random.choice(album_tracks)
                                track_id = artist_details["albums"][session_album]["tracks"][track_name]["track_id"]
                            else:
                                session_album = "Single"
                                track_name = self._generate_track_name()
                                track_id = self._create_spotify_id("track")
                            
                            # Generate duration based on artist's typical duration
                            duration = max(
                                60000,  # Minimum 1 minute
                                random.randint(
                                    artist_details["avg_duration"] - artist_details["duration_variance"],
                                    artist_details["avg_duration"] + artist_details["duration_variance"]
                                )
                            )
                            
                            # Generate playback position (usually listen to most of song)
                            if random.random() < 0.8:  # 80% chance of listening to most of song
                                playback_position = int(duration * random.uniform(0.7, 1.0))
                            else:  # 20% chance of partial listen
                                playback_position = int(duration * random.uniform(0.1, 0.6))
                            
                            # Create track data
                            track_data = {
                                "timestamp": current_time.isoformat(),
                                "track_name": track_name,
                                "artist_name": session_artist,
                                "album_name": session_album,
                                "track_id": track_id,
                                "artist_id": artist_details["artist_id"],
                                "album_id": f"spotify:album:{''.join(random.choices(string.ascii_lowercase + string.digits, k=22))}",
                                "is_playing": True,
                                "playback_position_ms": playback_position,
                                "track_duration_ms": duration,
                                "device_type": device_type,
                                "device_name": f"My {device_type}",
                                "shuffle_state": random.random() < 0.3,  # 30% chance shuffle is on
                                "repeat_state": random.choices(
                                    self.repeat_states, 
                                    weights=[0.1, 0.2, 0.7]  # Mostly off
                                )[0],
                                "volume_percent": random.randint(40, 100),
                                "genres": artist_details["genres"],
                                "location": current_location,
                                # Add audio features
                                "danceability": round(random.uniform(0, 1.0), 3),
                                "energy": round(random.uniform(0, 1.0), 3),
                                "valence": round(random.uniform(0, 1.0), 3),
                                "instrumentalness": round(random.uniform(0, 1.0), 3),
                                "acousticness": round(random.uniform(0, 1.0), 3),
                            }
                            
                            session_tracks.append(track_data)
                            
                            # Advance time by the playback duration
                            advance_seconds = playback_position / 1000
                            current_time += timedelta(seconds=advance_seconds)
                    
                    # Add all tracks from this session
                    sessions.extend(session_tracks)
            
            # Move to next day
            current_date += timedelta(days=1)
            
        return sessions
    
    def create_music_activity_data(
        self, 
        session_data: Dict[str, Any], 
        location_context: Optional[Dict[str, Any]] = None
    ) -> SpotifyAmbientData:
        """
        Create a structured SpotifyAmbientData object from session data.
        
        Args:
            session_data: Dictionary containing track/session information
            location_context: Optional location data to associate with this music activity
            
        Returns:
            SpotifyAmbientData object ready for database insertion
        """
        # Create base record
        timestamp = datetime.fromisoformat(session_data["timestamp"])
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            
        record = IndalekoRecordDataModel(
            SourceIdentifier=IndalekoSourceIdentifierDataModel(
                Identifier=self.source_data["Identifier"],
                Version=self.source_data["Version"],
                Description=self.source_data["Description"]
            ),
            Timestamp=timestamp,
            Data="",  # Will be filled by encoder
            Attributes={}
        )
        
        # Create semantic attributes
        semantic_attributes = []
        for attr_id, field_name in self.semantic_attributes_map.items():
            if field_name in session_data:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=attr_id,
                            Version="1",
                            Description=field_name
                        ),
                        Data=session_data[field_name]
                    )
                )
                
        # Create the music data model
        spotify_data = SpotifyAmbientData(
            # Base fields
            Record=record,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes,
            source="spotify",
            
            # Music-specific fields
            track_name=session_data["track_name"],
            artist_name=session_data["artist_name"],
            album_name=session_data["album_name"],
            is_playing=session_data["is_playing"],
            playback_position_ms=session_data["playback_position_ms"],
            track_duration_ms=session_data["track_duration_ms"],
            volume_percent=session_data["volume_percent"],
            genre=session_data["genres"],
            
            # Spotify-specific fields
            track_id=session_data["track_id"],
            artist_id=session_data["artist_id"],
            album_id=session_data["album_id"],
            device_name=session_data["device_name"],
            device_type=session_data["device_type"],
            shuffle_state=session_data["shuffle_state"],
            repeat_state=session_data["repeat_state"],
            danceability=session_data["danceability"],
            energy=session_data["energy"],
            valence=session_data["valence"],
            instrumentalness=session_data["instrumentalness"],
            acousticness=session_data["acousticness"],
        )
        
        return spotify_data
    
    def prepare_for_database(self, spotify_data: SpotifyAmbientData) -> Dict[str, Any]:
        """
        Convert a SpotifyAmbientData object to a dictionary ready for database insertion.
        
        Args:
            spotify_data: The SpotifyAmbientData object to convert
            
        Returns:
            Dictionary formatted for ArangoDB insertion
        """
        # Create the core activity data model
        activity_data = IndalekoActivityDataModel(
            Record=spotify_data.Record,
            Timestamp=spotify_data.Timestamp,
            SemanticAttributes=spotify_data.SemanticAttributes
        )
        
        # Convert to dictionary for database insertion
        return json.loads(activity_data.model_dump_json(exclude_none=True, exclude_unset=True))
    
    def generate_music_activity(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        location_data: Optional[List[Dict[str, Any]]] = None,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate music activity data for a time period.
        
        Args:
            start_date: Start date for the activity (defaults to 7 days ago)
            end_date: End date for the activity (defaults to now)
            location_data: Optional location data to correlate with music activity
            count: If provided, generate exactly this many activities
            
        Returns:
            List of formatted activity data ready for database insertion
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
            
        # Generate listening sessions with temporal patterns
        all_sessions = self._generate_listening_sessions(
            start_date=start_date,
            end_date=end_date,
            location_data=location_data
        )
        
        # If count specified, sample that many sessions
        if count is not None and count < len(all_sessions):
            all_sessions = random.sample(all_sessions, count)
        
        # Convert to SpotifyAmbientData objects and prepare for database
        db_records = []
        for session in all_sessions:
            spotify_data = self.create_music_activity_data(
                session_data=session,
                location_context=session.get("location")
            )
            db_record = self.prepare_for_database(spotify_data)
            db_records.append(db_record)
            
        return db_records
    
    def insert_into_database(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert generated music activity data into the ArangoDB database.
        
        Args:
            records: List of formatted activity records
            
        Returns:
            Number of records successfully inserted
        """
        try:
            # Get database connection
            db_config = IndalekoDBConfig()
            db = db_config.db
            
            # Get or create the music activity collection
            collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
            collection = db.collection(collection_name)
            
            # Insert records in batches
            batch_size = 100
            successful_inserts = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                result = collection.insert_many(batch)
                successful_inserts += len(result)
                
            return successful_inserts
            
        except Exception as e:
            print(f"Error inserting music activity data: {str(e)}")
            return 0


class MusicActivityGeneratorTool:
    """Tool for generating synthetic music activity data."""
    
    def __init__(self):
        """Initialize the music activity generator tool."""
        self.generator = MusicActivityGenerator()
    
    def generate_music_activities(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        count: Optional[int] = None,
        location_data: Optional[List[Dict[str, Any]]] = None,
        insert_to_db: bool = False
    ) -> Dict[str, Any]:
        """
        Generate synthetic music activity data with temporal patterns.
        
        Args:
            start_date: Start date for the activity (defaults to 7 days ago)
            end_date: End date for the activity (defaults to now)
            count: If provided, generate exactly this many activities
            location_data: Optional location data to correlate with music activity
            insert_to_db: Whether to insert the generated data into the database
            
        Returns:
            Dictionary containing generated data and summary statistics
        """
        # Generate music activity data
        records = self.generator.generate_music_activity(
            start_date=start_date,
            end_date=end_date,
            count=count,
            location_data=location_data
        )
        
        # Insert into database if requested
        db_inserts = 0
        if insert_to_db and records:
            db_inserts = self.generator.insert_into_database(records)
        
        # Compute summary statistics
        artist_counts = {}
        genre_counts = {}
        device_counts = {}
        hourly_distribution = {hour: 0 for hour in range(24)}
        
        for record in records:
            # Extract semantic attributes
            for attr in record.get("SemanticAttributes", []):
                if "artist_name" in attr.get("Identifier", {}).get("Description", ""):
                    artist = attr.get("Data", "")
                    artist_counts[artist] = artist_counts.get(artist, 0) + 1
                    
                if "device_type" in attr.get("Identifier", {}).get("Description", ""):
                    device = attr.get("Data", "")
                    device_counts[device] = device_counts.get(device, 0) + 1
            
            # Extract hour for time distribution
            timestamp = datetime.fromisoformat(record.get("Timestamp", ""))
            hour = timestamp.hour
            hourly_distribution[hour] += 1
            
        # Prepare summary statistics
        top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        device_distribution = {k: v / len(records) for k, v in device_counts.items()}
        
        return {
            "total_records": len(records),
            "db_inserts": db_inserts,
            "date_range": {
                "start": str(start_date),
                "end": str(end_date)
            },
            "top_artists": top_artists,
            "device_distribution": device_distribution,
            "hourly_distribution": hourly_distribution,
            "sample_records": records[:3] if records else []
        }


def main():
    """Test the MusicActivityGenerator directly."""
    generator_tool = MusicActivityGeneratorTool()
    
    # Generate a small batch of music activity data
    start_date = datetime.now(timezone.utc) - timedelta(days=3)
    end_date = datetime.now(timezone.utc)
    
    result = generator_tool.generate_music_activities(
        start_date=start_date,
        end_date=end_date,
        count=10,
        insert_to_db=False
    )
    
    print(f"Generated {result['total_records']} music activity records")
    print(f"Top artists: {result['top_artists']}")
    print(f"Device distribution: {result['device_distribution']}")
    
    if result['sample_records']:
        print("\nSample record:")
        sample = result['sample_records'][0]
        print(f"Timestamp: {sample.get('Timestamp')}")
        for attr in sample.get('SemanticAttributes', []):
            print(f"  {attr.get('Identifier', {}).get('Description', '')}: {attr.get('Data', '')}")


if __name__ == "__main__":
    main()