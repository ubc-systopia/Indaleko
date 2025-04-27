"""
OAuth utilities for Google Drive integration with Indaleko.

This module provides helper functions for OAuth 2.0 authentication with Google APIs,
with special handling for scope validation issues and cross-platform support.

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

import json
import logging
import os
import sys
from typing import Any

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Google OAuth libraries
try:
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Google API client libraries not found. Please install them with:")
    print(
        "pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib",
    )

# Set up logging
logger = logging.getLogger(__name__)


class GoogleOAuthManager:
    """
    Manager for Google OAuth authentication.

    This class provides methods for obtaining, refreshing, and storing
    Google OAuth credentials.
    """

    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        scopes: list[str],
        debug: bool = False,
    ):
        """
        Initialize the Google OAuth manager.

        Args:
            credentials_file: Path to OAuth client secrets file
            token_file: Path to token storage file
            scopes: List of OAuth scopes to request
            debug: Whether to enable debug logging
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self.debug = debug
        self.credentials = None

        # Configure logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled for Google OAuth Manager")

    def load_credentials(self) -> Credentials | None:
        """
        Load credentials from the token file or request new ones.

        Returns:
            Valid OAuth credentials or None if authentication failed
        """
        # Try to load existing credentials
        if os.path.exists(self.token_file):
            logger.debug(f"Loading credentials from {self.token_file}")
            try:
                # Load credentials without explicitly checking scopes
                with open(self.token_file) as f:
                    token_data = json.load(f)

                # Create credentials directly with minimal scope checking
                self.credentials = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes"),
                )
            except Exception as e:
                logger.error(f"Error loading token file: {e}")
                self.credentials = None

        # Check if credentials are valid or need refreshing
        if not self.credentials or not self.credentials.valid:
            query_user = True

            # Try to refresh expired credentials
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    logger.debug("Refreshing expired credentials")
                    self.credentials.refresh(Request())
                    query_user = False
                except RefreshError as e:
                    logger.error(f"Error refreshing credentials: {e}")

            # If refresh failed or no credentials, request new ones
            if query_user:
                logger.debug("Requesting new credentials from user")
                self.credentials = self._request_user_credentials()

            # Store valid credentials
            if self.credentials and self.credentials.valid:
                self._store_credentials()
            else:
                logger.error("Failed to obtain valid credentials")
                return None

        return self.credentials

    def _request_user_credentials(self) -> Credentials | None:
        """
        Request credentials from the user via OAuth flow.

        Returns:
            OAuth credentials or None if authentication failed
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            from utils.misc.directory_management import indaleko_default_config_dir
        except ImportError as e:
            logger.error(f"Error importing required libraries: {e}")
            logger.error("Make sure google-auth-oauthlib is installed")
            return None

        try:
            # Check if we're using a client_secrets.json file
            if os.path.exists(self.credentials_file):
                logger.debug(f"Using client secrets file: {self.credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    self.scopes,
                )
            else:
                # Try to use config from storage/collectors/cloud/g_drive.py
                logger.debug("Client secrets file not found, checking config directory")

                # Try to load existing Google Drive config
                gdrive_config_file = os.path.join(
                    indaleko_default_config_dir,
                    "gdrive_config.json",
                )

                if os.path.exists(gdrive_config_file):
                    logger.debug(f"Using existing config from {gdrive_config_file}")
                    with open(gdrive_config_file) as f:
                        config = json.load(f)

                    flow = InstalledAppFlow.from_client_config(config, self.scopes)
                else:
                    logger.error(
                        f"No credentials file found at {self.credentials_file} and no config file found at {gdrive_config_file}",
                    )
                    return None

            # Use the standard flow approach but with a workaround for scope validation
            logger.info("Using standard approach with scope validation workaround...")

            # Create a local server to receive the callback
            import socket
            from wsgiref.simple_server import make_server

            # Find an available port first
            sock = socket.socket()
            sock.bind(("localhost", 0))
            port = sock.getsockname()[1]
            sock.close()

            # Set the redirect URI before creating the auth URL
            redirect_uri = f"http://localhost:{port}"
            flow.redirect_uri = redirect_uri

            # Get auth URL from flow with the redirect_uri properly set
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
            )

            print("\nPlease visit this URL to authorize this application:", auth_url)

            # Set up WSGI callback server
            auth_code = []

            def wsgi_app(environ, start_response):
                """WSGI callback app to capture OAuth code."""
                from urllib.parse import parse_qs

                # Get authorization code from query parameters
                query = parse_qs(environ["QUERY_STRING"])
                if query.get("code"):
                    auth_code.append(query["code"][0])

                # Return success page
                start_response("200 OK", [("Content-type", "text/plain")])
                return [b"Authentication successful! You can close this tab."]

            # Try to open the browser automatically
            import webbrowser

            try:
                webbrowser.open(auth_url)
                print(
                    "Your browser should open automatically. If not, please manually open the URL above.",
                )
            except:
                print(
                    "Unable to open browser automatically. Please manually copy and paste the URL into your browser.",
                )

            # Start local server
            httpd = make_server("localhost", port, wsgi_app)
            print(f"Waiting for authentication on port {port}...")

            # Wait for auth code
            while not auth_code:
                httpd.handle_request()

            # Use flow.fetch_token, but monkey-patch to bypass validation
            if hasattr(flow, "_oauth2session") and hasattr(
                flow._oauth2session,
                "_validate_token_response",
            ):
                # Save original validation method
                original_validate = flow._oauth2session._validate_token_response

                # Replace with no-op function
                flow._oauth2session._validate_token_response = lambda *args, **kwargs: None

                try:
                    # Fetch token with validation disabled
                    flow.fetch_token(code=auth_code[0])

                    # Get credentials from flow
                    credentials = flow.credentials

                    # Set the scopes directly to avoid scope issues
                    if hasattr(credentials, "_scopes") and not credentials._scopes:
                        credentials._scopes = self.scopes

                    logger.info(
                        "Successfully obtained credentials with validation bypass",
                    )
                finally:
                    # Restore original validation method
                    flow._oauth2session._validate_token_response = original_validate
            else:
                # Fall back to direct token exchange if _oauth2session doesn't exist
                logger.info("Falling back to direct token exchange")

                # Get client info - handle both config formats
                try:
                    # Try the 'installed' format first
                    if "installed" in flow.client_config:
                        client_id = flow.client_config["installed"]["client_id"]
                        client_secret = flow.client_config["installed"]["client_secret"]
                        token_uri = flow.client_config["installed"]["token_uri"]
                    # Try flat format
                    elif "client_id" in flow.client_config:
                        client_id = flow.client_config["client_id"]
                        client_secret = flow.client_config["client_secret"]
                        token_uri = flow.client_config.get(
                            "token_uri",
                            "https://oauth2.googleapis.com/token",
                        )
                    # For debugging
                    else:
                        logger.debug(
                            f"Client config structure: {flow.client_config.keys()}",
                        )
                        raise ValueError(
                            f"Unsupported client_config format: {flow.client_config.keys()}",
                        )
                except Exception as config_error:
                    logger.error(f"Error extracting client info: {config_error}")
                    # Let's extract the info directly from the auth URL as a fallback
                    # The URL contains the client_id
                    from urllib.parse import parse_qs, urlparse

                    parsed_url = urlparse(auth_url)
                    query_params = parse_qs(parsed_url.query)

                    client_id = query_params.get("client_id", [""])[0]
                    # We need to load from the config file since we can't get secret from URL
                    try:
                        # Get config path from utils
                        from utils.misc.directory_management import (
                            indaleko_default_config_dir,
                        )

                        config_path = os.path.join(
                            indaleko_default_config_dir,
                            "gdrive_config.json",
                        )

                        with open(config_path) as f:
                            config_data = json.load(f)
                        if "installed" in config_data:
                            client_secret = config_data["installed"]["client_secret"]
                        else:
                            client_secret = config_data["client_secret"]
                    except Exception as e:
                        logger.error(
                            f"Failed to get client_secret from config file: {e}",
                        )
                        raise

                    token_uri = "https://oauth2.googleapis.com/token"  # Default token URI

                # Exchange authorization code for token
                import requests

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

                # Create credentials object directly
                credentials = Credentials(
                    token=token["access_token"],
                    refresh_token=token.get("refresh_token"),
                    token_uri=token_uri,
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=self.scopes,  # Use our original scopes
                )

                logger.info(
                    "Successfully obtained credentials with direct token exchange",
                )

            logger.info("Successfully obtained credentials using manual token exchange")
            return credentials

        except Exception as e:
            logger.error(f"Error obtaining credentials: {e}")
            return None

    def _store_credentials(self) -> bool:
        """
        Store credentials to token file.

        Returns:
            True if successful, False otherwise
        """
        if not self.credentials:
            logger.error("No credentials to store")
            return False

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)

            # Write credentials to file
            with open(self.token_file, "w") as f:
                f.write(self.credentials.to_json())

            logger.info(f"Credentials stored to {self.token_file}")
            return True

        except Exception as e:
            logger.error(f"Error storing credentials: {e}")
            return False

    def get_user_info(self) -> dict[str, Any]:
        """
        Get information about the authenticated user.

        Returns:
            Dictionary with user information or empty dict if failed
        """
        if not self.credentials:
            self.load_credentials()

        if not self.credentials or not self.credentials.valid:
            logger.error("No valid credentials available")
            return {}

        try:
            # Use People API to get user info
            service = build("people", "v1", credentials=self.credentials)
            results = (
                service.people()
                .get(
                    resourceName="people/me",
                    personFields="names,emailAddresses,photos",
                )
                .execute()
            )

            # Extract user info
            user_info = {
                "id": results.get("resourceName", "").replace("people/", ""),
                "email": None,
                "name": None,
                "photo_url": None,
            }

            # Extract email
            if results.get("emailAddresses"):
                user_info["email"] = results["emailAddresses"][0].get("value")

            # Extract name
            if results.get("names"):
                user_info["name"] = results["names"][0].get("displayName")

            # Extract photo
            if results.get("photos"):
                user_info["photo_url"] = results["photos"][0].get("url")

            return user_info

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}

    def build_service(self, api_name: str, api_version: str) -> Any:
        """
        Build a Google API service using the credentials.

        Args:
            api_name: Name of the API (e.g., "drive", "driveactivity")
            api_version: Version of the API (e.g., "v3", "v2")

        Returns:
            Google API service object
        """
        if not self.credentials:
            self.load_credentials()

        if not self.credentials or not self.credentials.valid:
            logger.error("No valid credentials available")
            return None

        try:
            return build(api_name, api_version, credentials=self.credentials)
        except Exception as e:
            logger.error(f"Error building {api_name} service: {e}")
            return None
