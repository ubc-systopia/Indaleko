#!/usr/bin/env python3
"""
Google Drive Activity Collector Example for Indaleko.

This example demonstrates the collection of Google Drive activity data
and showcases the OAuth authentication process in both Windows and WSL environments.

IMPORTANT: This is an updated example that uses the new reorganized code structure.
Use this example rather than the older gdrive_example.py.

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
import builtins
import contextlib
import logging
import os
import platform
import sys

from datetime import UTC, datetime, timedelta


# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import Indaleko components
try:
    from activity.collectors.storage.cloud.google_drive.google_drive_collector import (
        GoogleDriveActivityCollector,
    )
    from activity.recorders.storage.cloud.google_drive.recorder import (
        GoogleDriveActivityRecorder,
    )
except ImportError as e:
    logger.exception(f"Error importing Indaleko components: {e}")
    logger.exception(
        "Make sure the virtual environment is activated and all dependencies are installed.",
    )
    logger.exception(f"Python path: {sys.path}")
    sys.exit(1)


def detect_environment() -> str:
    """Detect whether we're running in Windows, native Linux, or WSL."""
    # Check for WSL (Windows Subsystem for Linux)
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                return "WSL"
    except:
        pass

    # Check platform
    if platform.system() == "Windows":
        return "Windows"
    if platform.system() == "Linux":
        return "Linux"
    if platform.system() == "Darwin":
        return "macOS"
    return "Unknown"


def display_file_details(file_info) -> None:
    """Display detailed information about a file."""
    # Format timestamps

    if file_info.created_time:
        try:
            created_dt = datetime.fromisoformat(
                file_info.created_time,
            )
            created_dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

    if file_info.modified_time:
        try:
            modified_dt = datetime.fromisoformat(
                file_info.modified_time,
            )
            modified_dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass


    if file_info.web_view_link:
        pass

    # Print file size in human-readable format if available
    if file_info.size:
        size_bytes = int(file_info.size)
        if size_bytes < 1024:
            pass
        elif size_bytes < 1024 * 1024:
            f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"



def display_activity(activity, detailed=False) -> None:
    """Display activity details in a human-readable format."""
    # Format timestamp
    timestamp = activity.timestamp
    if isinstance(timestamp, str):
        with contextlib.suppress(builtins.BaseException):
            timestamp = datetime.fromisoformat(timestamp)

    if isinstance(timestamp, datetime):
        timestamp.strftime("%Y-%m-%d %H:%M:%S")
    else:
        str(timestamp)

    # Get user info

    # Get file info

    # Get activity type name
    activity_type = activity.activity_type.name

    # Print basic activity info

    # Print detailed info if requested
    if detailed:

        # Show additional info based on activity type
        if activity_type in {"RENAME", "MOVE"} or activity_type == "COMMENT":
            pass
        elif activity_type == "SHARE":
            if activity.shared_with:
                ", ".join(
                    [f"{u.display_name or u.email or u.user_id}" for u in activity.shared_with],
                )

            if activity.permission_changes:
                for _email, _role in activity.permission_changes.items():
                    pass

        # Print primary classification dimension
        if activity.activity_classification:
            class_dict = activity.activity_classification.model_dump()
            primary_dim = max(class_dict.items(), key=lambda x: x[1])[0]
            class_dict[primary_dim]



