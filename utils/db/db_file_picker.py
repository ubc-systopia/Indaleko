"""
This is a utility class that can be used for picking files from the ArangoDB database
for further processing, particularly for background semantic extraction tasks.

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

import argparse
import logging
import os
import random
import sys
import threading
import time
import uuid

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from queue import PriorityQueue
from typing import Any

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
"""
Note: IndalekoTimestampDataModel has replaced IndalekoTimestamp.
Use datetime.now(UTC) directly instead of IndalekoTimestamp.now().
"""
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections
from platforms.machine_config import get_machine_id
from storage.i_object import IndalekoObject
from storage.known_attributes import StorageSemanticAttributes


# pylint: enable=wrong-import-position

# Logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


class IndalekoFilePicker:
    """
    Utility class for selecting files from the database for background processing,
    particularly for computationally expensive semantic metadata extraction.

    Features:
    - Random file selection from database
    - Filtering for local files only
    - Selection by last processed time for specific semantic attributes
    - Low-priority background processing queue
    """

    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()) -> None:
        self.db_config = db_config
        self.object_collection = IndalekoCollections.get_collection(
            IndalekoDBCollections.Indaleko_Object_Collection,
        )
        self.local_machine_id = str(get_machine_id())
        self.processing_queue = PriorityQueue()
        self.processing_thread = None
        self.should_stop = threading.Event()
        self.currently_processing = set()
        self.processor_lock = threading.Lock()

        # Volume GUID to path mapping cache for local machine
        self.volume_guid_map = {}
        self._init_volume_guid_map()

    def _init_volume_guid_map(self) -> None:
        """Initialize the volume GUID to path mapping for the local machine."""
        # This implementation will depend on the platform
        if sys.platform == "win32":
            import win32file

            for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive_path = f"{drive_letter}:\\"
                if os.path.exists(drive_path):
                    try:
                        volume_name = win32file.GetVolumeNameForVolumeMountPoint(drive_path)
                        # Strip trailing backslash and store without the \\?\ prefix
                        volume_guid = volume_name.rstrip("\\").replace("\\\\?\\Volume", "Volume")
                        self.volume_guid_map[volume_guid] = drive_path
                    except Exception as e:
                        logger.warning(f"Could not get volume GUID for {drive_path}: {e}")
        else:
            # For Unix-like systems, we use mount points
            try:
                with open("/proc/mounts") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            device, mount_point = parts[0], parts[1]
                            if device.startswith("/dev/"):
                                # Use device ID as a substitute for volume GUID
                                stat_info = os.stat(device)
                                device_id = f"Volume{stat_info.st_dev:x}"
                                self.volume_guid_map[device_id] = mount_point
            except Exception as e:
                logger.warning(f"Could not initialize volume map: {e}")

    def is_file_local(self, file_obj: IndalekoObject) -> bool:
        """
        Determine if a file exists on the local machine by checking:
        1. If the file's machine ID matches the current machine
        2. If the file's volume GUID corresponds to a local volume
        3. If the file actually exists at the expected local path.

        Args:
            file_obj: The IndalekoObject to check

        Returns:
            bool: True if the file is accessible locally, False otherwise
        """
        try:
            # Check if serialization works
            doc = file_obj.serialize()

            # Check if machine ID matches
            machine_id = doc.get("MachineID")
            if machine_id != self.local_machine_id:
                return False

            # Extract volume info from URI
            uri = doc.get("URI", "")
            if not uri:
                return False

            # Extract volume GUID from URI
            volume_parts = uri.split("Volume")
            if len(volume_parts) < 2:
                return False

            volume_guid = f"Volume{volume_parts[1].split('\\')[0]}"

            # Check if volume exists locally
            if volume_guid not in self.volume_guid_map:
                return False

            # Convert URI to local path
            local_path = self._uri_to_local_path(uri, volume_guid)
            if not local_path:
                return False

            # Check if file exists and is accessible
            return os.path.exists(local_path) and os.access(local_path, os.R_OK)

        except Exception as e:
            logger.warning(f"Error checking if file is local: {e}")
            return False

    def _uri_to_local_path(self, uri: str, volume_guid: str) -> str | None:
        """
        Convert a URI to a local file path.

        Args:
            uri: The URI to convert
            volume_guid: The volume GUID extracted from the URI

        Returns:
            Optional[str]: The local path if conversion is successful, None otherwise
        """
        try:
            if volume_guid not in self.volume_guid_map:
                return None

            # Replace the \\?\Volume{GUID} with the appropriate drive letter or mount point
            local_drive = self.volume_guid_map[volume_guid]
            relative_path = uri.split(volume_guid, 1)[1]

            # Ensure proper path separators for the current platform
            if sys.platform == "win32":
                # For Windows, convert forward slashes to backslashes
                local_path = os.path.join(local_drive, relative_path.lstrip("\\"))
            else:
                # For Unix-like systems, convert backslashes to forward slashes
                relative_path = relative_path.replace("\\", "/")
                local_path = os.path.join(local_drive, relative_path.lstrip("/"))

            return local_path

        except Exception as e:
            logger.warning(f"Error converting URI to local path: {e}")
            return None

    def pick_random_files(
        self,
        process_func: Callable[["IndalekoObject"], None] | None = None,
        count: int = 1,
        local_only: bool = False,
    ) -> list[IndalekoObject]:
        """
        Pick random files from the ArangoDB (using the Objects collection)
        and optionally process them using the provided function.

        Args:
            process_func: Optional function to process each file
            count: Number of files to pick
            local_only: If True, only return files that are accessible locally

        Returns:
            List[IndalekoObject]: List of selected file objects
        """
        # Get the total number of documents in the collection
        total_docs = self.object_collection._arangodb_collection.count()
        if total_docs == 0:
            logger.warning("No documents found in the collection")
            return []

        # We may need to pick more than requested to account for filtering
        pick_count = min(count * 3 if local_only else count, total_docs)

        # Generate random offsets
        random_offsets = random.sample(range(total_docs), pick_count)

        # Retrieve documents at the random offsets
        all_files = []
        local_files = []

        for _ in random_offsets:
            file_obj = IndalekoObject(**self.object_collection._arangodb_collection.random())
            all_files.append(file_obj)

            # If we're filtering for local files, check if this file is local
            if local_only and self.is_file_local(file_obj):
                local_files.append(file_obj)
                if len(local_files) >= count:
                    break

        # Determine which files to process
        result_files = local_files if local_only else all_files[:count]

        # Process files if a processing function was provided
        if process_func is not None:
            for file in result_files:
                process_func(file)

        return result_files

    def pick_files_for_semantic_processing(
        self,
        semantic_attribute_id: uuid.UUID | str,
        process_func: Callable[["IndalekoObject", str], None] | None = None,
        count: int = 10,
        max_age_days: int | None = None,
        min_last_processed_days: int | None = None,
    ) -> list[IndalekoObject]:
        """
        Pick files that need semantic attribute processing, prioritizing:
        1. Files that have never had this attribute processed
        2. Files where this attribute was processed longest ago.

        Args:
            semantic_attribute_id: UUID of the semantic attribute to check
            process_func: Optional function to process each file
            count: Maximum number of files to pick
            max_age_days: Only select files modified within this many days
            min_last_processed_days: Only select files not processed in this many days

        Returns:
            List[IndalekoObject]: List of files that need processing
        """
        attr_id_str = str(semantic_attribute_id)

        # Build the AQL query conditions
        conditions = []
        bind_vars = {"attr_id": attr_id_str}

        # Add condition for max age
        if max_age_days is not None:
            cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
            conditions.append("obj.LastModified >= @cutoff_date")
            bind_vars["cutoff_date"] = cutoff_date.isoformat()

        # Create the main AQL query
        # Strategy:
        # 1. First find files with no such semantic attribute (missing the attribute entirely)
        # 2. Then find files where the attribute exists but is old
        query = f"""
        LET missing_attr = (
            FOR obj IN Objects
                FILTER obj.type == 'file'
                FILTER NOT obj.SemanticAttributes[*].Identifier ANY == @attr_id
                {"FILTER " + " AND ".join(conditions) if conditions else ""}
                LIMIT {count}
                RETURN obj
        )

        LET needs_update = (
            FOR obj IN Objects
                FILTER obj.type == 'file'
                FILTER obj.SemanticAttributes[*].Identifier ANY == @attr_id
        """

        # Add condition for minimum time since last processing
        if min_last_processed_days is not None:
            cutoff_date = datetime.now(UTC) - timedelta(days=min_last_processed_days)
            query += """
                LET attr = (
                    FOR a IN obj.SemanticAttributes
                        FILTER a.Identifier == @attr_id
                        RETURN a
                )[0]
                FILTER attr.LastUpdated <= @update_cutoff
            """
            bind_vars["update_cutoff"] = cutoff_date.isoformat()

        # Complete the query
        query += f"""
                {"FILTER " + " AND ".join(conditions) if conditions else ""}
                SORT obj.SemanticAttributes[*].LastUpdated ASC
                LIMIT {count}
                RETURN obj
        )

        LET combined = APPEND(missing_attr, needs_update)
        RETURN SLICE(combined, 0, {count})
        """

        # Execute the query
        try:
            results = self.db_config._arangodb.aql.execute(query, bind_vars=bind_vars)
            files = [IndalekoObject(**doc) for doc in results]

            # Filter for local files
            local_files = [file for file in files if self.is_file_local(file)]

            # Process files if a processing function was provided
            if process_func is not None:
                for file in local_files:
                    # Get the local path
                    doc = file.serialize()
                    uri = doc.get("URI", "")
                    volume_parts = uri.split("Volume")
                    if len(volume_parts) >= 2:
                        volume_guid = f"Volume{volume_parts[1].split('\\')[0]}"
                        local_path = self._uri_to_local_path(uri, volume_guid)
                        if local_path:
                            process_func(file, local_path)

            return local_files

        except Exception as e:
            logger.exception(f"Error executing query for semantic processing: {e}")
            return []

    def pick_all_files(
        self,
        process_func: Callable[["IndalekoObject"], None],
        local_only: bool = False,
        batch_size: int = 100,
    ) -> int:
        """
        Process all files from the ArangoDB (using the Objects collection)
        with the provided function, optionally filtering for local files only.

        Args:
            process_func: Function to process each file
            local_only: If True, only process files that are accessible locally
            batch_size: Number of documents to retrieve in each batch

        Returns:
            int: Number of files processed
        """
        cursor = None
        processed_count = 0

        try:
            query = "FOR obj IN Objects FILTER obj.type == 'file' RETURN obj"
            cursor = self.db_config._arangodb.aql.execute(query, batch_size=batch_size)

            while True:
                batch = cursor.batch()
                if not batch:
                    break

                for doc in batch:
                    file_obj = IndalekoObject(**doc)

                    # If we're filtering for local files, check if this file is local
                    if local_only and not self.is_file_local(file_obj):
                        continue

                    process_func(file_obj)
                    processed_count += 1

            return processed_count

        except Exception as e:
            logger.exception(f"Error processing all files: {e}")
            return processed_count
        finally:
            if cursor:
                cursor.close()

    def queue_for_background_processing(
        self,
        files: list[IndalekoObject],
        process_func: Callable[[IndalekoObject, str], Any],
        priority: int = 1,
        semantic_attribute_id: uuid.UUID | str | None = None,
    ) -> int:
        """
        Queue files for background processing at low priority.

        Args:
            files: List of files to process
            process_func: Function to process each file
            priority: Priority level (lower number = higher priority)
            semantic_attribute_id: Optional semantic attribute ID for tracking

        Returns:
            int: Number of files queued
        """
        queued_count = 0

        for file in files:
            # Skip if already being processed
            file_id = file.get_object_id()
            with self.processor_lock:
                if file_id in self.currently_processing:
                    continue

            # Convert to local path
            doc = file.serialize()
            uri = doc.get("URI", "")
            if not uri:
                continue

            volume_parts = uri.split("Volume")
            if len(volume_parts) < 2:
                continue

            volume_guid = f"Volume{volume_parts[1].split('\\')[0]}"
            local_path = self._uri_to_local_path(uri, volume_guid)

            if not local_path or not os.path.exists(local_path):
                continue

            # Queue the file for processing
            queue_item = (
                priority,
                time.time(),  # timestamp for FIFO within same priority
                {
                    "file": file,
                    "local_path": local_path,
                    "process_func": process_func,
                    "semantic_attribute_id": str(semantic_attribute_id) if semantic_attribute_id else None,
                },
            )

            self.processing_queue.put(queue_item)
            queued_count += 1

        # Start the background processing thread if not already running
        self._ensure_processor_thread()

        return queued_count

    def _ensure_processor_thread(self) -> None:
        """Ensure the background processor thread is running."""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.should_stop.clear()
            self.processing_thread = threading.Thread(
                target=self._background_processor,
                daemon=True,
                name="Indaleko-BackgroundProcessor",
            )
            self.processing_thread.start()

    def _background_processor(self) -> None:
        """Background thread for processing queued files at low priority."""
        # Set process priority to below normal
        try:
            # Lower process priority
            if sys.platform == "win32":
                import psutil

                process = psutil.Process()
                process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                os.nice(10)  # Increase niceness (lower priority)
        except Exception as e:
            logger.warning(f"Could not set process priority: {e}")

        while not self.should_stop.is_set():
            try:
                # Get the next item with a timeout to allow for stopping
                try:
                    _, _, item = self.processing_queue.get(timeout=1.0)
                except Exception:
                    continue

                file = item["file"]
                local_path = item["local_path"]
                process_func = item["process_func"]

                # Mark as being processed
                file_id = file.get_object_id()
                with self.processor_lock:
                    self.currently_processing.add(file_id)

                try:
                    # Process the file
                    result = process_func(file, local_path)

                    # If processing returned specific update data and we have a semantic_attribute_id,
                    # we could update the file's semantic attributes here
                    if item.get("semantic_attribute_id") and result:
                        self._update_semantic_attribute(file, item["semantic_attribute_id"], result)

                except Exception as e:
                    logger.exception(f"Error processing file {local_path}: {e}")

                finally:
                    # Mark as no longer being processed
                    with self.processor_lock:
                        self.currently_processing.discard(file_id)

                    # Mark queue item as done
                    self.processing_queue.task_done()

            except Exception as e:
                logger.exception(f"Error in background processor: {e}")
                time.sleep(1)  # Avoid tight loop on error

    def _update_semantic_attribute(
        self,
        file: IndalekoObject,
        attribute_id: str,
        value: Any,
    ) -> bool:
        """
        Update a semantic attribute for a file in the database.

        Args:
            file: The file object to update
            attribute_id: The semantic attribute ID
            value: The new attribute value

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            file_id = file.get_object_id()
            # Use current UTC time directly
            now = datetime.now(UTC)

            # Build AQL query to update the semantic attribute
            query = """
            FOR obj IN Objects
                FILTER obj._key == @file_id
                LET attrIndex = POSITION(obj.SemanticAttributes[*].Identifier, @attr_id)
                LET updatedAttrs = (
                    attrIndex == -1
                    ? APPEND(obj.SemanticAttributes, {
                        Identifier: @attr_id,
                        Value: @value,
                        LastUpdated: @now
                      })
                    : MERGE(
                        obj.SemanticAttributes,
                        { [attrIndex]: {
                            Identifier: @attr_id,
                            Value: @value,
                            LastUpdated: @now
                          }
                        }
                      )
                )
                UPDATE obj WITH { SemanticAttributes: updatedAttrs } IN Objects
                RETURN NEW
            """

            bind_vars = {
                "file_id": file_id,
                "attr_id": attribute_id,
                "value": value,
                "now": now.isoformat(),
            }

            cursor = self.db_config._arangodb.aql.execute(query, bind_vars=bind_vars)
            return len(list(cursor)) > 0

        except Exception as e:
            logger.exception(f"Error updating semantic attribute: {e}")
            return False

    def stop_background_processing(self, wait: bool = True) -> None:
        """
        Stop the background processing thread.

        Args:
            wait: If True, wait for the processing queue to be empty
        """
        if wait:
            self.processing_queue.join()

        self.should_stop.set()

        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
            if self.processing_thread.is_alive():
                logger.warning("Background processor thread did not terminate gracefully")


