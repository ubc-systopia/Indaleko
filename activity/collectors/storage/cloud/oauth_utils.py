"""
OAuth utilities for cloud storage collectors.

This module provides shared OAuth functionality for cloud storage collectors,
allowing them to share authentication logic.

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

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Google OAuth libraries
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Google API client libraries not found. Please install them with:")
    print("pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib")

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
        scopes: List[str],
        debug: bool = False
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
    
    def load_credentials(self) -> Optional[Credentials]:
        """
        Load credentials from the token file or request new ones.
        
        Returns:
            Valid OAuth credentials or None if authentication failed
        """
        # Try to load existing credentials
        if os.path.exists(self.token_file):
            logger.debug(f"Loading credentials from {self.token_file}")
            try:
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_file, self.scopes
                )
            except Exception as e:
                logger.error(f"Error loading token file: {e}")
                self.credentials = None
        
        # Check if credentials are valid or need refreshing
        if not self.credentials or not self.credentials.valid:
            query_user = True
            
            # Try to refresh expired credentials
            if (
                self.credentials 
                and self.credentials.expired 
                and self.credentials.refresh_token
            ):
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
    
    def _request_user_credentials(self) -> Optional[Credentials]:
        """
        Request credentials from the user via OAuth flow.
        
        Returns:
            OAuth credentials or None if authentication failed
        """
        try:
            # Check if we're using a client_secrets.json file
            if os.path.exists(self.credentials_file):
                logger.debug(f"Using client secrets file: {self.credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
            else:
                # Try to use config from storage/collectors/cloud/g_drive.py
                logger.debug("Client secrets file not found, checking config directory")
                from utils.misc.directory_management import indaleko_default_config_dir
                
                # Try to load existing Google Drive config
                gdrive_config_file = os.path.join(
                    indaleko_default_config_dir, "gdrive_config.json"
                )
                
                if os.path.exists(gdrive_config_file):
                    logger.debug(f"Using existing config from {gdrive_config_file}")
                    with open(gdrive_config_file, "rt") as f:
                        config = json.load(f)
                    
                    flow = InstalledAppFlow.from_client_config(
                        config, self.scopes
                    )
                else:
                    logger.error(f"No credentials file found at {self.credentials_file} and no config file found at {gdrive_config_file}")
                    return None
            
            # Run the OAuth flow
            credentials = flow.run_local_server(port=0)
            logger.info("Successfully obtained new credentials")
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
    
    def get_user_info(self) -> Dict[str, Any]:
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
            results = service.people().get(
                resourceName="people/me",
                personFields="names,emailAddresses,photos"
            ).execute()
            
            # Extract user info
            user_info = {
                "id": results.get("resourceName", "").replace("people/", ""),
                "email": None,
                "name": None,
                "photo_url": None
            }
            
            # Extract email
            if "emailAddresses" in results and results["emailAddresses"]:
                user_info["email"] = results["emailAddresses"][0].get("value")
            
            # Extract name
            if "names" in results and results["names"]:
                user_info["name"] = results["names"][0].get("displayName")
            
            # Extract photo
            if "photos" in results and results["photos"]:
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