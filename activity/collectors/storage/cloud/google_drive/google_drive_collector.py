#!/usr/bin/env python3
"""
Google Drive Activity Collector for Indaleko.

This module collects file activity data from Google Drive using the Drive Activity
API and stores it in a format compatible with Indaleko's activity system.

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
import datetime
import json
import logging
import os
import sys
import uuid

from datetime import UTC, datetime, timedelta
from typing import Any


# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Google Drive API libraries
try:
    import google.auth
    import google.auth.transport.requests

    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    sys.exit(1)

# pylint: disable=wrong-import-position
import contextlib

from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.base import CollectorBase
from activity.collectors.storage.cloud.google_drive.data_models.google_drive_activity_model import (
    GDriveActivityData,
    GDriveActivityType,
    GDriveFileInfo,
    GDriveFileType,
    GDriveUserInfo,
)
from activity.data_model.activity_classification import IndalekoActivityClassification
from utils.misc.directory_management import indaleko_default_config_dir


# pylint: enable=wrong-import-position

# Set up logging
logger = logging.getLogger(__name__)


# Configure logging when debug is enabled
def configure_debug_logging() -> None:
    """Configure logging for debug mode."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug logging enabled for Google Drive Activity Collector")


# OAuth 2.0 scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive.activity.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.activity",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Default collector ID
GDRIVE_COLLECTOR_UUID = "3e7d8f29-7c73-41c5-b3d4-1a9b42567890"


