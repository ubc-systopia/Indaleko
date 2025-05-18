"""Task activity data models for ablation testing."""

from ..utils.semantic_attributes import SemanticAttributeRegistry
from .activity import ActivityData, ActivityType


class TaskActivity(ActivityData):
    """Model for task activity (application usage)."""

    task_name: str
    application: str
    window_title: str | None = None
    duration_seconds: int
    active: bool = True
    source: str  # e.g., "windows_task_manager", "mac_activity_monitor", etc.

    def __init__(self, **data):
        """Initialize a task activity with proper activity type and semantic attributes."""
        # Set the activity type to TASK
        data["activity_type"] = ActivityType.TASK

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
        """Add task-specific semantic attributes."""
        attrs = SemanticAttributeRegistry()

        # Add task name
        self.semantic_attributes[SemanticAttributeRegistry.TASK_NAME] = attrs.create_attribute(
            SemanticAttributeRegistry.TASK_NAME,
            self.task_name,
        )

        # Add application
        self.semantic_attributes[SemanticAttributeRegistry.TASK_APPLICATION] = attrs.create_attribute(
            SemanticAttributeRegistry.TASK_APPLICATION,
            self.application,
        )

        # Add window title if available
        if self.window_title:
            self.semantic_attributes[SemanticAttributeRegistry.TASK_WINDOW_TITLE] = attrs.create_attribute(
                SemanticAttributeRegistry.TASK_WINDOW_TITLE,
                self.window_title,
            )

        # Add duration
        self.semantic_attributes[SemanticAttributeRegistry.TASK_DURATION] = attrs.create_attribute(
            SemanticAttributeRegistry.TASK_DURATION,
            self.duration_seconds,
        )

        # Add active status
        self.semantic_attributes[SemanticAttributeRegistry.TASK_ACTIVE] = attrs.create_attribute(
            SemanticAttributeRegistry.TASK_ACTIVE,
            self.active,
        )

        # Add source
        self.semantic_attributes[SemanticAttributeRegistry.TASK_SOURCE] = attrs.create_attribute(
            SemanticAttributeRegistry.TASK_SOURCE,
            self.source,
        )
