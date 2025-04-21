#!/usr/bin/env python3
"""
Example usage of Google Drive Activity Collector and Recorder.

This script demonstrates how to use the Google Drive Activity Collector and Recorder
to collect and store file activity data from Google Drive.

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
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko components
from activity.collectors.storage.cloud.gdrive_activity_collector import GoogleDriveActivityCollector
from activity.recorders.storage.cloud.gdrive.recorder import GoogleDriveActivityRecorder


def setup_logging(debug=False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def list_activities(activities):
    """List activities in a readable format."""
    print(f"\nFound {len(activities)} activities:")
    print("-" * 80)
    
    for i, activity in enumerate(activities, 1):
        print(f"{i}. {activity.activity_type} - {activity.file.name} ({activity.file.file_type})")
        print(f"   Time: {activity.timestamp}")
        print(f"   User: {activity.user.display_name} ({activity.user.email})")
        if activity.activity_type.value == "SHARE" and activity.shared_with:
            shared_users = ", ".join([u.display_name or u.email for u in activity.shared_with])
            print(f"   Shared with: {shared_users}")
        print(f"   File ID: {activity.file.file_id}")
        if activity.file.parent_folder_name:
            print(f"   Folder: {activity.file.parent_folder_name}")
        print("-" * 80)


def print_statistics(stats):
    """Print statistics in a readable format."""
    print("\nActivity Statistics:")
    print("-" * 80)
    
    # Print total count
    print(f"Total activities: {stats.get('total_count', 0)}")
    
    # Print activity types
    if 'by_type' in stats:
        print("\nBy Activity Type:")
        for activity_type, count in stats.get('by_type', {}).items():
            print(f"  {activity_type}: {count}")
    
    # Print file types
    if 'top_file_types' in stats:
        print("\nBy File Type:")
        for file_type, count in stats.get('top_file_types', {}).items():
            print(f"  {file_type}: {count}")
    
    # Print mime types
    if 'top_mime_types' in stats:
        print("\nTop MIME Types:")
        for mime_type, count in stats.get('top_mime_types', {}).items():
            print(f"  {mime_type}: {count}")
    
    # Print sharing statistics
    if 'sharing' in stats:
        sharing = stats.get('sharing', {})
        shared = sharing.get('shared', 0)
        not_shared = sharing.get('not_shared', 0)
        total = shared + not_shared
        if total > 0:
            print(f"\nSharing: {shared}/{total} files shared ({stats.get('sharing_percentage', 0):.1f}%)")
    
    # Print date distribution if available
    if 'by_date' in stats:
        print("\nActivity by Date:")
        for date_info in stats.get('by_date', [])[:7]:  # Show last 7 days
            print(f"  {date_info['date']}: {date_info['count']} activities")
    
    print("-" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Google Drive Activity Collector Example")
    parser.add_argument("--credentials", help="Path to OAuth credentials file")
    parser.add_argument("--token", help="Path to token file")
    parser.add_argument("--output", help="Output file path for activities")
    parser.add_argument("--days", type=int, default=7, help="Number of days to collect activities for")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of activities to display")
    parser.add_argument("--to-db", action="store_true", help="Store activities in database")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.debug)
    
    # Determine config directory
    config_dir = os.path.join(os.path.expanduser("~"), ".indaleko")
    os.makedirs(config_dir, exist_ok=True)
    
    # Set default paths if not provided
    credentials_file = args.credentials or os.path.join(config_dir, "gdrive_client_secrets.json")
    token_file = args.token or os.path.join(config_dir, "gdrive_token.json")
    output_file = args.output or os.path.join(config_dir, "gdrive_activities.jsonl")
    
    # Check for credentials file or existing token file
    token_exists = os.path.exists(token_file)
    credentials_exists = os.path.exists(credentials_file)
    from utils.misc.directory_management import indaleko_default_config_dir
    gdrive_config_exists = os.path.exists(os.path.join(indaleko_default_config_dir, "gdrive_config.json"))
    
    if not credentials_exists and not token_exists and not gdrive_config_exists:
        print(f"Error: No Google Drive credentials found")
        print("Options:")
        print(f"1. Save OAuth credentials to {credentials_file}")
        print(f"2. Save OAuth token to {token_file}")
        print(f"3. Run the g_drive.py script to set up Google Drive access")
        print("\nTo get OAuth credentials:")
        print("1. Go to https://console.developers.google.com/")
        print("2. Create a project and enable the Drive API and Drive Activity API")
        print("3. Create OAuth credentials (Desktop application)")
        print("4. Download the credentials file and save it to one of the paths above")
        return 1
    
    try:
        # Create collector
        print(f"Initializing Google Drive Activity Collector...")
        collector = GoogleDriveActivityCollector(
            credentials_file=credentials_file,
            token_file=token_file,
            output_file=output_file,
            direct_to_db=args.to_db,
            debug=args.debug
        )
        
        # Create recorder if storing to database
        recorder = None
        if args.to_db:
            print("Initializing Google Drive Activity Recorder...")
            recorder = GoogleDriveActivityRecorder(
                collector=collector,
                debug=args.debug
            )
        
        # Calculate start time
        days_ago = args.days
        start_time = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        
        # Set start time in collector state
        collector.state["last_start_time"] = start_time
        
        # Collect activities
        print(f"Collecting Google Drive activities from the past {days_ago} days...")
        success = collector.collect_data()
        
        if not success:
            print("Failed to collect activities")
            return 1
        
        # Display collected activities
        activities = collector.activities
        if activities:
            # Sort by timestamp (newest first)
            activities.sort(key=lambda a: a.timestamp, reverse=True)
            
            # Limit display count
            display_activities = activities[:args.limit]
            list_activities(display_activities)
            
            # Show total count if limited
            if len(activities) > args.limit:
                print(f"Note: Only showing {args.limit} of {len(activities)} activities")
        else:
            print("No activities found")
        
        # Store activities
        if activities:
            print(f"Storing {len(activities)} activities to {output_file}...")
            collector.store_data()
            
            if args.to_db and recorder:
                print("Storing activities in database...")
                storage_activities = [activity.to_storage_activity() for activity in activities]
                activity_ids = recorder.store_activities(storage_activities)
                print(f"Stored {len(activity_ids)} activities in database")
                
                # Print statistics
                print("Retrieving activity statistics from database...")
                stats = recorder.get_google_drive_specific_statistics()
                print_statistics(stats)
        
        print("Done!")
        return 0
    
    except KeyboardInterrupt:
        print("\nOperation canceled by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())