def main() -> None:
    """Main entry point for the Google Drive Activity Collector example."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Google Drive Activity Collector Example",
    )
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--credentials", help="Path to OAuth credentials file")
    parser.add_argument("--token", help="Path to token file")
    parser.add_argument("--state", help="Path to state file")
    parser.add_argument("--output", help="Output file path for activities")
    parser.add_argument(
        "--to-db",
        action="store_true",
        help="Store activities in database",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of history to collect",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of activities to display",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed activity information",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--test-oauth",
        action="store_true",
        help="Test only the OAuth flow",
    )
    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Force re-authentication by removing the token file",
    )
    args = parser.parse_args()

    # Configure debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # Also set root logger
        logging.getLogger().setLevel(logging.DEBUG)
        # Explicitly set OAuth utils logger
        logging.getLogger(
            "activity.collectors.storage.cloud.google_drive.oauth_utils",
        ).setLevel(logging.DEBUG)

    # Detect environment
    detect_environment()

    # Prepare kwargs for collector
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
    if args.debug:
        kwargs["debug"] = True

    # Set start time based on days argument
    start_time = datetime.now(UTC) - timedelta(days=args.days)
    start_time_str = start_time.isoformat()

    # Test OAuth flow only if requested
    if args.test_oauth:
        try:
            # Get default config directory and verify its existence
            default_config_dir = os.path.join(
                os.environ.get("INDALEKO_ROOT", "."),
                "config",
            )
            if not os.path.exists(default_config_dir):
                os.makedirs(default_config_dir, exist_ok=True)

            # Set paths for credentials and token files
            credentials_file = args.credentials or os.path.join(
                default_config_dir,
                "gdrive_client_secrets.json",
            )
            token_file = args.token or os.path.join(
                default_config_dir,
                "gdrive_token.json",
            )

            # Check for gdrive_config.json
            config_file = os.path.join(default_config_dir, "gdrive_config.json")
            if os.path.exists(config_file):
                pass
            elif not os.path.exists(credentials_file):
                return

            # Handle reauth if requested - add this early to make sure it's processed
            if args.reauth and os.path.exists(token_file):
                with contextlib.suppress(Exception):
                    os.remove(token_file)

            # Import our components - wrapped in try/except for clear dependency errors
            try:
                # Also try importing other dependencies to check they're available
                import google.auth
                import requests

                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build

                from activity.collectors.storage.cloud.google_drive.oauth_utils import (
                    GoogleOAuthManager,
                )
            except ImportError:
                return

            # Define the scopes needed
            scopes = [
                "https://www.googleapis.com/auth/drive.activity.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.activity",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]

            for _scope in scopes:
                pass


            # If a token file exists, mention it
            if os.path.exists(token_file):
                pass

            # Create OAuth manager with all scopes
            oauth_manager = GoogleOAuthManager(
                credentials_file=credentials_file,
                token_file=token_file,
                scopes=scopes,
                debug=args.debug,
            )

            # Load credentials
            credentials = oauth_manager.load_credentials()

            # Verify credentials were obtained
            if credentials:

                # Get and display user info
                try:
                    user_info = oauth_manager.get_user_info()
                    if user_info:
                        pass
                    else:
                        pass
                except Exception:
                    pass

                # Display scopes
                if hasattr(credentials, "scopes"):
                    for _scope in credentials.scopes:
                        pass


                # Try to build a service to verify the token works
                try:
                    service = oauth_manager.build_service("drive", "v3")
                    if service:

                        # Try a simple API call
                        with contextlib.suppress(Exception):
                            service.about().get(fields="user").execute()
                    else:
                        pass
                except Exception:
                    pass
            else:
                pass

            # Exit early since we're just testing OAuth
            return

        except Exception:
            if args.debug:
                import traceback

                traceback.print_exc()
            return

    # Handle reauth if requested
    if args.reauth:
        token_file = kwargs.get("token_file")
        if not token_file:
            # Get default token file path
            default_config_dir = os.path.join(
                os.environ.get("INDALEKO_ROOT", "."),
                "config",
            )
            token_file = os.path.join(default_config_dir, "gdrive_token.json")

        if os.path.exists(token_file):
            with contextlib.suppress(Exception):
                os.remove(token_file)

    # Create collector
    try:
        collector = GoogleDriveActivityCollector(**kwargs)
    except Exception:
        if args.debug:
            import traceback

            traceback.print_exc()
        return

    # Create recorder if storing to database
    recorder = None
    if args.to_db:
        try:
            recorder = GoogleDriveActivityRecorder(
                collector=collector,
                debug=args.debug,
                auto_connect=False,  # Don't automatically connect to DB
            )
        except Exception:
            args.to_db = False

    # Collect activities
    try:
        # First get the activities
        activities, next_page_token = collector._get_activities(start_time_str)

        if not activities:
            return


        # Process the activities
        processed_activities = []
        for activity in activities:
            activity_data = collector._extract_activity_details(activity)
            if activity_data:
                processed_activities.append(activity_data)

        if not processed_activities:
            return


        # Display activities

        # Sort by timestamp (newest first)
        sorted_activities = sorted(
            processed_activities,
            key=lambda a: (
                a.timestamp
                if isinstance(a.timestamp, datetime)
                else datetime.fromisoformat(a.timestamp)
            ),
            reverse=True,
        )

        # Display activities (limit to requested number)
        for activity in sorted_activities[: args.limit]:
            display_activity(activity, args.detailed)

        # Store activities if requested
        if args.to_db and recorder:
            try:
                recorder._db.connect()

                storage_activities = [activity.to_storage_activity() for activity in processed_activities]
                recorder.store_activities(storage_activities)


                # Get statistics
                stats = recorder.get_google_drive_specific_statistics()
                for value in stats.values():
                    if not isinstance(value, dict) and not isinstance(value, list):
                        pass

            except Exception:
                if args.debug:
                    import traceback

                    traceback.print_exc()

        # Save to file if output path specified
        if args.output:
            try:
                # Create directory if it doesn't exist
                os.makedirs(
                    os.path.dirname(os.path.abspath(args.output)),
                    exist_ok=True,
                )

                with open(args.output, "w", encoding="utf-8") as f:
                    for activity in processed_activities:
                        f.write(activity.model_dump_json() + "\n")

            except Exception:
                if args.debug:
                    import traceback

                    traceback.print_exc()


    except Exception:
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