class GoogleDriveActivityCollector(CollectorBase):
    """Google Drive Activity Collector for Indaleko."""

    def __init__(self, **kwargs) -> None:
        """Initialize the Google Drive Activity Collector.

        Args:
            config_path: Path to configuration file
            credentials_file: Path to OAuth credentials file
            token_file: Path to token file
            state_file: Path to state file
            output_file: Path to output file
            direct_to_db: Whether to write directly to the database
            debug: Enable debug logging
        """
        # Do not call super().__init__() as CollectorBase is an ABC

        # Set collector identifier
        self._provider_id = kwargs.get("provider_id", uuid.UUID(GDRIVE_COLLECTOR_UUID))

        # Set up configuration
        self.config_dir = kwargs.get("config_dir", indaleko_default_config_dir)
        self.config_path = kwargs.get(
            "config_path",
            os.path.join(self.config_dir, "gdrive_collector_config.json"),
        )
        self.credentials_file = kwargs.get(
            "credentials_file",
            os.path.join(self.config_dir, "gdrive_client_secrets.json"),
        )
        self.token_file = kwargs.get(
            "token_file",
            os.path.join(self.config_dir, "gdrive_token.json"),
        )

        # Default paths for state and output files
        data_dir = os.path.join(os.environ.get("INDALEKO_ROOT", "."), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        self.state_file = kwargs.get(
            "state_file",
            os.path.join(data_dir, "gdrive_collector_state.json"),
        )
        self.output_file = kwargs.get(
            "output_file",
            os.path.join(data_dir, "gdrive_activities.jsonl"),
        )

        # Database configuration
        self.direct_to_db = kwargs.get("direct_to_db", False)
        self.db_config = kwargs.get("db_config", {"use_default": True})

        # Debug mode
        self.debug = kwargs.get("debug", False)
        if self.debug:
            configure_debug_logging()

        # Load configuration
        self.config = self._load_config()

        # Load state
        self.state = self._load_state()

        # Set up Google Drive API clients
        self.drive_service = None
        self.activity_service = None
        self.credentials = None

        # Initialize API connections
        self._authenticate()
        self._init_apis()

        # Store activities
        self.activities = []

        logger.info("Google Drive Activity Collector initialized")

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            "credentials_file": self.credentials_file,
            "token_file": self.token_file,
            "state_file": self.state_file,
            "output_file": self.output_file,
            "direct_to_db": self.direct_to_db,
            "db_config": self.db_config,
            "collection": {
                "max_results_per_page": 100,
                "max_pages_per_run": 10,
                "include_drive_items": True,
                "include_comments": True,
                "include_shared_drives": True,
                "filter_apps": ["docs", "sheets", "slides", "forms"],
            },
            "scheduling": {
                "interval_minutes": 15,
                "retry_delay_seconds": 60,
                "max_retries": 3,
            },
            "logging": {
                "log_file": os.path.join(
                    os.environ.get("INDALEKO_ROOT", "."),
                    "logs",
                    "gdrive_collector.log",
                ),
                "log_level": "INFO",
            },
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    loaded_config = json.load(f)

                # Update default config with loaded values
                self._deep_update(default_config, loaded_config)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.exception(f"Error loading configuration: {e}")
        else:
            logger.info(
                f"Configuration file not found at {self.config_path}, using defaults",
            )

            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Save default configuration
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default configuration at {self.config_path}")
            except Exception as e:
                logger.exception(f"Error saving default configuration: {e}")

        # Update instance variables from config
        self.credentials_file = default_config["credentials_file"]
        self.token_file = default_config["token_file"]
        self.state_file = default_config["state_file"]
        self.output_file = default_config["output_file"]
        self.direct_to_db = default_config["direct_to_db"]
        self.db_config = default_config["db_config"]

        return default_config

    def _deep_update(self, d: dict[str, Any], u: dict[str, Any]) -> dict[str, Any]:
        """Recursively update a dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d

    def _load_state(self) -> dict[str, Any]:
        """Load collector state from file."""
        default_state = {
            "last_run": datetime.now(UTC).isoformat(),
            "last_page_token": None,
            "last_start_time": None,
            "activities_collected": 0,
            "total_activities_collected": 0,
            "errors": 0,
        }

        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    state = json.load(f)
                logger.info(f"Loaded state from {self.state_file}")
                return state
            except Exception as e:
                logger.exception(f"Error loading state: {e}")

        logger.info(f"No state file found at {self.state_file}, using default state")
        return default_state

    def _save_state(self) -> None:
        """Save collector state to file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.exception(f"Error saving state: {e}")

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API."""
        from activity.collectors.storage.cloud.oauth_utils import GoogleOAuthManager

        # Create OAuth manager
        oauth_manager = GoogleOAuthManager(
            credentials_file=self.credentials_file,
            token_file=self.token_file,
            scopes=SCOPES,
            debug=self.debug,
        )

        # Get credentials
        self.credentials = oauth_manager.load_credentials()
        if not self.credentials:
            raise RuntimeError("Failed to authenticate: No valid credentials obtained")

        # Get user info if available
        try:
            user_info = oauth_manager.get_user_info()
            if user_info:
                logger.info(
                    f"Authenticated as {user_info.get('name')} ({user_info.get('email')})",
                )
        except Exception as e:
            logger.debug(f"Error getting user info: {e}")

        logger.info("Authentication successful")

    def _init_apis(self) -> None:
        """Initialize Google Drive API clients."""
        from activity.collectors.storage.cloud.oauth_utils import GoogleOAuthManager

        # Create OAuth manager
        oauth_manager = GoogleOAuthManager(
            credentials_file=self.credentials_file,
            token_file=self.token_file,
            scopes=SCOPES,
            debug=self.debug,
        )

        try:
            # Initialize Drive API client
            self.drive_service = oauth_manager.build_service("drive", "v3")
            if not self.drive_service:
                raise RuntimeError("Failed to initialize Drive API client")
            logger.info("Initialized Drive API client")

            # Initialize Drive Activity API client
            self.activity_service = oauth_manager.build_service("driveactivity", "v2")
            if not self.activity_service:
                raise RuntimeError("Failed to initialize Drive Activity API client")
            logger.info("Initialized Drive Activity API client")
        except Exception as e:
            logger.exception(f"Error initializing API clients: {e}")
            raise RuntimeError(f"Failed to initialize API clients: {e}")

    def _get_user_info(self, actor: dict[str, Any]) -> GDriveUserInfo:
        """Extract user information from actor data."""
        from activity.collectors.storage.cloud.oauth_utils import GoogleOAuthManager

        user_id = None
        email = None
        display_name = None
        photo_url = None

        # Extract user information based on actor type
        if "user" in actor:
            user = actor["user"]

            if "knownUser" in user:
                known_user = user["knownUser"]
                user_id = known_user.get("personName", "unknown")

                # Try to get additional user info from People API
                if self.credentials and user_id != "unknown":
                    try:
                        # Create OAuth manager
                        oauth_manager = GoogleOAuthManager(
                            credentials_file=self.credentials_file,
                            token_file=self.token_file,
                            scopes=SCOPES,
                            debug=self.debug,
                        )

                        # Get People API service
                        people_service = oauth_manager.build_service("people", "v1")
                        if people_service:
                            profile = (
                                people_service.people()
                                .get(
                                    resourceName=f"people/{user_id}",
                                    personFields="emailAddresses,names,photos",
                                )
                                .execute()
                            )

                            # Extract email
                            if profile.get("emailAddresses"):
                                email = profile["emailAddresses"][0].get("value")

                            # Extract display name
                            if profile.get("names"):
                                display_name = profile["names"][0].get("displayName")

                            # Extract photo URL
                            if profile.get("photos"):
                                photo_url = profile["photos"][0].get("url")
                    except Exception as e:
                        logger.debug(f"Error getting user details: {e}")

            # If we couldn't get email from People API, try to use impersonation email
            if not email and "knownUser" in user and "isCurrentUser" in user["knownUser"]:
                try:
                    about = self.drive_service.about().get(fields="user").execute()
                    email = about["user"].get("emailAddress")
                    display_name = about["user"].get("displayName")
                except Exception as e:
                    logger.debug(f"Error getting current user details: {e}")

        elif "impersonation" in actor:
            imp = actor["impersonation"]
            if "impersonatedUser" in imp:
                imp_user = imp["impersonatedUser"]
                user_id = imp_user.get("knownUser", {}).get("personName", "unknown")

        elif "system" in actor:
            user_id = "system"
            display_name = "Google Drive System"

        elif "anonymous" in actor:
            user_id = "anonymous"
            display_name = "Anonymous User"

        # Create and return user info model
        return GDriveUserInfo(
            user_id=user_id or "unknown",
            email=email,
            display_name=display_name,
            photo_url=photo_url,
        )

    def _get_file_info(self, target: dict[str, Any]) -> GDriveFileInfo | None:
        """Extract file information from target data."""
        # Check if this is a Drive item
        if "driveItem" not in target:
            return None

        drive_item = target["driveItem"]

        # Get basic file information
        file_id = drive_item.get("name", "unknown")
        file_id = file_id.removeprefix("items/")  # Remove 'items/' prefix

        # Get detailed file information using Drive API
        try:
            file_details = (
                self.drive_service.files()
                .get(
                    fileId=file_id,
                    fields="id,name,mimeType,description,size,md5Checksum,version,starred,trashed,"
                    "createdTime,modifiedTime,viewedByMeTime,shared,webViewLink,parents",
                )
                .execute()
            )

            # Get parent folder name if available
            parent_folder_id = None
            parent_folder_name = None

            if file_details.get("parents"):
                parent_folder_id = file_details["parents"][0]
                try:
                    parent = self.drive_service.files().get(fileId=parent_folder_id, fields="name").execute()
                    parent_folder_name = parent.get("name")
                except Exception as e:
                    logger.debug(f"Error getting parent folder name: {e}")

            # Determine file type from MIME type
            mime_type = file_details.get("mimeType", "application/octet-stream")
            file_type = GDriveFileType.UNKNOWN

            mime_to_type = {
                "application/vnd.google-apps.document": GDriveFileType.DOCUMENT,
                "application/vnd.google-apps.spreadsheet": GDriveFileType.SPREADSHEET,
                "application/vnd.google-apps.presentation": GDriveFileType.PRESENTATION,
                "application/vnd.google-apps.form": GDriveFileType.FORM,
                "application/vnd.google-apps.drawing": GDriveFileType.DRAWING,
                "application/vnd.google-apps.folder": GDriveFileType.FOLDER,
                "application/vnd.google-apps.drive-sdk": GDriveFileType.OTHER,
                "application/vnd.google-apps.shortcut": GDriveFileType.SHORTCUT,
                "application/vnd.google-apps.drive": GDriveFileType.SHARED_DRIVE,
                "application/pdf": GDriveFileType.PDF,
            }

            if mime_type in mime_to_type:
                file_type = mime_to_type[mime_type]
            elif mime_type.startswith("image/"):
                file_type = GDriveFileType.IMAGE
            elif mime_type.startswith("video/"):
                file_type = GDriveFileType.VIDEO
            elif mime_type.startswith("audio/"):
                file_type = GDriveFileType.AUDIO

            # Create and return file info model
            return GDriveFileInfo(
                file_id=file_id,
                name=file_details.get("name", "Unknown"),
                mime_type=mime_type,
                file_type=file_type,
                description=file_details.get("description"),
                size=file_details.get("size"),
                md5_checksum=file_details.get("md5Checksum"),
                version=file_details.get("version"),
                starred=file_details.get("starred"),
                trashed=file_details.get("trashed"),
                created_time=file_details.get("createdTime"),
                modified_time=file_details.get("modifiedTime"),
                viewed_time=file_details.get("viewedByMeTime"),
                shared=file_details.get("shared"),
                web_view_link=file_details.get("webViewLink"),
                parent_folder_id=parent_folder_id,
                parent_folder_name=parent_folder_name,
            )
        except HttpError as e:
            logger.warning(f"Error getting file details (ID: {file_id}): {e}")

            # Return minimal file info
            return GDriveFileInfo(
                file_id=file_id,
                name=f"Unknown File ({file_id})",
                mime_type="application/octet-stream",
                file_type=GDriveFileType.UNKNOWN,
            )

    def _determine_activity_type(
        self,
        action_detail: dict[str, Any],
    ) -> GDriveActivityType:
        """Determine activity type from action details."""
        # Check each action type
        if "create" in action_detail:
            return GDriveActivityType.CREATE
        if "edit" in action_detail:
            return GDriveActivityType.EDIT
        if "delete" in action_detail:
            return GDriveActivityType.DELETE
        if "move" in action_detail:
            return GDriveActivityType.MOVE
        if "rename" in action_detail:
            return GDriveActivityType.RENAME
        if "comment" in action_detail:
            return GDriveActivityType.COMMENT
        if "dlpChange" in action_detail:
            # Data Loss Prevention changes usually involve sharing settings
            return GDriveActivityType.SHARE
        if "permissionChange" in action_detail:
            return GDriveActivityType.SHARE
        if "reference" in action_detail:
            if "copy" in action_detail["reference"]:
                return GDriveActivityType.COPY
        elif "restore" in action_detail:
            return GDriveActivityType.RESTORE
        elif "trash" in action_detail:
            return GDriveActivityType.TRASH

        # Fall back to unknown
        return GDriveActivityType.UNKNOWN

    def _extract_activity_details(
        self,
        activity: dict[str, Any],
    ) -> GDriveActivityData | None:
        """Extract activity details from API response."""
        try:
            # Get timestamp
            timestamp_str = activity.get("timestamp")
            timestamp = datetime.fromisoformat(timestamp_str)

            # Get actors (users) involved
            actors = activity.get("actors", [])
            if not actors:
                logger.debug(f"No actors found for activity: {activity}")
                return None

            # Get primary actor
            primary_actor = actors[0]
            user_info = self._get_user_info(primary_actor)

            # Get targets (files) involved
            targets = activity.get("targets", [])
            if not targets:
                logger.debug(f"No targets found for activity: {activity}")
                return None

            # Get primary target
            primary_target = targets[0]
            file_info = self._get_file_info(primary_target)
            if not file_info:
                logger.debug(f"No file info for target: {primary_target}")
                return None

            # Get action details
            action_details = []
            if "primaryActionDetail" in activity:
                action_details.append(activity["primaryActionDetail"])
            if "actions" in activity:
                for action in activity["actions"]:
                    if "detail" in action:
                        action_details.append(action["detail"])

            if not action_details:
                logger.debug(f"No action details found for activity: {activity}")
                return None

            # Determine activity type from primary action
            activity_type = self._determine_activity_type(action_details[0])

            # Extract additional metadata
            destination_folder_id = None
            destination_folder_name = None
            previous_file_name = None
            comment_id = None
            comment_content = None
            shared_with = None
            permission_changes = None

            for detail in action_details:
                # Handle move
                if "move" in detail and activity_type == GDriveActivityType.MOVE:
                    move_details = detail["move"]
                    if move_details.get("addedParents"):
                        parent = move_details["addedParents"][0]
                        if "driveItem" in parent:
                            drive_item = parent["driveItem"]
                            destination_folder_id = drive_item.get("name")
                            destination_folder_id = destination_folder_id.removeprefix("items/")

                            # Get folder name
                            try:
                                folder = (
                                    self.drive_service.files()
                                    .get(fileId=destination_folder_id, fields="name")
                                    .execute()
                                )
                                destination_folder_name = folder.get("name")
                            except Exception as e:
                                logger.debug(
                                    f"Error getting destination folder name: {e}",
                                )

                # Handle rename
                if "rename" in detail and activity_type == GDriveActivityType.RENAME:
                    rename_details = detail["rename"]
                    if "oldTitle" in rename_details:
                        previous_file_name = rename_details["oldTitle"]

                # Handle comment
                if "comment" in detail and activity_type == GDriveActivityType.COMMENT:
                    comment_details = detail["comment"]
                    if "post" in comment_details:
                        post = comment_details["post"]
                        comment_content = post.get("value")

                    # Try to get comment ID
                    if "assignment" in comment_details:
                        comment_id = comment_details["assignment"].get("subtype")

                # Handle sharing
                if "permissionChange" in detail and activity_type == GDriveActivityType.SHARE:
                    perm_details = detail["permissionChange"]
                    if "addedPermissions" in perm_details:
                        added_perms = perm_details["addedPermissions"]

                        if not shared_with:
                            shared_with = []

                        if not permission_changes:
                            permission_changes = {}

                        for perm in added_perms:
                            if "user" in perm:
                                shared_user = self._get_user_info(
                                    {"user": perm["user"]},
                                )
                                shared_with.append(shared_user)

                            if "role" in perm:
                                role = perm["role"]
                                if shared_user.email:
                                    permission_changes[shared_user.email] = role

            # Create activity classification
            activity_classification = self._classify_activity(
                activity_type=activity_type,
                file_info=file_info,
            )

            # Create activity data
            return GDriveActivityData(
                activity_id=activity.get("actionId", str(uuid.uuid4())),
                activity_type=activity_type,
                timestamp=timestamp,
                user=user_info,
                file=file_info,
                destination_folder_id=destination_folder_id,
                destination_folder_name=destination_folder_name,
                previous_file_name=previous_file_name,
                comment_id=comment_id,
                comment_content=comment_content,
                shared_with=shared_with,
                permission_changes=permission_changes,
                raw_data=activity if self.debug else None,
                activity_classification=activity_classification,
            )
        except Exception as e:
            logger.exception(f"Error extracting activity details: {e}")
            if self.debug:
                logger.debug(f"Activity data: {activity}")
            return None

    def _classify_activity(
        self,
        activity_type: GDriveActivityType,
        file_info: GDriveFileInfo,
    ) -> IndalekoActivityClassification:
        """Classify activity along multiple dimensions."""
        # Default classification values
        ambient = 0.0
        consumption = 0.0
        productivity = 0.0
        research = 0.0
        social = 0.0
        creation = 0.0

        # Classify based on activity type
        if activity_type == GDriveActivityType.CREATE:
            creation = 0.8
            productivity = 0.6
        elif activity_type == GDriveActivityType.EDIT:
            productivity = 0.7
            creation = 0.5
        elif activity_type == GDriveActivityType.VIEW:
            consumption = 0.7
            ambient = 0.3
        elif activity_type == GDriveActivityType.COMMENT:
            social = 0.7
            productivity = 0.4
        elif activity_type == GDriveActivityType.SHARE:
            social = 0.8
            productivity = 0.3

        # Adjust based on file type
        if file_info.file_type == GDriveFileType.DOCUMENT:
            research += 0.2
            if "proposal" in file_info.name.lower() or "report" in file_info.name.lower():
                research += 0.3
        elif file_info.file_type == GDriveFileType.SPREADSHEET:
            productivity += 0.2
        elif file_info.file_type == GDriveFileType.PRESENTATION:
            productivity += 0.2
            social += 0.1
        elif file_info.file_type == GDriveFileType.IMAGE:
            creation += 0.1
            consumption += 0.2
        elif file_info.file_type == GDriveFileType.VIDEO:
            consumption += 0.3
            ambient += 0.2

        # Create classification
        return IndalekoActivityClassification(
            ambient=min(1.0, ambient),
            consumption=min(1.0, consumption),
            productivity=min(1.0, productivity),
            research=min(1.0, research),
            social=min(1.0, social),
            creation=min(1.0, creation),
        )

    def _get_activities(
        self,
        start_time: str | None = None,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Get activities from Drive Activity API."""
        # Prepare request body according to the API specification
        # See: https://developers.google.com/drive/activity/v2/reference/rest/v2/activity/query

        # Start with basic request
        request_body = {}

        # Set page size
        request_body["pageSize"] = self.config["collection"]["max_results_per_page"]

        # Add ancestorName field (required)
        request_body["ancestorName"] = "items/root"

        # Add time filter if provided
        # Format according to https://developers.google.com/drive/activity/v2/reference/rest/v2/activity/query
        if start_time:
            # First convert to RFC 3339 format required by the API
            if isinstance(start_time, str):
                # Parse the string to datetime if necessary
                try:
                    dt = datetime.fromisoformat(start_time)
                    # Convert back to RFC 3339 string format
                    start_time_rfc = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    # If parsing fails, use the original string
                    start_time_rfc = start_time
            else:
                # If already a datetime, convert to RFC 3339 string
                start_time_rfc = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            # Create the filter based on the Drive Activity API specification
            request_body["filter"] = f'time > "{start_time_rfc}"'
        else:
            # Default to last 7 days if no start time provided
            seven_days_ago = datetime.now(UTC) - timedelta(days=7)
            start_time_rfc = seven_days_ago.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            request_body["filter"] = f'time > "{start_time_rfc}"'

        logger.debug(f"Time filter: {request_body['filter']}")

        # Add page token if provided
        if page_token:
            request_body["pageToken"] = page_token

        try:
            # Log request for debugging
            logger.debug(f"Drive Activity API request: {json.dumps(request_body)}")

            # Execute API request
            response = self.activity_service.activity().query(body=request_body).execute()

            # Return activities and next page token
            activities = response.get("activities", [])
            next_page_token = response.get("nextPageToken")

            logger.debug(
                f"Received {len(activities)} activities from Drive Activity API",
            )
            return activities, next_page_token
        except HttpError as e:
            logger.exception(f"Error querying Drive Activity API: {e}")
            return [], None

    def collect_data(self) -> bool:
        """Collect Google Drive activity data."""
        # Initialize variables
        start_time = self.state.get("last_start_time")
        page_token = None
        page_count = 0
        max_pages = self.config["collection"]["max_pages_per_run"]
        activity_count = 0

        # If no start time available, use a week ago
        if not start_time:
            start_time = (datetime.now(UTC) - timedelta(days=7)).isoformat()

        logger.info(f"Collecting Google Drive activities since {start_time}")

        # Get activities page by page
        while page_count < max_pages:
            # Get activities
            activities, next_page_token = self._get_activities(start_time, page_token)

            # Process activities
            for activity in activities:
                activity_data = self._extract_activity_details(activity)
                if activity_data:
                    self.activities.append(activity_data)
                    activity_count += 1

            # Update page count
            page_count += 1

            # Break if no more pages
            if not next_page_token:
                logger.info("No more activity pages to fetch")
                break

            # Update page token for next page
            page_token = next_page_token
            logger.debug(f"Fetched page {page_count}, next page token: {page_token}")

        # Update state
        self.state["last_run"] = datetime.now(UTC).isoformat()
        self.state["last_page_token"] = page_token
        self.state["last_start_time"] = self.activities[0].timestamp.isoformat() if self.activities else start_time
        self.state["activities_collected"] = activity_count
        self.state["total_activities_collected"] += activity_count

        # Save state
        self._save_state()

        logger.info(f"Collected {activity_count} activities")
        return True

    def store_data(self) -> bool:
        """Store collected activities."""
        if not self.activities:
            logger.info("No activities to store")
            return True

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        # Convert to storage activity model
        storage_activities = []
        for activity in self.activities:
            storage_activities.append(activity.to_storage_activity())

        try:
            # Write to JSONL file
            with open(self.output_file, "a", encoding="utf-8") as f:
                for activity in self.activities:
                    f.write(activity.model_dump_json() + "\n")

            logger.info(
                f"Stored {len(self.activities)} activities to {self.output_file}",
            )

            # If direct DB writing is enabled, write to database
            if self.direct_to_db:
                try:
                    # Import late to avoid circular import
                    from activity.recorders.storage.cloud.gdrive.recorder import (
                        GoogleDriveActivityRecorder,
                    )

                    # Create recorder
                    recorder = GoogleDriveActivityRecorder(
                        collector=self,
                        auto_connect=True,
                        debug=self.debug,
                    )

                    # Store activities
                    recorder.store_activities(storage_activities)

                    logger.info(f"Stored {len(self.activities)} activities to database")
                except ImportError as e:
                    logger.exception(
                        f"Recorder not found: {e}. Make sure activity/recorders/storage/cloud/gdrive/recorder.py exists",
                    )
                except Exception as e:
                    logger.exception(f"Error storing activities in database: {e}")
        except Exception as e:
            logger.exception(f"Error storing activities: {e}")
            return False

        return True

    def process_data(self) -> bool:
        """Process collected data."""
        # For this collector, processing is handled during collection
        return True

    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get characteristics of this collector."""
        logger.debug("Getting collector characteristics")

        # Initialize characteristics object
        characteristics = []

        # Add storage characteristic
        storage_char = ActivityDataCharacteristics()
        characteristics.append(storage_char)

        # Return characteristics
        return characteristics

    def get_collector_name(self) -> str:
        """Get the name of this collector."""
        return "Google Drive Activity Collector"

    def get_provider_id(self) -> uuid.UUID:
        """Get the provider ID for this collector."""
        return self._provider_id

    def retrieve_data(self, data_id: uuid.UUID) -> dict[str, Any]:
        """Retrieve specific data by ID."""
        logger.debug(f"Retrieving data for ID: {data_id}")
        # Convert UUID to string if needed
        identifier = str(data_id)

        # Find activity by ID
        for activity in self.activities:
            if activity.activity_id == identifier:
                return activity.model_dump()

        # If not found, return empty dict
        logger.warning(f"Data not found for ID: {data_id}")
        return {}

    def get_cursor(self, activity_context: uuid.UUID | None = None) -> uuid.UUID:
        """Get a position cursor for the data."""
        logger.debug(f"Getting cursor for activity context: {activity_context}")
        # Return a UUID based on the last page token
        token = self.state.get("last_page_token")
        if token:
            # Create a deterministic UUID from the token
            namespace = uuid.UUID(
                "3e7d8f29-7c73-41c5-b3d4-1a9b42567890",
            )  # Our collector UUID
            cursor_uuid = uuid.uuid5(namespace, token)
        else:
            # Return a nil UUID if no token
            cursor_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")

        return cursor_uuid

    def cache_duration(self) -> int:
        """Report how long data can be cached."""
        # Cache for 1 hour (in seconds)
        return 3600

    def get_description(self) -> str:
        """Return a human-readable description."""
        return "Collects activity data from Google Drive"

    def get_json_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the data."""
        return GDriveActivityData.model_json_schema()

    def run(self) -> bool:
        """Run the collector."""
        success = False
        try:
            # Collect data
            if self.collect_data():
                # Process data
                if self.process_data():
                    # Store data
                    success = self.store_data()
        except Exception as e:
            logger.exception(f"Error running collector: {e}")
            if self.debug:
                logger.exception("Detailed error:")
            success = False

            # Update error count in state
            self.state["errors"] = self.state.get("errors", 0) + 1
            self._save_state()

        logger.info(f"Collector run {'successful' if success else 'failed'}")
        return success


def main() -> None:
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Google Drive Activity Collector for Indaleko",
    )
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--output", help="Output file path for activities")
    parser.add_argument("--credentials", help="Path to OAuth credentials file")
    parser.add_argument("--token", help="Path to token file")
    parser.add_argument("--state", help="Path to state file")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Perform full collection instead of incremental",
    )
    parser.add_argument(
        "--direct-to-db",
        action="store_true",
        help="Write directly to database",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Prepare kwargs
    kwargs = {}
    if args.config:
        kwargs["config_path"] = args.config
    if args.output:
        kwargs["output_file"] = args.output
    if args.credentials:
        kwargs["credentials_file"] = args.credentials
    if args.token:
        kwargs["token_file"] = args.token
    if args.state:
        kwargs["state_file"] = args.state
    if args.direct_to_db:
        kwargs["direct_to_db"] = True
    if args.debug:
        kwargs["debug"] = True
        configure_debug_logging()

    # If full collection requested, reset state
    if args.full:
        state_file = kwargs.get("state_file")
        if not state_file:
            config_path = kwargs.get("config_path")
            if config_path and os.path.exists(config_path):
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                    state_file = config.get("state_file")

        if state_file and os.path.exists(state_file):
            with contextlib.suppress(Exception):
                os.remove(state_file)

    # Create and run collector
    collector = GoogleDriveActivityCollector(**kwargs)
    success = collector.run()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
