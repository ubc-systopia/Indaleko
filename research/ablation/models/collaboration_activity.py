"""Collaboration activity data models for ablation testing."""

from pydantic import BaseModel

from ..utils.semantic_attributes import SemanticAttributeRegistry
from .activity import ActivityData, ActivityType


class Participant(BaseModel):
    """Model for collaboration participant."""

    name: str
    email: str | None = None
    user_id: str | None = None

    def __str__(self) -> str:
        """String representation of participant."""
        if self.email:
            return f"{self.name} <{self.email}>"
        return self.name


class CollaborationActivity(ActivityData):
    """Model for collaboration activity."""

    platform: str  # e.g., "Teams", "Slack", "Email", "Zoom", etc.
    event_type: str  # e.g., "Meeting", "Chat", "File Share", "Email", etc.
    participants: list[Participant]
    content: str | None = None
    duration_seconds: int | None = None
    source: str  # e.g., "outlook", "teams", "slack", etc.

    def __init__(self, **data):
        """Initialize a collaboration activity with proper activity type and semantic attributes."""
        # Set the activity type to COLLABORATION
        data["activity_type"] = ActivityType.COLLABORATION

        # Set the source if not provided
        if "source" not in data:
            data["source"] = "ablation_synthetic_generator"

        # Initialize semantic attributes if not provided
        if "semantic_attributes" not in data:
            data["semantic_attributes"] = {}

        # Convert participants list if it's a list of dictionaries
        if "participants" in data and isinstance(data["participants"], list):
            if data["participants"] and isinstance(data["participants"][0], dict):
                data["participants"] = [Participant(**p) for p in data["participants"]]

        # Call the parent constructor
        super().__init__(**data)

        # Add semantic attributes
        self.add_semantic_attributes()

    def add_semantic_attributes(self):
        """Add collaboration-specific semantic attributes."""
        attrs = SemanticAttributeRegistry()

        # Add platform
        self.semantic_attributes[SemanticAttributeRegistry.COLLAB_PLATFORM] = attrs.create_attribute(
            SemanticAttributeRegistry.COLLAB_PLATFORM,
            self.platform,
        )

        # Add event type
        self.semantic_attributes[SemanticAttributeRegistry.COLLAB_TYPE] = attrs.create_attribute(
            SemanticAttributeRegistry.COLLAB_TYPE,
            self.event_type,
        )

        # Add participants
        participant_names = [str(p) for p in self.participants]
        self.semantic_attributes[SemanticAttributeRegistry.COLLAB_PARTICIPANTS] = attrs.create_attribute(
            SemanticAttributeRegistry.COLLAB_PARTICIPANTS,
            participant_names,
        )

        # Add content if available
        if self.content:
            self.semantic_attributes[SemanticAttributeRegistry.COLLAB_CONTENT] = attrs.create_attribute(
                SemanticAttributeRegistry.COLLAB_CONTENT,
                self.content,
            )

        # Add duration if available
        if self.duration_seconds:
            self.semantic_attributes[SemanticAttributeRegistry.COLLAB_DURATION] = attrs.create_attribute(
                SemanticAttributeRegistry.COLLAB_DURATION,
                self.duration_seconds,
            )

        # Add source
        self.semantic_attributes[SemanticAttributeRegistry.COLLAB_SOURCE] = attrs.create_attribute(
            SemanticAttributeRegistry.COLLAB_SOURCE,
            self.source,
        )
