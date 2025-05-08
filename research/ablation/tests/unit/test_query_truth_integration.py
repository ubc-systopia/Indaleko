"""Unit tests for the query-truth integration functionality."""

import unittest

from research.ablation.models.activity import ActivityType
from research.ablation.query.generator import QueryGenerator


class TestQueryTruthIntegration(unittest.TestCase):
    """Test case for the query-truth integration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.query_generator = QueryGenerator()

    def test_expected_matches_generation(self):
        """Test that queries are generated with expected matches."""
        # Generate test queries
        queries = self.query_generator.generate_queries(10)

        # Check that all queries have expected matches
        for query in queries:
            self.assertIsNotNone(query.expected_matches)
            self.assertGreater(len(query.expected_matches), 0)

            # Expected matches should be a list of strings
            self.assertIsInstance(query.expected_matches, list)
            for match_id in query.expected_matches:
                self.assertIsInstance(match_id, str)

            # Each match ID should follow our pattern based on activity type
            activity_prefix = f"ablation_{query.activity_types[0].name.lower()}"
            for match_id in query.expected_matches:
                self.assertIn(activity_prefix, match_id)

    def test_match_count_by_difficulty(self):
        """Test that match count varies by difficulty level."""
        # Generate queries with different difficulty levels
        easy_queries = self.query_generator.generate_queries(10, difficulty_levels=["easy"])
        medium_queries = self.query_generator.generate_queries(10, difficulty_levels=["medium"])
        hard_queries = self.query_generator.generate_queries(10, difficulty_levels=["hard"])

        # Calculate average match counts
        avg_easy_matches = sum(len(q.expected_matches) for q in easy_queries) / len(easy_queries)
        avg_medium_matches = sum(len(q.expected_matches) for q in medium_queries) / len(medium_queries)
        avg_hard_matches = sum(len(q.expected_matches) for q in hard_queries) / len(hard_queries)

        # Easy queries should generally have more matches than hard queries
        self.assertGreater(avg_easy_matches, avg_hard_matches)

    def test_activity_specific_patterns(self):
        """Test that expected matches follow activity-specific patterns."""
        # Generate queries for each activity type
        for activity_type in ActivityType:
            queries = self.query_generator.generate_queries(5, activity_types=[activity_type])

            # Check that matches follow activity-specific patterns
            for query in queries:
                self.assertEqual(query.activity_types[0], activity_type)

                # Expected matches should contain activity type name
                for match_id in query.expected_matches:
                    self.assertIn(activity_type.name.lower(), match_id)
                    self.assertTrue(match_id.startswith("Objects/ablation_"))

    def test_metadata_generation(self):
        """Test that appropriate metadata is generated for each query."""
        # Generate queries for each activity type
        for activity_type in ActivityType:
            queries = self.query_generator.generate_queries(2, activity_types=[activity_type])

            for query in queries:
                # Check that metadata exists
                self.assertIn("template_params", query.metadata)
                self.assertIn("activity_context", query.metadata)

                # Check activity-specific metadata fields
                activity_context = query.metadata["activity_context"]
                self.assertEqual(activity_context["activity_type"], activity_type.name)

                if activity_type == ActivityType.MUSIC:
                    self.assertIn("artist", activity_context)
                    self.assertIn("genre", activity_context)

                elif activity_type == ActivityType.LOCATION:
                    self.assertIn("location", activity_context)
                    self.assertIn("coordinates", activity_context)

                elif activity_type == ActivityType.TASK:
                    self.assertIn("task_name", activity_context)
                    self.assertIn("priority", activity_context)

                elif activity_type == ActivityType.COLLABORATION:
                    self.assertIn("meeting_name", activity_context)
                    self.assertIn("participants", activity_context)

                elif activity_type == ActivityType.STORAGE:
                    self.assertIn("folder_name", activity_context)
                    self.assertIn("storage_type", activity_context)

                elif activity_type == ActivityType.MEDIA:
                    self.assertIn("video_name", activity_context)
                    self.assertIn("platform", activity_context)

    def test_diverse_queries_with_expected_matches(self):
        """Test that diverse queries also have expected matches."""
        # Generate diverse queries
        queries = self.query_generator.generate_diverse_queries(10)

        # Check expected matches
        for query in queries:
            self.assertIsNotNone(query.expected_matches)
            self.assertGreater(len(query.expected_matches), 0)

        # Verify diversity
        results = self.query_generator.analyze_query_diversity(queries)
        self.assertGreater(results["diversity_score"], 0.7)


if __name__ == "__main__":
    unittest.main()
