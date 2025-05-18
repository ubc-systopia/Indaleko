"""Unit tests for query diversity analysis functionality."""

import unittest
import uuid
from datetime import UTC, datetime

from research.ablation.models.activity import ActivityType
from research.ablation.query.generator import QueryGenerator, TestQuery


class TestQueryDiversity(unittest.TestCase):
    """Test case for the query diversity analysis functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.query_generator = QueryGenerator()

        # Create some test queries with known similarity patterns
        self.identical_queries = [
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I worked on while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I worked on while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
        ]

        self.similar_queries = [
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I worked on while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I created while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
        ]

        self.dissimilar_queries = [
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I worked on while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Show files I accessed at the coffee shop",
                activity_types=[ActivityType.LOCATION],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
        ]

        self.mixed_queries = [
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I worked on while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents I created while listening to Taylor Swift",
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Show files I accessed at the coffee shop",
                activity_types=[ActivityType.LOCATION],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
            TestQuery(
                query_id=uuid.uuid4(),
                query_text="Find documents related to my coding task",
                activity_types=[ActivityType.TASK],
                created_at=datetime.now(UTC),
                difficulty="medium",
            ),
        ]

    def test_identical_queries_diversity(self):
        """Test diversity analysis with identical queries."""
        results = self.query_generator.analyze_query_diversity(self.identical_queries)

        # Expect very low diversity
        self.assertEqual(results["diversity_score"], 0.0)
        self.assertEqual(results["similar_query_pairs"], 1)
        self.assertEqual(results["total_query_pairs"], 1)
        self.assertEqual(results["similar_pair_percent"], 100.0)

    def test_similar_queries_diversity(self):
        """Test diversity analysis with similar queries."""
        results = self.query_generator.analyze_query_diversity(self.similar_queries)

        # Expect moderate diversity
        self.assertGreater(results["diversity_score"], 0.0)
        self.assertLess(results["diversity_score"], 0.5)
        self.assertEqual(results["similar_query_pairs"], 1)
        self.assertEqual(results["total_query_pairs"], 1)

    def test_dissimilar_queries_diversity(self):
        """Test diversity analysis with dissimilar queries."""
        results = self.query_generator.analyze_query_diversity(self.dissimilar_queries)

        # Expect high diversity
        self.assertGreater(results["diversity_score"], 0.5)
        self.assertEqual(results["similar_query_pairs"], 0)
        self.assertEqual(results["total_query_pairs"], 1)
        self.assertEqual(results["similar_pair_percent"], 0.0)

    def test_mixed_queries_diversity(self):
        """Test diversity analysis with a mix of similar and dissimilar queries."""
        results = self.query_generator.analyze_query_diversity(self.mixed_queries)

        # Expect moderate diversity
        self.assertGreater(results["diversity_score"], 0.0)
        self.assertLess(results["diversity_score"], 1.0)
        self.assertGreater(results["total_query_pairs"], 0)

    def test_generate_diverse_queries(self):
        """Test generation of diverse queries."""
        # Generate 10 diverse queries
        queries = self.query_generator.generate_diverse_queries(10)

        # Check that we got some queries
        self.assertGreater(len(queries), 0)

        # Analyze their diversity
        results = self.query_generator.analyze_query_diversity(queries)

        # Expect high diversity
        self.assertGreater(results["diversity_score"], 0.7)


if __name__ == "__main__":
    unittest.main()
