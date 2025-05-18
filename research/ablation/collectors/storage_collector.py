"""Storage activity collector for ablation testing."""

import logging
import os
import random
from typing import Any
from uuid import UUID

from ..base import ISyntheticCollector
from ..models.storage_activity import StorageActivity, StorageOperationType
from ..utils.uuid_utils import generate_deterministic_uuid


class StorageActivityCollector(ISyntheticCollector):
    """Synthetic collector for storage activity."""

    def __init__(self, seed_value: int = 42):
        """Initialize the storage activity collector.

        Args:
            seed_value: Random seed for deterministic data generation.
        """
        self.seed(seed_value)
        self.logger = logging.getLogger(__name__)

        # Sample file types and extensions
        self.file_types = {
            "Document": ["docx", "pdf", "txt", "md", "xlsx"],
            "Image": ["jpg", "png", "gif", "bmp", "tiff"],
            "Video": ["mp4", "avi", "mov", "mkv", "wmv"],
            "Audio": ["mp3", "wav", "flac", "aac", "ogg"],
            "Archive": ["zip", "rar", "tar", "gz", "7z"],
            "Code": ["py", "js", "ts", "java", "c", "cpp"],
        }

        # Sample directories and paths
        self.base_directories = [
            "/home/user/Documents",
            "/home/user/Pictures",
            "/home/user/Videos",
            "/home/user/Music",
            "/home/user/Downloads",
            "/mnt/data/shared",
            "C:/Users/user/Documents",
            "C:/Users/user/Pictures",
            "C:/Users/user/Videos",
            "C:/Users/user/Music",
        ]

        # Sample sources
        self.sources = ["ntfs", "posix", "dropbox", "onedrive", "gdrive", "s3"]

    def collect(self) -> dict:
        """Generate synthetic storage activity data.

        Returns:
            Dict: The generated storage activity data.
        """
        # Select a random file type and extension
        file_type = random.choice(list(self.file_types.keys()))
        extension = random.choice(self.file_types[file_type])

        # Generate a random file name
        file_name = f"file_{random.randint(1000, 9999)}.{extension}"

        # Select a base directory
        base_dir = random.choice(self.base_directories)

        # Create a path
        path = os.path.join(base_dir, file_name).replace("\\", "/")

        # Generate a random file size from 1KB to 100MB
        size_bytes = random.randint(1024, 104857600)

        # Select a random operation type
        operation = random.choice(list(StorageOperationType))

        # Select a random source
        source = random.choice(self.sources)

        # If the operation is MOVE or COPY or RENAME, we need a related path
        related_path = None
        if operation in [StorageOperationType.MOVE, StorageOperationType.COPY, StorageOperationType.RENAME]:
            # Select a different base directory for the source
            source_dir = random.choice([d for d in self.base_directories if d != base_dir])
            related_path = os.path.join(source_dir, file_name).replace("\\", "/")

        # Create a storage activity
        if operation == StorageOperationType.MOVE:
            activity = StorageActivity.create_file_moved(related_path, path, file_type, size_bytes, source)
        elif operation == StorageOperationType.COPY:
            activity = StorageActivity.create_file_copied(related_path, path, file_type, size_bytes, source)
        elif operation == StorageOperationType.RENAME:
            old_name = f"file_{random.randint(1000, 9999)}.{extension}"
            related_path = os.path.join(os.path.dirname(path), old_name).replace("\\", "/")
            activity = StorageActivity.create_file_renamed(related_path, path, file_type, size_bytes, source)
        elif operation == StorageOperationType.CREATE:
            activity = StorageActivity.create_file_created(path, file_type, size_bytes, source)
        elif operation == StorageOperationType.READ:
            activity = StorageActivity.create_file_accessed(path, file_type, size_bytes, source)
        elif operation == StorageOperationType.UPDATE:
            activity = StorageActivity.create_file_modified(path, file_type, size_bytes, source)
        elif operation == StorageOperationType.DELETE:
            activity = StorageActivity.create_file_deleted(path, file_type, size_bytes, source)

        # Return the activity as a dictionary
        return activity.model_dump()

    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a storage-related query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        matching_entities = set()
        query_lower = query.lower()

        # Check for file type mentions
        for file_type in self.file_types.keys():
            if file_type.lower() in query_lower:
                for i in range(5):  # Generate 5 matching activities
                    entity_id = generate_deterministic_uuid(f"storage_activity:{file_type}:{i}")
                    matching_entities.add(entity_id)

        # Check for operation type mentions
        for operation in StorageOperationType:
            if operation.value.lower() in query_lower:
                for i in range(3):  # Generate 3 matching activities
                    entity_id = generate_deterministic_uuid(f"storage_activity:{operation.value}:{i}")
                    matching_entities.add(entity_id)

        # Check for source mentions
        for source in self.sources:
            if source.lower() in query_lower:
                for i in range(3):  # Generate 3 matching activities
                    entity_id = generate_deterministic_uuid(f"storage_activity:{source}:{i}")
                    matching_entities.add(entity_id)

        # Check for path/directory mentions
        for base_dir in self.base_directories:
            # Extract the last part of the path
            dir_name = os.path.basename(base_dir)
            if dir_name.lower() in query_lower:
                for i in range(3):  # Generate 3 matching activities
                    entity_id = generate_deterministic_uuid(f"storage_activity:{dir_name}:{i}")
                    matching_entities.add(entity_id)

        return matching_entities

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic storage activity data.

        Args:
            count: Number of storage activity records to generate.

        Returns:
            List[Dict]: List of generated storage activity data.
        """
        return [self.collect() for _ in range(count)]

    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate storage activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated storage activity data that should match the query.
        """
        query_lower = query.lower()
        matching_data = []

        # Extract key terms from the query
        # Check for file type mentions
        for file_type in self.file_types.keys():
            if file_type.lower() in query_lower:
                # Generate matching data for this file type
                for i in range(count):
                    extension = random.choice(self.file_types[file_type])
                    file_name = f"file_match_{i}.{extension}"
                    base_dir = random.choice(self.base_directories)
                    path = os.path.join(base_dir, file_name).replace("\\", "/")
                    size_bytes = random.randint(1024, 104857600)

                    activity = StorageActivity.create_file_created(
                        path, file_type, size_bytes, random.choice(self.sources),
                    )

                    # Generate a deterministic ID
                    activity_dict = activity.model_dump()
                    activity_dict["id"] = generate_deterministic_uuid(f"storage_activity:{file_type}:{i}")

                    matching_data.append(activity_dict)
                    if len(matching_data) >= count:
                        return matching_data

        # Check for operation mentions
        for operation in StorageOperationType:
            if operation.value.lower() in query_lower:
                # Generate matching data for this operation
                for i in range(count):
                    file_type = random.choice(list(self.file_types.keys()))
                    extension = random.choice(self.file_types[file_type])
                    file_name = f"file_match_{i}.{extension}"
                    base_dir = random.choice(self.base_directories)
                    path = os.path.join(base_dir, file_name).replace("\\", "/")
                    size_bytes = random.randint(1024, 104857600)

                    if operation == StorageOperationType.CREATE:
                        activity = StorageActivity.create_file_created(
                            path, file_type, size_bytes, random.choice(self.sources),
                        )
                    elif operation == StorageOperationType.READ:
                        activity = StorageActivity.create_file_accessed(
                            path, file_type, size_bytes, random.choice(self.sources),
                        )
                    elif operation == StorageOperationType.UPDATE:
                        activity = StorageActivity.create_file_modified(
                            path, file_type, size_bytes, random.choice(self.sources),
                        )
                    elif operation == StorageOperationType.DELETE:
                        activity = StorageActivity.create_file_deleted(
                            path, file_type, size_bytes, random.choice(self.sources),
                        )
                    elif operation == StorageOperationType.RENAME:
                        old_name = f"old_file_{i}.{extension}"
                        old_path = os.path.join(base_dir, old_name).replace("\\", "/")
                        activity = StorageActivity.create_file_renamed(
                            old_path, path, file_type, size_bytes, random.choice(self.sources),
                        )
                    elif operation == StorageOperationType.MOVE:
                        src_dir = random.choice([d for d in self.base_directories if d != base_dir])
                        old_path = os.path.join(src_dir, file_name).replace("\\", "/")
                        activity = StorageActivity.create_file_moved(
                            old_path, path, file_type, size_bytes, random.choice(self.sources),
                        )
                    elif operation == StorageOperationType.COPY:
                        src_dir = random.choice([d for d in self.base_directories if d != base_dir])
                        old_path = os.path.join(src_dir, file_name).replace("\\", "/")
                        activity = StorageActivity.create_file_copied(
                            old_path, path, file_type, size_bytes, random.choice(self.sources),
                        )

                    # Generate a deterministic ID
                    activity_dict = activity.model_dump()
                    activity_dict["id"] = generate_deterministic_uuid(f"storage_activity:{operation.value}:{i}")

                    matching_data.append(activity_dict)
                    if len(matching_data) >= count:
                        return matching_data

        # If we couldn't generate specific matching data, create generic matches
        while len(matching_data) < count:
            data = self.collect()
            data["id"] = generate_deterministic_uuid(f"storage_activity:generic_match:{len(matching_data)}")
            matching_data.append(data)

        return matching_data

    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate storage activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated storage activity data that should NOT match the query.
        """
        query_lower = query.lower()
        non_matching_data = []

        # Determine non-matching file types
        non_matching_file_types = [ft for ft in self.file_types.keys() if ft.lower() not in query_lower]
        if not non_matching_file_types:
            non_matching_file_types = list(self.file_types.keys())  # Fallback

        # Determine non-matching operations
        non_matching_operations = [op for op in StorageOperationType if op.value.lower() not in query_lower]
        if not non_matching_operations:
            non_matching_operations = list(StorageOperationType)  # Fallback

        # Determine non-matching sources
        non_matching_sources = [src for src in self.sources if src.lower() not in query_lower]
        if not non_matching_sources:
            non_matching_sources = self.sources  # Fallback

        # Generate non-matching data
        for i in range(count):
            file_type = random.choice(non_matching_file_types)
            extension = random.choice(self.file_types[file_type])
            operation = random.choice(non_matching_operations)
            source = random.choice(non_matching_sources)

            file_name = f"non_match_{i}_{random.randint(1000, 9999)}.{extension}"
            base_dir = random.choice(self.base_directories)
            path = os.path.join(base_dir, file_name).replace("\\", "/")
            size_bytes = random.randint(1024, 104857600)

            if operation == StorageOperationType.CREATE:
                activity = StorageActivity.create_file_created(path, file_type, size_bytes, source)
            elif operation == StorageOperationType.READ:
                activity = StorageActivity.create_file_accessed(path, file_type, size_bytes, source)
            elif operation == StorageOperationType.UPDATE:
                activity = StorageActivity.create_file_modified(path, file_type, size_bytes, source)
            elif operation == StorageOperationType.DELETE:
                activity = StorageActivity.create_file_deleted(path, file_type, size_bytes, source)
            elif operation == StorageOperationType.RENAME:
                old_name = f"old_non_match_{i}.{extension}"
                old_path = os.path.join(base_dir, old_name).replace("\\", "/")
                activity = StorageActivity.create_file_renamed(old_path, path, file_type, size_bytes, source)
            elif operation == StorageOperationType.MOVE:
                src_dir = random.choice([d for d in self.base_directories if d != base_dir])
                old_path = os.path.join(src_dir, file_name).replace("\\", "/")
                activity = StorageActivity.create_file_moved(old_path, path, file_type, size_bytes, source)
            elif operation == StorageOperationType.COPY:
                src_dir = random.choice([d for d in self.base_directories if d != base_dir])
                old_path = os.path.join(src_dir, file_name).replace("\\", "/")
                activity = StorageActivity.create_file_copied(old_path, path, file_type, size_bytes, source)

            # Generate a deterministic ID
            activity_dict = activity.model_dump()
            activity_dict["id"] = generate_deterministic_uuid(
                f"storage_activity:non_match:{file_type}:{operation.value}:{i}",
            )

            non_matching_data.append(activity_dict)

        return non_matching_data

    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        random.seed(seed_value)
