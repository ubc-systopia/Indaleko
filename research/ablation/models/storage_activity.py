"""Storage activity data models for ablation testing."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from ..utils.semantic_attributes import SemanticAttributeRegistry
from .activity import ActivityData, ActivityType


class StorageOperationType(str, Enum):
    """Enumeration of storage operation types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"
    COPY = "copy"


class StorageActivity(ActivityData):
    """Model for storage activity (file system operations)."""

    path: str
    file_type: str  # e.g., "Document", "Image", "Video", "Audio", etc.
    size_bytes: int
    operation: StorageOperationType
    operation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str  # e.g., "ntfs", "posix", "dropbox", "onedrive", etc.
    related_path: str | None = None  # For operations like move, copy, rename

    def __init__(self, **data):
        """Initialize a storage activity with proper activity type and semantic attributes."""
        # Set the activity type to STORAGE
        data["activity_type"] = ActivityType.STORAGE

        # Set the source if not provided
        if "source" not in data:
            data["source"] = "ablation_synthetic_generator"

        # Initialize semantic attributes if not provided
        if "semantic_attributes" not in data:
            data["semantic_attributes"] = {}

        # Convert operation to enum if it's a string
        if "operation" in data and isinstance(data["operation"], str):
            try:
                data["operation"] = StorageOperationType(data["operation"].lower())
            except ValueError:
                pass  # Will be caught by pydantic validation

        # Call the parent constructor
        super().__init__(**data)

        # Add semantic attributes
        self.add_semantic_attributes()

    def add_semantic_attributes(self):
        """Add storage-specific semantic attributes."""
        attrs = SemanticAttributeRegistry()

        # Add path
        self.semantic_attributes[SemanticAttributeRegistry.STORAGE_PATH] = attrs.create_attribute(
            SemanticAttributeRegistry.STORAGE_PATH,
            self.path,
        )

        # Add file type
        self.semantic_attributes[SemanticAttributeRegistry.STORAGE_FILE_TYPE] = attrs.create_attribute(
            SemanticAttributeRegistry.STORAGE_FILE_TYPE,
            self.file_type,
        )

        # Add size
        self.semantic_attributes[SemanticAttributeRegistry.STORAGE_SIZE] = attrs.create_attribute(
            SemanticAttributeRegistry.STORAGE_SIZE,
            self.size_bytes,
        )

        # Add operation
        self.semantic_attributes[SemanticAttributeRegistry.STORAGE_OPERATION] = attrs.create_attribute(
            SemanticAttributeRegistry.STORAGE_OPERATION,
            self.operation.value,
        )

        # Add timestamp
        self.semantic_attributes[SemanticAttributeRegistry.STORAGE_TIMESTAMP] = attrs.create_attribute(
            SemanticAttributeRegistry.STORAGE_TIMESTAMP,
            self.operation_timestamp.isoformat(),
        )

        # Add source
        self.semantic_attributes[SemanticAttributeRegistry.STORAGE_SOURCE] = attrs.create_attribute(
            SemanticAttributeRegistry.STORAGE_SOURCE,
            self.source,
        )

    @classmethod
    def create_file_created(
        cls, path: str, file_type: str, size_bytes: int, source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file creation event.

        Args:
            path: The file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.CREATE,
            source=source,
        )

    @classmethod
    def create_file_accessed(
        cls, path: str, file_type: str, size_bytes: int, source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file access event.

        Args:
            path: The file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.READ,
            source=source,
        )

    @classmethod
    def create_file_modified(
        cls, path: str, file_type: str, size_bytes: int, source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file modification event.

        Args:
            path: The file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.UPDATE,
            source=source,
        )

    @classmethod
    def create_file_deleted(
        cls, path: str, file_type: str, size_bytes: int, source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file deletion event.

        Args:
            path: The file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.DELETE,
            source=source,
        )

    @classmethod
    def create_file_renamed(
        cls, old_path: str, new_path: str, file_type: str, size_bytes: int, source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file rename event.

        Args:
            old_path: The old file path.
            new_path: The new file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=new_path,
            related_path=old_path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.RENAME,
            source=source,
        )

    @classmethod
    def create_file_moved(
        cls, old_path: str, new_path: str, file_type: str, size_bytes: int, source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file move event.

        Args:
            old_path: The old file path.
            new_path: The new file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=new_path,
            related_path=old_path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.MOVE,
            source=source,
        )

    @classmethod
    def create_file_copied(
        cls,
        original_path: str,
        new_path: str,
        file_type: str,
        size_bytes: int,
        source: str = "ablation_synthetic_generator",
    ):
        """Create a storage activity for a file copy event.

        Args:
            original_path: The original file path.
            new_path: The new file path.
            file_type: The file type.
            size_bytes: The file size in bytes.
            source: The data source.

        Returns:
            StorageActivity: The storage activity.
        """
        return cls(
            path=new_path,
            related_path=original_path,
            file_type=file_type,
            size_bytes=size_bytes,
            operation=StorageOperationType.COPY,
            source=source,
        )
