"""
Music activity models for the ablation study framework.

This module provides Pydantic models for music activity data,
including playback sessions, tracks, artists, and albums.
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from uuid import UUID, uuid4

from pydantic import Field, validator

from tools.ablation.models.base import ActivityBaseModel, SemanticAttribute


class MusicGenre(str, Enum):
    """Enumeration of music genres."""
    
    POP = "pop"
    ROCK = "rock"
    HIPHOP = "hip_hop"
    RNB = "r&b"
    JAZZ = "jazz"
    CLASSICAL = "classical"
    ELECTRONIC = "electronic"
    COUNTRY = "country"
    FOLK = "folk"
    METAL = "metal"
    BLUES = "blues"
    REGGAE = "reggae"
    PUNK = "punk"
    ALTERNATIVE = "alternative"
    INDIE = "indie"


class PlaybackMode(str, Enum):
    """Enumeration of playback modes."""
    
    NORMAL = "normal"
    REPEAT_TRACK = "repeat_track"
    REPEAT_ALBUM = "repeat_album"
    SHUFFLE = "shuffle"
    SHUFFLE_REPEAT = "shuffle_repeat"


class StreamingQuality(str, Enum):
    """Enumeration of streaming quality levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LOSSLESS = "lossless"
    HI_RES = "hi_res"


class TrackModel(ActivityBaseModel):
    """Model for music tracks."""
    
    title: str
    artist: str
    album: Optional[str] = None
    duration_seconds: int
    release_date: Optional[datetime] = None
    genre: Optional[MusicGenre] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    isrc: Optional[str] = None  # International Standard Recording Code
    
    @validator('release_date')
    def ensure_timezone(cls, v):
        """Ensure datetimes are timezone-aware."""
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AlbumModel(ActivityBaseModel):
    """Model for music albums."""
    
    title: str
    artist: str
    release_date: Optional[datetime] = None
    genre: Optional[MusicGenre] = None
    track_count: Optional[int] = None
    total_duration_seconds: Optional[int] = None
    upc: Optional[str] = None  # Universal Product Code
    
    @validator('release_date')
    def ensure_timezone(cls, v):
        """Ensure datetimes are timezone-aware."""
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class ArtistModel(ActivityBaseModel):
    """Model for music artists."""
    
    name: str
    genres: List[MusicGenre] = Field(default_factory=list)
    
    # Optional fields
    origin: Optional[str] = None
    formed_year: Optional[int] = None
    disbanded_year: Optional[int] = None
    biography: Optional[str] = None


