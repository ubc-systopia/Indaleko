#!/usr/bin/env python3
"""
Google Drive Activity Collector Example for Indaleko.

This example demonstrates the collection of Google Drive activity data
and showcases the OAuth authentication process in both Windows and WSL environments.

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
import json
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
    logger.error(f"Error importing Indaleko components: {e}")
    logger.error(
        "Make sure the virtual environment is activated and all dependencies are installed.",
    )
    logger.error(f"Python path: {sys.path}")
    sys.exit(1)


def detect_environment():
    """Detect whether we're running in Windows, native Linux, or WSL."""
    # Check for WSL (Windows Subsystem for Linux)
    is_wsl = False
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                is_wsl = True
                return "WSL"
    except:
        pass

    # Check platform
    if platform.system() == "Windows":
        return "Windows"
    elif platform.system() == "Linux":
        return "Linux"
    elif platform.system() == "Darwin":
        return "macOS"
    else:
        return "Unknown"


def display_file_details(file_info):
    """Display detailed information about a file."""
    print(f"\nFile: {file_info.name} ({file_info.file_id})")
    print(f"Type: {file_info.file_type.name}")
    print(f"MIME Type: {file_info.mime_type}")
    print(f"Parent Folder: {file_info.parent_folder_name}")

    # Format timestamps
    created = "Unknown"
    modified = "Unknown"

    if file_info.created_time:
        try:
            created_dt = datetime.fromisoformat(
                file_info.created_time.replace("Z", "+00:00"),
            )
            created = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

    if file_info.modified_time:
        try:
            modified_dt = datetime.fromisoformat(
                file_info.modified_time.replace("Z", "+00:00"),
            )
            modified = modified_dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

    print(f"Created: {created}")
    print(f"Modified: {modified}")
    print(f"Shared: {'Yes' if file_info.shared else 'No'}")

    if file_info.web_view_link:
        print(f"Web Link: {file_info.web_view_link}")

    # Print file size in human-readable format if available
    if file_info.size:
        size_bytes = int(file_info.size)
        size_str = ""
        if size_bytes < 1024:
            size_str = f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

        print(f"Size: {size_str}")


def display_activity(activity, detailed=False):
    """Display activity details in a human-readable format."""
    # Format timestamp
    timestamp = activity.timestamp
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except:
            pass

    if isinstance(timestamp, datetime):
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(timestamp)

    # Get user info
    user_name = activity.user.display_name or activity.user.email or activity.user.user_id

    # Get file info
    file_name = activity.file.name

    # Get activity type name
    activity_type = activity.activity_type.name

    # Print basic activity info
    print(f"{time_str} | {activity_type} | {user_name} | {file_name}")

    # Print detailed info if requested
    if detailed:
        print(f"  Activity ID: {activity.activity_id}")
        print(f"  File ID: {activity.file.file_id}")
        print(f"  File Type: {activity.file.file_type.name}")
        print(f"  MIME Type: {activity.file.mime_type}")

        # Show additional info based on activity type
        if activity_type == "RENAME":
            print(f"  Previous Name: {activity.previous_file_name}")
        elif activity_type == "MOVE":
            print(f"  Destination Folder: {activity.destination_folder_name}")
        elif activity_type == "COMMENT":
            print(f"  Comment: {activity.comment_content}")
        elif activity_type == "SHARE":
            if activity.shared_with:
                shared_with = ", ".join(
                    [f"{u.display_name or u.email or u.user_id}" for u in activity.shared_with],
                )
                print(f"  Shared With: {shared_with}")

            if activity.permission_changes:
                print("  Permission Changes:")
                for email, role in activity.permission_changes.items():
                    print(f"    {email}: {role}")

        # Print primary classification dimension
        if activity.activity_classification:
            class_dict = activity.activity_classification.model_dump()
            primary_dim = max(class_dict.items(), key=lambda x: x[1])[0]
            primary_val = class_dict[primary_dim]
            print(f"  Primary Classification: {primary_dim} ({primary_val:.2f})")

        print()


