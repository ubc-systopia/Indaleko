"""
Dropbox Storage Activity Collector for Indaleko.

This module provides a collector for Dropbox storage activities, monitoring
file operations within a Dropbox account and creating standardized storage
activity records for them.

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

import datetime
import json
import logging
import os
import socket
import sys
import time
import uuid

from pathlib import Path
from urllib.parse import urlencode

import requests

import dropbox


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.storage.base import StorageActivityCollector
from activity.collectors.storage.data_models.storage_activity_data_model import (
    DropboxStorageActivityData,
    StorageActivityMetadata,
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)
from utils.misc.directory_management import indaleko_default_config_dir


# pylint: enable=wrong-import-position


class DropboxStorageActivityCollector(StorageActivityCollector):
    """
    Collector for Dropbox storage activities.

    This collector monitors file operations in a Dropbox account and creates
    standardized storage activity records for them.
    """

    # Configuration constants
    DROPBOX_PLATFORM = "Dropbox"
    DROPBOX_CONFIG_FILE = "dropbox_config.json"
    DROPBOX_TOKEN_FILE = "dropbox_token.json"
    DROPBOX_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"

    def __init__(self, **kwargs):
        """
        Initialize the Dropbox storage activity collector.

        Args:
            config_dir: Directory for configuration and token files
            webhooks_enabled: Whether to use webhooks for real-time monitoring
            monitor_interval: How often to poll for changes if webhooks not used
            path: Root path to monitor in Dropbox (default: "/")
            auto_start: Whether to start monitoring automatically
            debug: Enable debug logging
        """
        # Initialize with provider-specific values
        kwargs["name"] = kwargs.get("name", "Dropbox Storage Activity Collector")
        kwargs["provider_id"] = kwargs.get(
            "provider_id",
            uuid.UUID("8a4f6b23-9c57-4e31-b78d-f5e9c7a1b2d3"),
        )
        kwargs["provider_type"] = StorageProviderType.DROPBOX
        kwargs["description"] = kwargs.get(
            "description",
            "Collects storage activities from Dropbox",
        )

        # Call parent initializer
        super().__init__(**kwargs)

        # Dropbox-specific configuration
        self._config_dir = kwargs.get("config_dir", indaleko_default_config_dir)
        self._webhook_enabled = kwargs.get("webhooks_enabled", False)
        self._monitor_interval = kwargs.get("monitor_interval", 60.0)  # seconds
        self._path = kwargs.get("path", "")  # Root of Dropbox by default
        self._dropbox_config_file = str(
            Path(self._config_dir) / self.DROPBOX_CONFIG_FILE,
        )
        self._dropbox_token_file = str(Path(self._config_dir) / self.DROPBOX_TOKEN_FILE)

        # Dropbox client objects
        self._dropbox_config = None
        self._dropbox_credentials = None
        self._dbx = None
        self._user_info = None
        self._cursor = None

        # Activity tracking
        self._file_operations = {}  # Track file operations for correlation
        self._last_check_time = None

        # Initialize Dropbox connection
        self._load_dropbox_config()
        self._load_dropbox_credentials()

        # If we don't have credentials, we need to get them
        if self._dropbox_credentials is None:
            self._query_user_for_credentials()

        # Refresh token if needed and initialize the Dropbox client
        if self._dropbox_credentials is not None:
            if self._is_token_expired():
                self._refresh_access_token()
            self._dbx = dropbox.Dropbox(self._dropbox_credentials["token"])
            self._user_info = self._dbx.users_get_current_account()

            # Set up metadata
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.DROPBOX,
                provider_name=self._name,
                source_machine=socket.gethostname(),
                storage_location=f"Dropbox:{self._user_info.email}",
            )

        # Start monitoring if requested
        if kwargs.get("auto_start", False):
            self.start_monitoring()

    def start_monitoring(self):
        """Start monitoring Dropbox for changes."""
        if self._active:
            return

        self._active = True
        self._stop_event.clear()

        # Initialize the last check time
        self._last_check_time = datetime.datetime.now()

        # Start the polling thread if not using webhooks
        if not self._webhook_enabled:
            # Only start polling thread if not already running
            if self._processing_thread is None or not self._processing_thread.is_alive():
                self._processing_thread = self._create_thread(self._poll_for_changes)
                self._processing_thread.start()
                self._logger.info("Started Dropbox polling thread")
        else:
            # Set up webhooks for real-time monitoring
            # Note: Webhook implementation details would be added here
            self._logger.info("Dropbox webhooks not yet implemented")

    def stop_monitoring(self):
        """Stop monitoring Dropbox for changes."""
        if not self._active:
            return

        # Signal all threads to stop
        self._stop_event.set()
        self._active = False

        # Wait for processing thread to stop
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
            self._processing_thread = None

        self._logger.info("Stopped Dropbox monitoring")

    def _poll_for_changes(self):
        """Poll for changes in Dropbox at regular intervals."""
        while not self._stop_event.is_set():
            try:
                # Check for changes since last poll
                self._check_for_changes()

                # Sleep until next check
                time.sleep(self._monitor_interval)
            except Exception as e:
                self._logger.error(f"Error during Dropbox polling: {e}")
                time.sleep(self._monitor_interval * 2)  # Wait longer after error

    def _check_for_changes(self):
        """Check for changes in Dropbox since last check."""
        try:
            # If we have a cursor, use it to get changes
            if self._cursor:
                result = self._dbx.files_list_folder_continue(self._cursor)
            else:
                # Otherwise, get all files and save the cursor for next time
                result = self._dbx.files_list_folder(
                    self._path,
                    recursive=True,
                    include_deleted=True,
                    include_media_info=True,
                )

            # Save the cursor for next time
            self._cursor = result.cursor

            # Process each entry
            for entry in result.entries:
                # Create activity data for this entry
                self._process_dropbox_entry(entry)

        except dropbox.exceptions.ApiError as e:
            if "expired_access_token" in str(e):
                self._logger.info("Refreshing access token")
                self._refresh_access_token()
                self._dbx = dropbox.Dropbox(self._dropbox_credentials["token"])
            else:
                self._logger.error(f"Dropbox API error: {e}")

    def _process_dropbox_entry(self, entry):
        """
        Process a Dropbox entry and create an activity record.

        Args:
            entry: A Dropbox entry object
        """
        # Determine activity type based on entry type
        activity_type = self._determine_activity_type(entry)

        # Skip if we can't determine activity type
        if activity_type is None:
            return

        # Extract basic information from the entry
        try:
            file_name = getattr(entry, "name", "")
            file_path = getattr(entry, "path_display", "")

            # Determine if this is a directory
            is_directory = False
            if hasattr(entry, "FolderMetadata") or isinstance(
                entry,
                dropbox.files.FolderMetadata,
            ):
                is_directory = True
                item_type = StorageItemType.DIRECTORY
            else:
                item_type = StorageItemType.FILE

            # Get Dropbox-specific fields
            dropbox_file_id = getattr(entry, "id", "")
            revision = getattr(entry, "rev", None)

            # Determine shared folder information if applicable
            shared_folder_id = None
            if hasattr(entry, "sharing_info"):
                sharing_info = getattr(entry, "sharing_info", None)
                if sharing_info and hasattr(sharing_info, "shared_folder_id"):
                    shared_folder_id = getattr(sharing_info, "shared_folder_id", None)

            # Create the activity data
            activity_data = DropboxStorageActivityData(
                timestamp=datetime.datetime.now(datetime.UTC),
                activity_type=activity_type,
                item_type=item_type,
                file_name=file_name,
                file_path=file_path,
                provider_type=StorageProviderType.DROPBOX,
                provider_id=self._provider_id,
                is_directory=is_directory,
                cloud_item_id=dropbox_file_id,
                dropbox_file_id=dropbox_file_id,
                revision=revision,
                shared_folder_id=shared_folder_id,
                mime_type=(getattr(entry, "content_type", None) if hasattr(entry, "content_type") else None),
                size=getattr(entry, "size", None) if hasattr(entry, "size") else None,
                web_url=getattr(entry, "url", None) if hasattr(entry, "url") else None,
                created_time=(
                    self._parse_datetime(getattr(entry, "client_modified", None))
                    if hasattr(entry, "client_modified")
                    else None
                ),
                modified_time=(
                    self._parse_datetime(getattr(entry, "server_modified", None))
                    if hasattr(entry, "server_modified")
                    else None
                ),
            )

            # Add the activity to our collection
            self.add_activity(activity_data)

        except Exception as e:
            self._logger.error(f"Error processing Dropbox entry: {e}")

    def _determine_activity_type(self, entry) -> StorageActivityType | None:
        """
        Determine the activity type based on the Dropbox entry.

        Args:
            entry: A Dropbox entry object

        Returns:
            The determined activity type or None if can't be determined
        """
        # Check for deleted entries
        if hasattr(entry, "DeletedMetadata") or isinstance(
            entry,
            dropbox.files.DeletedMetadata,
        ):
            return StorageActivityType.DELETE

        # Check entry type
        if isinstance(entry, dropbox.files.FileMetadata):
            # For file metadata, we need to check if it's new or modified
            # We'll use revision information if available
            if hasattr(entry, "id") and entry.id in self._file_operations:
                # We've seen this file before, so it's a modification
                return StorageActivityType.MODIFY
            else:
                # First time we've seen this file, so it's a creation
                if hasattr(entry, "id"):
                    self._file_operations[entry.id] = {
                        "last_rev": getattr(entry, "rev", None),
                        "last_modified": getattr(entry, "server_modified", None),
                    }
                return StorageActivityType.CREATE

        elif isinstance(entry, dropbox.files.FolderMetadata):
            # For folders, we'll treat them as creations
            return StorageActivityType.CREATE

        # If we can't determine, return None
        return None

    def collect_data(self) -> None:
        """
        Collect storage activity data from Dropbox.

        This method starts monitoring if not already active and returns
        currently collected activities.
        """
        if not self._active:
            self.start_monitoring()

        # Return current activities through the get_activities() method

    def _load_dropbox_config(self) -> None:
        """
        Load the Dropbox configuration from the config file.
        """
        if not os.path.exists(self._dropbox_config_file):
            self._logger.warning(
                f"Config file {self._dropbox_config_file} does not exist",
            )
            return

        try:
            with open(self._dropbox_config_file, encoding="utf-8") as f:
                self._dropbox_config = json.load(f)

            # Validate config
            if "app_key" not in self._dropbox_config or "app_secret" not in self._dropbox_config:
                self._logger.warning(
                    "Invalid Dropbox config file: missing app_key or app_secret",
                )
                self._dropbox_config = None
        except Exception as e:
            self._logger.error(f"Error loading Dropbox config: {e}")
            self._dropbox_config = None

    def _load_dropbox_credentials(self) -> None:
        """
        Load the Dropbox credentials from the token file.
        """
        try:
            if not os.path.exists(self._dropbox_token_file):
                self._logger.warning(
                    f"Token file {self._dropbox_token_file} does not exist",
                )
                self._dropbox_credentials = None
                return

            with open(self._dropbox_token_file, encoding="utf-8-sig") as f:
                self._dropbox_credentials = json.load(f)

            self._logger.debug("Loaded Dropbox credentials")
        except Exception as e:
            self._logger.error(f"Error loading Dropbox credentials: {e}")
            self._dropbox_credentials = None

    def _store_dropbox_credentials(self) -> None:
        """
        Store the Dropbox credentials in the token file.
        """
        if self._dropbox_credentials is None:
            self._logger.warning("No credentials to store")
            return

        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self._dropbox_token_file), exist_ok=True)

            with open(self._dropbox_token_file, "w", encoding="utf-8-sig") as f:
                json.dump(self._dropbox_credentials, f, indent=4)

            self._logger.debug("Stored Dropbox credentials")
        except Exception as e:
            self._logger.error(f"Error storing Dropbox credentials: {e}")

    def _query_user_for_credentials(self) -> None:
        """
        Query the user for Dropbox credentials.

        This will guide the user through the OAuth flow to authorize the application.
        """
        if self._dropbox_config is None:
            self._logger.error("No Dropbox config found")
            return

        try:
            # Set up OAuth flow
            params = {
                "response_type": "code",
                "client_id": self._dropbox_config["app_key"],
                "token_access_type": "offline",
            }
            auth_request_url = f"{self.DROPBOX_AUTH_URL}?{urlencode(params)}"

            # Guide the user through the authorization process
            print("\n=== Dropbox Authorization ===")
            print("Please visit the following URL to authorize this application:")
            print(auth_request_url)
            auth_code = input("Enter the authorization code here: ").strip()

            # Exchange the auth code for tokens
            data = {
                "code": auth_code,
                "grant_type": "authorization_code",
                "client_id": self._dropbox_config["app_key"],
                "client_secret": self._dropbox_config["app_secret"],
            }

            response = requests.post(self.DROPBOX_TOKEN_URL, data=data, timeout=10)

            # Handle the response
            response.raise_for_status()
            response_data = response.json()

            # Validate response data
            if "expires_in" not in response_data:
                self._logger.error("No expires_in in response")
                return

            if "access_token" not in response_data and "refresh_token" not in response_data:
                self._logger.error(f"Invalid response from Dropbox: {response_data}")
                return

            # Store the credentials
            self._dropbox_credentials = {
                "expires_at": time.time() + response_data["expires_in"],
            }

            if "access_token" in response_data:
                self._dropbox_credentials["token"] = response_data["access_token"]

            if "refresh_token" in response_data:
                self._dropbox_credentials["refresh_token"] = response_data["refresh_token"]

            # Save the credentials
            self._store_dropbox_credentials()

            print("Dropbox authorization successful!")

        except Exception as e:
            self._logger.error(f"Error during Dropbox authorization: {e}")

    def _is_token_expired(self) -> bool:
        """
        Check if the access token is expired.

        Returns:
            True if the token is expired, False otherwise
        """
        if self._dropbox_credentials is None:
            return True

        if "expires_at" not in self._dropbox_credentials:
            return True

        # Add some buffer to ensure we refresh before the actual expiration
        buffer_time = 60  # seconds

        return time.time() + buffer_time > self._dropbox_credentials["expires_at"]

    def _refresh_access_token(self) -> None:
        """
        Refresh the access token using the refresh token.
        """
        if self._dropbox_credentials is None:
            self._logger.error("No credentials to refresh")
            return

        if "refresh_token" not in self._dropbox_credentials:
            self._logger.error("No refresh token available")
            return

        if self._dropbox_config is None:
            self._logger.error("No Dropbox config found")
            return

        try:
            # Prepare the request
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._dropbox_credentials["refresh_token"],
                "client_id": self._dropbox_config["app_key"],
                "client_secret": self._dropbox_config["app_secret"],
            }

            # Make the request
            response = requests.post(self.DROPBOX_TOKEN_URL, data=data, timeout=10)

            # Handle the response
            response.raise_for_status()
            response_data = response.json()

            # Update the credentials
            if "access_token" in response_data and "expires_in" in response_data:
                self._dropbox_credentials["token"] = response_data["access_token"]
                self._dropbox_credentials["expires_at"] = time.time() + response_data["expires_in"]

                # Save the updated credentials
                self._store_dropbox_credentials()

                self._logger.info("Dropbox access token refreshed")
            else:
                self._logger.error(
                    f"Invalid response during token refresh: {response_data}",
                )

        except Exception as e:
            self._logger.error(f"Error refreshing Dropbox access token: {e}")

    def _parse_datetime(self, dt_str) -> datetime.datetime | None:
        """
        Parse a datetime string into a datetime object.

        Args:
            dt_str: Datetime string to parse

        Returns:
            Parsed datetime with timezone, or None if parsing fails
        """
        if not dt_str:
            return None

        try:
            if isinstance(dt_str, datetime.datetime):
                # If it's already a datetime, ensure it has timezone
                if dt_str.tzinfo is None:
                    return dt_str.replace(tzinfo=datetime.UTC)
                return dt_str

            # Parse the string
            dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

            # Ensure timezone is set
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.UTC)

            return dt
        except Exception as e:
            self._logger.error(f"Error parsing datetime: {e}")
            return None


# Test functionality if module is run directly
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create a collector
    collector = DropboxStorageActivityCollector(auto_start=True, debug=True)

    # Monitor for some time
    try:
        import time

        print(
            f"Monitoring Dropbox activities for {collector._monitor_interval * 5} seconds...",
        )
        time.sleep(collector._monitor_interval * 5)

        # Get collected activities
        activities = collector.get_activities()
        print(f"Collected {len(activities)} activities")

        # Print summary by type
        activity_types = {}
        for activity in activities:
            activity_type = activity.activity_type
            if activity_type not in activity_types:
                activity_types[activity_type] = 0
            activity_types[activity_type] += 1

        print("Activities by type:")
        for activity_type, count in activity_types.items():
            print(f"  {activity_type}: {count}")

    except KeyboardInterrupt:
        print("Monitoring interrupted")
    finally:
        # Stop monitoring
        collector.stop_monitoring()