class PlaybackEventModel(ActivityBaseModel):
    """Model for individual playback events."""
    
    track_id: UUID
    position_seconds: int  # Playback position in seconds
    event_type: str  # play, pause, skip, seek, etc.
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @validator('timestamp')
    def ensure_timezone(cls, v):
        """Ensure datetimes are timezone-aware."""
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class MusicActivityModel(ActivityBaseModel):
    """Model for music playback activity sessions."""
    
    # Basic session information
    track: TrackModel
    artist: ArtistModel
    album: Optional[AlbumModel] = None
    
    # Playback details
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    completed: bool = False
    
    # Playback context
    playback_mode: PlaybackMode = PlaybackMode.NORMAL
    streaming_quality: StreamingQuality = StreamingQuality.MEDIUM
    volume_percent: int = 100
    device_type: str = "unknown"
    
    # Events during playback
    events: List[PlaybackEventModel] = Field(default_factory=list)
    
    # User feedback
    liked: bool = False
    rating: Optional[int] = None  # 1-5 stars
    
    # Semantic attributes specifically for music activity
    semantic_attributes: List[SemanticAttribute] = Field(default_factory=list)
    
    @validator('start_time', 'end_time')
    def ensure_timezone(cls, v):
        """Ensure datetimes are timezone-aware."""
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    @validator('rating')
    def validate_rating(cls, v):
        """Validate rating is between 1 and 5."""
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating must be between 1 and 5")
        return v
    
    def calculate_duration(self) -> int:
        """Calculate the duration of the playback session.
        
        Returns:
            Duration in seconds
        """
        if self.end_time and self.start_time:
            return int((self.end_time - self.start_time).total_seconds())
        return 0
    
    def update_end_time(self, end_time: Optional[datetime] = None) -> None:
        """Update the end time of the playback session.
        
        Args:
            end_time: Optional end time, defaults to now
        """
        if end_time:
            self.end_time = end_time
        else:
            self.end_time = datetime.now(timezone.utc)
        
        self.duration_seconds = self.calculate_duration()
    
    def add_event(self, event_type: str, position_seconds: int) -> None:
        """Add a playback event to the session.
        
        Args:
            event_type: Type of event (play, pause, skip, etc.)
            position_seconds: Playback position in seconds
        """
        event = PlaybackEventModel(
            track_id=self.track.id,
            position_seconds=position_seconds,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.events.append(event)


# Semantic attribute identifiers for music activity
class MusicSemanticAttributes:
    """Semantic attribute identifiers for music activity."""
    
    # Artist attributes
    ARTIST_NAME = UUID("11111111-0000-0000-0000-000000000001")
    ARTIST_GENRE = UUID("11111111-0000-0000-0000-000000000002")
    
    # Track attributes
    TRACK_TITLE = UUID("22222222-0000-0000-0000-000000000001")
    TRACK_DURATION = UUID("22222222-0000-0000-0000-000000000002")
    TRACK_GENRE = UUID("22222222-0000-0000-0000-000000000003")
    
    # Album attributes
    ALBUM_TITLE = UUID("33333333-0000-0000-0000-000000000001")
    ALBUM_RELEASE_DATE = UUID("33333333-0000-0000-0000-000000000002")
    
    # Playback attributes
    PLAYBACK_COMPLETED = UUID("44444444-0000-0000-0000-000000000001")
    PLAYBACK_DURATION = UUID("44444444-0000-0000-0000-000000000002")
    PLAYBACK_MODE = UUID("44444444-0000-0000-0000-000000000003")
    
    # User feedback
    USER_LIKED = UUID("55555555-0000-0000-0000-000000000001")
    USER_RATING = UUID("55555555-0000-0000-0000-000000000002")


def create_music_semantic_attribute(identifier: UUID, label: str, value: Any) -> SemanticAttribute:
    """Create a semantic attribute for music activity.
    
    Args:
        identifier: UUID identifier for the attribute
        label: Human-readable label for the attribute
        value: Value of the attribute
        
    Returns:
        Semantic attribute instance
    """
    return SemanticAttribute(
        Identifier={
            "Identifier": str(identifier),
            "Label": label
        },
        Value=value
    )


def create_semantic_attributes_from_music_activity(activity: MusicActivityModel) -> List[SemanticAttribute]:
    """Create semantic attributes from a music activity.
    
    Args:
        activity: Music activity model instance
        
    Returns:
        List of semantic attributes
    """
    attributes = []
    
    # Artist attributes
    attributes.append(create_music_semantic_attribute(
        MusicSemanticAttributes.ARTIST_NAME,
        "Artist Name",
        activity.artist.name
    ))
    
    if activity.artist.genres:
        attributes.append(create_music_semantic_attribute(
            MusicSemanticAttributes.ARTIST_GENRE,
            "Artist Genre",
            [genre.value for genre in activity.artist.genres]
        ))
    
    # Track attributes
    attributes.append(create_music_semantic_attribute(
        MusicSemanticAttributes.TRACK_TITLE,
        "Track Title",
        activity.track.title
    ))
    
    attributes.append(create_music_semantic_attribute(
        MusicSemanticAttributes.TRACK_DURATION,
        "Track Duration",
        activity.track.duration_seconds
    ))
    
    if activity.track.genre:
        attributes.append(create_music_semantic_attribute(
            MusicSemanticAttributes.TRACK_GENRE,
            "Track Genre",
            activity.track.genre.value
        ))
    
    # Album attributes
    if activity.album:
        attributes.append(create_music_semantic_attribute(
            MusicSemanticAttributes.ALBUM_TITLE,
            "Album Title",
            activity.album.title
        ))
        
        if activity.album.release_date:
            attributes.append(create_music_semantic_attribute(
                MusicSemanticAttributes.ALBUM_RELEASE_DATE,
                "Album Release Date",
                activity.album.release_date.isoformat()
            ))
    
    # Playback attributes
    attributes.append(create_music_semantic_attribute(
        MusicSemanticAttributes.PLAYBACK_COMPLETED,
        "Playback Completed",
        activity.completed
    ))
    
    if activity.duration_seconds:
        attributes.append(create_music_semantic_attribute(
            MusicSemanticAttributes.PLAYBACK_DURATION,
            "Playback Duration",
            activity.duration_seconds
        ))
    
    attributes.append(create_music_semantic_attribute(
        MusicSemanticAttributes.PLAYBACK_MODE,
        "Playback Mode",
        activity.playback_mode.value
    ))
    
    # User feedback
    attributes.append(create_music_semantic_attribute(
        MusicSemanticAttributes.USER_LIKED,
        "User Liked",
        activity.liked
    ))
    
    if activity.rating:
        attributes.append(create_music_semantic_attribute(
            MusicSemanticAttributes.USER_RATING,
            "User Rating",
            activity.rating
        ))
    
    return attributes