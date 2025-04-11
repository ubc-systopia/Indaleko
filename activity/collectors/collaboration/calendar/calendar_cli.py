#!/usr/bin/env python3
"""
Command-line interface for the calendar activity collector.

This module provides a command-line interface for testing and using the
calendar activity collector and recorder.

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
import argparse
import logging
import datetime
import json
from typing import Dict, List, Any

# Ensure INDALEKO_ROOT is available
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CalendarCLI")

# Check for Google API availability
try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Check for MSAL availability
try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

# Indaleko imports
from activity.collectors.collaboration.calendar.google_calendar import GoogleCalendarCollector
from activity.collectors.collaboration.calendar.outlook_calendar import OutlookCalendarCollector
from activity.recorders.collaboration.calendar_recorder import CalendarRecorder


def setup_google_calendar(args):
    """Set up Google Calendar collector configuration.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Tuple containing the collector and config path
    """
    # Check if Google API is available
    if not GOOGLE_API_AVAILABLE:
        print("Google API libraries not available. Please install required packages:")
        print("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return None, None
        
    # Set up configuration paths
    config_path = args.config or os.path.join(
        os.environ.get("INDALEKO_ROOT"), "config", "gcalendar_config.json"
    )
    token_path = args.token or os.path.join(
        os.environ.get("INDALEKO_ROOT"), "config", "gcalendar_token.json"
    )
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"Google Calendar API config file not found: {config_path}")
        print("Please download OAuth 2.0 Client ID credentials from Google Cloud Console")
        print("and save them as 'gcalendar_config.json' in the config directory")
        return None, None
        
    # Create collector
    collector = GoogleCalendarCollector(
        config_path=config_path,
        token_path=token_path,
        event_limit=args.limit
    )
    
    return collector, config_path


def setup_outlook_calendar(args):
    """Set up Outlook Calendar collector configuration.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Tuple containing the collector and config path
    """
    # Check if MSAL is available
    if not MSAL_AVAILABLE:
        print("Microsoft Authentication Library not available. Please install required packages:")
        print("pip install msal requests")
        return None, None
        
    # Set up configuration paths
    config_path = args.config or os.path.join(
        os.environ.get("INDALEKO_ROOT"), "config", "outlook_calendar_config.json"
    )
    token_path = args.token or os.path.join(
        os.environ.get("INDALEKO_ROOT"), "config", "outlook_calendar_token.json"
    )
    
    # Load or create config
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            
    # Check for client ID and secret
    client_id = args.client_id or config.get("client_id")
    client_secret = args.client_secret or config.get("client_secret")
    
    if not client_id or not client_secret:
        print("Microsoft Graph API credentials not found")
        print("Please provide client_id and client_secret using command-line options")
        print("or configure outlook_calendar_config.json")
        return None, None
        
    # Update config
    config["client_id"] = client_id
    config["client_secret"] = client_secret
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        
    # Create collector
    collector = OutlookCalendarCollector(
        client_id=client_id,
        client_secret=client_secret,
        config_path=config_path,
        token_path=token_path,
        event_limit=args.limit
    )
    
    return collector, config_path


def collect_events(collector, args):
    """Collect events from the calendar.
    
    Args:
        collector: Calendar collector instance
        args: Command-line arguments
        
    Returns:
        List of calendar events
    """
    # Calculate time range
    now = datetime.datetime.now(datetime.timezone.utc)
    start_days = args.start_days
    end_days = args.end_days
    
    start_time = now - datetime.timedelta(days=start_days)
    end_time = now + datetime.timedelta(days=end_days)
    
    print(f"Collecting events from {start_time.date()} to {end_time.date()}")
    
    # Authenticate
    print("Authenticating with calendar service...")
    if not collector.authenticate():
        print("Authentication failed")
        return []
        
    # Collect events
    print("Collecting events...")
    collector.collect_data(
        start_time=start_time,
        end_time=end_time
    )
    
    # Process events
    events = collector.process_data()
    print(f"Collected {len(events)} events")
    
    return events


def display_events(events, args):
    """Display events in a readable format.
    
    Args:
        events: List of calendar events
        args: Command-line arguments
    """
    if not events:
        print("No events found")
        return
        
    # Display events
    print(f"\n{'-' * 80}")
    print(f"{'SUBJECT':<40} {'START TIME':<20} {'LOCATION':<20}")
    print(f"{'-' * 80}")
    
    for event in events:
        # Format start time
        start_time = event.start_time.strftime("%Y-%m-%d %H:%M")
        
        # Format location
        location = event.location.display_name if event.location else ""
        if event.is_online_meeting:
            if location:
                location += " (Online)"
            else:
                location = f"Online ({event.online_meeting_provider})"
                
        # Format subject
        subject = event.subject
        if len(subject) > 38:
            subject = subject[:35] + "..."
            
        # Print event
        print(f"{subject:<40} {start_time:<20} {location:<20}")
        
    print(f"{'-' * 80}")


def store_events(events, args):
    """Store events in the database.
    
    Args:
        events: List of calendar events
        args: Command-line arguments
        
    Returns:
        Number of events stored
    """
    # Create recorder
    recorder = CalendarRecorder(
        collection_name=args.collection
    )
    
    # Store events
    print(f"Storing {len(events)} events in collection '{args.collection}'...")
    stored_count = recorder.store_calendar_events(events)
    
    return stored_count


def main():
    """Main entry point for the calendar CLI."""
    parser = argparse.ArgumentParser(description="Indaleko Calendar Collector CLI")
    
    # Provider selection
    parser.add_argument("--provider", choices=["google", "outlook"], default="google",
                       help="Calendar provider to use (default: google)")
    
    # Common options
    parser.add_argument("--config", help="Path to the configuration file")
    parser.add_argument("--token", help="Path to the token file")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of events to retrieve")
    parser.add_argument("--start-days", type=int, default=30, 
                       help="Number of days in the past to collect events from (default: 30)")
    parser.add_argument("--end-days", type=int, default=90,
                       help="Number of days in the future to collect events to (default: 90)")
    
    # Outlook-specific options
    parser.add_argument("--client-id", help="Microsoft application (client) ID")
    parser.add_argument("--client-secret", help="Microsoft application (client) secret")
    
    # Storage options
    parser.add_argument("--store", action="store_true", help="Store events in the database")
    parser.add_argument("--collection", default="CalendarEvents", 
                       help="Name of the collection to store events in (default: CalendarEvents)")
                       
    # Registration options
    parser.add_argument("--register", action="store_true", 
                       help="Register with the activity service manager")
    
    # Parse arguments
    args = parser.parse_args()
    
    # If only registration is requested, create recorder and exit
    if args.register and not (args.store or args.provider):
        print("Registering calendar recorder with activity service manager...")
        recorder = CalendarRecorder(collection_name=args.collection)
        print("Registration complete. Calendar events will now appear in query results.")
        return 0
    
    # Set up collector
    if args.provider == "google":
        collector, config_path = setup_google_calendar(args)
    else:  # outlook
        collector, config_path = setup_outlook_calendar(args)
        
    # Exit if collector setup failed
    if not collector:
        return 1
        
    # Collect events
    events = collect_events(collector, args)
    
    # Display events
    display_events(events, args)
    
    # Store events if requested
    if args.store and events:
        stored_count = store_events(events, args)
        print(f"Stored {stored_count} events in the database")
        
        # Register with service manager if requested
        if args.register:
            print("Calendar recorder is automatically registered with the activity service manager")
            print("Calendar events will now appear in query results")
        
    return 0


if __name__ == "__main__":
    sys.exit(main())