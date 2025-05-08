"""Query generator for ablation tests."""

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

try:
    from utils.misc.string_similarity import jaro_winkler_similarity

    HAS_JARO_WINKLER = True
except ImportError:
    # Fallback implementation if utils.misc.string_similarity is not available
    def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
        """
        Simple fallback implementation of Jaro-Winkler similarity.

        Args:
            s1: First string to compare
            s2: Second string to compare
            prefix_weight: Weight given to common prefix (default: 0.1)

        Returns:
            A similarity score between 0 (completely different) and 1 (identical)
        """
        if s1 == s2:
            return 1.0

        # For fallback, just use a simple ratio of common characters
        s1_chars = set(s1.lower())
        s2_chars = set(s2.lower())

        if not s1_chars and not s2_chars:
            return 1.0

        common_chars = len(s1_chars.intersection(s2_chars))
        all_chars = len(s1_chars.union(s2_chars))

        return common_chars / all_chars

    HAS_JARO_WINKLER = False

from ..models.activity import ActivityType


class QueryTemplate(BaseModel):
    """Template for generating natural language queries."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    template: str
    parameters: dict[str, list[str]] = Field(default_factory=dict)
    activity_type: str
    description: str

    def generate_query(self, params: dict[str, str] | None = None) -> str:
        """Generate a query from this template.

        Args:
            params: Optional dictionary of parameter values to use.
                   If not provided, random values will be selected.

        Returns:
            str: The generated query.
        """
        # Simple implementation for now - to be expanded
        query = self.template
        if params:
            for key, value in params.items():
                placeholder = f"{{{key}}}"
                query = query.replace(placeholder, value)
        return query


@dataclass
class TestQuery:
    """Data class for a test query.

    This class represents a generated query along with its
    associated metadata for testing.
    """

    query_id: uuid.UUID = field(default_factory=uuid.uuid4)
    query_text: str = ""
    activity_types: list[ActivityType] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    difficulty: str = "medium"  # easy, medium, hard
    metadata: dict[str, object] = field(default_factory=dict)
    expected_matches: list[str] = field(default_factory=list)  # List of document IDs that should match this query


class QueryGenerator:
    """Generator for ablation test queries.

    This class generates realistic queries that target specific
    activity types with different levels of complexity.
    """

    def __init__(self, templates: list[QueryTemplate] | None = None):
        """Initialize the query generator."""
        self.logger = logging.getLogger(__name__)
        self.templates = templates or self._load_default_templates()

    def generate_queries(
        self,
        count: int,
        activity_types: list[ActivityType] | None = None,
        difficulty_levels: list[str] | None = None,
    ) -> list[TestQuery]:
        """Generate test queries.

        Args:
            count: Number of queries to generate.
            activity_types: Optional list of specific activity types to target.
            difficulty_levels: Optional list of difficulty levels to include.

        Returns:
            List[TestQuery]: List of generated test queries.
        """
        self.logger.info(f"Generating {count} test queries")

        # Default to all activity types if not specified
        if activity_types is None:
            activity_types = list(ActivityType)

        # Default to all difficulty levels if not specified
        if difficulty_levels is None:
            difficulty_levels = ["easy", "medium", "hard"]

        # Generate the queries
        queries = []
        for i in range(count):
            # Select an activity type for this query
            act_type = activity_types[i % len(activity_types)]

            # Select difficulty level
            difficulty = difficulty_levels[i % len(difficulty_levels)]

            # Get relevant templates for this activity type
            relevant_templates = [t for t in self.templates if t.activity_type == act_type.name.lower()]

            if not relevant_templates:
                # Fall back to generic templates if no specific ones exist
                query_template = self._get_query_template_for_activity_type(act_type)
                query_text = query_template.replace("{index}", str(i))
                template_params = {}
            else:
                # Select a random template and generate a query
                template = random.choice(relevant_templates)

                # Generate parameter values if needed
                template_params = {}
                for param_name, param_values in template.parameters.items():
                    template_params[param_name] = random.choice(param_values)

                query_text = template.generate_query(template_params)

            # Generate synthetic matching document IDs
            # Number of matches depends on difficulty level
            match_count = self._get_match_count_for_difficulty(difficulty)
            expected_matches = self._generate_expected_matches(act_type, match_count, template_params)

            # Add metadata based on the template parameters and activity type
            metadata = {
                "template_params": template_params,
                "activity_context": self._generate_activity_metadata(act_type, template_params),
            }

            # Create query object
            query = TestQuery(
                query_text=query_text,
                activity_types=[act_type],
                difficulty=difficulty,
                expected_matches=expected_matches,
                metadata=metadata,
            )

            queries.append(query)

        return queries

    def generate_diverse_queries(
        self,
        count: int,
        activity_types: list[ActivityType] | None = None,
        difficulty_levels: list[str] | None = None,
        similarity_threshold: float = 0.85,
        max_attempts: int = 100,
    ) -> list[TestQuery]:
        """Generate a diverse set of queries, ensuring minimal redundancy.

        This method generates queries and then filters out those that are
        too similar to existing ones, to ensure a diverse test set.

        Args:
            count: The number of unique queries to generate
            activity_types: Optional list of specific activity types to target
            difficulty_levels: Optional list of difficulty levels to include
            similarity_threshold: Maximum similarity allowed between queries
            max_attempts: Maximum number of attempts to generate diverse queries

        Returns:
            List[TestQuery]: List of diverse test queries
        """
        self.logger.info(f"Generating {count} diverse test queries (threshold: {similarity_threshold})")

        diverse_queries = []
        attempts = 0

        while len(diverse_queries) < count and attempts < max_attempts:
            # Generate a candidate query
            candidate = self.generate_queries(1, activity_types, difficulty_levels)[0]
            candidate_text = candidate.query_text

            # Check similarity with existing queries
            is_diverse = True
            for existing_query in diverse_queries:
                existing_text = existing_query.query_text
                similarity = jaro_winkler_similarity(candidate_text, existing_text)

                if similarity >= similarity_threshold:
                    is_diverse = False
                    break

            # Add to diverse set if sufficiently different
            if is_diverse:
                diverse_queries.append(candidate)

            attempts += 1

        # If we couldn't get enough diverse queries, return what we have
        if len(diverse_queries) < count:
            self.logger.warning(
                f"Could only generate {len(diverse_queries)}/{count} diverse queries after {attempts} attempts",
            )

        return diverse_queries

    def analyze_query_diversity(self, queries: list[TestQuery], similarity_threshold: float = 0.85) -> dict[str, Any]:
        """Analyze the diversity of a set of queries using Jaro-Winkler similarity.

        Args:
            queries: List of test queries to analyze
            similarity_threshold: Threshold for considering queries as similar

        Returns:
            Dict[str, Any]: Dictionary with diversity metrics
        """
        self.logger.info(f"Analyzing diversity of {len(queries)} queries")

        # Extract query texts
        query_texts = [q.query_text for q in queries]

        # Calculate similarity matrix
        similarity_matrix = []
        for q1 in query_texts:
            row = []
            for q2 in query_texts:
                row.append(jaro_winkler_similarity(q1, q2))
            similarity_matrix.append(row)

        # Calculate diversity metrics
        n_queries = len(query_texts)

        # Count similar query pairs (excluding self-comparisons)
        similar_pairs = 0
        total_pairs = 0

        # Track particularly similar pairs for reporting
        high_similarity_pairs = []

        for i in range(n_queries):
            for j in range(i + 1, n_queries):  # Only count each pair once
                similarity = similarity_matrix[i][j]
                total_pairs += 1

                if similarity >= similarity_threshold:
                    similar_pairs += 1
                    high_similarity_pairs.append(
                        {"query1": query_texts[i], "query2": query_texts[j], "similarity": similarity},
                    )

        # Calculate average similarity (ignoring self-comparisons)
        total_similarity = sum(similarity_matrix[i][j] for i in range(n_queries) for j in range(i + 1, n_queries))
        avg_similarity = total_similarity / total_pairs if total_pairs > 0 else 0

        # Calculate diversity score (1 - avg_similarity)
        diversity_score = 1 - avg_similarity

        return {
            "diversity_score": diversity_score,
            "similar_query_pairs": similar_pairs,
            "total_query_pairs": total_pairs,
            "similar_pair_percent": (similar_pairs / total_pairs * 100) if total_pairs > 0 else 0,
            "average_similarity": avg_similarity,
            "high_similarity_pairs": high_similarity_pairs,
        }

    def _load_default_templates(self) -> list[QueryTemplate]:
        """Load default query templates.

        Returns:
            List[QueryTemplate]: A list of default query templates.
        """
        # Placeholder implementation - to be expanded with real templates
        return [
            QueryTemplate(
                template="Find documents I worked on while listening to {artist}",
                parameters={"artist": ["Taylor Swift", "The Beatles", "Beyoncé"]},
                activity_type="music",
                description="Query for documents with music activity context",
            ),
            QueryTemplate(
                template="Show files I accessed at {location}",
                parameters={"location": ["home", "work", "coffee shop"]},
                activity_type="location",
                description="Query for files accessed at a specific location",
            ),
            QueryTemplate(
                template="Find documents related to my {task_name} task",
                parameters={"task_name": ["coding", "writing", "research", "design"]},
                activity_type="task",
                description="Query for files related to a specific task",
            ),
            QueryTemplate(
                template="Show me files I shared during the {meeting_name} meeting",
                parameters={"meeting_name": ["team", "client", "strategy", "project"]},
                activity_type="collaboration",
                description="Query for files shared during a specific meeting",
            ),
            QueryTemplate(
                template="Find documents I saved in my {folder_name} folder",
                parameters={"folder_name": ["downloads", "documents", "projects", "work"]},
                activity_type="storage",
                description="Query for files saved in a specific folder",
            ),
            QueryTemplate(
                template="Show me files I worked on while watching {video_name}",
                parameters={"video_name": ["YouTube videos", "Netflix", "tutorials", "lectures"]},
                activity_type="media",
                description="Query for files accessed while consuming media",
            ),
        ]

    def _get_query_template_for_activity_type(self, activity_type: ActivityType) -> str:
        """Get a query template for a specific activity type.

        Args:
            activity_type: The activity type to get a template for.

        Returns:
            str: A query template for the activity type.
        """
        # Simple placeholder templates for each activity type
        templates = {
            ActivityType.MUSIC: "Find documents I worked on while listening to music track number {index}",
            ActivityType.LOCATION: "Show me files I accessed while at location {index}",
            ActivityType.TASK: "Find documents related to task {index}",
            ActivityType.COLLABORATION: "Show me files I shared during meeting {index}",
            ActivityType.STORAGE: "Find documents I saved in folder {index}",
            ActivityType.MEDIA: "Show me files I worked on while watching video {index}",
        }

        return templates.get(activity_type, "Find documents related to {index}")

    def _get_match_count_for_difficulty(self, difficulty: str) -> int:
        """Get the number of expected matches based on difficulty level.

        Args:
            difficulty: The difficulty level of the query

        Returns:
            int: The number of expected matches
        """
        # The harder the query, the fewer matches we expect
        difficulty_map = {
            "easy": random.randint(5, 15),  # Many matches for easy queries
            "medium": random.randint(3, 8),  # Moderate number of matches
            "hard": random.randint(1, 4),  # Few matches for hard queries
        }
        return difficulty_map.get(difficulty, 5)  # Default to 5 matches

    def _generate_expected_matches(
        self, activity_type: ActivityType, count: int, template_params: dict[str, str],
    ) -> list[str]:
        """Generate synthetic document IDs that should match a query.

        This method creates realistic document IDs with a consistent pattern
        that can be used as ground truth for evaluating query results.

        Args:
            activity_type: The activity type targeted by the query
            count: The number of matching documents to generate
            template_params: Template parameters used in query generation

        Returns:
            List[str]: List of document IDs that should match the query
        """
        matches = []

        # Create a deterministic but unique prefix for this activity type
        # This helps ensure consistent results across test runs
        activity_prefix = f"ablation_{activity_type.name.lower()}"

        # Use template parameters to create more specific matches
        param_string = "_".join(f"{k}_{v}".lower().replace(" ", "_") for k, v in template_params.items())

        # Generate synthetic document IDs
        for i in range(count):
            # Create a document ID with a pattern like:
            # "Objects/ablation_music_artist_taylor_swift_1"
            doc_id = f"Objects/{activity_prefix}"
            if param_string:
                doc_id += f"_{param_string}"
            doc_id += f"_{i+1}"

            matches.append(doc_id)

        return matches

    def _generate_activity_metadata(
        self, activity_type: ActivityType, template_params: dict[str, str],
    ) -> dict[str, Any]:
        """Generate activity-specific metadata for a query.

        This metadata helps provide context for the query and can be used
        for more sophisticated truth data generation.

        Args:
            activity_type: The activity type targeted by the query
            template_params: Template parameters used in query generation

        Returns:
            Dict[str, Any]: Activity-specific metadata
        """
        metadata = {"activity_type": activity_type.name}

        # Add activity-specific metadata based on template parameters
        if activity_type == ActivityType.MUSIC:
            metadata["artist"] = template_params.get("artist", "Unknown Artist")
            metadata["genre"] = random.choice(["Pop", "Rock", "Classical", "Jazz", "Hip Hop"])
            metadata["duration_minutes"] = random.randint(3, 10)

        elif activity_type == ActivityType.LOCATION:
            metadata["location"] = template_params.get("location", "Unknown Location")
            metadata["coordinates"] = {
                "latitude": round(random.uniform(-90, 90), 6),
                "longitude": round(random.uniform(-180, 180), 6),
            }
            metadata["accuracy_meters"] = random.randint(5, 50)

        elif activity_type == ActivityType.TASK:
            metadata["task_name"] = template_params.get("task_name", "Unknown Task")
            metadata["completion"] = random.uniform(0, 1)
            metadata["priority"] = random.choice(["Low", "Medium", "High"])

        elif activity_type == ActivityType.COLLABORATION:
            metadata["meeting_name"] = template_params.get("meeting_name", "Unknown Meeting")
            metadata["participants"] = random.randint(2, 10)
            metadata["duration_minutes"] = random.randint(15, 120)

        elif activity_type == ActivityType.STORAGE:
            metadata["folder_name"] = template_params.get("folder_name", "Unknown Folder")
            metadata["file_count"] = random.randint(1, 50)
            metadata["storage_type"] = random.choice(["Local", "Cloud", "Network"])

        elif activity_type == ActivityType.MEDIA:
            metadata["video_name"] = template_params.get("video_name", "Unknown Video")
            metadata["duration_minutes"] = random.randint(5, 180)
            metadata["platform"] = random.choice(["YouTube", "Netflix", "Local", "Streaming"])

        return metadata
