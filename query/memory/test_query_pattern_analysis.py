"""
Test script for the Advanced Query Pattern Analysis module.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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

import argparse
import logging
import os
import sys
import unittest
import uuid

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.query_pattern_analysis import (
    ProactiveSuggestion,
    QueryChain,
    QueryChainType,
    QueryPattern,
    QueryPatternAnalyzer,
    QueryRefinementType,
)


# pylint: enable=wrong-import-position


class TestQueryPatternAnalysis(unittest.TestCase):
    """Test cases for the Query Pattern Analysis module."""

    def setUp(self):
        """Set up test case."""
        # Mock database config
        self.mock_db_config = MagicMock()
        self.mock_db = MagicMock()
        self.mock_db_config.db = self.mock_db

        # Create analyzer with mock config
        self.analyzer = QueryPatternAnalyzer(self.mock_db_config)

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def test_init(self):
        """Test initialization."""
        assert self.analyzer is not None
        assert self.analyzer.db_config == self.mock_db_config
        assert self.analyzer.data is not None

    @patch(
        "query.memory.query_pattern_analysis.QueryPatternAnalyzer._process_query_entities",
    )
    def test_load_query_history(self, mock_process):
        """Test loading query history from the database."""
        # Mock collection
        mock_collection = MagicMock()
        self.mock_db.has_collection.return_value = True
        self.mock_db.collection.return_value = mock_collection

        # Mock cursor with query documents
        mock_cursor = [
            {
                "_key": "query1",
                "Record": {"Timestamp": datetime.now(UTC).isoformat()},
                "QueryHistory": {"OriginalQuery": "test query 1"},
            },
            {
                "_key": "query2",
                "Record": {"Timestamp": datetime.now(UTC).isoformat()},
                "QueryHistory": {"OriginalQuery": "test query 2"},
            },
        ]
        mock_collection.find.return_value = mock_cursor

        # Call the method
        result = self.analyzer.load_query_history()

        # Assertions
        assert result == 2
        assert len(self.analyzer.data.queries) == 2
        assert len(self.analyzer.data.query_timeline) == 2
        mock_process.assert_called()

    def test_extract_entities(self):
        """Test extracting entities from query data."""
        # Test with QueryHistory path
        query_data = {
            "QueryHistory": {
                "ParsedResults": {
                    "Entities": [{"name": "entity1"}, {"name": "entity2"}],
                },
            },
        }

        entities = self.analyzer._extract_entities(query_data)
        assert entities == ["entity1", "entity2"]

        # Test with direct ParsedResults path
        query_data = {
            "ParsedResults": {"Entities": [{"name": "entity3"}, {"name": "entity4"}]},
        }

        entities = self.analyzer._extract_entities(query_data)
        assert entities == ["entity3", "entity4"]

        # Test with empty data
        query_data = {}
        entities = self.analyzer._extract_entities(query_data)
        assert entities == []

    def test_query_has_results(self):
        """Test checking if a query has results."""
        # Test with results
        query_data = {"QueryHistory": {"RawResults": [{"result": 1}, {"result": 2}]}}

        assert self.analyzer._query_has_results(query_data)

        # Test with empty results
        query_data = {"QueryHistory": {"RawResults": []}}

        assert not self.analyzer._query_has_results(query_data)

        # Test with alternative path
        query_data = {"RawResults": [{"result": 1}]}

        assert self.analyzer._query_has_results(query_data)

    def test_calculate_query_similarity(self):
        """Test calculating similarity between queries."""
        # Test identical queries
        similarity = self.analyzer._calculate_query_similarity(
            "test query",
            "test query",
        )
        assert similarity == 1.0

        # Test similar queries
        similarity = self.analyzer._calculate_query_similarity(
            "test query",
            "test queries",
        )
        assert similarity > 0.7

        # Test dissimilar queries
        similarity = self.analyzer._calculate_query_similarity(
            "test query",
            "completely different",
        )
        assert similarity < 0.3

        # Test with empty strings
        similarity = self.analyzer._calculate_query_similarity("", "")
        assert similarity == 0.0

        similarity = self.analyzer._calculate_query_similarity("test", "")
        assert similarity == 0.0

    def test_determine_refinement_type(self):
        """Test determining refinement type between queries."""
        # Test temporal refinement
        refinement_type = self.analyzer._determine_refinement_type(
            "show me documents",
            "show me documents from last week",
            ["documents"],
            ["documents", "week"],
        )
        assert refinement_type == QueryRefinementType.TEMPORAL_REFINEMENT

        # Test location refinement
        refinement_type = self.analyzer._determine_refinement_type(
            "show me restaurants",
            "show me restaurants near downtown",
            ["restaurants"],
            ["restaurants", "downtown"],
        )
        assert refinement_type == QueryRefinementType.LOCATION_REFINEMENT

        # Test entity change
        refinement_type = self.analyzer._determine_refinement_type(
            "show me documents about Python",
            "show me documents about JavaScript",
            ["documents", "Python"],
            ["documents", "JavaScript"],
        )
        assert refinement_type == QueryRefinementType.CHANGE_ENTITY

        # Test narrowing
        refinement_type = self.analyzer._determine_refinement_type(
            "show me documents",
            "show me PDF documents about programming",
            ["documents"],
            ["documents", "PDF", "programming"],
        )
        assert refinement_type == QueryRefinementType.NARROW

    def test_process_query_entities(self):
        """Test processing and analyzing entities in a query."""
        # Create a test query
        query_id = "test_query_1"
        query_data = {
            "Record": {"Timestamp": datetime.now(UTC).isoformat()},
            "QueryHistory": {
                "OriginalQuery": "show me documents about Python",
                "ParsedResults": {
                    "Entities": [{"name": "documents"}, {"name": "Python"}],
                    "Intent": "search",
                },
                "RawResults": [{"result": 1}],  # Has results
            },
        }

        # Process query entities
        self.analyzer._process_query_entities(query_id, query_data)

        # Verify entity usage was created
        assert "documents" in self.analyzer.data.entity_usage
        assert "Python" in self.analyzer.data.entity_usage

        # Verify entity usage data
        documents_usage = self.analyzer.data.entity_usage["documents"]
        assert documents_usage.mention_count == 1
        assert documents_usage.success_rate == 1.0  # Had results
        assert documents_usage.intents == {"search": 1}
        assert documents_usage.co_occurring_entities == {"Python": 1}

        # Process another query with the same entities
        query_id2 = "test_query_2"
        query_data2 = {
            "Record": {"Timestamp": datetime.now(UTC).isoformat()},
            "QueryHistory": {
                "OriginalQuery": "find Python documents about web development",
                "ParsedResults": {
                    "Entities": [
                        {"name": "documents"},
                        {"name": "Python"},
                        {"name": "web development"},
                    ],
                    "Intent": "search",
                },
                "RawResults": [],  # No results
            },
        }

        # Process second query
        self.analyzer._process_query_entities(query_id2, query_data2)

        # Verify entity usage was updated
        documents_usage = self.analyzer.data.entity_usage["documents"]
        assert documents_usage.mention_count == 2
        assert documents_usage.success_rate == 0.5  # 1 out of 2 had results
        assert documents_usage.intents == {"search": 2}
        assert documents_usage.co_occurring_entities["Python"] == 2
        assert documents_usage.co_occurring_entities["web development"] == 1

    def create_mock_query_timeline(self):
        """Create a mock query timeline for testing."""
        # Create a base timestamp
        base_time = datetime.now(UTC) - timedelta(days=1)

        # Create a series of queries in a timeline
        timeline = []
        queries = {}

        # Query 1
        query_id1 = str(uuid.uuid4())
        timestamp1 = base_time
        query1 = {
            "_key": query_id1,
            "Record": {"Timestamp": timestamp1.isoformat()},
            "QueryHistory": {
                "OriginalQuery": "show me documents about Python",
                "ParsedResults": {
                    "Entities": [{"name": "documents"}, {"name": "Python"}],
                    "Intent": "search",
                },
                "RawResults": [{"result": 1}],
            },
        }
        timeline.append((query_id1, timestamp1))
        queries[query_id1] = query1

        # Query 2 - a refinement 5 minutes later
        query_id2 = str(uuid.uuid4())
        timestamp2 = base_time + timedelta(minutes=5)
        query2 = {
            "_key": query_id2,
            "Record": {"Timestamp": timestamp2.isoformat()},
            "QueryHistory": {
                "OriginalQuery": "show me PDF documents about Python",
                "ParsedResults": {
                    "Entities": [
                        {"name": "documents"},
                        {"name": "Python"},
                        {"name": "PDF"},
                    ],
                    "Intent": "search",
                },
                "RawResults": [{"result": 1}, {"result": 2}],
            },
        }
        timeline.append((query_id2, timestamp2))
        queries[query_id2] = query2

        # Query 3 - unrelated query 1 hour later
        query_id3 = str(uuid.uuid4())
        timestamp3 = base_time + timedelta(hours=1)
        query3 = {
            "_key": query_id3,
            "Record": {"Timestamp": timestamp3.isoformat()},
            "QueryHistory": {
                "OriginalQuery": "show me information about JavaScript",
                "ParsedResults": {
                    "Entities": [{"name": "information"}, {"name": "JavaScript"}],
                    "Intent": "search",
                },
                "RawResults": [{"result": 1}],
            },
        }
        timeline.append((query_id3, timestamp3))
        queries[query_id3] = query3

        # Query 4 - a refinement of Query 3, 10 minutes later
        query_id4 = str(uuid.uuid4())
        timestamp4 = timestamp3 + timedelta(minutes=10)
        query4 = {
            "_key": query_id4,
            "Record": {"Timestamp": timestamp4.isoformat()},
            "QueryHistory": {
                "OriginalQuery": "show me information about JavaScript frameworks",
                "ParsedResults": {
                    "Entities": [
                        {"name": "information"},
                        {"name": "JavaScript"},
                        {"name": "frameworks"},
                    ],
                    "Intent": "search",
                },
                "RawResults": [],  # No results
            },
        }
        timeline.append((query_id4, timestamp4))
        queries[query_id4] = query4

        # Query 5 - another refinement of Query 4, 5 minutes later
        query_id5 = str(uuid.uuid4())
        timestamp5 = timestamp4 + timedelta(minutes=5)
        query5 = {
            "_key": query_id5,
            "Record": {"Timestamp": timestamp5.isoformat()},
            "QueryHistory": {
                "OriginalQuery": "show me popular JavaScript frameworks",
                "ParsedResults": {
                    "Entities": [
                        {"name": "popular"},
                        {"name": "JavaScript"},
                        {"name": "frameworks"},
                    ],
                    "Intent": "search",
                },
                "RawResults": [{"result": 1}, {"result": 2}, {"result": 3}],
            },
        }
        timeline.append((query_id5, timestamp5))
        queries[query_id5] = query5

        return timeline, queries

    def test_analyze_query_chains(self):
        """Test analyzing query chains."""
        # Create mock data
        timeline, queries = self.create_mock_query_timeline()

        # Set up the analyzer with mock data
        self.analyzer.data.query_timeline = timeline
        self.analyzer.data.queries = queries

        # Analyze chains
        chains = self.analyzer.analyze_query_chains()

        # Verify chains were detected
        assert len(chains) >= 2  # Should detect at least 2 chains

        # Verify chain properties
        for chain in chains:
            # Check that chains have multiple queries
            assert len(chain.queries) >= 2

            # Check that chains have timestamps
            assert chain.start_time is not None
            assert chain.end_time is not None

            # Check that chain duration is calculated
            assert chain.duration > 0

            # Check that transition patterns are recorded
            assert len(chain.transition_patterns) >= 1

            # If this is a refinement chain, check shared entities
            if chain.chain_type == QueryChainType.REFINEMENT:
                assert len(chain.shared_entities) >= 1

    def test_detect_query_patterns(self):
        """Test detecting patterns in query behavior."""
        # Create mock data
        timeline, queries = self.create_mock_query_timeline()

        # Set up the analyzer with mock data
        self.analyzer.data.query_timeline = timeline
        self.analyzer.data.queries = queries

        # Set minimum pattern support to 1 for testing
        self.analyzer.min_pattern_support = 1

        # Process entities for each query
        for query_id, _ in timeline:
            self.analyzer._process_query_entities(query_id, queries[query_id])

        # Analyze chains (needed for refinement patterns)
        chains = self.analyzer.analyze_query_chains()
        self.analyzer.data.query_chains = chains

        # Detect patterns
        patterns = self.analyzer.detect_query_patterns()

        # Verify patterns were detected
        assert len(patterns) >= 1

        # Verify pattern properties
        for pattern in patterns:
            assert pattern.pattern_name is not None
            assert pattern.description is not None
            assert pattern.pattern_type is not None
            assert pattern.confidence >= 0.0
            assert pattern.confidence <= 1.0

    def test_generate_query_suggestions(self):
        """Test generating query suggestions based on patterns."""
        # Create a mock pattern
        pattern = QueryPattern(
            pattern_name="Test Pattern",
            description="Test pattern description",
            pattern_type="entity_cooccurrence",
            confidence=0.8,
            entities_involved=["Python", "programming"],
            observation_count=5,
        )

        # Add pattern to analyzer
        self.analyzer.data.query_patterns = [pattern]

        # Generate suggestions with context
        context = {"entities": ["Python"]}

        suggestions = self.analyzer.generate_query_suggestions(context)

        # Verify suggestions were generated
        assert len(suggestions) >= 1

        # Verify suggestion properties
        for suggestion in suggestions:
            assert suggestion.title is not None
            assert suggestion.content is not None
            assert suggestion.suggestion_type is not None
            assert suggestion.confidence >= 0.0
            assert suggestion.confidence <= 1.0

    def test_calculate_metrics(self):
        """Test calculating metrics on query behavior."""
        # Create mock data
        timeline, queries = self.create_mock_query_timeline()

        # Set up the analyzer with mock data
        self.analyzer.data.query_timeline = timeline
        self.analyzer.data.queries = queries

        # Analyze chains (needed for chain metrics)
        chains = self.analyzer.analyze_query_chains()
        self.analyzer.data.query_chains = chains

        # Calculate metrics
        metrics = self.analyzer.calculate_metrics()

        # Verify metrics
        assert metrics is not None
        assert metrics.total_queries == len(timeline)
        assert metrics.successful_queries >= 0
        assert metrics.success_rate >= 0.0
        assert metrics.success_rate <= 1.0

        # Verify temporal metrics
        assert metrics.queries_by_hour is not None
        assert metrics.queries_by_day is not None

        # Verify content metrics
        assert metrics.top_entities is not None
        assert metrics.top_intents is not None

        # Verify chain metrics
        assert metrics.avg_chain_length >= 0.0

    def test_analyze_and_generate(self):
        """Test the complete analysis and suggestion generation flow."""
        # Mock the component methods
        with patch.object(self.analyzer, "load_query_history", return_value=5):
            with patch.object(
                self.analyzer,
                "analyze_query_chains",
            ) as mock_analyze_chains:
                with patch.object(
                    self.analyzer,
                    "detect_query_patterns",
                ) as mock_detect_patterns:
                    with patch.object(
                        self.analyzer,
                        "calculate_metrics",
                    ) as mock_calculate_metrics:
                        with patch.object(
                            self.analyzer,
                            "generate_query_suggestions",
                        ) as mock_generate_suggestions:
                            # Mock return values
                            mock_analyze_chains.return_value = [MagicMock(spec=QueryChain) for _ in range(2)]
                            mock_detect_patterns.return_value = [MagicMock(spec=QueryPattern) for _ in range(3)]
                            mock_calculate_metrics.return_value = MagicMock()
                            mock_calculate_metrics.return_value.success_rate = 0.75
                            mock_calculate_metrics.return_value.refinement_rate = 0.5
                            mock_calculate_metrics.return_value.top_entities = {
                                "Python": 3,
                                "JavaScript": 2,
                            }
                            mock_calculate_metrics.return_value.top_intents = {
                                "search": 4,
                                "list": 1,
                            }
                            mock_generate_suggestions.return_value = [
                                MagicMock(spec=ProactiveSuggestion) for _ in range(2)
                            ]

                            # Run the analysis
                            summary, suggestions = self.analyzer.analyze_and_generate()

                            # Verify all component methods were called
                            self.analyzer.load_query_history.assert_called_once()
                            mock_analyze_chains.assert_called_once()
                            mock_detect_patterns.assert_called_once()
                            mock_calculate_metrics.assert_called_once()
                            mock_generate_suggestions.assert_called_once()

                            # Verify summary
                            assert summary["query_count"] == 5
                            assert summary["chain_count"] == 2
                            assert summary["pattern_count"] == 3
                            assert summary["success_rate"] == 0.75
                            assert summary["refinement_rate"] == 0.5

                            # Verify suggestions
                            assert len(suggestions) == 2


class MockQueryGeneratorTests(unittest.TestCase):
    """Tests with a mock query generator for creating test data."""

    def setUp(self):
        """Set up test case."""
        self.analyzer = QueryPatternAnalyzer()

    def test_with_generated_queries(self):
        """Test using generated queries."""
        # Generate mock query data
        self.analyzer.data.queries = {}
        self.analyzer.data.query_timeline = []

        # Create base time for consistent testing
        base_time = datetime.now(UTC) - timedelta(days=5)

        # Generate a series of queries about Python programming
        python_query_times = [
            base_time + timedelta(hours=10),  # Morning
            base_time + timedelta(hours=11),  # Morning
            base_time + timedelta(days=1, hours=10),  # Next day morning
            base_time + timedelta(days=2, hours=10),  # Third day morning
        ]

        for i, timestamp in enumerate(python_query_times):
            query_id = f"python_{i}"
            query = self.generate_mock_query(
                query_id=query_id,
                timestamp=timestamp,
                query_text=f"show me python programming resources {i+1}",
                entities=["python", "programming", "resources"],
                has_results=True,
            )
            self.analyzer.data.queries[query_id] = query
            self.analyzer.data.query_timeline.append((query_id, timestamp))
            self.analyzer._process_query_entities(query_id, query)

        # Generate a series of queries about JavaScript in the evening
        js_query_times = [
            base_time + timedelta(hours=18),  # Evening
            base_time + timedelta(hours=19),  # Evening
            base_time + timedelta(days=1, hours=18),  # Next day evening
            base_time + timedelta(days=2, hours=18),  # Third day evening
        ]

        for i, timestamp in enumerate(js_query_times):
            query_id = f"js_{i}"
            query = self.generate_mock_query(
                query_id=query_id,
                timestamp=timestamp,
                query_text=f"show me javascript frameworks {i+1}",
                entities=["javascript", "frameworks"],
                has_results=(i != 2),  # One query without results
            )
            self.analyzer.data.queries[query_id] = query
            self.analyzer.data.query_timeline.append((query_id, timestamp))
            self.analyzer._process_query_entities(query_id, query)

        # Generate a refinement chain
        chain_base = base_time + timedelta(days=3)

        query_id1 = "chain_1"
        timestamp1 = chain_base
        query1 = self.generate_mock_query(
            query_id=query_id1,
            timestamp=timestamp1,
            query_text="show me database systems",
            entities=["database", "systems"],
            has_results=True,
        )
        self.analyzer.data.queries[query_id1] = query1
        self.analyzer.data.query_timeline.append((query_id1, timestamp1))
        self.analyzer._process_query_entities(query_id1, query1)

        query_id2 = "chain_2"
        timestamp2 = chain_base + timedelta(minutes=5)
        query2 = self.generate_mock_query(
            query_id=query_id2,
            timestamp=timestamp2,
            query_text="show me SQL database systems",
            entities=["SQL", "database", "systems"],
            has_results=True,
        )
        self.analyzer.data.queries[query_id2] = query2
        self.analyzer.data.query_timeline.append((query_id2, timestamp2))
        self.analyzer._process_query_entities(query_id2, query2)

        query_id3 = "chain_3"
        timestamp3 = chain_base + timedelta(minutes=10)
        query3 = self.generate_mock_query(
            query_id=query_id3,
            timestamp=timestamp3,
            query_text="show me open source SQL database systems",
            entities=["open source", "SQL", "database", "systems"],
            has_results=True,
        )
        self.analyzer.data.queries[query_id3] = query3
        self.analyzer.data.query_timeline.append((query_id3, timestamp3))
        self.analyzer._process_query_entities(query_id3, query3)

        # Sort timeline by timestamp
        self.analyzer.data.query_timeline.sort(key=lambda x: x[1])

        # Set minimum pattern support to 3 for testing
        self.analyzer.min_pattern_support = 3

        # Run analysis
        # 1. Analyze chains
        chains = self.analyzer.analyze_query_chains()
        assert len(chains) >= 1

        # 2. Detect patterns
        patterns = self.analyzer.detect_query_patterns()
        assert len(patterns) >= 1

        # 3. Calculate metrics
        metrics = self.analyzer.calculate_metrics()
        assert metrics is not None

        # 4. Generate suggestions
        suggestions = self.analyzer.generate_query_suggestions()

        # Log all the results
        logging.info(f"Generated {len(chains)} chains")
        logging.info(f"Detected {len(patterns)} patterns")
        logging.info(f"Generated {len(suggestions)} suggestions")

        # Detailed logging for patterns
        for pattern in patterns:
            logging.info(f"Pattern: {pattern.pattern_name}")
            logging.info(f"  Description: {pattern.description}")
            logging.info(f"  Type: {pattern.pattern_type}")
            logging.info(f"  Confidence: {pattern.confidence}")

        # Check for temporal patterns (hour-based)
        has_hour_pattern = any(p.pattern_type == "temporal_hour" for p in patterns)
        # Note: This might fail if not enough patterns for the hours, but should generally work
        assert has_hour_pattern, "Should detect at least one temporal hour pattern"

    def generate_mock_query(
        self,
        query_id,
        timestamp,
        query_text,
        entities,
        has_results,
    ):
        """Generate a mock query document."""
        entity_objects = [{"name": entity} for entity in entities]

        raw_results = []
        if has_results:
            raw_results = [{"result": 1}]

        return {
            "_key": query_id,
            "Record": {"Timestamp": timestamp.isoformat()},
            "QueryHistory": {
                "OriginalQuery": query_text,
                "ParsedResults": {"Entities": entity_objects, "Intent": "search"},
                "RawResults": raw_results,
                "ElapsedTime": 0.5,
            },
        }


def run_tests():
    """Run the unit tests."""
    unittest.main()


def run_demo():
    """Run a demonstration of the Query Pattern Analyzer."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create analyzer
    analyzer = QueryPatternAnalyzer()

    # Generate mock data
    test_generator = MockQueryGeneratorTests()
    test_generator.setUp()
    test_generator.test_with_generated_queries()

    # Use the analyzer with the mock data
    analyzer = test_generator.analyzer

    # Run analysis and generate suggestions
    summary, suggestions = analyzer.analyze_and_generate()

    # Print results

    if summary["top_entities"]:
        pass

    if summary["top_intents"]:
        pass


    for _i, _pattern in enumerate(analyzer.data.query_patterns, 1):
        pass

    if suggestions:
        for _i, _suggestion in enumerate(suggestions, 1):
            pass


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Query Pattern Analysis")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with mock data",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.test:
        run_tests()
    elif args.demo:
        run_demo()
    else:
        # Default to demo
        run_demo()


if __name__ == "__main__":
    main()
