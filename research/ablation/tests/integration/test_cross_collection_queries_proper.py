"""Integration tests for cross-collection query generation with real connections.

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
from research.ablation.models.relationship_patterns import (
    LocationCollaborationPattern,
    TaskCollaborationPattern,
)
from research.ablation.query.enhanced.cross_collection_query_generator import (
    CrossCollectionQueryGenerator,
)
from research.ablation.recorders.enhanced_base import EnhancedActivityRecorder
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry


class TestCrossCollectionQueriesIntegrationProper(unittest.TestCase):
    """Integration tests for cross-collection query generation with real connections."""

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

        # Create enhanced recorders with real connections and the registry
        cls.task_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry, db_config=cls.db_config)
        cls.collaboration_recorder = EnhancedActivityRecorder(
            entity_registry=cls.entity_registry,
            db_config=cls.db_config,
        )
        cls.location_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry, db_config=cls.db_config)
        cls.music_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry, db_config=cls.db_config)

        # Set up relationship patterns
        cls.task_collaboration_pattern = TaskCollaborationPattern(entity_registry=cls.entity_registry)

        cls.location_collaboration_pattern = LocationCollaborationPattern(entity_registry=cls.entity_registry)

        # Generate test data with relationships using real recorders
        cls.generate_test_data()

        # Create the query generator with real registry
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)

    @classmethod
    def generate_test_data(cls):
        """Generate test data with cross-collection relationships."""
        cls.logger.info("Generating test data with relationships")

        # Generate task+meeting relationships
        for i in range(3):
            # Generate a meeting with tasks
            meeting, tasks = cls.task_collaboration_pattern.generate_meeting_with_tasks()
            cls.logger.info(f"Generated meeting '{meeting.get('event_type', 'Unknown')}' with {len(tasks)} tasks")

            # Record the meeting with real recorder
            try:
                meeting_key = cls.collaboration_recorder.record_with_references(meeting)
                if not meeting_key:
                    cls.logger.error("CRITICAL: Failed to record meeting")
                    sys.exit(1)  # Fail-stop on recording failure
                cls.logger.info(f"Recorded meeting with key {meeting_key}")
            except Exception as e:
                cls.logger.error(f"CRITICAL: Error recording meeting: {e!s}")
                sys.exit(1)  # Fail-stop on exception

            # Record the tasks with references to the meeting
            for task in tasks:
                try:
                    task_key = cls.task_recorder.record_with_references(task)
                    if not task_key:
                        cls.logger.error("CRITICAL: Failed to record task")
                        sys.exit(1)  # Fail-stop on recording failure
                    cls.logger.info(f"Recorded task with key {task_key}")
                except Exception as e:
                    cls.logger.error(f"CRITICAL: Error recording task: {e!s}")
                    sys.exit(1)  # Fail-stop on exception

        # Generate task+related meetings
        for i in range(2):
            # Generate a task with related meetings
            task, meetings = cls.task_collaboration_pattern.generate_task_with_related_meetings()
            cls.logger.info(
                f"Generated task '{task.get('task_name', 'Unknown')}' with {len(meetings)} related meetings",
            )

            # Record the task with real recorder
            try:
                task_key = cls.task_recorder.record_with_references(task)
                if not task_key:
                    cls.logger.error("CRITICAL: Failed to record task")
                    sys.exit(1)  # Fail-stop on recording failure
                cls.logger.info(f"Recorded task with key {task_key}")
            except Exception as e:
                cls.logger.error(f"CRITICAL: Error recording task: {e!s}")
                sys.exit(1)  # Fail-stop on exception

            # Record the meetings with references to the task
            for meeting in meetings:
                try:
                    meeting_key = cls.collaboration_recorder.record_with_references(meeting)
                    if not meeting_key:
                        cls.logger.error("CRITICAL: Failed to record meeting")
                        sys.exit(1)  # Fail-stop on recording failure
                    cls.logger.info(f"Recorded meeting with key {meeting_key}")
                except Exception as e:
                    cls.logger.error(f"CRITICAL: Error recording meeting: {e!s}")
                    sys.exit(1)  # Fail-stop on exception

        # Generate meeting+location relationships
        for i in range(3):
            # Generate a meeting at a location
            location, meeting = cls.location_collaboration_pattern.generate_meeting_at_location()
            cls.logger.info(
                f"Generated meeting '{meeting.get('event_type', 'Unknown')}' at location '{location.get('location_name', 'Unknown')}'",
            )

            # Record the location with real recorder
            try:
                location_key = cls.location_recorder.record_with_references(location)
                if not location_key:
                    cls.logger.error("CRITICAL: Failed to record location")
                    sys.exit(1)  # Fail-stop on recording failure
                cls.logger.info(f"Recorded location with key {location_key}")
            except Exception as e:
                cls.logger.error(f"CRITICAL: Error recording location: {e!s}")
                sys.exit(1)  # Fail-stop on exception

            # Record the meeting with real recorder
            try:
                meeting_key = cls.collaboration_recorder.record_with_references(meeting)
                if not meeting_key:
                    cls.logger.error("CRITICAL: Failed to record meeting")
                    sys.exit(1)  # Fail-stop on recording failure
                cls.logger.info(f"Recorded meeting with key {meeting_key}")
            except Exception as e:
                cls.logger.error(f"CRITICAL: Error recording meeting: {e!s}")
                sys.exit(1)  # Fail-stop on exception

    def test_registry_population(self):
        """Test that the registry has been populated with entities and relationships."""
        # Check that the registry has task entities
        task_entities = self.entity_registry.get_entities_by_collection("ablation_task")
        self.assertGreaterEqual(len(task_entities), 1)
        self.logger.info(f"Found {len(task_entities)} task entities in registry")

        # Check that the registry has meeting entities
        meeting_entities = self.entity_registry.get_entities_by_collection("ablation_collaboration")
        self.assertGreaterEqual(len(meeting_entities), 1)
        self.logger.info(f"Found {len(meeting_entities)} meeting entities in registry")

        # Check that the registry has location entities
        location_entities = self.entity_registry.get_entities_by_collection("ablation_location")
        self.assertGreaterEqual(len(location_entities), 1)
        self.logger.info(f"Found {len(location_entities)} location entities in registry")

        # Pick a task entity and verify it has relationships
        if task_entities:
            task_id = next(iter(task_entities.keys()))
            task_relationships = self.entity_registry.get_entity_references(task_id)
            self.assertGreaterEqual(len(task_relationships), 1)
            self.logger.info(f"Task {task_id} has {len(task_relationships)} relationships")

        # Pick a meeting entity and verify it has relationships
        if meeting_entities:
            meeting_id = next(iter(meeting_entities.keys()))
            meeting_relationships = self.entity_registry.get_entity_references(meeting_id)
            self.assertGreaterEqual(len(meeting_relationships), 1)
            self.logger.info(f"Meeting {meeting_id} has {len(meeting_relationships)} relationships")

    def test_generate_cross_collection_queries_with_registry(self):
        """Test that cross-collection query generation uses the entity registry."""
        # Call the method with specific relationship and collection pairs
        queries = self.query_generator.generate_cross_collection_queries(
            count=1,
            relationship_types=["created_in", "discussed_in"],
            collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)],
        )

        # Verify at least one query was generated
        self.assertGreaterEqual(len(queries), 1)
        self.logger.info(f"Generated {len(queries)} cross-collection queries")

        # Verify the first query has the expected structure
        query = queries[0]
        self.assertTrue(hasattr(query, "query_text"))
        self.assertTrue(hasattr(query, "activity_types"))
        self.assertTrue(hasattr(query, "expected_matches"))
        self.assertTrue(hasattr(query, "metadata"))

        # Verify the query metadata
        self.assertEqual(query.activity_types, [ActivityType.TASK, ActivityType.COLLABORATION])
        self.assertTrue(query.metadata["cross_collection"])
        self.assertIn("relationship_type", query.metadata)
        self.assertEqual(query.metadata["primary_activity"], "TASK")
        self.assertEqual(query.metadata["secondary_activity"], "COLLABORATION")

        # Verify the query text is non-empty
        self.assertTrue(query.query_text)
        self.logger.info(f"Generated query text: {query.query_text}")

        # Verify expected matches exist
        self.assertTrue(query.expected_matches)
        self.logger.info(f"Query has {len(query.expected_matches)} expected matches")

    def test_find_real_entity_matches(self):
        """Test finding real entity matches based on registry relationships."""
        # Manually register some test entities and relationships
        task_id = self.entity_registry.register_entity("task", "Test Real Entity Match Task", "ablation_task")
        meeting_id = self.entity_registry.register_entity(
            "meeting",
            "Test Real Entity Match Meeting",
            "ablation_collaboration",
        )
        location_id = self.entity_registry.register_entity(
            "location",
            "Test Real Entity Match Location",
            "ablation_location",
        )

        # Create relationships
        self.entity_registry.add_relationship(task_id, meeting_id, "created_in")
        self.entity_registry.add_relationship(meeting_id, task_id, "has_tasks")
        self.entity_registry.add_relationship(meeting_id, location_id, "located_at")

        # Look for tasks created in meetings
        task_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
        )

        # We should find our test task
        self.assertGreaterEqual(len(task_matches), 1)
        self.assertIn(task_id, task_matches)
        self.logger.info(f"Found {len(task_matches)} tasks with 'created_in' relationship")

        # Look for meetings with tasks
        meeting_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION,
            ActivityType.TASK,
            "has_tasks",
        )

        # We should find our test meeting
        self.assertGreaterEqual(len(meeting_matches), 1)
        self.assertIn(meeting_id, meeting_matches)
        self.logger.info(f"Found {len(meeting_matches)} meetings with 'has_tasks' relationship")

        # Look for meetings at locations
        location_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION,
            ActivityType.LOCATION,
            "located_at",
        )

        # We should find our test meeting
        self.assertGreaterEqual(len(location_matches), 1)
        self.assertIn(meeting_id, location_matches)
        self.logger.info(f"Found {len(location_matches)} meetings with 'located_at' relationship")

    def test_generate_expected_matches_with_real_entities(self):
        """Test generating expected matches using real entities from the registry."""
        # Set up some test entities and relationships
        task_id = self.entity_registry.register_entity("task", "Test Expected Match Task", "ablation_task")
        meeting_id = self.entity_registry.register_entity(
            "meeting",
            "Test Expected Match Meeting",
            "ablation_collaboration",
        )

        # Create relationship
        self.entity_registry.add_relationship(task_id, meeting_id, "created_in")

        # Generate expected matches for tasks created in meetings
        matches = self.query_generator._generate_cross_collection_matches(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
        )

        # We should get at least some matches based on real relationships
        self.assertGreaterEqual(len(matches), 1)

        # Check that the matches reference our entity
        expected_match = f"Objects/{task_id}"
        self.assertIn(expected_match, matches)
        self.logger.info(f"Generated {len(matches)} expected matches for cross-collection query")

    def test_generate_cross_collection_queries_all_pairs(self):
        """Test generating cross-collection queries for all default collection pairs."""
        # Generate 1 query for each default collection pair
        all_queries = []
        for pair in self.query_generator.DEFAULT_COLLECTION_PAIRS:
            primary, secondary = pair
            for rel_type in self.query_generator.DEFAULT_RELATIONSHIP_TYPES:
                queries = self.query_generator.generate_cross_collection_queries(
                    count=1,
                    relationship_types=[rel_type],
                    collection_pairs=[(primary, secondary)],
                )
                if queries:
                    all_queries.extend(queries)
                    self.logger.info(
                        f"Generated query for {primary.name}-{secondary.name} with relationship {rel_type}",
                    )
                    break  # Move to next pair after first success

        # We should get several queries across different collection pairs
        self.assertGreaterEqual(len(all_queries), 1)

        # Log the generated queries
        self.logger.info(f"Generated {len(all_queries)} queries across collection pairs")
        for q in all_queries:
            self.logger.info(f"Query: {q.query_text}")
            self.logger.info(f"Activity types: {[a.name for a in q.activity_types]}")
            self.logger.info(f"Relationship: {q.metadata.get('relationship_type')}")
            self.logger.info(f"Expected matches: {len(q.expected_matches)}")
            self.logger.info("---")


if __name__ == "__main__":
    unittest.main()
