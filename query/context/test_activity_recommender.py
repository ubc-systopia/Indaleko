"""
Simple test script for the ActivityContextRecommender.

This script provides a simplified test for the ActivityContextRecommender
that avoids complex import dependencies.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import sys
import uuid

from datetime import UTC, datetime, timedelta
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# Define simplified test classes to avoid import issues
class RecommendationSource:
    """Simplified enum for recommendation sources."""

    ACTIVITY_CONTEXT = "activity_context"


class FeedbackType:
    """Simplified enum for feedback types."""

    ACCEPTED = "accepted"
    HELPFUL = "helpful"


class ActivityRecommender:
    """
    Simplified ActivityContextRecommender for testing.

    This class implements a basic version of the recommender that
    works directly with the database without all the dependencies.
    """

    def __init__(self, debug=False):
        """Initialize the recommender."""
        self.debug = debug
        self.source_type = RecommendationSource.ACTIVITY_CONTEXT
        self.logger = logging.getLogger("ActivityRecommender")
        if debug:
            self.logger.setLevel(logging.DEBUG)

        # Connect to database
        try:
            from db.db_config import IndalekoDBConfig

            self.db_config = IndalekoDBConfig()
            self.db = IndalekoDBConfig.get_db()
            self.logger.info("Connected to database")
        except Exception as e:
            self.logger.exception(f"Error connecting to database: {e}")
            self.db = None

        # Template success tracking
        self.successful_templates = {}
        self.failed_templates = {}

    def get_recent_activities(self) -> list[dict[str, Any]]:
        """
        Get recent activities from database.

        Returns:
            List of activities
        """
        activities = []

        if not self.db:
            self.logger.warning("Database not available")
            return self._get_fallback_activities()

        try:
            # Query NTFS activities
            query = """
                FOR doc IN NtfsActivity
                SORT doc.timestamp DESC
                LIMIT 20
                RETURN doc
            """

            cursor = self.db.aql.execute(query)
            file_docs = list(cursor)

            for doc in file_docs:
                activity_type = "file_default"

                # Determine activity type
                if "action" in doc:
                    action = doc.get("action", "").lower()
                    if "create" in action:
                        activity_type = "file_created"
                    elif "modify" in action or "write" in action:
                        activity_type = "file_modified"
                    elif "rename" in action:
                        activity_type = "file_renamed"

                # Extract attributes
                attributes = {
                    "file_name": doc.get("fileName", ""),
                    "file_path": doc.get("filePath", ""),
                    "timestamp": doc.get(
                        "timestamp",
                        datetime.now(UTC).isoformat(),
                    ),
                }

                # Add file type if available
                if "." in attributes["file_name"]:
                    attributes["file_type"] = attributes["file_name"].split(".")[-1].lower()

                # Add folder path
                attributes["folder_path"] = os.path.dirname(attributes["file_path"])

                # For rename operations, extract old and new names
                if activity_type == "file_renamed" and "oldName" in doc:
                    attributes["old_name"] = doc.get("oldName", "")
                    attributes["new_name"] = attributes["file_name"]

                activities.append({"type": activity_type, "attributes": attributes})

            self.logger.info(f"Retrieved {len(file_docs)} activities from database")

            # If no activities found, use fallback
            if not activities:
                self.logger.warning("No activities found in database, using fallback")
                activities = self._get_fallback_activities()

            return activities

        except Exception as e:
            self.logger.exception(f"Error retrieving activities: {e}")
            return self._get_fallback_activities()

    def _get_fallback_activities(self) -> list[dict[str, Any]]:
        """Provide fallback activities if database retrieval fails."""
        return [
            {
                "type": "file_created",
                "attributes": {
                    "file_name": "test_document.pdf",
                    "file_path": "/documents/test_document.pdf",
                    "file_type": "pdf",
                    "folder_path": "/documents",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            },
            {
                "type": "file_modified",
                "attributes": {
                    "file_name": "report.docx",
                    "file_path": "/documents/reports/report.docx",
                    "file_type": "docx",
                    "folder_path": "/documents/reports",
                    "timestamp": (datetime.now(UTC) - timedelta(minutes=30)).isoformat(),
                },
            },
        ]

    def generate_query_suggestions(self, max_suggestions=5) -> list[dict[str, Any]]:
        """
        Generate query suggestions based on activities.

        Args:
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggestion dictionaries
        """
        suggestions = []

        # Get recent activities
        activities = self.get_recent_activities()

        if not activities:
            self.logger.warning("No activities found")
            return []

        # Template mappings for different activity types
        templates = {
            "file_created": [
                "Find files created in the same folder as {file_name}",
                "Show files similar to {file_name}",
                "Find other {file_type} files created recently",
            ],
            "file_modified": [
                "Show recent changes to {file_name}",
                "Find other files modified in the last hour",
                "List files related to {file_name}",
            ],
            "file_renamed": [
                "Find files that reference {old_name}",
                "Show recent changes to {new_name}",
            ],
        }

        # Generate suggestions from activities
        for activity in activities:
            activity_type = activity.get("type", "default")
            attributes = activity.get("attributes", {})

            # Get templates for this activity type
            activity_templates = templates.get(activity_type, [])
            if not activity_templates:
                continue

            # Try to apply templates
            for template in activity_templates:
                try:
                    # Format template with attributes
                    query_text = template.format(**attributes)

                    # Calculate confidence
                    recency = self._calculate_recency(attributes.get("timestamp"))
                    confidence = 0.7 * recency

                    # Create suggestion
                    suggestion = {
                        "id": str(uuid.uuid4()),
                        "query_text": query_text,
                        "confidence": confidence,
                        "rationale": f"Based on recent {activity_type.replace('_', ' ')} activity",
                        "source": "activity_context",
                        "activity_type": activity_type,
                        "template": template,
                    }

                    suggestions.append(suggestion)

                    # Limit suggestions per activity
                    if len(suggestions) >= max_suggestions:
                        break

                except KeyError:
                    # Skip templates that can't be formatted with available attributes
                    continue

            # Limit total suggestions
            if len(suggestions) >= max_suggestions:
                break

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:max_suggestions]

    def _calculate_recency(self, timestamp_str: str | None) -> float:
        """Calculate recency score from timestamp."""
        if not timestamp_str:
            return 0.5

        try:
            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str)

            # Calculate age in hours
            now = datetime.now(UTC)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)

            age_hours = (now - timestamp).total_seconds() / 3600

            # Score based on age (1.0 for now, decreasing as age increases)
            if age_hours < 1:
                return 1.0  # Less than an hour old
            if age_hours < 4:
                return 0.9  # Less than 4 hours old
            if age_hours < 24:
                return 0.8  # Less than a day old
            if age_hours < 72:
                return 0.7  # Less than 3 days old
            return 0.5  # Older

        except (ValueError, TypeError):
            return 0.5  # Default if timestamp is invalid

    def record_feedback(self, suggestion_id: str, feedback: str, template: str) -> None:
        """
        Record feedback on a suggestion.

        Args:
            suggestion_id: ID of the suggestion
            feedback: Feedback type (accepted, helpful, etc.)
            template: Template used for the suggestion
        """
        if feedback in [FeedbackType.ACCEPTED, FeedbackType.HELPFUL]:
            # Positive feedback
            self.successful_templates[template] = self.successful_templates.get(template, 0) + 1
        else:
            # Negative feedback
            self.failed_templates[template] = self.failed_templates.get(template, 0) + 1

        self.logger.info(f"Recorded feedback for template: {template}")


def main():
    """Test the ActivityRecommender."""
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


    # Create recommender
    recommender = ActivityRecommender(debug=True)

    # Get activities
    activities = recommender.get_recent_activities()
    for _i, activity in enumerate(activities[:3]):  # Show first 3
        for _key, _value in activity["attributes"].items():
            pass

    # Generate suggestions
    suggestions = recommender.generate_query_suggestions(max_suggestions=5)
    for _i, suggestion in enumerate(suggestions):
        pass

    # Test feedback
    if suggestions:
        suggestion = suggestions[0]
        recommender.record_feedback(
            suggestion_id=suggestion["id"],
            feedback=FeedbackType.ACCEPTED,
            template=suggestion["template"],
        )

        # Show tracking
        for _template, _count in recommender.successful_templates.items():
            pass
        for _template, _count in recommender.failed_templates.items():
            pass


if __name__ == "__main__":
    main()
