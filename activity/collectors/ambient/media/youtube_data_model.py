"""
This module defines the data model for YouTube activity data collectors
in the Indaleko project.

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
import uuid
from datetime import UTC, datetime
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.data_model.activity_classification import (
    IndalekoActivityClassification,
    IndalekoMultiClassifiedActivityDataModel,
)

# pylint: enable=wrong-import-position


class YouTubeVideoActivity(IndalekoMultiClassifiedActivityDataModel):
    """
    Data model for YouTube video watching activity.

    This model captures details about YouTube videos watched by the user,
    including video metadata, watch statistics, and multi-dimensional
    classification of the activity.
    """

    Source: str = "youtube"
    ActivityType: str = "video_watch"

    # These fields are stored in AdditionalMetadata but defined here
    # for type checking and documentation purposes
    class YouTubeMetadata(IndalekoMultiClassifiedActivityDataModel.Config):
        """Type definition for YouTube-specific metadata."""

        video_id: str
        title: str
        channel: str
        channel_id: str | None = None
        category_id: str | None = None
        category_name: str | None = None
        tags: list[str] | None = None
        watch_percentage: float = 0.0
        like_status: str | None = None  # 'liked', 'disliked', or None
        comment_count: int | None = None
        view_count: int | None = None
        published_at: datetime | None = None
        thumbnail_url: str | None = None

    @classmethod
    def from_youtube_api(cls, video_data: dict[str, Any], watch_data: dict[str, Any]):
        """
        Create an instance from YouTube API data.

        Args:
            video_data: Video data from YouTube API
            watch_data: Watch history data from YouTube API

        Returns:
            YouTubeVideoActivity: An instance with processed data
        """
        # Extract basic metadata
        video_id = video_data.get("id", "")
        title = video_data.get("snippet", {}).get("title", "Unknown Video")
        channel = video_data.get("snippet", {}).get("channelTitle", "Unknown Channel")

        # Build metadata dictionary
        metadata = {
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "channel_id": video_data.get("snippet", {}).get("channelId"),
            "category_id": video_data.get("snippet", {}).get("categoryId"),
            "tags": video_data.get("snippet", {}).get("tags", []),
            "watch_percentage": calculate_watch_percentage(watch_data),
            "like_status": watch_data.get("like_status"),
            "comment_count": video_data.get("statistics", {}).get("commentCount"),
            "view_count": video_data.get("statistics", {}).get("viewCount"),
            "published_at": parse_youtube_datetime(
                video_data.get("snippet", {}).get("publishedAt"),
            ),
            "thumbnail_url": get_best_thumbnail(video_data),
        }

        # Calculate classification scores
        classification = IndalekoActivityClassification(
            ambient=calculate_ambient_score(video_data, watch_data),
            consumption=calculate_consumption_score(video_data, watch_data),
            research=calculate_research_score(video_data, watch_data),
            social=calculate_social_score(video_data, watch_data),
            productivity=calculate_productivity_score(video_data, watch_data),
            creation=0.0,  # Watching videos is not creation
        )

        # Create the base record and activity model
        # Note: This is a simplified version, in a real implementation
        # you would create a proper Record and SemanticAttributes
        from data_models.record import IndalekoRecordDataModel
        from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel

        # Create a basic record
        record = IndalekoRecordDataModel(
            Key=str(uuid.uuid4()),
            Operation="Watch",
            Attributes={
                "URI": f"https://www.youtube.com/watch?v={video_id}",
                "Description": title,
            },
        )

        # Create basic semantic attributes (would be expanded in real implementation)
        semantic_attrs = [
            IndalekoSemanticAttributeDataModel(
                AttributeType="MediaType",
                Value="Video",
            ),
            IndalekoSemanticAttributeDataModel(
                AttributeType="Platform",
                Value="YouTube",
            ),
        ]

        # Determine watch duration if available
        duration_sec = None
        if "contentDetails" in video_data and "duration" in video_data["contentDetails"]:
            duration_sec = parse_youtube_duration(
                video_data["contentDetails"]["duration"],
            )

        # Create the activity model
        return cls(
            Record=record,
            Timestamp=parse_watch_timestamp(watch_data),
            SemanticAttributes=semantic_attrs,
            Classification=classification,
            Duration=duration_sec,
            AdditionalMetadata=metadata,
        )


# Helper functions for working with YouTube data


def calculate_watch_percentage(watch_data):
    """Calculate the percentage of the video that was watched."""
    if "percent_watched" in watch_data:
        return float(watch_data["percent_watched"])
    elif "current_time" in watch_data and "duration" in watch_data:
        if watch_data["duration"] > 0:
            return min(
                1.0,
                float(watch_data["current_time"]) / float(watch_data["duration"]),
            )
    return 0.0


def parse_youtube_datetime(datetime_str):
    """Parse YouTube API datetime string to Python datetime object."""
    if not datetime_str:
        return None
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return dt
    except (ValueError, TypeError):
        return None


def parse_watch_timestamp(watch_data):
    """Parse the timestamp when the video was watched."""
    if "timestamp" in watch_data:
        return parse_youtube_datetime(watch_data["timestamp"])
    return datetime.now(UTC)


def parse_youtube_duration(duration_str):
    """
    Parse YouTube duration string (ISO 8601 format) to seconds.

    Example: 'PT1H30M15S' -> 5415 seconds (1h + 30m + 15s)
    """
    if not duration_str or not duration_str.startswith("PT"):
        return None

    seconds = 0
    duration_str = duration_str[2:]  # Remove 'PT'

    # Handle hours
    if "H" in duration_str:
        hours, duration_str = duration_str.split("H", 1)
        seconds += int(hours) * 3600

    # Handle minutes
    if "M" in duration_str:
        minutes, duration_str = duration_str.split("M", 1)
        seconds += int(minutes) * 60

    # Handle seconds
    if "S" in duration_str:
        s_seconds = duration_str.split("S", 1)[0]
        seconds += int(s_seconds)

    return seconds


def get_best_thumbnail(video_data):
    """Get the URL of the best available thumbnail."""
    if "snippet" not in video_data or "thumbnails" not in video_data["snippet"]:
        return None

    thumbnails = video_data["snippet"]["thumbnails"]
    for quality in ["maxres", "high", "medium", "default"]:
        if quality in thumbnails and "url" in thumbnails[quality]:
            return thumbnails[quality]["url"]

    return None


# Classification score calculation functions


def calculate_ambient_score(video_data, watch_data):
    """Calculate how likely this video was used as ambient content."""
    score = 0.0

    # Music videos tend to be ambient
    if video_data.get("snippet", {}).get("categoryId") == "10":  # Music category
        score += 0.7

    # Long videos that are background-friendly
    duration = parse_youtube_duration(
        video_data.get("contentDetails", {}).get("duration", ""),
    )
    if duration and duration > 1200:  # > 20 minutes
        score += 0.2

    # Videos that are often replayed
    if watch_data.get("replay_count", 0) > 1:
        score += 0.2

    # Keywords suggesting ambient use
    ambient_keywords = [
        "ambient",
        "background",
        "music",
        "asmr",
        "noise",
        "sleep",
        "study",
        "relaxing",
    ]
    title = video_data.get("snippet", {}).get("title", "").lower()
    if any(kw in title for kw in ambient_keywords):
        score += 0.4

    # Time of day might indicate ambient use (e.g., night time)
    watch_time = parse_watch_timestamp(watch_data)
    if watch_time and (watch_time.hour < 6 or watch_time.hour > 22):
        score += 0.1

    return min(score, 1.0)  # Cap at 1.0


def calculate_consumption_score(video_data, watch_data):
    """Calculate how much this video represents content consumption."""
    score = 0.5  # Base score for watching any video

    # Videos watched to completion are likely consumed fully
    watch_percentage = calculate_watch_percentage(watch_data)
    if watch_percentage > 0.9:  # Watched more than 90%
        score += 0.3

    # Entertainment categories indicate consumption
    entertainment_categories = [
        "1",
        "17",
        "24",
        "23",
        "20",
    ]  # Film, Sports, Entertainment, Comedy, Gaming
    if video_data.get("snippet", {}).get("categoryId") in entertainment_categories:
        score += 0.3

    # Short content is often consumed fully
    duration = parse_youtube_duration(
        video_data.get("contentDetails", {}).get("duration", ""),
    )
    if duration and duration < 600:  # < 10 minutes
        score += 0.2

    # Popular content is often consumed attentively
    if int(video_data.get("statistics", {}).get("viewCount", 0)) > 1000000:
        score += 0.1

    return min(score, 1.0)  # Cap at 1.0


def calculate_research_score(video_data, watch_data):
    """Calculate how much this video represents research or learning."""
    score = 0.0

    # Educational categories
    educational_categories = [
        "27",
        "28",
        "22",
        "15",
    ]  # Education, Science, Howto, Pets&Animals
    if video_data.get("snippet", {}).get("categoryId") in educational_categories:
        score += 0.6

    # Educational keywords
    edu_keywords = [
        "tutorial",
        "how to",
        "guide",
        "learn",
        "course",
        "lecture",
        "explained",
        "lesson",
    ]
    title = video_data.get("snippet", {}).get("title", "").lower()
    if any(kw in title for kw in edu_keywords):
        score += 0.5

    # Documentation or educational channels often have identifiable patterns
    channel = video_data.get("snippet", {}).get("channelTitle", "").lower()
    edu_channels = [
        "academy",
        "university",
        "school",
        "learn",
        "education",
        "course",
        "tutorial",
    ]
    if any(term in channel for term in edu_channels):
        score += 0.3

    # Videos that are paused and resumed multiple times suggest studying
    if watch_data.get("pause_count", 0) > 3:
        score += 0.2

    return min(score, 1.0)  # Cap at 1.0


def calculate_social_score(video_data, watch_data):
    """Calculate how much this video represents social activity."""
    score = 0.0

    # User interaction metrics
    if watch_data.get("like_status") == "liked":
        score += 0.3

    if watch_data.get("commented", False):
        score += 0.5

    if watch_data.get("shared", False):
        score += 0.7

    # Social content categories
    social_categories = ["24", "23", "22"]  # Entertainment, Comedy, People & Blogs
    if video_data.get("snippet", {}).get("categoryId") in social_categories:
        score += 0.2

    # Content from user's subscriptions is more socially relevant
    if watch_data.get("from_subscription", False):
        score += 0.2

    # Videos accessed via shares or recommendations
    if watch_data.get("source", "") == "shared_link":
        score += 0.4

    # Trending or current content has social dimension
    if video_data.get("trending", False):
        score += 0.3

    return min(score, 1.0)  # Cap at 1.0


def calculate_productivity_score(video_data, watch_data):
    """Calculate how much this video relates to productivity."""
    score = 0.0

    # Productivity keywords
    prod_keywords = [
        "productivity",
        "workflow",
        "organization",
        "time management",
        "efficiency",
        "gtd",
        "getting things done",
        "work",
        "business",
    ]
    title = video_data.get("snippet", {}).get("title", "").lower()
    if any(kw in title for kw in prod_keywords):
        score += 0.6

    # Work-related categories
    work_categories = [
        "28",
        "27",
        "22",
    ]  # Science & Technology, Education, Howto & Style
    if video_data.get("snippet", {}).get("categoryId") in work_categories:
        score += 0.2

    # Work hours viewing suggests work relation
    watch_time = parse_watch_timestamp(watch_data)
    if watch_time and (9 <= watch_time.hour <= 17) and watch_time.weekday() < 5:  # Weekday 9am-5pm
        score += 0.2

    # Software tutorials or tool videos
    tool_keywords = [
        "software",
        "tutorial",
        "tool",
        "app",
        "application",
        "program",
        "coding",
    ]
    if any(kw in title for kw in tool_keywords):
        score += 0.3

    return min(score, 1.0)  # Cap at 1.0


def main():
    """This allows testing the data model"""
    YouTubeVideoActivity.test_model_main()


if __name__ == "__main__":
    main()
