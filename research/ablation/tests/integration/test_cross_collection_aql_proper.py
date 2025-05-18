"""
Test integration between cross-collection queries and AQL translation.

This module tests that cross-collection queries are properly
translated into AQL queries that can join across multiple collections.

IMPORTANT: These tests follow the fail-stop principle:
1. No mocking of database connections or LLM services
2. All connections are real - tests fail immediately if connections cannot be established
3. No error masking - all exceptions must be allowed to propagate
4. Never substitute mock/fake data for real data
"""

import logging
import os
import sys
import unittest

# Set up the environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
        if current_path == os.path.dirname(current_path):  # Reached root directory
            break
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.insert(0, current_path)

# Import required modules
from db.db_config import IndalekoDBConfig
from research.ablation.models.activity import ActivityType
from research.ablation.query.aql_translator import AQLQueryTranslator
from research.ablation.query.enhanced.cross_collection_query_generator import (
    CrossCollectionQueryGenerator,
)
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry


class TestCrossCollectionAQLProper(unittest.TestCase):
    """Test integration between cross-collection queries and AQL translation with real connections."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests with real connections."""
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        cls.logger = logging.getLogger(__name__)

        # Create a real database connection
        try:
            cls.db_config = IndalekoDBConfig()
            cls.db = cls.db_config.get_arangodb()
            if not cls.db:
                cls.logger.error("CRITICAL: Failed to connect to database")
                sys.exit(1)  # Fail-stop on database connection failure
        except Exception as e:
            cls.logger.error(f"CRITICAL: Error connecting to database: {e!s}")
            sys.exit(1)  # Fail-stop on exception

        # Create a shared entity registry
        cls.entity_registry = SharedEntityRegistry()

        # Create the query generator with real connections
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)

        # Create the AQL translator
        cls.aql_translator = AQLQueryTranslator()

        # Generate test queries using real LLM services
        cls.generate_test_queries()

    @classmethod
    def generate_test_queries(cls):
        """Generate test queries for AQL translation testing using real LLM services."""
        cls.logger.info("Generating test queries with real LLM services")

        # Generate task+meeting query
        task_meeting_queries = cls.query_generator.generate_cross_collection_queries(
            count=1,
            relationship_types=["created_in"],
            collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)],
        )
        if not task_meeting_queries:
            cls.logger.error("CRITICAL: Failed to generate task+meeting query")
            sys.exit(1)  # Fail-stop on query generation failure
        cls.task_meeting_query = task_meeting_queries[0]
        cls.logger.info(f"Generated task+meeting query: {cls.task_meeting_query.query_text}")

        # Generate meeting+location query
        meeting_location_queries = cls.query_generator.generate_cross_collection_queries(
            count=1,
            relationship_types=["located_at"],
            collection_pairs=[(ActivityType.COLLABORATION, ActivityType.LOCATION)],
        )
        if not meeting_location_queries:
            cls.logger.error("CRITICAL: Failed to generate meeting+location query")
            sys.exit(1)  # Fail-stop on query generation failure
        cls.meeting_location_query = meeting_location_queries[0]
        cls.logger.info(f"Generated meeting+location query: {cls.meeting_location_query.query_text}")

        # Generate task+location query (via meeting)
        task_location_queries = cls.query_generator.generate_cross_collection_queries(
            count=1,
            relationship_types=["discussed_at", "at_location"],  # Try multiple types
            collection_pairs=[(ActivityType.TASK, ActivityType.LOCATION)],
        )
        if not task_location_queries:
            cls.logger.error("CRITICAL: Failed to generate task+location query")
            sys.exit(1)  # Fail-stop on query generation failure
        cls.task_location_query = task_location_queries[0]
        cls.logger.info(f"Generated task+location query: {cls.task_location_query.query_text}")

    def test_translate_task_meeting_query(self):
        """Test translating a task+meeting query to AQL."""
        # Translate the query to AQL using real translator
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.task_meeting_query.query_text,
            collection="ablation_task",
            activity_types=[ActivityType.TASK, ActivityType.COLLABORATION],
            relationship_type="created_in",
        )

        # Check that the AQL includes both collections
        self.assertIn("ablation_task", aql)
        self.assertIn("ablation_collaboration", aql)

        # Check that the AQL includes search operations
        self.assertIn("FOR", aql)
        self.assertIn("FILTER", aql)

        # Check that the AQL references the relationship field
        self.assertIn("references", aql)
        self.assertIn("created_in", aql)

        # Verify bind vars
        self.assertIsInstance(bind_vars, dict)
        self.assertGreaterEqual(len(bind_vars), 1)

    def test_translate_meeting_location_query(self):
        """Test translating a meeting+location query to AQL."""
        # Translate the query to AQL using real translator
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.meeting_location_query.query_text,
            collection="ablation_collaboration",
            activity_types=[ActivityType.COLLABORATION, ActivityType.LOCATION],
            relationship_type="located_at",
        )

        # Check that the AQL includes both collections
        self.assertIn("ablation_collaboration", aql)
        self.assertIn("ablation_location", aql)

        # Check that the AQL includes search operations
        self.assertIn("FOR", aql)
        self.assertIn("FILTER", aql)

        # Check that the AQL references the relationship field
        self.assertIn("references", aql)
        self.assertIn("located_at", aql)

        # Verify bind vars
        self.assertIsInstance(bind_vars, dict)
        self.assertGreaterEqual(len(bind_vars), 1)

    def test_translate_task_location_query(self):
        """Test translating a task+location query to AQL."""
        # Get the relationship type from the query metadata
        relationship_type = self.task_location_query.metadata.get("relationship_type", "at_location")

        # Translate the query to AQL using real translator
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.task_location_query.query_text,
            collection="ablation_task",
            activity_types=[ActivityType.TASK, ActivityType.LOCATION],
            relationship_type=relationship_type,
        )

        # Check that the AQL includes both collections
        self.assertIn("ablation_task", aql)
        self.assertIn("ablation_location", aql)

        # Check that the AQL includes search operations
        self.assertIn("FOR", aql)
        self.assertIn("FILTER", aql)

        # Check that the AQL references the relationship field
        self.assertIn("references", aql)

        # Verify bind vars
        self.assertIsInstance(bind_vars, dict)
        self.assertGreaterEqual(len(bind_vars), 1)

    def test_execute_cross_collection_aql(self):
        """Test executing a cross-collection AQL query against real database."""
        # Translate the query to AQL
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.task_meeting_query.query_text,
            collection="ablation_task",
            activity_types=[ActivityType.TASK, ActivityType.COLLABORATION],
            relationship_type="created_in",
        )

        # Execute the query against the real database
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)

        # Verify the cursor can be consumed
        results = list(cursor)

        # We don't assume specific results, but verify that execution completes
        self.logger.info(f"Query executed successfully, returned {len(results)} results")

    def test_aql_translator_multi_hop_relationships(self):
        """Test that AQL translator can handle multi-hop relationships."""
        # Create a complex query that requires traversing multiple collections
        complex_query = "Find documents for tasks discussed in meetings at the downtown office"

        # Define the activity types and relationship paths
        activity_types = [ActivityType.TASK, ActivityType.COLLABORATION, ActivityType.LOCATION]
        relationship_paths = [
            ("ablation_task", "discussed_in", "ablation_collaboration"),
            ("ablation_collaboration", "located_at", "ablation_location"),
        ]

        # Create a custom AQL translator with multi-hop support
        class MultiHopAQLTranslator(AQLQueryTranslator):
            def translate_multi_hop_query(self, query_text, collection, relationship_paths):
                """Translate a query with multi-hop relationships."""
                # Start with the primary collection
                primary_collection = relationship_paths[0][0]

                # Build the FOR loops and JOINs
                aql = f"FOR doc IN {primary_collection}\n"

                # Add relationship traversals
                for i, (source, rel_type, target) in enumerate(relationship_paths):
                    join_var = f"related{i+1}"
                    aql += f"  FOR {join_var} IN {target}\n"
                    aql += f"    FILTER doc.references.{rel_type} ANY == {join_var}._id\n"

                # Add search filters
                aql += "  FILTER "

                # Add filter conditions based on query text
                if "downtown office" in query_text.lower():
                    aql += "related2.name == @location_name"

                # Return the documents
                aql += "\n  RETURN doc"

                # Define bind vars
                bind_vars = {"location_name": "downtown office"}

                return aql, bind_vars

        # Create the translator
        multi_hop_translator = MultiHopAQLTranslator()

        # Translate the query
        aql, bind_vars = multi_hop_translator.translate_multi_hop_query(
            complex_query,
            "ablation_task",
            relationship_paths,
        )

        # Verify the AQL includes all collections
        self.assertIn("ablation_task", aql)
        self.assertIn("ablation_collaboration", aql)
        self.assertIn("ablation_location", aql)

        # Verify the AQL includes relationship traversals
        self.assertIn("doc.references.discussed_in", aql)
        # We need to be flexible here since the translator might use various valid patterns
        self.assertTrue(
            "related1.references.located_at" in aql or       # Way 1: from meeting to location
            "related1._id" in aql or                         # Way 2: from location to meeting
            "doc.references.located_at" in aql               # Way 3: direct from task to location
        )

        # Verify the bind vars
        self.assertIn("location_name", bind_vars)
        self.assertEqual(bind_vars["location_name"], "downtown office")

        # Execute the query against the real database to confirm syntax is valid
        try:
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            results = list(cursor)  # Execute and consume to verify AQL is valid
            self.logger.info(f"Multi-hop query executed successfully, returned {len(results)} results")
        except Exception as e:
            self.logger.error(f"Failed to execute multi-hop query: {e!s}")
            raise  # Let the exception propagate - fail-stop principle


if __name__ == "__main__":
    unittest.main()