def check_mime_type(file: IndalekoObject) -> None:
    """Check the mime type of the file."""
    doc = file.serialize()
    semantic_attributes = doc.get("SemanticAttributes")
    ic(type(semantic_attributes))
    for attribute in semantic_attributes:
        identifier = attribute.get("Identifier")
        value = attribute.get("Value")
        match (identifier):
            case StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX:
                ic("MIMETYPE from SUFFIX: ", value)
            case StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_STORAGE_PROVIDER:
                ic("MIMETYPE from PROVIDER: ", value)
            case StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_CONTENT:
                ic("MIMETYPE from CONTENT: ", value)
            case _:
                pass


def process_file_with_path(file: IndalekoObject, local_path: str) -> dict:
    """
    Example processing function that requires local file access.
    Returns a dictionary with file information.

    Args:
        file: The IndalekoObject to process
        local_path: The local path to the file

    Returns:
        dict: Information about the processed file
    """
    file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
    doc = file.serialize()
    file_name = doc.get("Label", "Unknown")

    ic(f"Processing {file_name} at {local_path}, size: {file_size} bytes")

    # Just a demo, return some basic file info
    return {
        "size": file_size,
        "extension": os.path.splitext(local_path)[1].lower() if local_path else "",
        "processed_time": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    """Test the enhanced IndalekoFilePicker functionality."""
    parser = argparse.ArgumentParser(description="Test IndalekoFilePicker functionality")
    parser.add_argument("--random", action="store_true", help="Pick random files")
    parser.add_argument("--local-only", action="store_true", help="Filter for local files only")
    parser.add_argument("--semantic", action="store_true", help="Pick files for semantic processing")
    parser.add_argument("--background", action="store_true", help="Queue files for background processing")
    parser.add_argument("--count", type=int, default=5, help="Number of files to pick")
    parser.add_argument("--attribute", type=str, default=None, help="Semantic attribute ID to use")
    args = parser.parse_args()

    # Create file picker instance
    file_picker = IndalekoFilePicker()

    if args.random:
        # Pick random files
        ic(f"Picking {args.count} random files, local_only={args.local_only}")
        files = file_picker.pick_random_files(
            process_func=check_mime_type,
            count=args.count,
            local_only=args.local_only,
        )

        ic(f"Found {len(files)} files")
        for file in files:
            doc = file.serialize()
            ic(f"File: {doc.get('Label')}, URI: {doc.get('URI')}")

    elif args.semantic:
        # Pick files for semantic processing
        attribute_id = args.attribute
        if not attribute_id:
            # Default to MIME type attribute if none specified
            attribute_id = StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_CONTENT

        ic(f"Picking {args.count} files for semantic attribute {attribute_id}")
        files = file_picker.pick_files_for_semantic_processing(
            semantic_attribute_id=attribute_id,
            process_func=process_file_with_path,
            count=args.count,
            min_last_processed_days=30,  # Files not processed in the last 30 days
        )

        ic(f"Found {len(files)} files needing semantic processing")

    elif args.background:
        # Queue files for background processing
        ic(f"Queueing {args.count} files for background processing")

        # First get some files
        files = file_picker.pick_random_files(count=args.count, local_only=True)

        # Queue them for background processing
        attribute_id = args.attribute or StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_CONTENT
        queued = file_picker.queue_for_background_processing(
            files=files,
            process_func=process_file_with_path,
            priority=2,
            semantic_attribute_id=attribute_id,
        )

        ic(f"Queued {queued} files for background processing")

        # Wait for a while to see some processing happen
        ic("Waiting for processing to complete (10 seconds)...")
        time.sleep(10)

        # Stop the background processing
        file_picker.stop_background_processing(wait=True)
        ic("Background processing stopped")

    else:
        # Default: pick one random file
        ic("Picking one random file")
        file_picker.pick_random_files(process_func=check_mime_type, count=1)


if __name__ == "__main__":
    main()
