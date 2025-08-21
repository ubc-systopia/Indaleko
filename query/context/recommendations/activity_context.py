"""
Activity Context Recommender for the Contextual Query Recommendation Engine.

This module provides the ActivityContextRecommender class, which generates
query suggestions based on the user's current activities in the Indaleko
Activity Context system.

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

from datetime import UTC, datetime, timedelta
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.context.service import IndalekoActivityContextService
from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationSource,
)
from query.context.recommendations.base import RecommendationProvider


# pylint: enable=wrong-import-position


class ActivityContextRecommender(RecommendationProvider):
    """
    Generates query suggestions based on the current activity context.

    This recommender analyzes the user's current and recent activities across
    different collectors to generate contextually relevant query suggestions.
    It maps activity types to appropriate query templates and uses activity
    content to fill in query parameters.
    """

    def __init__(self, db_config=None, debug: bool = False) -> None:
        """
        Initialize the activity context recommender.

        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug output
        """
        super().__init__(RecommendationSource.ACTIVITY_CONTEXT, debug)

        # Set up logging
        self._logger = logging.getLogger("ActivityContextRecommender")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # Connect to activity context service
        try:
            self._context_service = IndalekoActivityContextService(db_config=db_config)
            self._logger.info("Connected to Activity Context Service")
        except Exception as e:
            self._logger.exception(f"Error connecting to Activity Context Service: {e}")
            self._context_service = None

        # Initialize activity-to-query mappings
        self._activity_query_mappings = self._initialize_activity_mappings()

        # Success/failure tracking for learning
        self._successful_templates = {}  # {template: success_count}
        self._failed_templates = {}  # {template: failure_count}

        # Keep track of recently generated suggestions to avoid repetition
        self._recent_suggestions = set()
        self._max_recent_suggestions = 50

    def _initialize_activity_mappings(self) -> dict[str, dict[str, Any]]:
        """
        Initialize mappings between activity types and query templates.

        Returns:
            Dictionary mapping activity types to query templates and parameters
        """
        return {
            # Storage activities
            "file_created": {
                "templates": [
                    "Find files created in the same folder as {file_name}",
                    "Show files similar to {file_name}",
                    "Find other {file_type} files created recently",
                ],
                "confidence": 0.85,
                "required_attributes": ["file_name", "file_path"],
                "extracted_attributes": ["file_type", "folder_path"],
                "tag": "storage_activity",
            },
            "file_modified": {
                "templates": [
                    "Show recent changes to {file_name}",
                    "Find other files modified in the last hour",
                    "List files related to {file_name}",
                ],
                "confidence": 0.8,
                "required_attributes": ["file_name"],
                "extracted_attributes": ["file_type", "folder_path"],
                "tag": "storage_activity",
            },
            "file_renamed": {
                "templates": [
                    "Find files that reference {old_name}",
                    "Show recent changes to {new_name}",
                ],
                "confidence": 0.75,
                "required_attributes": ["old_name", "new_name"],
                "extracted_attributes": ["file_type", "folder_path"],
                "tag": "storage_activity",
            },
            # Collaboration activities
            "email_received": {
                "templates": [
                    "Find files shared by {sender}",
                    "Show recent communication with {sender}",
                    "Find files related to {subject}",
                ],
                "confidence": 0.85,
                "required_attributes": ["sender", "subject"],
                "extracted_attributes": ["recipient", "has_attachments"],
                "tag": "collaboration_activity",
            },
            "file_shared": {
                "templates": [
                    "Find other files shared with {recipient}",
                    "Show files related to {file_name}",
                ],
                "confidence": 0.9,
                "required_attributes": ["file_name", "recipient"],
                "extracted_attributes": ["platform", "sharing_type"],
                "tag": "collaboration_activity",
            },
            "meeting_scheduled": {
                "templates": [
                    "Find files related to {meeting_title}",
                    "Show communications with {participants}",
                ],
                "confidence": 0.8,
                "required_attributes": ["meeting_title"],
                "extracted_attributes": ["participants", "duration"],
                "tag": "collaboration_activity",
            },
            # Media activities
            "video_watched": {
                "templates": [
                    "Find documents related to {video_title}",
                    "Show other content from {channel}",
                    "Find files with content about {topic}",
                ],
                "confidence": 0.75,
                "required_attributes": ["video_title"],
                "extracted_attributes": ["channel", "topic", "duration"],
                "tag": "media_activity",
            },
            "music_played": {
                "templates": [
                    "Find files related to {artist}",
                    "Show documents mentioning {song_title}",
                ],
                "confidence": 0.7,
                "required_attributes": ["song_title"],
                "extracted_attributes": ["artist", "genre"],
                "tag": "media_activity",
            },
            # Generic activities (fallbacks)
            "default": {
                "templates": [
                    "Find recent files",
                    "Show recently modified documents",
                    "Find files created today",
                ],
                "confidence": 0.6,
                "required_attributes": [],
                "extracted_attributes": [],
                "tag": "generic_activity",
            },
        }

    def generate_suggestions(
        self,
        current_query: str | None = None,
        context_data: dict[str, Any] | None = None,
        max_suggestions: int = 10,
    ) -> list[QuerySuggestion]:
        """
        Generate query suggestions based on current activity context.

        Args:
            current_query: The current query, if any
            context_data: Additional context data
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of query suggestions based on current activities
        """
        if self._context_service is None:
            self._logger.warning("Activity context service not available")
            return []

        try:
            # Retrieve current activity context
            context_data = context_data or {}

            # Get current activity handle if not provided
            activity_handle = context_data.get("activity_handle")
            if not activity_handle:
                activity_handle = self._context_service.get_activity_handle()
                context_data["activity_handle"] = activity_handle

            # Retrieve recent activities
            recent_activities = self._get_recent_activities(activity_handle)

            if not recent_activities:
                self._logger.info("No recent activities found")
                return self._generate_default_suggestions(max_suggestions // 2)

            # Analyze activities and generate suggestions
            suggestions = []

            # Group activities by type
            activity_types = self._group_activities_by_type(recent_activities)

            for activity_type, activities in activity_types.items():
                # Generate suggestions for this activity type
                type_suggestions = self._generate_suggestions_for_activity_type(
                    activity_type,
                    activities,
                    max_per_type=max_suggestions // len(activity_types) + 1,  # Ensure even distribution
                )

                suggestions.extend(type_suggestions)

            # Add some default suggestions if we don't have enough
            if len(suggestions) < max_suggestions:
                default_count = max_suggestions - len(suggestions)
                suggestions.extend(self._generate_default_suggestions(default_count))

            # Sort by confidence and limit to max_suggestions
            suggestions.sort(key=lambda x: x.confidence, reverse=True)
            return suggestions[:max_suggestions]

        except Exception as e:
            self._logger.exception(f"Error generating activity-based recommendations: {e}")
            return self._generate_default_suggestions(max_suggestions // 2)

    def _get_recent_activities(
        self,
        activity_handle: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent activities from the context service and database.

        Args:
            activity_handle: Current activity context handle

        Returns:
            List of recent activities
        """
        activities = []

        try:
            # Get current context document from ArangoDB using the handle
            if self._context_service:
                # Get context document for this handle
                query = """
                    FOR doc IN @@collection
                    FILTER doc.Handle == @handle
                    RETURN doc
                """

                import Indaleko

                from db.db_config import IndalekoDBConfig

                bind_vars = {
                    "@collection": Indaleko.Indaleko.Indaleko_ActivityContext_Collection,
                    "handle": str(activity_handle),
                }

                # Execute query
                try:
                    db = IndalekoDBConfig.get_db()
                    results = db.aql.execute(query, bind_vars=bind_vars)
                    context_docs = list(results)

                    if context_docs:
                        context_doc = context_docs[0]
                        # Extract activities from cursors
                        if "Cursors" in context_doc:
                            for cursor in context_doc["Cursors"]:
                                provider_type = self._detect_provider_type(
                                    cursor.get("Provider", ""),
                                )

                                # Create activity entry
                                activity = {
                                    "type": provider_type,
                                    "attributes": cursor.get("ProviderAttributes", {}),
                                }

                                # Add timestamp if not present
                                if "timestamp" not in activity["attributes"] and "Timestamp" in context_doc:
                                    activity["attributes"]["timestamp"] = context_doc["Timestamp"]

                                activities.append(activity)

                    self._logger.info(
                        f"Retrieved {len(activities)} activities from context document",
                    )
                except Exception as e:
                    self._logger.exception(f"Error querying context document: {e}")

            # Query file activities from NTFS collection
            try:
                # Query recent NTFS activities
                file_query = """
                    FOR doc IN NtfsActivity
                    SORT doc.timestamp DESC
                    LIMIT 20
                    RETURN doc
                """

                results = db.aql.execute(file_query)
                file_docs = list(results)

                for doc in file_docs:
                    activity_type = "file_default"

                    # Determine activity type based on operation
                    if "action" in doc:
                        action = doc["action"].lower()
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

                    # Add file type from extension if available
                    if "." in attributes["file_name"]:
                        attributes["file_type"] = attributes["file_name"].split(".")[-1].lower()

                    # Add folder path
                    attributes["folder_path"] = os.path.dirname(attributes["file_path"])

                    # For rename operations, extract old and new names
                    if activity_type == "file_renamed" and "oldName" in doc:
                        attributes["old_name"] = doc.get("oldName", "")
                        attributes["new_name"] = attributes["file_name"]

                    activities.append({"type": activity_type, "attributes": attributes})

                self._logger.info(
                    f"Retrieved {len(file_docs)} file activities from database",
                )
            except Exception as e:
                self._logger.exception(f"Error querying file activities: {e}")

            # If no activities found, return fallback simulated activities
            if not activities:
                self._logger.warning(
                    "No activities found in database, using fallback data",
                )
                activities = self._get_fallback_activities()

            return activities

        except Exception as e:
            self._logger.exception(f"Error retrieving activities: {e}")
            return self._get_fallback_activities()

    def _detect_provider_type(self, provider_id: str) -> str:
        """
        Detect activity type from provider ID.

        Args:
            provider_id: Provider UUID as string

        Returns:
            Activity type string
        """
        # Map known provider IDs to activity types
        provider_map = {
            # These would be actual UUIDs in production code
            "ntfs": "file_modified",
            "email": "email_received",
            "calendar": "meeting_scheduled",
            "youtube": "video_watched",
            "spotify": "music_played",
        }

        # Check for known provider types in the ID string
        for key, value in provider_map.items():
            if key in provider_id.lower():
                return value

        return "default"

    def _get_fallback_activities(self) -> list[dict[str, Any]]:
        """
        Get fallback simulated activities when database retrieval fails.

        Returns:
            List of simulated activities
        """
        return [
            {
                "type": "file_created",
                "attributes": {
                    "file_name": "quarterly_report.pdf",
                    "file_path": "/documents/reports/quarterly_report.pdf",
                    "file_type": "pdf",
                    "folder_path": "/documents/reports",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            },
            {
                "type": "email_received",
                "attributes": {
                    "sender": "alice@example.com",
                    "subject": "Project Update",
                    "recipient": "user@example.com",
                    "has_attachments": True,
                    "timestamp": (datetime.now(UTC) - timedelta(minutes=30)).isoformat(),
                },
            },
            {
                "type": "file_modified",
                "attributes": {
                    "file_name": "project_plan.docx",
                    "file_path": "/documents/projects/project_plan.docx",
                    "file_type": "docx",
                    "folder_path": "/documents/projects",
                    "timestamp": (datetime.now(UTC) - timedelta(minutes=45)).isoformat(),
                },
            },
        ]

    def _group_activities_by_type(
        self,
        activities: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Group activities by their type.

        Args:
            activities: List of activities

        Returns:
            Dictionary mapping activity types to lists of activities
        """
        grouped = {}

        for activity in activities:
            activity_type = activity.get("type", "default")

            if activity_type not in grouped:
                grouped[activity_type] = []

            grouped[activity_type].append(activity)

        return grouped

    def _generate_suggestions_for_activity_type(
        self,
        activity_type: str,
        activities: list[dict[str, Any]],
        max_per_type: int = 3,
    ) -> list[QuerySuggestion]:
        """
        Generate suggestions for a specific activity type.

        Args:
            activity_type: The type of activity
            activities: List of activities of this type
            max_per_type: Maximum suggestions per activity type

        Returns:
            List of query suggestions
        """
        suggestions = []

        # Get mapping for this activity type or use default
        mapping = self._activity_query_mappings.get(
            activity_type,
            self._activity_query_mappings["default"],
        )

        # Sort activities by recency (most recent first)
        sorted_activities = sorted(
            activities,
            key=lambda a: a.get("attributes", {}).get("timestamp", ""),
            reverse=True,
        )

        # Generate suggestions for the most recent activities
        for activity in sorted_activities[:max_per_type]:
            attributes = activity.get("attributes", {})

            # Check if activity has required attributes
            has_required = all(attr in attributes for attr in mapping["required_attributes"])

            if not has_required:
                continue

            # Extract additional attributes if possible
            extracted = {}
            for attr in mapping["extracted_attributes"]:
                if attr in attributes:
                    extracted[attr] = attributes[attr]
                else:
                    # Try to derive attributes if not directly available
                    derived = self._derive_attribute(attr, attributes)
                    if derived:
                        extracted[attr] = derived

            # Combine all available attributes
            all_attrs = {**attributes, **extracted}

            # Generate suggestions from templates
            for template in mapping["templates"]:
                try:
                    # Try to format the template with available attributes
                    query_text = template.format(**all_attrs)

                    # Skip if this is a duplicate suggestion
                    if query_text in self._recent_suggestions:
                        continue

                    # Calculate confidence based on base confidence and attribute coverage
                    confidence = self._calculate_confidence(
                        mapping["confidence"],
                        activity_type,
                        template,
                        all_attrs,
                    )

                    # Create suggestion
                    suggestion = self.create_suggestion(
                        query_text=query_text,
                        rationale=f"Based on recent {activity_type.replace('_', ' ')} activity",
                        confidence=confidence,
                        source_context={
                            "activity_type": activity_type,
                            "attributes": {k: str(v) for k, v in all_attrs.items()},
                            "template": template,
                        },
                        relevance_factors={
                            "recency": self._calculate_recency_score(
                                attributes.get("timestamp"),
                            ),
                            "attribute_coverage": (
                                len(all_attrs)
                                / (len(mapping["required_attributes"]) + len(mapping["extracted_attributes"]))
                                if mapping["required_attributes"] or mapping["extracted_attributes"]
                                else 0.5
                            ),
                            "template_success": self._get_template_success_ratio(
                                template,
                            ),
                        },
                        tags=[mapping["tag"], f"activity_type:{activity_type}"],
                    )

                    suggestions.append(suggestion)

                    # Track this suggestion to avoid duplicates
                    self._recent_suggestions.add(query_text)
                    if len(self._recent_suggestions) > self._max_recent_suggestions:
                        self._recent_suggestions.pop()

                except KeyError:
                    # Skip templates with missing attributes
                    continue

            # Limit suggestions per activity
            if len(suggestions) >= max_per_type:
                break

        return suggestions[:max_per_type]

    def _derive_attribute(
        self,
        attribute: str,
        available_attributes: dict[str, Any],
    ) -> str | None:
        """
        Attempt to derive an attribute that isn't directly available.

        Args:
            attribute: The attribute to derive
            available_attributes: Dictionary of available attributes

        Returns:
            Derived attribute value or None if not derivable
        """
        # Derive file_type from file_name or file_path
        if attribute == "file_type" and ("file_name" in available_attributes or "file_path" in available_attributes):
            file_name = available_attributes.get(
                "file_name",
                available_attributes.get("file_path", ""),
            )
            if "." in file_name:
                return file_name.split(".")[-1].lower()

        # Derive folder_path from file_path
        if attribute == "folder_path" and "file_path" in available_attributes:
            file_path = available_attributes["file_path"]
            return os.path.dirname(file_path)

        # Add more derivation rules as needed

        return None

    def _calculate_confidence(
        self,
        base_confidence: float,
        activity_type: str,
        template: str,
        attributes: dict[str, Any],
    ) -> float:
        """
        Calculate confidence score for a suggestion.

        Args:
            base_confidence: Base confidence from the mapping
            activity_type: Type of activity
            template: Query template
            attributes: Available attributes

        Returns:
            Confidence score (0.0-1.0)
        """
        # Factors that influence confidence
        recency_factor = self._calculate_recency_score(attributes.get("timestamp"))
        template_success_factor = self._get_template_success_ratio(template)

        # For more complex suggestions, reduce confidence slightly
        complexity_factor = 1.0 - (0.05 * template.count("{"))

        # Calculate final confidence
        confidence_factors = {
            "base": base_confidence,
            "recency": recency_factor,
            "template_success": template_success_factor,
            "complexity": complexity_factor,
        }

        # Use weighted calculation from base class
        return self.calculate_confidence(
            confidence_factors,
            {"base": 0.4, "recency": 0.3, "template_success": 0.2, "complexity": 0.1},
        )

    def _calculate_recency_score(self, timestamp_str: str | None) -> float:
        """
        Calculate recency score based on timestamp.

        Args:
            timestamp_str: ISO format timestamp string or None

        Returns:
            Recency score (0.0-1.0)
        """
        if not timestamp_str:
            return 0.5  # Default if no timestamp

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

    def _get_template_success_ratio(self, template: str) -> float:
        """
        Get success ratio for a template based on feedback history.

        Args:
            template: The query template

        Returns:
            Success ratio (0.0-1.0)
        """
        successes = self._successful_templates.get(template, 0)
        failures = self._failed_templates.get(template, 0)

        if successes + failures == 0:
            return 0.5  # No history

        return successes / (successes + failures)

    def _generate_default_suggestions(self, count: int) -> list[QuerySuggestion]:
        """
        Generate default suggestions when no activities are available.

        Args:
            count: Number of suggestions to generate

        Returns:
            List of default query suggestions
        """
        default_queries = [
            ("Find recently modified files", "Based on current time"),
            ("Show files created today", "Based on current date"),
            ("Find documents shared with me", "Based on common information need"),
            ("Show my recent activity", "To review recent work"),
            ("Find large files in my documents", "Based on storage management needs"),
            ("Show recent presentations", "Based on common file type"),
            (
                "Find email attachments from last week",
                "Based on common information need",
            ),
            ("Show files with pending actions", "Based on task management"),
            ("Find files related to current project", "Based on current context"),
            ("Show files I've shared with others", "Based on collaboration patterns"),
        ]

        suggestions = []

        # Take at most 'count' suggestions
        for i in range(min(count, len(default_queries))):
            query_text, rationale = default_queries[i]

            suggestion = self.create_suggestion(
                query_text=query_text,
                rationale=rationale,
                confidence=0.6,
                source_context={"type": "default"},
                relevance_factors={"default_relevance": 0.6},
                tags=["default", "generic"],
            )

            suggestions.append(suggestion)

        return suggestions

    def update_from_feedback(
        self,
        suggestion: QuerySuggestion,
        feedback: FeedbackType,
        result_count: int | None = None,
    ) -> None:
        """
        Update internal models based on feedback.

        Args:
            suggestion: The suggestion that received feedback
            feedback: The type of feedback provided
            result_count: Number of results from the suggested query, if applicable
        """
        # Extract template from source context
        source_context = suggestion.source_context
        template = source_context.get("template")

        if not template:
            return

        # Update template success/failure tracking
        if self.is_positive_feedback(feedback):
            # Positive feedback - increment success count
            self._successful_templates[template] = self._successful_templates.get(template, 0) + 1

            # Bonus for highly successful queries (many results)
            if result_count and result_count > 5:
                self._successful_templates[template] = self._successful_templates.get(template, 0) + 1

        elif self.is_negative_feedback(feedback):
            # Negative feedback - increment failure count
            self._failed_templates[template] = self._failed_templates.get(template, 0) + 1

        # The neutral feedback doesn't affect our tracking

        self._logger.debug(
            f"Updated template feedback: {template}, successes: {self._successful_templates.get(template, 0)}, failures: {self._failed_templates.get(template, 0)}",
        )


def main() -> None:
    """Test the ActivityContextRecommender with actual database."""
    logging.basicConfig(level=logging.DEBUG)


    # Set up database connection
    try:
        from db.db_config import IndalekoDBConfig

        db_config = IndalekoDBConfig()
    except Exception:
        db_config = None

    # Create recommender with actual database
    recommender = ActivityContextRecommender(db_config=db_config, debug=True)

    # Generate suggestions
    suggestions = recommender.generate_suggestions(max_suggestions=5)

    # Print suggestions
    for _i, suggestion in enumerate(suggestions):
        suggestion.source_context.get("activity_type", "unknown")

        # Show relevance factors
        if suggestion.relevance_factors:
            for _factor, _value in suggestion.relevance_factors.items():
                pass

    # Test feedback
    if suggestions:
        recommender.update_from_feedback(
            suggestion=suggestions[0],
            feedback=FeedbackType.ACCEPTED,
            result_count=7,
        )

        # Generate new suggestions to see the effect
        new_suggestions = recommender.generate_suggestions(max_suggestions=5)

        for _i, suggestion in enumerate(new_suggestions):

            # Check if this is the same as a previous suggestion to show confidence changes
            for old_suggestion in suggestions:
                if suggestion.query_text == old_suggestion.query_text:
                    confidence_change = suggestion.confidence - old_suggestion.confidence
                    if abs(confidence_change) > 0.01:
                        pass


if __name__ == "__main__":
    main()