def main():
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
        logging.getLogger("activity.collectors.storage.cloud.oauth_utils").setLevel(
            logging.DEBUG,
        )

    # Detect environment
    env = detect_environment()
    print(f"Detected environment: {env}")

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
    print(f"Collecting activities since {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Test OAuth flow only if requested
    if args.test_oauth:
        print("Testing OAuth authentication flow...")
        try:
            # Get default config directory and verify its existence
            default_config_dir = os.path.join(
                os.environ.get("INDALEKO_ROOT", "."),
                "config",
            )
            if not os.path.exists(default_config_dir):
                os.makedirs(default_config_dir, exist_ok=True)
                print(f"Created config directory: {default_config_dir}")

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
                print(f"Found Google Drive config file: {config_file}")
            else:
                print(f"Google Drive config file not found at: {config_file}")
                if not os.path.exists(credentials_file):
                    print(f"Credentials file not found at: {credentials_file}")
                    print("\nTo proceed, you need either:")
                    print(f"1. A credentials file at {credentials_file}")
                    print(f"2. A config file at {config_file}")
                    return

            # Handle reauth if requested - add this early to make sure it's processed
            if args.reauth and os.path.exists(token_file):
                print(
                    f"Removing existing token file {token_file} to force re-authentication",
                )
                try:
                    os.remove(token_file)
                    print("Token file removed successfully.")
                except Exception as e:
                    print(f"Error removing token file: {e}")

            # Import our components - wrapped in try/except for clear dependency errors
            try:
                # Also try importing other dependencies to check they're available
                import google.auth
                import requests
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build

                from activity.collectors.storage.cloud.oauth_utils import (
                    GoogleOAuthManager,
                )
            except ImportError as import_err:
                print(f"\nImport error: {import_err}")
                print("\nPlease install the required dependencies:")
                print(
                    "  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib requests",
                )
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

            print("\nAttempting to authenticate with the following scopes:")
            for scope in scopes:
                print(f"  • {scope}")

            print(f"\nUsing token file: {token_file}")

            # If a token file exists, mention it
            if os.path.exists(token_file):
                print("Existing token file found. Will attempt to refresh if needed.")

            # Create OAuth manager with all scopes
            print("\nInitializing OAuth manager...")
            oauth_manager = GoogleOAuthManager(
                credentials_file=credentials_file,
                token_file=token_file,
                scopes=scopes,
                debug=args.debug,
            )

            # Load credentials with additional error handling
            print("Starting authentication process...")
            try:
                credentials = oauth_manager.load_credentials()
            except Exception as auth_error:
                print(f"\nAuthentication error: {auth_error}")
                print("\nTrying a direct manual approach as fallback...")

                # Direct manual approach as a last resort
                try:
                    # If we're in WSL, use the special wsgi server approach
                    if detect_environment() == "WSL":
                        # In WSL, use requests directly to get a token
                        import webbrowser
                        from wsgiref.simple_server import make_server

                        # 1. Load the flow
                        if os.path.exists(config_file):
                            with open(config_file) as f:
                                client_config = json.load(f)
                            flow = InstalledAppFlow.from_client_config(
                                client_config,
                                scopes,
                            )
                        elif os.path.exists(credentials_file):
                            flow = InstalledAppFlow.from_client_secrets_file(
                                credentials_file,
                                scopes,
                            )
                        else:
                            print("No OAuth configuration files found")
                            return

                        # 2. Set up WSGI callback server
                        auth_code = []

                        def wsgi_app(environ, start_response):
                            from urllib.parse import parse_qs

                            query = parse_qs(environ["QUERY_STRING"])
                            if query.get("code"):
                                auth_code.append(query["code"][0])
                            start_response("200 OK", [("Content-type", "text/plain")])
                            return [
                                b"Authentication successful! You can close this tab.",
                            ]

                        # 3. Find available port
                        import socket

                        sock = socket.socket()
                        sock.bind(("localhost", 0))
                        port = sock.getsockname()[1]
                        sock.close()

                        # 4. Create redirect URI
                        redirect_uri = f"http://localhost:{port}"
                        flow.redirect_uri = redirect_uri

                        # 5. Get auth URL and start server
                        auth_url = flow.authorization_url(
                            access_type="offline",
                            include_granted_scopes="true",
                        )[0]
                        print(
                            "\nPlease copy this URL and open it in your browser to authorize the application:",
                        )
                        print("\n" + auth_url + "\n")

                        httpd = make_server("localhost", port, wsgi_app)
                        print(f"Waiting for authentication on port {port}...")

                        # 6. Wait for auth code
                        while not auth_code:
                            httpd.handle_request()

                        # 7. Use requests directly to exchange code for token
                        import requests

                        client_id = flow.client_config["client_id"]
                        client_secret = flow.client_config["client_secret"]
                        token_uri = flow.client_config.get(
                            "token_uri",
                            "https://oauth2.googleapis.com/token",
                        )

                        token_data = {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "code": auth_code[0],
                            "redirect_uri": redirect_uri,
                            "grant_type": "authorization_code",
                        }

                        token_response = requests.post(token_uri, data=token_data)
                        token_response.raise_for_status()
                        token = token_response.json()

                        # 8. Create credentials
                        credentials = Credentials(
                            token=token["access_token"],
                            refresh_token=token.get("refresh_token"),
                            token_uri=token_uri,
                            client_id=client_id,
                            client_secret=client_secret,
                            scopes=token.get("scope", "").split(" "),
                        )

                        # 9. Save credentials
                        with open(token_file, "w") as f:
                            f.write(credentials.to_json())

                        print(
                            "Successfully obtained and saved credentials with manual approach",
                        )
                    else:
                        # On Windows/macOS/Linux, use a different direct approach
                        # by monkey patching the scope validation

                        # 1. Get a clean flow object
                        if os.path.exists(config_file):
                            with open(config_file) as f:
                                client_config = json.load(f)
                            flow = InstalledAppFlow.from_client_config(
                                client_config,
                                scopes,
                            )
                        elif os.path.exists(credentials_file):
                            flow = InstalledAppFlow.from_client_secrets_file(
                                credentials_file,
                                scopes,
                            )
                        else:
                            print("No OAuth configuration files found")
                            return

                        # 2. Monkey patch fetch_token to bypass scope validation
                        original_fetch_token = InstalledAppFlow.fetch_token

                        def patched_fetch_token(self, **kwargs):
                            # Save the original validation method
                            original_validate = self._oauth2session._validate_token_response

                            # Replace it with a no-op function
                            self._oauth2session._validate_token_response = lambda *args, **kwargs: None

                            try:
                                # Call original fetch_token without validation
                                result = original_fetch_token(self, **kwargs)
                                return result
                            finally:
                                # Restore the original validation method
                                self._oauth2session._validate_token_response = original_validate

                        # Apply the patch
                        InstalledAppFlow.fetch_token = patched_fetch_token

                        # 3. Run the flow with patched validation
                        credentials = flow.run_local_server(port=0)

                        # 4. Save the credentials
                        with open(token_file, "w") as f:
                            f.write(credentials.to_json())

                        print(
                            "Successfully obtained and saved credentials with patched validation",
                        )
                except Exception as manual_error:
                    print(f"Manual authentication also failed: {manual_error}")
                    if args.debug:
                        import traceback

                        traceback.print_exc()
                    return

            # Verify credentials were obtained
            if credentials:
                print("\n✅ Authentication successful!")

                # Get and display user info
                print("Retrieving user information...")
                try:
                    user_info = oauth_manager.get_user_info()
                    if user_info:
                        print(
                            f"Authenticated as: {user_info.get('name')} ({user_info.get('email')})",
                        )
                    else:
                        print(
                            "Could not retrieve user information, but authentication succeeded.",
                        )
                except Exception as e:
                    print(f"Error getting user info: {e}")

                # Display scopes
                if hasattr(credentials, "scopes"):
                    print("\nGranted scopes:")
                    for scope in credentials.scopes:
                        print(f"  • {scope}")

                print(f"\nToken file stored at: {token_file}")

                # Try to build a service to verify the token works
                print("\nVerifying token by building Drive API service...")
                try:
                    service = oauth_manager.build_service("drive", "v3")
                    if service:
                        print(
                            "✅ Successfully built Drive API service. Token is working correctly.",
                        )

                        # Try a simple API call
                        try:
                            about = service.about().get(fields="user").execute()
                            print(
                                f"API call successful! Connected to Google Drive as: {about['user'].get('emailAddress')}",
                            )
                        except Exception as e:
                            print(f"API call failed: {e}")
                    else:
                        print(
                            "⚠️ Could not build Drive API service. Token may have issues.",
                        )
                except Exception as e:
                    print(f"Error building service: {e}")
            else:
                print("\n❌ Authentication failed.")

            # Exit early
            return
        except ImportError as e:
            print(f"Import error: {e}")
            print("\nMake sure you have the required dependencies installed:")
            print(
                "  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib requests",
            )
            if args.debug:
                import traceback

                traceback.print_exc()
            return
        except Exception as e:
            print(f"\n❌ OAuth test failed: {e}")
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
            print(
                f"Removing existing token file {token_file} to force re-authentication",
            )
            try:
                os.remove(token_file)
                print("Token file removed successfully.")
            except Exception as e:
                print(f"Error removing token file: {e}")

    # Create collector
    print("Initializing Google Drive Activity Collector...")
    try:
        collector = GoogleDriveActivityCollector(**kwargs)
        print("Collector initialized successfully")
    except Exception as e:
        print(f"Error initializing collector: {e}")
        print("\nTips to resolve this issue:")
        print(
            "1. Try running with the --test-oauth flag to debug authentication issues",
        )
        print("2. Use --reauth to force a fresh authentication")
        print("3. Check that the credentials file or gdrive_config.json exists")
        print("4. Make sure you have the necessary Python packages installed")
        if args.debug:
            import traceback

            traceback.print_exc()
        return

    # Create recorder if storing to database
    recorder = None
    if args.to_db:
        print("Initializing Google Drive Activity Recorder...")
        try:
            recorder = GoogleDriveActivityRecorder(
                collector=collector,
                debug=args.debug,
                auto_connect=False,  # Don't automatically connect to DB
            )
            print("Recorder initialized successfully without database connection")
        except Exception as e:
            print(f"Warning: Could not initialize recorder with database: {e}")
            print("Continuing without database support...")
            args.to_db = False

    # Collect activities
    print("Collecting Google Drive activities...")
    try:
        # First get the activities
        activities, next_page_token = collector._get_activities(start_time_str)

        if not activities:
            print("No activities found for the specified time period.")
            return

        print(f"Collected {len(activities)} raw activities from Google Drive API")

        # Process the activities
        processed_activities = []
        for activity in activities:
            activity_data = collector._extract_activity_details(activity)
            if activity_data:
                processed_activities.append(activity_data)

        if not processed_activities:
            print("No activities could be processed.")
            return

        print(f"Successfully processed {len(processed_activities)} activities")

        # Display activities
        print("\nActivity Timeline:")
        print("=" * 80)
        print("Timestamp | Activity Type | User | File")
        print("-" * 80)

        # Sort by timestamp (newest first)
        sorted_activities = sorted(
            processed_activities,
            key=lambda a: (
                a.timestamp
                if isinstance(a.timestamp, datetime)
                else datetime.fromisoformat(a.timestamp.replace("Z", "+00:00"))
            ),
            reverse=True,
        )

        # Display activities (limit to requested number)
        for activity in sorted_activities[: args.limit]:
            display_activity(activity, args.detailed)

        # Store activities if requested
        if args.to_db and recorder:
            print("\nConnecting to database...")
            try:
                # Connect using the recorder's method for database connection
                recorder._connect_to_db()
                print("Database connection successful")

                print(f"Storing {len(processed_activities)} activities in database...")
                storage_activities = [activity.to_storage_activity() for activity in processed_activities]
                activity_ids = recorder.store_activities(storage_activities)

                print(f"Successfully stored {len(activity_ids)} activities in database")

                # Get statistics
                print("\nActivity Statistics:")
                stats = recorder.get_activity_statistics()
                for key, value in stats.items():
                    if not isinstance(value, dict) and not isinstance(value, list):
                        print(f"  {key}: {value}")

            except Exception as e:
                print(f"Error storing activities in database: {e}")
                if args.debug:
                    import traceback

                    traceback.print_exc()

        # Save to file if output path specified
        if args.output:
            print(f"\nSaving activities to {args.output}...")
            try:
                # Create directory if it doesn't exist
                os.makedirs(
                    os.path.dirname(os.path.abspath(args.output)),
                    exist_ok=True,
                )

                with open(args.output, "w", encoding="utf-8") as f:
                    for activity in processed_activities:
                        f.write(activity.model_dump_json() + "\n")

                print(
                    f"Successfully saved {len(processed_activities)} activities to {args.output}",
                )
            except Exception as e:
                print(f"Error saving activities to file: {e}")
                if args.debug:
                    import traceback

                    traceback.print_exc()

        print("\nExample completed successfully!")

    except Exception as e:
        print(f"Error collecting activities: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
