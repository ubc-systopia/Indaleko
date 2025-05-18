"""
Tests for the query generator module.

This module contains unit tests for the query generation functionality
in the ablation study framework.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Any

from tools.ablation.query.generator import QueryGenerator


class TestQueryGenerator(unittest.TestCase):
    """Test case for the QueryGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.query_generator = QueryGenerator()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_generate_query_text(self):
        """Test generating query text for each activity type."""
        for activity_type in ["music", "location", "task", "collaboration", "storage", "media"]:
            query_text = self.query_generator._generate_query_text(activity_type)

            # Check that the query is a non-empty string
            self.assertIsInstance(query_text, str)
            self.assertGreater(len(query_text), 0)

            # Check that placeholders have been filled in
            self.assertNotIn("{", query_text)
            self.assertNotIn("}", query_text)

    def test_generate_queries(self):
        """Test generating multiple queries."""
        for activity_type in ["music", "location", "task", "collaboration", "storage", "media"]:
            queries = self.query_generator.generate_queries(activity_type, 5)

            # Check that we get the right number of queries
            self.assertEqual(len(queries), 5)

            # Check that each query has the expected fields
            for query in queries:
                self.assertIn("id", query)
                self.assertIn("text", query)
                self.assertIn("activity_type", query)
                self.assertIn("components", query)
                self.assertIn("timestamp", query)

                # Check that the activity type is correct
                self.assertEqual(query["activity_type"], activity_type)

                # Check that the components have the expected structure
                components = query["components"]
                self.assertIsInstance(components, dict)

                # Components might be empty if extraction failed
                if components:
                    # Check that the components have the expected structure
                    if "entities" in components:
                        self.assertIsInstance(components["entities"], list)

                    if "attributes" in components:
                        self.assertIsInstance(components["attributes"], list)

                    if "relationships" in components:
                        self.assertIsInstance(components["relationships"], list)

                    if "temporal" in components:
                        self.assertIsInstance(components["temporal"], dict)

    def test_parse_query_rule_based(self):
        """Test parsing a query with the rule-based method."""
        # Test a music query
        query = "What songs did I listen to by Taylor Swift last week?"
        components = self.query_generator._extract_components_rule_based(query, "music")

        # Check that the components have the expected structure
        self.assertIsInstance(components, dict)
        self.assertIn("entities", components)
        self.assertIn("attributes", components)
        self.assertIn("relationships", components)
        self.assertIn("temporal", components)

        # Check that we extracted the artist entity
        found_artist = False
        for entity in components["entities"]:
            if entity["name"] == "Taylor Swift" and entity["type"] == "artist":
                found_artist = True
                break

        self.assertTrue(found_artist, "Failed to extract 'Taylor Swift' as an artist entity")

        # Check that we extracted the temporal information
        self.assertEqual(components["temporal"]["period"], "last week")

    def test_save_and_load_queries(self):
        """Test saving and loading queries."""
        # Generate some queries
        queries = self.query_generator.generate_queries("music", 5)

        # Save the queries
        output_path = self.temp_path / "queries.json"
        self.query_generator.save_queries(queries, output_path)

        # Check that the file exists
        self.assertTrue(output_path.exists())

        # Load the queries
        loaded_queries = self.query_generator.load_queries(output_path)

        # Check that we got the same queries back
        self.assertEqual(len(loaded_queries), len(queries))
        self.assertEqual(loaded_queries, queries)

    def test_invalid_activity_type(self):
        """Test that an invalid activity type raises an error."""
        with self.assertRaises(ValueError):
            self.query_generator.generate_queries("invalid_type", 5)


if __name__ == "__main__":
    unittest.main()
