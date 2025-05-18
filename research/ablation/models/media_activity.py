"""Media activity data models for ablation testing."""

from enum import Enum

from ..utils.semantic_attributes import SemanticAttributeRegistry
from .activity import ActivityData, ActivityType


class MediaType(str, Enum):
    """Enumeration of media types."""

    VIDEO = "video"
    AUDIO = "audio"
    STREAM = "stream"
    IMAGE = "image"
    GAME = "game"


class MediaActivity(ActivityData):
    """Model for media consumption activity."""

    media_type: MediaType
    title: str
    platform: str  # e.g., "YouTube", "Netflix", "Spotify", "Twitch", etc.
    duration_seconds: int | None = None
    creator: str | None = None
    url: str | None = None
    source: str  # e.g., "browser_extension", "app", etc.

    def __init__(self, **data):
        """Initialize a media activity with proper activity type and semantic attributes."""
        # Set the activity type to MEDIA
        data["activity_type"] = ActivityType.MEDIA

        # Set the source if not provided
        if "source" not in data:
            data["source"] = "ablation_synthetic_generator"

        # Initialize semantic attributes if not provided
        if "semantic_attributes" not in data:
            data["semantic_attributes"] = {}

        # Convert media_type to enum if it's a string
        if "media_type" in data and isinstance(data["media_type"], str):
            try:
                data["media_type"] = MediaType(data["media_type"].lower())
            except ValueError:
                pass  # Will be caught by pydantic validation

        # Call the parent constructor
        super().__init__(**data)

        # Add semantic attributes
        self.add_semantic_attributes()

    def add_semantic_attributes(self):
        """Add media-specific semantic attributes."""
        attrs = SemanticAttributeRegistry()

        # Add media type
        self.semantic_attributes[SemanticAttributeRegistry.MEDIA_TYPE] = attrs.create_attribute(
            SemanticAttributeRegistry.MEDIA_TYPE,
            self.media_type.value,
        )

        # Add title
        self.semantic_attributes[SemanticAttributeRegistry.MEDIA_TITLE] = attrs.create_attribute(
            SemanticAttributeRegistry.MEDIA_TITLE,
            self.title,
        )

        # Add platform
        self.semantic_attributes[SemanticAttributeRegistry.MEDIA_PLATFORM] = attrs.create_attribute(
            SemanticAttributeRegistry.MEDIA_PLATFORM,
            self.platform,
        )

        # Add duration if available
        if self.duration_seconds:
            self.semantic_attributes[SemanticAttributeRegistry.MEDIA_DURATION] = attrs.create_attribute(
                SemanticAttributeRegistry.MEDIA_DURATION,
                self.duration_seconds,
            )

        # Add creator if available
        if self.creator:
            self.semantic_attributes[SemanticAttributeRegistry.MEDIA_CREATOR] = attrs.create_attribute(
                SemanticAttributeRegistry.MEDIA_CREATOR,
                self.creator,
            )

        # Add source
        self.semantic_attributes[SemanticAttributeRegistry.MEDIA_SOURCE] = attrs.create_attribute(
            SemanticAttributeRegistry.MEDIA_SOURCE,
            self.source,
        )

    @classmethod
    def create_video_activity(
        cls,
        title: str,
        platform: str,
        duration_seconds: int | None = None,
        creator: str | None = None,
        url: str | None = None,
        source: str = "ablation_synthetic_generator",
    ):
        """Create a media activity for video consumption.

        Args:
            title: The video title.
            platform: The platform (e.g., "YouTube", "Netflix").
            duration_seconds: The duration in seconds.
            creator: The creator name.
            url: The URL to the video.
            source: The data source.

        Returns:
            MediaActivity: The media activity.
        """
        return cls(
            media_type=MediaType.VIDEO,
            title=title,
            platform=platform,
            duration_seconds=duration_seconds,
            creator=creator,
            url=url,
            source=source,
        )

    @classmethod
    def create_audio_activity(
        cls,
        title: str,
        platform: str,
        duration_seconds: int | None = None,
        creator: str | None = None,
        url: str | None = None,
        source: str = "ablation_synthetic_generator",
    ):
        """Create a media activity for audio consumption.

        Args:
            title: The audio title.
            platform: The platform (e.g., "Spotify", "Audible").
            duration_seconds: The duration in seconds.
            creator: The creator name.
            url: The URL to the audio.
            source: The data source.

        Returns:
            MediaActivity: The media activity.
        """
        return cls(
            media_type=MediaType.AUDIO,
            title=title,
            platform=platform,
            duration_seconds=duration_seconds,
            creator=creator,
            url=url,
            source=source,
        )

    @classmethod
    def create_stream_activity(
        cls,
        title: str,
        platform: str,
        duration_seconds: int | None = None,
        creator: str | None = None,
        url: str | None = None,
        source: str = "ablation_synthetic_generator",
    ):
        """Create a media activity for stream consumption.

        Args:
            title: The stream title.
            platform: The platform (e.g., "Twitch", "YouTube Live").
            duration_seconds: The duration in seconds.
            creator: The creator name.
            url: The URL to the stream.
            source: The data source.

        Returns:
            MediaActivity: The media activity.
        """
        return cls(
            media_type=MediaType.STREAM,
            title=title,
            platform=platform,
            duration_seconds=duration_seconds,
            creator=creator,
            url=url,
            source=source,
        )

    @classmethod
    def create_image_activity(
        cls,
        title: str,
        platform: str,
        creator: str | None = None,
        url: str | None = None,
        source: str = "ablation_synthetic_generator",
    ):
        """Create a media activity for image viewing.

        Args:
            title: The image title.
            platform: The platform (e.g., "Instagram", "Flickr").
            creator: The creator name.
            url: The URL to the image.
            source: The data source.

        Returns:
            MediaActivity: The media activity.
        """
        return cls(
            media_type=MediaType.IMAGE,
            title=title,
            platform=platform,
            creator=creator,
            url=url,
            source=source,
        )

    @classmethod
    def create_game_activity(
        cls,
        title: str,
        platform: str,
        duration_seconds: int | None = None,
        creator: str | None = None,
        source: str = "ablation_synthetic_generator",
    ):
        """Create a media activity for game play.

        Args:
            title: The game title.
            platform: The platform (e.g., "Steam", "PlayStation").
            duration_seconds: The duration in seconds.
            creator: The game developer/publisher.
            source: The data source.

        Returns:
            MediaActivity: The media activity.
        """
        return cls(
            media_type=MediaType.GAME,
            title=title,
            platform=platform,
            duration_seconds=duration_seconds,
            creator=creator,
            source=source,
        )
