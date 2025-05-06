#!/usr/bin/env python3
"""
Activity metadata generator.

This module provides implementation for generating realistic activity
metadata records (location, music, temperature, etc.) and storing them directly
in the database.
"""

import hashlib
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pytz
from data_models.base import IndalekoBaseModel
from data_models.location_data_model import LocationDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from pydantic import Field

from tools.data_generator_enhanced.generators.base import ActivityMetadataGenerator, BaseGenerator
from tools.data_generator_enhanced.utils.statistical import Distribution


class ActivityRecord(IndalekoBaseModel):
    """Activity record model for activity collections."""
    
    # Required fields
    Object: str  # _key of the storage object
    Record: Dict[str, Any]  # Record data from IndalekoRecordDataModel
    Timestamp: float
    SemanticAttributes: List[Dict[str, Any]]


class LocationActivityRecord(ActivityRecord):
    """Location activity record model."""
    
    # Location-specific fields
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    source: str = "GPS"
    
    # Optional metadata
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_name: Optional[str] = None
    timezone: Optional[str] = None


class MusicActivityRecord(ActivityRecord):
    """Music activity record model."""
    
    # Music-specific fields
    artist: str
    track: str
    album: Optional[str] = None
    genre: Optional[str] = None
    duration: Optional[float] = None  # in seconds
    played_at: float  # timestamp
    service: str = "Spotify"


class TempActivityRecord(ActivityRecord):
    """Temperature activity record model."""
    
    # Temperature-specific fields
    temperature: float  # in Celsius
    humidity: Optional[float] = None
    device: str = "SmartThermostat"
    room: Optional[str] = None
    setting: Optional[str] = None  # e.g., "Heat", "Cool", "Auto"


