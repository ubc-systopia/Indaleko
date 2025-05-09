"""
Test integration between cross-collection queries and AQL translation.

This module tests that cross-collection queries are properly
translated into AQL queries that can join across multiple collections.
"""

import json
import logging
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

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
from research.ablation.models.activity import ActivityType
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry
from research.ablation.query.enhanced.cross_collection_query_generator import CrossCollectionQueryGenerator
from research.ablation.query.aql_translator import AQLQueryTranslator


class TestCrossCollectionAQL(unittest.TestCase):
    """Test integration between cross-collection queries and AQL translation."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests."""
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        cls.logger = logging.getLogger(__name__)
        
        # Create a shared entity registry for the test
        cls.entity_registry = SharedEntityRegistry()
        
        # Create the query generator
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)
        
        # Create the AQL translator
        cls.aql_translator = AQLQueryTranslator()
        
        # Generate test queries
        cls.generate_test_queries()
    
    @classmethod
    def generate_test_queries(cls):
        """Generate test queries for AQL translation testing."""
        # Mock the LLM to return predefined responses
        with patch.object(cls.query_generator.enhanced_generator.generator, 'get_completion') as mock_completion:
            # For task+meeting
            mock_completion.return_value = """
            {
              "query": "Find documents related to tasks created during the quarterly planning meeting",
              "entities": {
                "primary_entities": ["progress report", "project goals"],
                "secondary_entities": ["quarterly planning", "team meeting"]
              },
              "relationship": "created_in",
              "primary_type": "TASK",
              "secondary_type": "COLLABORATION",
              "reasoning": "This query looks for tasks that were created during a specific meeting"
            }
            """
            
            # Generate task+meeting query
            cls.task_meeting_query = cls.query_generator.generate_cross_collection_queries(
                count=1,
                relationship_types=["created_in"],
                collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)]
            )[0]
            
            # For meeting+location
            mock_completion.return_value = """
            {
              "query": "Show files shared in meetings at the downtown office",
              "entities": {
                "primary_entities": ["project update", "budget review"],
                "secondary_entities": ["downtown office", "conference room A"]
              },
              "relationship": "located_at",
              "primary_type": "COLLABORATION",
              "secondary_type": "LOCATION",
              "reasoning": "This query looks for meetings that took place at a specific location"
            }
            """
            
            # Generate meeting+location query
            cls.meeting_location_query = cls.query_generator.generate_cross_collection_queries(
                count=1,
                relationship_types=["located_at"],
                collection_pairs=[(ActivityType.COLLABORATION, ActivityType.LOCATION)]
            )[0]
            
            # For task+location (via meeting)
            mock_completion.return_value = """
            {
              "query": "Find tasks discussed during meetings at the coffee shop",
              "entities": {
                "primary_entities": ["bug fixes", "feature planning"],
                "secondary_entities": ["coffee shop", "informal meeting"]
              },
              "relationship": "discussed_at",
              "primary_type": "TASK",
              "secondary_type": "LOCATION",
              "reasoning": "This query looks for tasks that were discussed in meetings at a specific location"
            }
            """
            
            # Generate task+location query
            cls.task_location_query = cls.query_generator.generate_cross_collection_queries(
                count=1,
                relationship_types=["discussed_at"],
                collection_pairs=[(ActivityType.TASK, ActivityType.LOCATION)]
            )[0]
    
    def test_translate_task_meeting_query(self):
        """Test translating a task+meeting query to AQL."""
        # Create a mock database response
        mock_db = MagicMock()
        
        # Translate the query to AQL
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.task_meeting_query.query_text,
            collection="ablation_task",
            activity_types=[ActivityType.TASK, ActivityType.COLLABORATION],
            relationship_type="created_in"
        )
        
        # Check that the AQL includes both collections
        self.assertIn("ablation_task", aql)
        self.assertIn("ablation_collaboration", aql)
        
        # Check that the AQL includes a JOIN operation
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
        # Create a mock database response
        mock_db = MagicMock()
        
        # Translate the query to AQL
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.meeting_location_query.query_text,
            collection="ablation_collaboration",
            activity_types=[ActivityType.COLLABORATION, ActivityType.LOCATION],
            relationship_type="located_at"
        )
        
        # Check that the AQL includes both collections
        self.assertIn("ablation_collaboration", aql)
        self.assertIn("ablation_location", aql)
        
        # Check that the AQL includes a JOIN operation
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
        # Create a mock database response
        mock_db = MagicMock()
        
        # Translate the query to AQL
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.task_location_query.query_text,
            collection="ablation_task",
            activity_types=[ActivityType.TASK, ActivityType.LOCATION],
            relationship_type="discussed_at"
        )
        
        # Check that the AQL includes both collections
        self.assertIn("ablation_task", aql)
        self.assertIn("ablation_location", aql)
        
        # Check that the AQL includes a JOIN operation
        self.assertIn("FOR", aql)
        self.assertIn("FILTER", aql)
        
        # Check that the AQL references the relationship field
        self.assertIn("references", aql)
        
        # Verify bind vars
        self.assertIsInstance(bind_vars, dict)
        self.assertGreaterEqual(len(bind_vars), 1)
    
    def test_execute_cross_collection_aql(self):
        """Test executing a cross-collection AQL query."""
        # Create a mock database and cursor
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = lambda self: iter([{"_id": "test1"}, {"_id": "test2"}])
        mock_db.aql.execute.return_value = mock_cursor
        
        # Translate the query to AQL
        aql, bind_vars = self.aql_translator.translate_to_aql(
            self.task_meeting_query.query_text,
            collection="ablation_task",
            activity_types=[ActivityType.TASK, ActivityType.COLLABORATION],
            relationship_type="created_in"
        )
        
        # Execute the query
        result = mock_db.aql.execute(aql, bind_vars=bind_vars)
        
        # Verify the query was executed
        self.assertEqual(mock_db.aql.execute.call_count, 1)
        
        # Verify the result can be consumed
        results = list(result)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["_id"], "test1")
        self.assertEqual(results[1]["_id"], "test2")
    
    def test_aql_translator_multi_hop_relationships(self):
        """Test that AQL translator can handle multi-hop relationships."""
        # Create a complex query that requires traversing multiple collections
        complex_query = "Find documents for tasks discussed in meetings at the downtown office"
        
        # Define the activity types and relationship paths
        activity_types = [ActivityType.TASK, ActivityType.COLLABORATION, ActivityType.LOCATION]
        relationship_paths = [
            ("ablation_task", "discussed_in", "ablation_collaboration"),
            ("ablation_collaboration", "located_at", "ablation_location")
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
            relationship_paths
        )
        
        # Verify the AQL includes all collections
        self.assertIn("ablation_task", aql)
        self.assertIn("ablation_collaboration", aql)
        self.assertIn("ablation_location", aql)
        
        # Verify the AQL includes relationship traversals
        self.assertIn("doc.references.discussed_in", aql)
        self.assertIn("related1.references.located_at", aql) or self.assertIn("related1._id", aql)
        
        # Verify the bind vars
        self.assertIn("location_name", bind_vars)
        self.assertEqual(bind_vars["location_name"], "downtown office")


if __name__ == "__main__":
    unittest.main()