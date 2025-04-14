"""
Example script for collecting and storing YouTube activity data.

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
import logging
import argparse
from datetime import datetime, timezone

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.media.youtube_collector import YouTubeActivityCollector
from activity.recorders.ambient.youtube_recorder import YouTubeActivityRecorder
from activity.collectors.ambient.media.youtube_data_model import YouTubeVideoActivity

# pylint: enable=wrong-import-position

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YouTube Activity Collector/Recorder Example")
    
    parser.add_argument(
        "--api-key",
        help="YouTube Data API key"
    )
    
    parser.add_argument(
        "--oauth-credentials",
        help="Path to OAuth credentials JSON file"
    )
    
    parser.add_argument(
        "--max-history-days",
        type=int,
        default=30,
        help="Maximum days of history to collect (default: 30)"
    )
    
    parser.add_argument(
        "--no-liked-videos",
        action="store_true",
        help="Exclude liked videos from collection"
    )
    
    parser.add_argument(
        "--collection-name",
        default="YouTubeActivity",
        help="Name of the collection to store data in (default: YouTubeActivity)"
    )
    
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Run in demo mode with simulated data"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def create_demo_activity():
    """Create a sample YouTube activity for demonstration purposes."""
    from data_models.record import IndalekoRecordDataModel
    from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
    from activity.data_model.activity_classification import IndalekoActivityClassification
    
    # Create demo record
    record = IndalekoRecordDataModel(
        Key="demo-youtube-activity",
        Operation="Watch",
        Attributes={
            "URI": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "Description": "Never Gonna Give You Up"
        }
    )
    
    # Create semantic attributes
    semantic_attrs = [
        IndalekoSemanticAttributeDataModel(
            AttributeType="MediaType",
            Value="Video"
        ),
        IndalekoSemanticAttributeDataModel(
            AttributeType="Platform",
            Value="YouTube"
        ),
        IndalekoSemanticAttributeDataModel(
            AttributeType="Genre",
            Value="Music"
        )
    ]
    
    # Create classification
    classification = IndalekoActivityClassification(
        ambient=0.8,
        consumption=0.9,
        research=0.1,
        social=0.3,
        productivity=0.0,
        creation=0.0
    )
    
    # Create activity
    activity = YouTubeVideoActivity(
        Record=record,
        Timestamp=datetime.now(timezone.utc),
        SemanticAttributes=semantic_attrs,
        Classification=classification,
        Duration=213,  # 3:33
        Source="youtube",
        ActivityType="video_watch",
        AdditionalMetadata={
            "video_id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
            "channel": "Rick Astley",
            "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "category_id": "10",  # Music
            "tags": ["Rick Astley", "Never Gonna Give You Up", "music video"],
            "watch_percentage": 1.0,
            "like_status": "liked",
            "comment_count": 3800000,
            "view_count": 1400000000,
            "published_at": "2009-10-25T06:57:33Z",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        }
    )
    
    return activity


def run_demo():
    """Run a demonstration with simulated data."""
    logger.info("Running in demo mode with simulated data")
    
    # Create recorder
    recorder = YouTubeActivityRecorder(
        collection_name="YouTubeActivity"
    )
    
    # Create a sample activity
    activity = create_demo_activity()
    
    # Print activity details
    logger.info(f"Created demo activity: {activity.Record.Attributes.get('Description')}")
    logger.info(f"Classification: {activity.Classification}")
    logger.info(f"Primary classification: {activity.get_primary_classification()}")
    
    # Store activity
    try:
        success = recorder.store_data(activity)
        if success:
            logger.info("Successfully stored demo activity")
        else:
            logger.error("Failed to store demo activity")
    except Exception as e:
        logger.error(f"Error storing demo activity: {e}")


def main():
    """Main function."""
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting YouTube activity collector/recorder example")
    
    if args.demo_mode:
        run_demo()
        return
    
    # Load OAuth credentials if provided
    oauth_credentials = None
    if args.oauth_credentials:
        try:
            import json
            with open(args.oauth_credentials, "r") as f:
                oauth_credentials = json.load(f)
        except Exception as e:
            logger.error(f"Error loading OAuth credentials: {e}")
            return
    
    # Create collector
    collector = YouTubeActivityCollector(
        api_key=args.api_key,
        oauth_credentials=oauth_credentials,
        max_history_days=args.max_history_days,
        include_liked_videos=not args.no_liked_videos
    )
    
    # Create recorder
    recorder = YouTubeActivityRecorder(
        collector=collector,
        collection_name=args.collection_name
    )
    
    # Collect and store data
    logger.info("Starting data collection and storage")
    try:
        success = recorder.collect_and_store()
        if success:
            activities = collector.get_activities()
            logger.info(f"Successfully collected and stored {len(activities)} activities")
            
            # Show statistics on classifications
            if activities:
                classification_stats = {}
                for activity in activities:
                    primary = activity.get_primary_classification()
                    if primary in classification_stats:
                        classification_stats[primary] += 1
                    else:
                        classification_stats[primary] = 1
                
                logger.info("Classification statistics:")
                for classification, count in classification_stats.items():
                    logger.info(f"  {classification}: {count} ({count/len(activities)*100:.1f}%)")
        else:
            logger.error("Failed to collect and store activities")
    except Exception as e:
        logger.error(f"Error in collect_and_store: {e}")


if __name__ == "__main__":
    main()