class ActivityMetadataGeneratorImpl(ActivityMetadataGenerator):
    """Generator for activity metadata records with direct database integration."""
    
    def __init__(self, config: Dict[str, Any], db_config: Optional[IndalekoDBConfig] = None, seed: Optional[int] = None):
        """Initialize the activity metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            db_config: Database configuration for direct insertion
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Initialize database connection
        self.db_config = db_config or IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config["database"]["database"])
        
        # Make sure the activity data collections exist
        self._ensure_collections_exist()
        
        # Initialize location datasets
        self.cities = [
            {"name": "New York", "lat": 40.7128, "lon": -74.0060, "country": "United States", "code": "US", "region": "NY"},
            {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "country": "United States", "code": "US", "region": "CA"},
            {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "country": "United States", "code": "US", "region": "IL"},
            {"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "United Kingdom", "code": "GB", "region": "England"},
            {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "France", "code": "FR", "region": "Île-de-France"},
            {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "country": "Japan", "code": "JP", "region": "Tokyo"},
            {"name": "Sydney", "lat": -33.8688, "lon": 151.2093, "country": "Australia", "code": "AU", "region": "NSW"},
            {"name": "Berlin", "lat": 52.5200, "lon": 13.4050, "country": "Germany", "code": "DE", "region": "Berlin"},
            {"name": "Toronto", "lat": 43.6532, "lon": -79.3832, "country": "Canada", "code": "CA", "region": "Ontario"},
            {"name": "Singapore", "lat": 1.3521, "lon": 103.8198, "country": "Singapore", "code": "SG", "region": "Singapore"}
        ]
        
        # Initialize music datasets
        self.artists = [
            "The Beatles", "Queen", "Pink Floyd", "Led Zeppelin", "AC/DC", 
            "Taylor Swift", "Ed Sheeran", "Beyoncé", "Drake", "Adele",
            "Kendrick Lamar", "Billie Eilish", "BTS", "The Weeknd", "Dua Lipa"
        ]
        
        self.genres = [
            "Rock", "Pop", "Hip Hop", "R&B", "Country", "Electronic", "Jazz", 
            "Classical", "Metal", "Folk", "Reggae", "Soul", "Blues", "Alternative", "Indie"
        ]
        
        self.album_templates = [
            "{artist}'s Greatest Hits", 
            "The Best of {artist}", 
            "{adjective} {noun}", 
            "{adjective} {verb}", 
            "{noun} of {noun}", 
            "The {adjective} {noun}"
        ]
        
        self.adjectives = [
            "Red", "Blue", "Dark", "Light", "Bright", "Silent", "Loud",
            "Midnight", "Golden", "Eternal", "Distant", "Beautiful", "Strange",
            "Wild", "Endless", "Broken", "Hidden", "Lost", "Frozen", "Burning"
        ]
        
        self.nouns = [
            "Heart", "Dream", "Night", "Light", "Star", "Moon", "Universe",
            "World", "Road", "River", "Ocean", "Mountain", "Forest", "Sky",
            "Love", "Mind", "Soul", "Ghost", "Memory", "Shadow"
        ]
        
        self.verbs = [
            "Dancing", "Dreaming", "Falling", "Rising", "Running", "Singing",
            "Sleeping", "Waking", "Breathing", "Breaking", "Flying", "Crying",
            "Laughing", "Hoping", "Remembering", "Forgetting", "Waiting", "Living"
        ]
        
        self.track_templates = [
            "{adjective} {noun}",
            "{noun} of {noun}",
            "{verb} in the {noun}",
            "The {adjective} {noun}",
            "{adjective} {verb}",
            "Don't {verb} My {noun}",
            "{verb} the {noun}",
            "{noun} and {noun}",
            "{verb} with {noun}",
            "When the {noun} {verb}"
        ]
        
        # Initialize temperature datasets
        self.rooms = [
            "Living Room", "Bedroom", "Kitchen", "Office", "Bathroom", 
            "Dining Room", "Basement", "Attic", "Garage", "Guest Room"
        ]
        
        self.thermostat_settings = ["Heat", "Cool", "Auto", "Off", "Fan Only"]
        
        # Truth generator tracks
        self.truth_list = []
        
    def _ensure_collections_exist(self):
        """Ensure all required collections exist in the database."""
        # Check and create location activity collection
        if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_GeoActivityData_Collection):
            self.logger.info(f"Creating GeoActivityData collection")
            self.db_config.db.create_collection(IndalekoDBCollections.Indaleko_GeoActivityData_Collection)
        
        # Check and create music activity collection
        if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_MusicActivityData_Collection):
            self.logger.info(f"Creating MusicActivityData collection")
            self.db_config.db.create_collection(IndalekoDBCollections.Indaleko_MusicActivityData_Collection)
        
        # Check and create temperature activity collection
        if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_TempActivityData_Collection):
            self.logger.info(f"Creating TempActivityData collection")
            self.db_config.db.create_collection(IndalekoDBCollections.Indaleko_TempActivityData_Collection)
        
        # Get collections
        self.geo_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_GeoActivityData_Collection)
        self.music_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_MusicActivityData_Collection)
        self.temp_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_TempActivityData_Collection)
    
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate the specified number of activity metadata records.
        
        Args:
            count: Number of records to generate
            
        Returns:
            List of generated activity metadata records
        """
        # First, we need to fetch storage records to generate activity metadata for
        storage_records = self._fetch_storage_records(count)
        
        if not storage_records:
            self.logger.warning("No storage records found in database. Cannot generate activity metadata.")
            return []
        
        # Generate activity metadata for the storage records
        activity_records = self._generate_activity_metadata(storage_records)
        
        # Insert records into the database
        self._insert_records(activity_records)
        
        return activity_records
    
    def generate_for_storage(self, storage_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate activity metadata for the given storage metadata.
        
        Args:
            storage_metadata: Storage metadata records
            
        Returns:
            List of generated activity metadata records
        """
        # Generate activity metadata for the storage records
        activity_records = self._generate_activity_metadata(storage_metadata)
        
        # Insert records into the database
        self._insert_records(activity_records)
        
        return activity_records
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth records that match specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        # Get storage records that match the criteria
        storage_keys = criteria.get("storage_keys", [])
        
        if not storage_keys:
            # Fetch storage records that match criteria
            query_criteria = criteria.get("storage_criteria", {})
            storage_records = self._fetch_specific_storage_records(count, query_criteria)
            storage_keys = [r.get("_key") for r in storage_records]
        
        if not storage_keys:
            self.logger.warning("No matching storage records found. Cannot generate truth records.")
            return []
        
        # Generate activity metadata with specific properties
        activity_criteria = criteria.get("activity_criteria", {})
        activity_type = activity_criteria.get("type", "location")
        
        # Ensure we only generate as many as requested
        storage_keys = storage_keys[:count]
        
        # Generate metadata for each storage record
        truth_records = []
        
        for storage_key in storage_keys:
            if activity_type == "location":
                record = self._generate_specific_location_metadata(storage_key, activity_criteria)
            elif activity_type == "music":
                record = self._generate_specific_music_metadata(storage_key, activity_criteria)
            elif activity_type == "temperature":
                record = self._generate_specific_temperature_metadata(storage_key, activity_criteria)
            else:
                self.logger.warning(f"Unsupported activity type: {activity_type}")
                record = None
                
            if record:
                truth_records.append(record)
                # Store the key for later evaluation
                self.truth_list.append(record.get("_key"))
        
        # Insert records into the database
        self._insert_records(truth_records)
        
        return truth_records
    
    def _fetch_storage_records(self, count: int) -> List[Dict[str, Any]]:
        """Fetch storage records from the database.
        
        Args:
            count: Maximum number of records to fetch
            
        Returns:
            List of storage records
        """
        # Query to get non-directory objects
        query = f"""
        FOR doc IN @@collection
        FILTER doc.IsDirectory == false || doc.IsDirectory == null
        SORT RAND()
        LIMIT {count}
        RETURN doc
        """
        
        # Prepare bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection
        }
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            records = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(records)} storage records from database")
            return records
        except Exception as e:
            self.logger.error(f"Error fetching storage records: {e}")
            # Fail fast - no point continuing if we can't get storage records
            raise
    
    def _fetch_specific_storage_records(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch storage records that match specific criteria.
        
        Args:
            count: Maximum number of records to fetch
            criteria: Criteria to filter records by
            
        Returns:
            List of storage records
        """
        # Build filter conditions based on criteria
        filter_conditions = []
        
        # Always exclude directories
        filter_conditions.append("doc.IsDirectory == false")
        
        # Add filters for file extensions
        if "file_extension" in criteria:
            extensions = criteria["file_extension"]
            if isinstance(extensions, str):
                extensions = [extensions]
            
            extension_conditions = []
            for ext in extensions:
                # Ensure extension starts with a dot
                if not ext.startswith("."):
                    ext = f".{ext}"
                extension_conditions.append(f'doc.Name LIKE "%{ext}"')
            
            if extension_conditions:
                filter_conditions.append(f"({' OR '.join(extension_conditions)})")
        
        # Add filters for file size
        if "min_size" in criteria:
            filter_conditions.append(f"doc.Size >= {criteria['min_size']}")
        if "max_size" in criteria:
            filter_conditions.append(f"doc.Size <= {criteria['max_size']}")
        
        # Add filters for time range
        if "time_range" in criteria:
            time_range = criteria["time_range"]
            if "start" in time_range:
                filter_conditions.append(f"doc.ModificationTime >= {time_range['start']}")
            if "end" in time_range:
                filter_conditions.append(f"doc.ModificationTime <= {time_range['end']}")
        
        # Add filters for name pattern
        if "name_pattern" in criteria:
            pattern = criteria["name_pattern"]
            if "%" in pattern:
                # Replace % with SQL-like wildcard for AQL
                pattern = pattern.replace("%", "%")
                filter_conditions.append(f'doc.Name LIKE "{pattern}"')
            else:
                filter_conditions.append(f'doc.Name == "{pattern}"')
        
        # Combine all filters
        filter_clause = " AND ".join(filter_conditions)
        
        # Build and execute query
        query = f"""
        FOR doc IN @@collection
        FILTER {filter_clause}
        SORT RAND()
        LIMIT {count}
        RETURN doc
        """
        
        # Prepare bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection
        }
        
        self.logger.debug(f"Storage query: {query}")
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            records = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(records)} specific storage records from database")
            return records
        except Exception as e:
            self.logger.error(f"Error fetching specific storage records: {e}")
            # Fail fast - no point continuing if we can't get storage records
            raise
    
    def _generate_activity_metadata(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate activity metadata for storage records.
        
        Args:
            storage_records: List of storage records
            
        Returns:
            List of activity metadata records
        """
        activity_records = []
        
        # Determine distribution of activity types
        # 50% location, 30% music, 20% temperature
        for storage_record in storage_records:
            # Get the storage record key
            storage_key = storage_record.get("_key")
            
            if not storage_key:
                self.logger.warning(f"Storage record missing _key: {storage_record}")
                continue
            
            # Choose activity type based on probability
            activity_type = random.choices(
                ["location", "music", "temperature"],
                weights=[0.5, 0.3, 0.2],
                k=1
            )[0]
            
            # Generate activity metadata based on type
            if activity_type == "location":
                record = self._generate_location_metadata(storage_record)
                if record:
                    activity_records.append(record)
            elif activity_type == "music":
                record = self._generate_music_metadata(storage_record)
                if record:
                    activity_records.append(record)
            elif activity_type == "temperature":
                record = self._generate_temperature_metadata(storage_record)
                if record:
                    activity_records.append(record)
        
        return activity_records
    
    def _generate_location_metadata(self, storage_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate location metadata for a storage record.
        
        Args:
            storage_record: Storage record to generate metadata for
            
        Returns:
            Generated location metadata record or None if generation failed
        """
        storage_key = storage_record.get("_key")
        
        if not storage_key:
            self.logger.warning(f"Storage record missing _key: {storage_record}")
            return None
        
        # Check if location metadata already exists for this object
        if self._location_exists(storage_key):
            self.logger.debug(f"Location metadata already exists for {storage_key}")
            return None
        
        # Select a random city
        city = random.choice(self.cities)
        
        # Add some randomness to the location
        lat_jitter = random.uniform(-0.01, 0.01)
        lon_jitter = random.uniform(-0.01, 0.01)
        
        latitude = city["lat"] + lat_jitter
        longitude = city["lon"] + lon_jitter
        altitude = random.uniform(0, 500)
        
        # Generate a timestamp (within last 30 days)
        now = datetime.now(timezone.utc)
        timestamp = now - timedelta(days=random.uniform(0, 30))
        timestamp_float = timestamp.timestamp()
        
        # Create record data
        record_data = {
            "Version": "1.0",
            "Source": "Indaleko Data Generator",
            "Type": "LocationActivity",
            "Attributes": {
                "URI": f"indaleko:activity/location/{storage_key}",
                "Description": f"Location data for file: {storage_record.get('Name', 'unknown')}",
            }
        }
        
        # Create semantic attributes
        uuid_lat = str(uuid.uuid4())
        uuid_lon = str(uuid.uuid4())
        uuid_alt = str(uuid.uuid4())
        
        semantic_attributes = [
            {
                "Identifier": {
                    "Identifier": uuid_lat,
                    "Label": "Latitude"
                },
                "Value": latitude
            },
            {
                "Identifier": {
                    "Identifier": uuid_lon,
                    "Label": "Longitude"
                },
                "Value": longitude
            },
            {
                "Identifier": {
                    "Identifier": uuid_alt,
                    "Label": "Altitude"
                },
                "Value": altitude
            }
        ]
        
        # Create location record
        location_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "Record": record_data,
            "Timestamp": timestamp_float,
            "SemanticAttributes": semantic_attributes,
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "accuracy": random.uniform(1.0, 10.0),
            "heading": random.uniform(0, 360),
            "speed": random.uniform(0, 30),
            "source": "GPS",
            "city": city["name"],
            "country": city["country"],
            "country_code": city["code"],
            "region": city["region"],
            "region_name": city["region"],
            "timezone": self._get_timezone_for_location(latitude, longitude)
        }
        
        return location_record
    
    def _generate_music_metadata(self, storage_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate music metadata for a storage record.
        
        Args:
            storage_record: Storage record to generate metadata for
            
        Returns:
            Generated music metadata record or None if generation failed
        """
        storage_key = storage_record.get("_key")
        
        if not storage_key:
            self.logger.warning(f"Storage record missing _key: {storage_record}")
            return None
        
        # Check if music metadata already exists for this object
        if self._music_exists(storage_key):
            self.logger.debug(f"Music metadata already exists for {storage_key}")
            return None
        
        # Generate music-related data
        artist = random.choice(self.artists)
        genre = random.choice(self.genres)
        
        # Generate track and album names
        track = self._generate_track_name()
        album = self._generate_album_name(artist)
        
        # Generate a timestamp (within last 30 days)
        now = datetime.now(timezone.utc)
        timestamp = now - timedelta(days=random.uniform(0, 30))
        timestamp_float = timestamp.timestamp()
        
        # Generate duration (2-10 minutes)
        duration = random.uniform(120, 600)
        
        # Create record data
        record_data = {
            "Version": "1.0",
            "Source": "Indaleko Data Generator",
            "Type": "MusicActivity",
            "Attributes": {
                "URI": f"indaleko:activity/music/{storage_key}",
                "Description": f"Music playback data for file: {storage_record.get('Name', 'unknown')}",
            }
        }
        
        # Create semantic attributes
        uuid_artist = str(uuid.uuid4())
        uuid_track = str(uuid.uuid4())
        uuid_album = str(uuid.uuid4())
        uuid_genre = str(uuid.uuid4())
        
        semantic_attributes = [
            {
                "Identifier": {
                    "Identifier": uuid_artist,
                    "Label": "Artist"
                },
                "Value": artist
            },
            {
                "Identifier": {
                    "Identifier": uuid_track,
                    "Label": "Track"
                },
                "Value": track
            },
            {
                "Identifier": {
                    "Identifier": uuid_album,
                    "Label": "Album"
                },
                "Value": album
            },
            {
                "Identifier": {
                    "Identifier": uuid_genre,
                    "Label": "Genre"
                },
                "Value": genre
            }
        ]
        
        # Create music record
        music_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "Record": record_data,
            "Timestamp": timestamp_float,
            "SemanticAttributes": semantic_attributes,
            "artist": artist,
            "track": track,
            "album": album,
            "genre": genre,
            "duration": duration,
            "played_at": timestamp_float,
            "service": "Spotify" if random.random() < 0.7 else random.choice(["Apple Music", "YouTube Music", "Tidal"])
        }
        
        return music_record
    
    def _generate_temperature_metadata(self, storage_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate temperature metadata for a storage record.
        
        Args:
            storage_record: Storage record to generate metadata for
            
        Returns:
            Generated temperature metadata record or None if generation failed
        """
        storage_key = storage_record.get("_key")
        
        if not storage_key:
            self.logger.warning(f"Storage record missing _key: {storage_record}")
            return None
        
        # Check if temperature metadata already exists for this object
        if self._temperature_exists(storage_key):
            self.logger.debug(f"Temperature metadata already exists for {storage_key}")
            return None
        
        # Generate temperature-related data
        temperature = random.uniform(15.0, 25.0)  # Celsius
        humidity = random.uniform(30.0, 70.0)
        room = random.choice(self.rooms)
        setting = random.choice(self.thermostat_settings)
        
        # Generate a timestamp (within last 30 days)
        now = datetime.now(timezone.utc)
        timestamp = now - timedelta(days=random.uniform(0, 30))
        timestamp_float = timestamp.timestamp()
        
        # Create record data
        record_data = {
            "Version": "1.0",
            "Source": "Indaleko Data Generator",
            "Type": "TemperatureActivity",
            "Attributes": {
                "URI": f"indaleko:activity/temperature/{storage_key}",
                "Description": f"Temperature data for file: {storage_record.get('Name', 'unknown')}",
            }
        }
        
        # Create semantic attributes
        uuid_temp = str(uuid.uuid4())
        uuid_humidity = str(uuid.uuid4())
        uuid_room = str(uuid.uuid4())
        uuid_setting = str(uuid.uuid4())
        
        semantic_attributes = [
            {
                "Identifier": {
                    "Identifier": uuid_temp,
                    "Label": "Temperature"
                },
                "Value": temperature
            },
            {
                "Identifier": {
                    "Identifier": uuid_humidity,
                    "Label": "Humidity"
                },
                "Value": humidity
            },
            {
                "Identifier": {
                    "Identifier": uuid_room,
                    "Label": "Room"
                },
                "Value": room
            },
            {
                "Identifier": {
                    "Identifier": uuid_setting,
                    "Label": "Setting"
                },
                "Value": setting
            }
        ]
        
        # Create temperature record
        temp_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "Record": record_data,
            "Timestamp": timestamp_float,
            "SemanticAttributes": semantic_attributes,
            "temperature": temperature,
            "humidity": humidity,
            "device": random.choice(["Nest", "Ecobee", "Honeywell", "SmartThermostat"]),
            "room": room,
            "setting": setting
        }
        
        return temp_record
    
    def _generate_specific_location_metadata(self, storage_key: str, criteria: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate location metadata for a specific storage record with custom criteria.
        
        Args:
            storage_key: Key of the storage record
            criteria: Custom criteria for the location metadata
            
        Returns:
            Generated location metadata record or None if generation failed
        """
        # Fetch the storage record
        try:
            storage_record = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(storage_key)
            if not storage_record:
                self.logger.warning(f"Storage record {storage_key} not found")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching storage record {storage_key}: {e}")
            return None
        
        # Generate location data based on criteria
        if "city" in criteria:
            # Find matching city or use the first one as default
            city_name = criteria["city"]
            city = next((c for c in self.cities if c["name"].lower() == city_name.lower()), self.cities[0])
        else:
            city = random.choice(self.cities)
        
        # Get coordinates with slight variation
        latitude = criteria.get("latitude", city["lat"] + random.uniform(-0.01, 0.01))
        longitude = criteria.get("longitude", city["lon"] + random.uniform(-0.01, 0.01))
        altitude = criteria.get("altitude", random.uniform(0, 500))
        
        # Generate a timestamp (within last 30 days, unless specified)
        if "timestamp" in criteria:
            timestamp_float = criteria["timestamp"]
        else:
            now = datetime.now(timezone.utc)
            days_ago = criteria.get("days_ago", random.uniform(0, 30))
            timestamp = now - timedelta(days=days_ago)
            timestamp_float = timestamp.timestamp()
        
        # Create record data
        record_data = {
            "Version": "1.0",
            "Source": "Indaleko Data Generator",
            "Type": "LocationActivity",
            "Attributes": {
                "URI": f"indaleko:activity/location/{storage_key}",
                "Description": criteria.get("description", f"Location data for file: {storage_record.get('Name', 'unknown')}"),
            }
        }
        
        # Create semantic attributes
        uuid_lat = str(uuid.uuid4())
        uuid_lon = str(uuid.uuid4())
        uuid_alt = str(uuid.uuid4())
        
        semantic_attributes = [
            {
                "Identifier": {
                    "Identifier": uuid_lat,
                    "Label": "Latitude"
                },
                "Value": latitude
            },
            {
                "Identifier": {
                    "Identifier": uuid_lon,
                    "Label": "Longitude"
                },
                "Value": longitude
            },
            {
                "Identifier": {
                    "Identifier": uuid_alt,
                    "Label": "Altitude"
                },
                "Value": altitude
            }
        ]
        
        # Create location record
        location_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "Record": record_data,
            "Timestamp": timestamp_float,
            "SemanticAttributes": semantic_attributes,
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "accuracy": criteria.get("accuracy", random.uniform(1.0, 10.0)),
            "heading": criteria.get("heading", random.uniform(0, 360)),
            "speed": criteria.get("speed", random.uniform(0, 30)),
            "source": criteria.get("source", "GPS"),
            "city": city["name"],
            "country": city["country"],
            "country_code": city["code"],
            "region": city["region"],
            "region_name": city["region"],
            "timezone": criteria.get("timezone", self._get_timezone_for_location(latitude, longitude))
        }
        
        return location_record
    
    def _generate_specific_music_metadata(self, storage_key: str, criteria: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate music metadata for a specific storage record with custom criteria.
        
        Args:
            storage_key: Key of the storage record
            criteria: Custom criteria for the music metadata
            
        Returns:
            Generated music metadata record or None if generation failed
        """
        # Fetch the storage record
        try:
            storage_record = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(storage_key)
            if not storage_record:
                self.logger.warning(f"Storage record {storage_key} not found")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching storage record {storage_key}: {e}")
            return None
        
        # Generate music-related data based on criteria
        artist = criteria.get("artist", random.choice(self.artists))
        genre = criteria.get("genre", random.choice(self.genres))
        track = criteria.get("track", self._generate_track_name())
        album = criteria.get("album", self._generate_album_name(artist))
        
        # Generate a timestamp (within last 30 days, unless specified)
        if "timestamp" in criteria:
            timestamp_float = criteria["timestamp"]
        else:
            now = datetime.now(timezone.utc)
            days_ago = criteria.get("days_ago", random.uniform(0, 30))
            timestamp = now - timedelta(days=days_ago)
            timestamp_float = timestamp.timestamp()
        
        # Generate duration (2-10 minutes, unless specified)
        duration = criteria.get("duration", random.uniform(120, 600))
        
        # Create record data
        record_data = {
            "Version": "1.0",
            "Source": "Indaleko Data Generator",
            "Type": "MusicActivity",
            "Attributes": {
                "URI": f"indaleko:activity/music/{storage_key}",
                "Description": criteria.get("description", f"Music playback data for file: {storage_record.get('Name', 'unknown')}"),
            }
        }
        
        # Create semantic attributes
        uuid_artist = str(uuid.uuid4())
        uuid_track = str(uuid.uuid4())
        uuid_album = str(uuid.uuid4())
        uuid_genre = str(uuid.uuid4())
        
        semantic_attributes = [
            {
                "Identifier": {
                    "Identifier": uuid_artist,
                    "Label": "Artist"
                },
                "Value": artist
            },
            {
                "Identifier": {
                    "Identifier": uuid_track,
                    "Label": "Track"
                },
                "Value": track
            },
            {
                "Identifier": {
                    "Identifier": uuid_album,
                    "Label": "Album"
                },
                "Value": album
            },
            {
                "Identifier": {
                    "Identifier": uuid_genre,
                    "Label": "Genre"
                },
                "Value": genre
            }
        ]
        
        # Create music record
        music_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "Record": record_data,
            "Timestamp": timestamp_float,
            "SemanticAttributes": semantic_attributes,
            "artist": artist,
            "track": track,
            "album": album,
            "genre": genre,
            "duration": duration,
            "played_at": timestamp_float,
            "service": criteria.get("service", "Spotify" if random.random() < 0.7 else random.choice(["Apple Music", "YouTube Music", "Tidal"]))
        }
        
        return music_record
    
    def _generate_specific_temperature_metadata(self, storage_key: str, criteria: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate temperature metadata for a specific storage record with custom criteria.
        
        Args:
            storage_key: Key of the storage record
            criteria: Custom criteria for the temperature metadata
            
        Returns:
            Generated temperature metadata record or None if generation failed
        """
        # Fetch the storage record
        try:
            storage_record = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(storage_key)
            if not storage_record:
                self.logger.warning(f"Storage record {storage_key} not found")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching storage record {storage_key}: {e}")
            return None
        
        # Generate temperature-related data based on criteria
        temperature = criteria.get("temperature", random.uniform(15.0, 25.0))  # Celsius
        humidity = criteria.get("humidity", random.uniform(30.0, 70.0))
        room = criteria.get("room", random.choice(self.rooms))
        setting = criteria.get("setting", random.choice(self.thermostat_settings))
        
        # Generate a timestamp (within last 30 days, unless specified)
        if "timestamp" in criteria:
            timestamp_float = criteria["timestamp"]
        else:
            now = datetime.now(timezone.utc)
            days_ago = criteria.get("days_ago", random.uniform(0, 30))
            timestamp = now - timedelta(days=days_ago)
            timestamp_float = timestamp.timestamp()
        
        # Create record data
        record_data = {
            "Version": "1.0",
            "Source": "Indaleko Data Generator",
            "Type": "TemperatureActivity",
            "Attributes": {
                "URI": f"indaleko:activity/temperature/{storage_key}",
                "Description": criteria.get("description", f"Temperature data for file: {storage_record.get('Name', 'unknown')}"),
            }
        }
        
        # Create semantic attributes
        uuid_temp = str(uuid.uuid4())
        uuid_humidity = str(uuid.uuid4())
        uuid_room = str(uuid.uuid4())
        uuid_setting = str(uuid.uuid4())
        
        semantic_attributes = [
            {
                "Identifier": {
                    "Identifier": uuid_temp,
                    "Label": "Temperature"
                },
                "Value": temperature
            },
            {
                "Identifier": {
                    "Identifier": uuid_humidity,
                    "Label": "Humidity"
                },
                "Value": humidity
            },
            {
                "Identifier": {
                    "Identifier": uuid_room,
                    "Label": "Room"
                },
                "Value": room
            },
            {
                "Identifier": {
                    "Identifier": uuid_setting,
                    "Label": "Setting"
                },
                "Value": setting
            }
        ]
        
        # Create temperature record
        temp_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "Record": record_data,
            "Timestamp": timestamp_float,
            "SemanticAttributes": semantic_attributes,
            "temperature": temperature,
            "humidity": humidity,
            "device": criteria.get("device", random.choice(["Nest", "Ecobee", "Honeywell", "SmartThermostat"])),
            "room": room,
            "setting": setting
        }
        
        return temp_record
    
    def _location_exists(self, storage_key: str) -> bool:
        """Check if location metadata exists for a storage record.
        
        Args:
            storage_key: Key of the storage record
            
        Returns:
            True if location metadata exists, False otherwise
        """
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_GeoActivityData_Collection}
        FILTER doc.Object == @storage_key
        LIMIT 1
        RETURN doc
        """
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars={"storage_key": storage_key})
            # Returns True if any record exists
            return any(cursor)
        except Exception as e:
            self.logger.error(f"Error checking if location metadata exists: {e}")
            # Assume it doesn't exist if we can't check
            return False
    
    def _music_exists(self, storage_key: str) -> bool:
        """Check if music metadata exists for a storage record.
        
        Args:
            storage_key: Key of the storage record
            
        Returns:
            True if music metadata exists, False otherwise
        """
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection}
        FILTER doc.Object == @storage_key
        LIMIT 1
        RETURN doc
        """
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars={"storage_key": storage_key})
            # Returns True if any record exists
            return any(cursor)
        except Exception as e:
            self.logger.error(f"Error checking if music metadata exists: {e}")
            # Assume it doesn't exist if we can't check
            return False
    
    def _temperature_exists(self, storage_key: str) -> bool:
        """Check if temperature metadata exists for a storage record.
        
        Args:
            storage_key: Key of the storage record
            
        Returns:
            True if temperature metadata exists, False otherwise
        """
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
        FILTER doc.Object == @storage_key
        LIMIT 1
        RETURN doc
        """
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars={"storage_key": storage_key})
            # Returns True if any record exists
            return any(cursor)
        except Exception as e:
            self.logger.error(f"Error checking if temperature metadata exists: {e}")
            # Assume it doesn't exist if we can't check
            return False
    
    def _insert_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert records into the appropriate collections.
        
        Args:
            records: Records to insert
        """
        if not records:
            self.logger.info("No records to insert")
            return
        
        # Organize records by type
        location_records = []
        music_records = []
        temperature_records = []
        
        for record in records:
            if "latitude" in record and "longitude" in record:
                location_records.append(record)
            elif "artist" in record and "track" in record:
                music_records.append(record)
            elif "temperature" in record and "humidity" in record:
                temperature_records.append(record)
        
        # Insert records by type
        self._insert_location_records(location_records)
        self._insert_music_records(music_records)
        self._insert_temperature_records(temperature_records)
    
    def _insert_location_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert location records into the geo activity collection.
        
        Args:
            records: Location records to insert
        """
        if not records:
            return
        
        try:
            self.logger.info(f"Inserting {len(records)} location records into database")
            results = self.geo_collection.insert_many(records)
            self.logger.info(f"Successfully inserted {len(results)} location records")
        except Exception as e:
            self.logger.error(f"Error inserting location records: {e}")
            # Fail fast - no point continuing if we can't insert records
            raise
    
    def _insert_music_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert music records into the music activity collection.
        
        Args:
            records: Music records to insert
        """
        if not records:
            return
        
        try:
            self.logger.info(f"Inserting {len(records)} music records into database")
            results = self.music_collection.insert_many(records)
            self.logger.info(f"Successfully inserted {len(results)} music records")
        except Exception as e:
            self.logger.error(f"Error inserting music records: {e}")
            # Fail fast - no point continuing if we can't insert records
            raise
    
    def _insert_temperature_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert temperature records into the temperature activity collection.
        
        Args:
            records: Temperature records to insert
        """
        if not records:
            return
        
        try:
            self.logger.info(f"Inserting {len(records)} temperature records into database")
            results = self.temp_collection.insert_many(records)
            self.logger.info(f"Successfully inserted {len(results)} temperature records")
        except Exception as e:
            self.logger.error(f"Error inserting temperature records: {e}")
            # Fail fast - no point continuing if we can't insert records
            raise
    
    def _get_timezone_for_location(self, latitude: float, longitude: float) -> str:
        """Get the timezone for a given latitude and longitude.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Timezone string
        """
        # This is a simplified approach - in a real implementation, we would use
        # a proper timezone lookup service or library
        
        # Just return a random timezone based on longitude
        if longitude < -30:
            # Americas
            return random.choice([
                "America/New_York", "America/Chicago", "America/Denver", 
                "America/Los_Angeles", "America/Toronto", "America/Mexico_City"
            ])
        elif longitude < 40:
            # Europe and Africa
            return random.choice([
                "Europe/London", "Europe/Paris", "Europe/Berlin", 
                "Europe/Rome", "Europe/Madrid", "Africa/Cairo"
            ])
        elif longitude < 100:
            # Middle East and Western Asia
            return random.choice([
                "Asia/Dubai", "Asia/Tehran", "Asia/Riyadh", 
                "Asia/Kolkata", "Asia/Mumbai", "Asia/Bangkok"
            ])
        else:
            # East Asia and Pacific
            return random.choice([
                "Asia/Shanghai", "Asia/Tokyo", "Asia/Seoul", 
                "Australia/Sydney", "Australia/Perth", "Pacific/Auckland"
            ])
    
    def _generate_track_name(self) -> str:
        """Generate a realistic track name.
        
        Returns:
            Generated track name
        """
        template = random.choice(self.track_templates)
        
        # Replace placeholders with random words
        track_name = template
        if "{adjective}" in track_name:
            track_name = track_name.replace("{adjective}", random.choice(self.adjectives))
        if "{noun}" in track_name:
            track_name = track_name.replace("{noun}", random.choice(self.nouns))
        if "{verb}" in track_name:
            track_name = track_name.replace("{verb}", random.choice(self.verbs))
        
        return track_name
    
    def _generate_album_name(self, artist: str) -> str:
        """Generate a realistic album name.
        
        Args:
            artist: Artist name
            
        Returns:
            Generated album name
        """
        template = random.choice(self.album_templates)
        
        # Replace placeholders with random words
        album_name = template
        if "{artist}" in album_name:
            album_name = album_name.replace("{artist}", artist)
        if "{adjective}" in album_name:
            album_name = album_name.replace("{adjective}", random.choice(self.adjectives))
        if "{noun}" in album_name:
            album_name = album_name.replace("{noun}", random.choice(self.nouns))
        if "{verb}" in album_name:
            album_name = album_name.replace("{verb}", random.choice(self.verbs))
        
        return album_name


def main():
    """Main function for testing the activity metadata generator."""
    logging.basicConfig(level=logging.INFO)
    
    # Sample configuration
    config = {}
    
    # Create generator with direct database connection
    db_config = IndalekoDBConfig()
    db_config.setup_database(db_config.config["database"]["database"])
    
    generator = ActivityMetadataGeneratorImpl(config, db_config, seed=42)
    
    # Generate activity metadata for existing storage records
    records = generator.generate(10)
    
    # Generate some truth records
    criteria = {
        "storage_criteria": {
            "file_extension": ".pdf"
        },
        "activity_criteria": {
            "type": "location",
            "city": "New York",
            "latitude": 40.7128,
            "longitude": -74.0060
        }
    }
    truth_records = generator.generate_truth(5, criteria)
    
    # Print records for inspection
    logging.info(f"Generated {len(records)} regular activity records")
    logging.info(f"Generated {len(truth_records)} truth activity records")
    
    # Print sample record
    if records:
        logging.info(f"Sample record: {records[0]}")
    
    # Print sample truth record
    if truth_records:
        logging.info(f"Sample truth record: {truth_records[0]}")
    
    # Print truth list
    logging.info(f"Truth list: {generator.truth_list}")


if __name__ == "__main__":
    main()
