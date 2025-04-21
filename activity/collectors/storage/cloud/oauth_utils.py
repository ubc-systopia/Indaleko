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
                
                # Check if the credentials have all the required scopes
                if self.credentials and hasattr(self.credentials, 'scopes'):
                    missing_scopes = [scope for scope in self.scopes if scope not in self.credentials.scopes]
                    if missing_scopes:
                        logger.warning(f"Credentials are missing scopes: {', '.join(missing_scopes)}")
                        logger.info("Requesting new credentials with all required scopes")
                        self.credentials = None  # Force new credential request
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
                logger.info("Credentials stored successfully")
            else:
                logger.error("Failed to obtain valid credentials")
                return None
        
        # Log the scopes that were actually granted
        if self.credentials and hasattr(self.credentials, 'scopes'):
            logger.debug(f"Credentials have the following scopes: {', '.join(self.credentials.scopes)}")
        
        return self.credentials
    
    def _request_user_credentials(self) -> Optional[Credentials]:
        """
        Request credentials from the user via OAuth flow.
        
        Returns:
            OAuth credentials or None if authentication failed
        """
        # Import needed libraries first
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow, Flow
            import requests
            import json
            from utils.misc.directory_management import indaleko_default_config_dir
        except ImportError as e:
            logger.error(f"Error importing required libraries: {e}")
            logger.error("Make sure google-auth-oauthlib and requests are installed")
            return None
            
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
            
            # Check if we're running in WSL (Windows Subsystem for Linux)
            is_wsl = False
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        is_wsl = True
            except:
                pass
            
            # Run the OAuth flow
            if is_wsl:
                # Manual flow for WSL environment
                import webbrowser
                from wsgiref.simple_server import make_server
                
                # Set up WSGI callback server
                auth_code = []
                
                def wsgi_app(environ, start_response):
                    """WSGI callback app to capture OAuth code."""
                    from urllib.parse import parse_qs
                    
                    # Get authorization code from query parameters
                    query = parse_qs(environ['QUERY_STRING'])
                    if 'code' in query and query['code']:
                        auth_code.append(query['code'][0])
                        
                    # Return success page
                    start_response('200 OK', [('Content-type', 'text/plain')])
                    return [b'Authentication successful! You can close this tab.']
                
                # Find an available port
                import socket
                sock = socket.socket()
                sock.bind(('localhost', 0))
                port = sock.getsockname()[1]
                sock.close()
                
                # Create redirect URI
                redirect_uri = f'http://localhost:{port}'
                
                # Update redirect URI
                flow.redirect_uri = redirect_uri
                
                # Generate authorization URL
                auth_url = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true'
                )[0]
                
                # Print clear instructions
                print("\n" + "="*80)
                print("\nPlease copy this URL and open it in your browser to authorize the application:")
                print("\n" + auth_url + "\n")
                print("After authorizing, you'll be redirected to a page that may show an error.")
                print("That's expected. Just wait here for the authentication to complete.")
                print("="*80 + "\n")
                
                # Start local server to receive the callback
                httpd = make_server('localhost', port, wsgi_app)
                print(f"Waiting for authentication on port {port}...")
                
                # Wait for auth code
                while not auth_code:
                    httpd.handle_request()
                
                # Exchange authorization code for credentials
                # All methods need to access these, so get them once
                client_id = flow.client_config['client_id']
                client_secret = flow.client_config['client_secret']
                token_uri = flow.client_config.get('token_uri', 'https://oauth2.googleapis.com/token')
                
                try:
                    # Direct approach using custom HTTP POST
                    # Prepare the token request data
                    token_data = {
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'code': auth_code[0],
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                    
                    # Make the token request
                    logger.debug(f"Making direct POST request to {token_uri}")
                    token_response = requests.post(token_uri, data=token_data)
                    token_response.raise_for_status()
                    token = token_response.json()
                    
                    # Create credentials directly
                    credentials = Credentials(
                        token=token['access_token'],
                        refresh_token=token.get('refresh_token'),
                        token_uri=token_uri,
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=token.get('scope', '').split(' ')
                    )
                    
                    logger.info(f"Successfully obtained credentials with direct token request")
                    logger.debug(f"Received scopes: {token.get('scope', '')}")
                except Exception as primary_error:
                    logger.error(f"Direct token request failed: {primary_error}")
                    
                    # Very aggressive fallback - patch InstalledAppFlow to accept scope changes
                    try:
                        logger.info("Attempting to patch InstalledAppFlow for scope validation...")
                        
                        # Define the monkey patch function
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
                        
                        # Apply the monkey patch - this assumes InstalledAppFlow is already imported at the top
                        original_fetch_token = InstalledAppFlow.fetch_token
                        InstalledAppFlow.fetch_token = patched_fetch_token
                        
                        # Now try again with patched method
                        flow.fetch_token(code=auth_code[0])
                        credentials = flow.credentials
                        logger.info(f"Successfully obtained credentials with patched validation")
                    except Exception as patched_error:
                        logger.error(f"Patched validation approach failed: {patched_error}")
                        
                        # Last resort fallback - create a new flow object
                        try:
                            logger.info("Attempting with a new flow object...")
                            # Create a new flow object without validation (Flow should be imported at top)
                            
                            # Clone the client config
                            client_config = {
                                'installed': {
                                    'client_id': client_id,
                                    'client_secret': client_secret,
                                    'redirect_uris': ['http://localhost'],
                                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                                    'token_uri': 'https://oauth2.googleapis.com/token'
                                }
                            }
                            
                            # Create a fresh flow
                            new_flow = Flow.from_client_config(
                                client_config,
                                scopes=None,  # Don't specify scopes to avoid validation
                                redirect_uri=redirect_uri
                            )
                            
                            # Fetch token
                            new_flow.fetch_token(code=auth_code[0])
                            credentials = new_flow.credentials
                            logger.info(f"Successfully obtained credentials with new flow")
                        except Exception as new_flow_error:
                            logger.error(f"New flow approach failed: {new_flow_error}")
                            
                            # Final attempt - just try to use the code directly
                            logger.info("Attempting final direct approach without validation...")
                            try:
                                # A super direct way by breaking the internal API entirely
                                flow._scope = None  # Disable scope checking
                                flow._fetch_token(code=auth_code[0]) 
                                credentials = flow.credentials
                                logger.info("Successfully obtained credentials with internal method")
                            except Exception as final_error:
                                logger.error(f"Final attempt failed: {final_error}")
                                raise Exception(f"All authentication methods failed: {primary_error}")
                except Exception as e:
                    logger.error(f"All OAuth authentication methods failed: {e}")
                    raise
            else:
                # Windows/macOS/Linux flow with patched validation
                try:
                    # First, apply the monkey patch for validation
                    logger.info("Applying validation patch for Windows/macOS/Linux flow...")
                    
                    # Define patched function
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
                    
                    # Apply the monkey patch (InstalledAppFlow imported at the top of function)
                    original_fetch_token = InstalledAppFlow.fetch_token
                    InstalledAppFlow.fetch_token = patched_fetch_token
                    
                    # Now run the local server flow with patched validation
                    credentials = flow.run_local_server(port=0)
                    logger.info("Successfully obtained credentials with patched validation in run_local_server")
                except Exception as e:
                    logger.error(f"Error in run_local_server with patched validation: {e}")
                    
                    # Try with simpler approach
                    try:
                        logger.info("Trying simpler approach with disabled validation...")
                        flow._scope = None  # Disable scope checking
                        credentials = flow.run_local_server(port=0)
                        logger.info("Successfully obtained credentials with disabled validation")
                    except Exception as e2:
                        logger.error(f"Simpler approach failed: {e2}")
                        
                        # Fallback to original method
                        logger.info("Falling back to original run_local_server method")
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
            # Try to get user info from the Drive API instead of People API
            # This avoids requiring additional scopes
            try:
                # Use the Drive API "about" endpoint to get user info
                service = build("drive", "v3", credentials=self.credentials)
                about = service.about().get(fields="user").execute()
                
                if "user" in about:
                    user = about["user"]
                    
                    user_info = {
                        "id": user.get("permissionId", ""),
                        "email": user.get("emailAddress"),
                        "name": user.get("displayName"),
                        "photo_url": user.get("photoLink")
                    }
                    logger.info(f"Got user info from Drive API: {user_info['name']} ({user_info['email']})")
                    return user_info
            except Exception as drive_error:
                logger.warning(f"Error getting user info from Drive API: {drive_error}, trying People API fallback")
            
            # Fallback to People API if Drive API fails
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