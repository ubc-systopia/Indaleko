"""
Query Relationship Detection for Indaleko.

This module provides the QueryRelationshipDetector class, which
analyzes relationships between queries to identify patterns like
refinements, broadening, pivots, and more.

Project Indaleko
Copyright (C) 2025 Tony Mason

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
import re
import sys
import uuid
from enum import Enum
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.context.navigation import QueryNavigator

# pylint: enable=wrong-import-position


class RelationshipType(str, Enum):
    """Types of relationships between queries."""

    REFINEMENT = "refinement"
    BROADENING = "broadening"
    PIVOT = "pivot"
    BACKTRACK = "backtrack"
    UNRELATED = "unrelated"


class QueryRelationshipDetector:
    """
    Detects relationships between queries.

    This class analyzes queries to identify patterns and relationships
    such as refinements, broadening, pivots, and more.
    """

    def __init__(self, db_config=None, debug=False, use_llm=False):
        """
        Initialize the QueryRelationshipDetector.

        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug logging
            use_llm: Whether to use LLM-based relationship detection
        """
        # Set up logging
        self._logger = logging.getLogger("QueryRelationshipDetector")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # Initialize dependencies
        self._navigator = QueryNavigator(db_config=db_config, debug=debug)
        self._db_config = db_config
        self._use_llm = use_llm

        # Initialize LLM connector if requested
        self._llm_connector = None
        if use_llm:
            try:
                from query.utils.llm_connector.llm_base import LLMConnector

                self._llm_connector = LLMConnector()
                self._logger.info(
                    "Initialized LLM connector for relationship detection",
                )
            except Exception as e:
                self._logger.error(f"Error initializing LLM connector: {e}")
                self._use_llm = False

    def detect_relationship(
        self,
        query1: str | uuid.UUID | dict[str, Any],
        query2: str | uuid.UUID | dict[str, Any],
    ) -> tuple[RelationshipType, float]:
        """
        Detect the relationship between two queries.

        Args:
            query1: First query (text, ID, or query dictionary)
            query2: Second query (text, ID, or query dictionary)

        Returns:
            Tuple of (relationship_type, confidence)
        """
        # Extract query text from various input types
        query1_text = self._get_query_text(query1)
        query2_text = self._get_query_text(query2)

        if not query1_text or not query2_text:
            return RelationshipType.UNRELATED, 0.0

        # Use LLM-based detection if available
        if self._use_llm and self._llm_connector:
            return self._detect_relationship_llm(query1_text, query2_text)

        # Otherwise, use rule-based detection
        return self._detect_relationship_rules(query1_text, query2_text)

    def _get_query_text(
        self, query: str | uuid.UUID | dict[str, Any],
    ) -> str | None:
        """
        Extract query text from various input types.

        Args:
            query: Query input (text, ID, or query dictionary)

        Returns:
            Query text or None if not found
        """
        if isinstance(query, str):
            return query

        if isinstance(query, uuid.UUID):
            query_data = self._navigator.get_query_by_id(query)
            return query_data.get("query_text") if query_data else None

        if isinstance(query, dict) and "query_text" in query:
            return query["query_text"]

        return None

    def _detect_relationship_rules(
        self, query1: str, query2: str,
    ) -> tuple[RelationshipType, float]:
        """
        Detect the relationship between queries using rule-based methods.

        Args:
            query1: First query text
            query2: Second query text

        Returns:
            Tuple of (relationship_type, confidence)
        """
        # Normalize queries
        q1 = query1.lower()
        q2 = query2.lower()

        # Extract words and tokens
        q1_words = set(re.findall(r"\b\w+\b", q1))
        q2_words = set(re.findall(r"\b\w+\b", q2))

        # Calculate word overlap metrics
        common_words = q1_words.intersection(q2_words)
        total_words = q1_words.union(q2_words)

        # Jaccard similarity
        jaccard = len(common_words) / len(total_words) if total_words else 0

        # Simple substring check (for exact containment)
        q1_contains_q2 = q2 in q1
        q2_contains_q1 = q1 in q2

        # Check if either query is a simple reformulation (same words, different order)
        same_words_different_order = q1_words == q2_words and q1 != q2

        # Check for refinement patterns
        refinement_patterns = [
            r"(only|just|specifically).*",
            r".*\bfilter\b.*",
            r".*\bwhere\b.*",
            r".*\bfrom\b.*",
            r".*(created|modified|authored)\s+(by|in|on|before|after).*",
            r".*\btype:.*",
            r".*\.(pdf|doc|txt|xlsx).*",
        ]

        refinement_detected = False
        for pattern in refinement_patterns:
            if not re.search(pattern, q1, re.IGNORECASE) and re.search(
                pattern, q2, re.IGNORECASE,
            ):
                refinement_detected = True
                break

        # Check for broadening patterns
        broadening_patterns = [
            r"all.*",
            r"any.*",
            r"every.*",
            r"without.*\bfilter\b.*",
            r".*\bor\b.*",
        ]

        broadening_detected = False
        for pattern in broadening_patterns:
            if not re.search(pattern, q1, re.IGNORECASE) and re.search(
                pattern, q2, re.IGNORECASE,
            ):
                broadening_detected = True
                break

        # Check for backtracking (returning to a previous query)
        backtracking = same_words_different_order or q1 == q2

        # Make relationship determination
        if refinement_detected or (
            q2_contains_q1 and not q1_contains_q2 and len(q2) > len(q1)
        ):
            # Refinement: query2 builds upon query1 by adding constraints
            return RelationshipType.REFINEMENT, min(0.9, 0.5 + jaccard * 0.5)

        if broadening_detected or (
            q1_contains_q2 and not q2_contains_q1 and len(q1) > len(q2)
        ):
            # Broadening: query2 relaxes constraints from query1
            return RelationshipType.BROADENING, min(0.9, 0.5 + jaccard * 0.5)

        if backtracking:
            # Backtracking: returning to a previous query or formulation
            return RelationshipType.BACKTRACK, 0.9 if q1 == q2 else 0.7

        if jaccard > 0.5:
            # Pivot: significant word overlap but different focus
            return RelationshipType.PIVOT, jaccard

        # Default: unrelated
        return RelationshipType.UNRELATED, 1.0 - jaccard

    def _detect_relationship_llm(
        self, query1: str, query2: str,
    ) -> tuple[RelationshipType, float]:
        """
        Detect the relationship between queries using LLM-based methods.

        Args:
            query1: First query text
            query2: Second query text

        Returns:
            Tuple of (relationship_type, confidence)
        """
        # This would use the LLM connector to classify the relationship
        # For now, it's a stub that we can implement once the basic
        # functionality is working

        # Fall back to rule-based detection
        self._logger.warning(
            "LLM-based detection not implemented, falling back to rules",
        )
        return self._detect_relationship_rules(query1, query2)

    def detect_relationship_batch(
        self, queries: list[str | uuid.UUID | dict[str, Any]],
    ) -> list[tuple[RelationshipType, float]]:
        """
        Detect relationships between consecutive queries in a list.

        Args:
            queries: List of queries (text, ID, or query dictionary)

        Returns:
            List of (relationship_type, confidence) tuples
        """
        if not queries or len(queries) < 2:
            return []

        relationships = []

        for i in range(len(queries) - 1):
            rel_type, confidence = self.detect_relationship(queries[i], queries[i + 1])
            relationships.append((rel_type, confidence))

        return relationships

    def detect_refinements(
        self,
        query1: str | uuid.UUID | dict[str, Any],
        query2: str | uuid.UUID | dict[str, Any],
    ) -> bool:
        """
        Detect if query2 is a refinement of query1.

        Args:
            query1: First query (text, ID, or query dictionary)
            query2: Second query (text, ID, or query dictionary)

        Returns:
            True if query2 is a refinement of query1
        """
        rel_type, confidence = self.detect_relationship(query1, query2)
        return rel_type == RelationshipType.REFINEMENT and confidence >= 0.5

    def detect_broadening(
        self,
        query1: str | uuid.UUID | dict[str, Any],
        query2: str | uuid.UUID | dict[str, Any],
    ) -> bool:
        """
        Detect if query2 is a broadening of query1.

        Args:
            query1: First query (text, ID, or query dictionary)
            query2: Second query (text, ID, or query dictionary)

        Returns:
            True if query2 is a broadening of query1
        """
        rel_type, confidence = self.detect_relationship(query1, query2)
        return rel_type == RelationshipType.BROADENING and confidence >= 0.5

    def detect_pivot(
        self,
        query1: str | uuid.UUID | dict[str, Any],
        query2: str | uuid.UUID | dict[str, Any],
    ) -> bool:
        """
        Detect if query2 is a pivot from query1.

        Args:
            query1: First query (text, ID, or query dictionary)
            query2: Second query (text, ID, or query dictionary)

        Returns:
            True if query2 is a pivot from query1
        """
        rel_type, confidence = self.detect_relationship(query1, query2)
        return rel_type == RelationshipType.PIVOT and confidence >= 0.5

    def analyze_query_sequence(
        self, query_id: uuid.UUID, max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        Analyze the sequence of queries leading to the specified query.

        Args:
            query_id: Query ID to analyze the path for
            max_depth: Maximum path depth to analyze

        Returns:
            Dictionary with analysis results
        """
        # Get the query path
        path = self._navigator.get_query_path(query_id, max_depth=max_depth)

        if not path:
            return {
                "path_length": 0,
                "relationships": [],
                "exploration_pattern": "unknown",
                "focus_shifts": 0,
            }

        # Detect relationships between consecutive queries
        relationships = []
        for i in range(len(path) - 1):
            rel_type, confidence = self.detect_relationship(path[i], path[i + 1])
            relationships.append(
                {
                    "from_query": path[i]["query_id"],
                    "to_query": path[i + 1]["query_id"],
                    "relationship": rel_type,
                    "confidence": confidence,
                },
            )

        # Count focus shifts (pivots)
        focus_shifts = sum(
            1 for rel in relationships if rel["relationship"] == RelationshipType.PIVOT
        )

        # Determine exploration pattern
        exploration_pattern = self._determine_exploration_pattern(relationships)

        return {
            "path_length": len(path),
            "relationships": relationships,
            "exploration_pattern": exploration_pattern,
            "focus_shifts": focus_shifts,
        }

    def _determine_exploration_pattern(
        self, relationships: list[dict[str, Any]],
    ) -> str:
        """
        Determine the overall exploration pattern from relationships.

        Args:
            relationships: List of relationship dictionaries

        Returns:
            Exploration pattern description
        """
        if not relationships:
            return "unknown"

        # Count relationship types
        counts = {}
        for rel in relationships:
            rel_type = rel["relationship"]
            counts[rel_type] = counts.get(rel_type, 0) + 1

        # Calculate proportions
        total = len(relationships)
        proportions = {rel_type: count / total for rel_type, count in counts.items()}

        # Determine dominant pattern
        if proportions.get(RelationshipType.REFINEMENT, 0) > 0.5:
            return "systematic-narrowing"

        if proportions.get(RelationshipType.BROADENING, 0) > 0.5:
            return "systematic-broadening"

        if proportions.get(RelationshipType.PIVOT, 0) > 0.5:
            return "exploratory"

        if proportions.get(RelationshipType.BACKTRACK, 0) > 0.3:
            return "depth-first-search"

        # Mixed or unclear pattern
        return "mixed"


