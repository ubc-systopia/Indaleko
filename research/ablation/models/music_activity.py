"""Music activity data models for ablation testing."""

from ..utils.semantic_attributes import SemanticAttributeRegistry
from .activity import ActivityData, ActivityType


class MusicActivity(ActivityData):
    """Model for music listening activity."""

    artist: str
    track: str
    album: str | None = None
    genre: str | None = None
    duration_seconds: int
    platform: str  # e.g., "Spotify", "Apple Music", etc.

    def __init__(self, **data):
        """Initialize a music activity with proper activity type and semantic attributes."""
        # Set the activity type to MUSIC
        data["activity_type"] = ActivityType.MUSIC

        # Set the source if not provided
        if "source" not in data:
            data["source"] = "ablation_synthetic_generator"

        # Initialize semantic attributes if not provided
        if "semantic_attributes" not in data:
            data["semantic_attributes"] = {}

        # Call the parent constructor
        super().__init__(**data)

        # Add semantic attributes
        self.add_semantic_attributes()

    def add_semantic_attributes(self):
        """Add music-specific semantic attributes."""
        attrs = SemanticAttributeRegistry()

        # Add artist
        self.semantic_attributes[SemanticAttributeRegistry.MUSIC_ARTIST] = attrs.create_attribute(
            SemanticAttributeRegistry.MUSIC_ARTIST,
            self.artist,
        )

        # Add track
        self.semantic_attributes[SemanticAttributeRegistry.MUSIC_TRACK] = attrs.create_attribute(
            SemanticAttributeRegistry.MUSIC_TRACK,
            self.track,
        )

        # Add album if available
        if self.album:
            self.semantic_attributes[SemanticAttributeRegistry.MUSIC_ALBUM] = attrs.create_attribute(
                SemanticAttributeRegistry.MUSIC_ALBUM,
                self.album,
            )

        # Add genre if available
        if self.genre:
            self.semantic_attributes[SemanticAttributeRegistry.MUSIC_GENRE] = attrs.create_attribute(
                SemanticAttributeRegistry.MUSIC_GENRE,
                self.genre,
            )

        # Add duration
        self.semantic_attributes[SemanticAttributeRegistry.MUSIC_DURATION] = attrs.create_attribute(
            SemanticAttributeRegistry.MUSIC_DURATION,
            self.duration_seconds,
        )

        # Add source
        self.semantic_attributes[SemanticAttributeRegistry.MUSIC_SOURCE] = attrs.create_attribute(
            SemanticAttributeRegistry.MUSIC_SOURCE,
            self.platform,
        )
