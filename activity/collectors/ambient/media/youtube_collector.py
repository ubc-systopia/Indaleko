"""
YouTube activity data collector for the Indaleko project.

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

import logging
import os
import sys
import uuid

from datetime import UTC, datetime
from typing import Any

import requests


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityCharacteristics
from activity.collectors.ambient.media.youtube_data_model import YouTubeVideoActivity
from activity.collectors.base import CollectorBase


# pylint: enable=wrong-import-position

# Set up logging
logger = logging.getLogger(__name__)


class YouTubeActivityCollector(CollectorBase):
    """
    YouTube activity data collector.

    This collector retrieves a user's YouTube watch history and video
    interactions using the YouTube Data API. It supports collection of:

    - Videos watched
    - Watch duration and percentage
    - User interactions (likes, comments, etc.)
    - Video metadata (title, channel, category, etc.)

    The collector applies multi-dimensional classification to each activity
    to support rich semantic understanding of the user's behavior.
    """

    def __init__(self, **kwargs):
        """
        Initialize the YouTube activity collector.

        Args:
            api_key (str, optional): YouTube Data API key
            oauth_credentials (dict, optional): OAuth credentials for accessing the user's data
            max_history_days (int, optional): Maximum days of history to collect (default: 30)
            include_liked_videos (bool, optional): Whether to include liked videos (default: True)
            name (str, optional): Custom name for the collector
            provider_id (uuid.UUID, optional): Custom provider ID
        """
        self._name = kwargs.get("name", "YouTube Activity Collector")
        self._provider_id = kwargs.get(
            "provider_id",
            uuid.UUID("7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"),
        )

        # YouTube API credentials
        self._api_key = kwargs.get("api_key")
        self._oauth_credentials = kwargs.get("oauth_credentials")

        # Collection parameters
        self._max_history_days = kwargs.get("max_history_days", 30)
        self._include_liked_videos = kwargs.get("include_liked_videos", True)

        # YouTube API endpoints
        self._api_base = "https://www.googleapis.com/youtube/v3"

        # Initialize collection state
        self._data = []
        self._last_cursor = None
        self._collection_timestamp = None

        # Description of this collector
        self._description = "Collects user's YouTube watch history and interactions"

    def get_collector_characteristics(self) -> ActivityCharacteristics:
        """Return the characteristics of this collector."""
        return ActivityCharacteristics(
            collector_type="ambient",
            data_category="media",
            data_sources=["youtube"],
            semantic_attributes=["MediaType", "Platform", "ContentConsumption"],
            related_objects=["YoutubeChannel", "YoutubeVideo"],
            requires_authentication=True,
        )

    def get_collector_name(self) -> str:
        """Return the name of this collector."""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Return the provider ID for this collector."""
        return self._provider_id

    def retrieve_data(self, identifier: str) -> dict[str, Any] | None:
        """
        Retrieve specific activity data by ID.

        Args:
            identifier (str): The ID of the activity to retrieve

        Returns:
            Optional[Dict[str, Any]]: The activity data or None if not found
        """
        if not self._data:
            return None

        for activity in self._data:
            if activity.Record.Key == identifier:
                return activity.dict()

        return None

    def get_cursor(self) -> str | None:
        """
        Return a cursor for resuming data collection.

        Returns:
            Optional[str]: A cursor string or None if no cursor is available
        """
        return self._last_cursor

    def cache_duration(self) -> int:
        """
        Return the recommended cache duration in seconds.

        Returns:
            int: Recommended cache duration in seconds
        """
        return 3600  # 1 hour

    def get_description(self) -> str:
        """
        Return a human-readable description of this collector.

        Returns:
            str: Collector description
        """
        return self._description

    def get_json_schema(self) -> dict[str, Any]:
        """
        Return the JSON schema for YouTube activity data.

        Returns:
            Dict[str, Any]: JSON schema
        """
        return YouTubeVideoActivity.schema()

    def collect_data(self) -> None:
        """
        Collect YouTube activity data for the user.

        This method uses the YouTube Data API to retrieve:
        1. Watch history
        2. Video details for each watched video
        3. User interactions (likes, comments, etc.)

        The collected data is stored in self._data as YouTubeVideoActivity objects.
        """
        if not self._api_key and not self._oauth_credentials:
            logger.error("No YouTube API credentials provided")
            return

        self._collection_timestamp = datetime.now(UTC)
        self._data = []

        try:
            # Step 1: Get watch history
            history_items = self._get_watch_history()
            if not history_items:
                logger.info("No watch history found or could not access history")
                return

            # Step 2: Process each watched video
            for item in history_items:
                try:
                    video_id = self._extract_video_id(item)
                    if not video_id:
                        continue

                    # Get full video details
                    video_data = self._get_video_details(video_id)
                    if not video_data:
                        continue

                    # Create activity model
                    activity = YouTubeVideoActivity.from_youtube_api(
                        video_data=video_data,
                        watch_data=item,
                    )

                    self._data.append(activity)

                except Exception as e:
                    logger.error(f"Error processing video: {e}")
                    continue

            # Step 3: Get liked videos if enabled
            if self._include_liked_videos:
                liked_videos = self._get_liked_videos()
                for video in liked_videos:
                    # Create fake watch data with like information
                    watch_data = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "like_status": "liked",
                        "from_likes_playlist": True,
                    }

                    # Create activity model
                    activity = YouTubeVideoActivity.from_youtube_api(
                        video_data=video,
                        watch_data=watch_data,
                    )

                    # Add to data if not already present
                    video_id = video.get("id")
                    if video_id and not any(a.AdditionalMetadata.get("video_id") == video_id for a in self._data):
                        self._data.append(activity)

            logger.info(f"Collected {len(self._data)} YouTube activities")

        except Exception as e:
            logger.error(f"Error collecting YouTube data: {e}")

    def process_data(self) -> list[YouTubeVideoActivity]:
        """
        Process the collected YouTube activity data.

        This method performs additional processing on the collected data,
        such as enriching with additional context, resolving references,
        or applying filters.

        Returns:
            List[YouTubeVideoActivity]: Processed activity data
        """
        # For now, we just return the collected data
        # Future implementations could add more processing here
        return self._data

    def store_data(self, recorder=None) -> bool:
        """
        Store the processed data using the provided recorder.

        Args:
            recorder: The recorder to use for storing data

        Returns:
            bool: True if successful, False otherwise
        """
        if not recorder:
            logger.warning("No recorder provided for storing YouTube activity data")
            return False

        if not self._data:
            logger.info("No YouTube activity data to store")
            return True

        try:
            # Process data first
            processed_data = self.process_data()

            # Use the recorder to store the data
            result = recorder.store_activities(processed_data)

            logger.info(f"Stored {len(processed_data)} YouTube activities")
            return result
        except Exception as e:
            logger.error(f"Error storing YouTube activity data: {e}")
            return False

    def get_activities(self) -> list[YouTubeVideoActivity]:
        """
        Get the collected YouTube activities.

        Returns:
            List[YouTubeVideoActivity]: Collected activities
        """
        return self._data

    # YouTube API interaction methods

    def _get_watch_history(self) -> list[dict[str, Any]]:
        """
        Retrieve the user's YouTube watch history.

        Returns:
            List[Dict[str, Any]]: List of watch history items
        """
        # This is a placeholder implementation that would need to be replaced
        # with actual YouTube API calls using the provided credentials

        # In a real implementation, this would:
        # 1. Use the YouTube API to get watch history
        # 2. Handle pagination to get all history within max_history_days
        # 3. Process API responses into a standardized format

        logger.info("Getting YouTube watch history (placeholder implementation)")

        # For now, return an empty list
        # In a real implementation, return actual watch history
        return []

    def _get_video_details(self, video_id: str) -> dict[str, Any] | None:
        """
        Get details for a specific YouTube video.

        Args:
            video_id (str): YouTube video ID

        Returns:
            Optional[Dict[str, Any]]: Video details or None if unavailable
        """
        if not self._api_key:
            logger.error("No YouTube API key provided")
            return None

        try:
            # Build API URL
            url = f"{self._api_base}/videos"
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": self._api_key,
            }

            # Make API request
            response = requests.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"Error getting video details: {response.status_code}")
                return None

            # Parse response
            data = response.json()
            if "items" not in data or not data["items"]:
                logger.warning(f"No details found for video {video_id}")
                return None

            return data["items"][0]

        except Exception as e:
            logger.error(f"Error getting video details for {video_id}: {e}")
            return None

    def _get_liked_videos(self) -> list[dict[str, Any]]:
        """
        Get the user's liked YouTube videos.

        Returns:
            List[Dict[str, Any]]: List of liked videos
        """
        # This is a placeholder implementation that would need to be replaced
        # with actual YouTube API calls using the provided credentials

        # In a real implementation, this would:
        # 1. Use the YouTube API to get the user's "Liked videos" playlist
        # 2. Handle pagination to get all liked videos
        # 3. Process API responses into a standardized format

        logger.info("Getting YouTube liked videos (placeholder implementation)")

        # For now, return an empty list
        # In a real implementation, return actual liked videos
        return []

    def _extract_video_id(self, watch_item: dict[str, Any]) -> str | None:
        """
        Extract the video ID from a watch history item.

        Args:
            watch_item (Dict[str, Any]): Watch history item

        Returns:
            Optional[str]: Video ID or None if not found
        """
        # This is a placeholder implementation
        # In a real implementation, this would handle various formats
        # of watch history items

        # Example:
        if "videoId" in watch_item:
            return watch_item["videoId"]
        elif "resourceId" in watch_item and "videoId" in watch_item["resourceId"]:
            return watch_item["resourceId"]["videoId"]

        return None


def main():
    """Test the YouTube activity collector."""
    # This is just a simple test
    collector = YouTubeActivityCollector()
    print(f"Collector: {collector.get_collector_name()}")
    print(f"Provider ID: {collector.get_provider_id()}")
    print(f"Description: {collector.get_description()}")

    # Test credentials would be needed for real collection
    # collector.collect_data()
    # activities = collector.get_activities()
    # print(f"Collected {len(activities)} activities")


if __name__ == "__main__":
    main()