def main():
    """Test functionality of QueryRelationshipDetector."""
    logging.basicConfig(level=logging.DEBUG)

    # Create detector
    detector = QueryRelationshipDetector(debug=True)

    # Test with some example queries
    query_pairs = [
        ("Find documents about Indaleko", "Find PDF documents about Indaleko"),
        ("Find PDF documents about Indaleko", "Find documents about Indaleko"),
        ("Find documents about Indaleko", "Show me the authors of Indaleko documents"),
        ("Find documents about Indaleko", "Find documents about Windows"),
        ("Find documents about Indaleko", "Find documents about Indaleko"),
    ]

    print("Testing relationship detection:")
    for i, (q1, q2) in enumerate(query_pairs):
        rel_type, confidence = detector.detect_relationship(q1, q2)
        print(f"\nQuery Pair {i+1}:")
        print(f"  Q1: {q1}")
        print(f"  Q2: {q2}")
        print(f"  Relationship: {rel_type.value}")
        print(f"  Confidence: {confidence:.2f}")

        # Test specific relationship methods
        print(f"  Is Refinement: {detector.detect_refinements(q1, q2)}")
        print(f"  Is Broadening: {detector.detect_broadening(q1, q2)}")
        print(f"  Is Pivot: {detector.detect_pivot(q1, q2)}")

    # Test batch detection
    queries = [
        "Find documents about Indaleko",
        "Find PDF documents about Indaleko",
        "Find PDF documents about Indaleko created last week",
        "Show me all documents about Indaleko",
        "Who authored Indaleko documents?",
    ]

    print("\nBatch relationship detection:")
    relationships = detector.detect_relationship_batch(queries)

    for i, (rel_type, confidence) in enumerate(relationships):
        print(f"  {i+1}. {queries[i]} → {queries[i+1]}")
        print(f"     {rel_type.value} ({confidence:.2f})")


if __name__ == "__main__":
    main()
