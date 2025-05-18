"""Test utilities for the ablation framework."""

import logging
import random
import string
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from ..db.database import AblationDatabaseManager
from ..error import AblationErrorHandler, ErrorSeverity
from ..models.activity import ActivityType


def random_string(length: int = 10) -> str:
    """Generate a random string.

    Args:
        length: The length of the string to generate.

    Returns:
        str: The random string.
    """
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_datetime(
    start_date: datetime = datetime(2020, 1, 1, tzinfo=UTC),
    end_date: datetime = datetime.now(UTC),
) -> datetime:
    """Generate a random datetime between start_date and end_date.

    Args:
        start_date: The start date.
        end_date: The end date.

    Returns:
        datetime: The random datetime.
    """
    delta = end_date - start_date
    seconds = random.randint(0, int(delta.total_seconds()))
    return start_date + timedelta(seconds=seconds)


def random_activity_data(activity_type: ActivityType) -> dict[str, Any]:
    """Generate random activity data for the specified type.

    Args:
        activity_type: The type of activity.

    Returns:
        Dict[str, Any]: The random activity data.
    """
    data = {
        "id": str(uuid4()),
        "activity_type": activity_type.name,
        "created_at": random_datetime().isoformat(),
        "modified_at": random_datetime().isoformat(),
        "source": "ablation_test",
        "semantic_attributes": {},
    }

    # Add type-specific fields
    if activity_type == ActivityType.MUSIC:
        data.update(
            {
                "artist": random_string(),
                "track": random_string(),
                "album": random_string(),
                "genre": random.choice(["Rock", "Pop", "Jazz", "Classical", "Hip Hop"]),
                "duration_seconds": random.randint(60, 600),
                "platform": random.choice(["Spotify", "Apple Music", "YouTube Music"]),
            },
        )
    elif activity_type == ActivityType.LOCATION:
        data.update(
            {
                "location_name": random.choice(["Home", "Work", "Coffee Shop", "Gym", "Park"]),
                "coordinates": {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180),
                },
                "accuracy_meters": random.uniform(1, 100),
                "location_type": random.choice(["GPS", "WiFi", "Cell", "Manual"]),
                "device": random.choice(["Phone", "Laptop", "Watch", "Tablet"]),
            },
        )
    elif activity_type == ActivityType.TASK:
        data.update(
            {
                "task_name": random_string(),
                "application": random.choice(["Browser", "Editor", "Terminal", "Email"]),
                "window_title": random_string(),
                "duration_seconds": random.randint(60, 3600),
                "is_active": random.choice([True, False]),
            },
        )
    elif activity_type == ActivityType.COLLABORATION:
        data.update(
            {
                "platform": random.choice(["Teams", "Slack", "Email", "Zoom"]),
                "event_type": random.choice(["Meeting", "Chat", "File Share", "Email"]),
                "participants": [random_string() for _ in range(random.randint(1, 5))],
                "content": random_string(30),
                "duration_seconds": random.randint(60, 3600),
            },
        )
    elif activity_type == ActivityType.STORAGE:
        data.update(
            {
                "path": f"/{random_string()}/{random_string()}.{random.choice(['txt', 'pdf', 'doc', 'jpg'])}",
                "file_type": random.choice(["Document", "Image", "Video", "Audio"]),
                "size_bytes": random.randint(1024, 1024 * 1024 * 10),
                "operation": random.choice(["Create", "Read", "Update", "Delete"]),
                "timestamp": random_datetime().isoformat(),
            },
        )
    elif activity_type == ActivityType.MEDIA:
        data.update(
            {
                "media_type": random.choice(["Video", "Audio", "Stream"]),
                "title": random_string(),
                "platform": random.choice(["YouTube", "Netflix", "Spotify", "Twitch"]),
                "duration_seconds": random.randint(60, 7200),
                "creator": random_string(),
            },
        )

    return data


def random_truth_data(activity_types: list[ActivityType] | None = None) -> dict[str, Any]:
    """Generate random truth data.

    Args:
        activity_types: The activity types to include.

    Returns:
        Dict[str, Any]: The random truth data.
    """
    activity_types = activity_types or [random.choice(list(ActivityType))]

    return {
        "query_id": str(uuid4()),
        "query_text": random_string(30),
        "matching_entities": [str(uuid4()) for _ in range(random.randint(1, 10))],
        "activity_types": [at.name for at in activity_types],
        "created_at": random_datetime().isoformat(),
    }


class AblationTestCase(unittest.TestCase):
    """Base test case for ablation framework tests.

    This class provides common functionality for testing the ablation framework.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up class-level test fixtures.

        This method sets up class-level fixtures that are shared across all test methods.
        It is called once before any test method in the class.
        """
        super().setUpClass()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Set up database manager
        cls.db_manager = AblationDatabaseManager()

        # Ensure collections exist
        if not cls.db_manager.ensure_collections():
            raise RuntimeError("Failed to ensure collections exist")

        # Set up error handler
        cls.error_handler = AblationErrorHandler()

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down class-level test fixtures.

        This method cleans up class-level fixtures. It is called once after
        all test methods in the class have been run.
        """
        super().tearDownClass()

        # Restore any ablated collections
        cls.db_manager.restore_all_collections()

    def setUp(self) -> None:
        """Set up test fixtures.

        This method sets up fixtures for each test method. It is called before
        each test method.
        """
        super().setUp()

        # Reset random seed for deterministic tests
        random.seed(42)

        # Clear error handler
        self.error_handler.clear_errors()

    def tearDown(self) -> None:
        """Tear down test fixtures.

        This method cleans up fixtures for each test method. It is called after
        each test method.
        """
        super().tearDown()

        # Check for uncaught errors
        if self.error_handler.has_errors(ErrorSeverity.ERROR):
            for error in self.error_handler.get_errors(ErrorSeverity.ERROR):
                self.fail(f"Uncaught error: {error}")

    def create_test_data(self, activity_type: ActivityType, count: int = 10) -> list[dict[str, Any]]:
        """Create test data for the specified activity type.

        Args:
            activity_type: The type of activity.
            count: The number of records to create.

        Returns:
            List[Dict[str, Any]]: The created test data.
        """
        return [random_activity_data(activity_type) for _ in range(count)]

    def create_test_truth_data(
        self, activity_types: list[ActivityType] | None = None, count: int = 5,
    ) -> list[dict[str, Any]]:
        """Create test truth data.

        Args:
            activity_types: The activity types to include.
            count: The number of records to create.

        Returns:
            List[Dict[str, Any]]: The created test truth data.
        """
        return [random_truth_data(activity_types) for _ in range(count)]

    def insert_test_data(self, collection_name: str, data: list[dict[str, Any]]) -> list[str]:
        """Insert test data into a collection.

        Args:
            collection_name: The name of the collection.
            data: The data to insert.

        Returns:
            List[str]: The keys of the inserted documents.
        """
        return self.db_manager.db.insert_batch(collection_name, data)

    def clear_test_data(self, collection_name: str) -> bool:
        """Clear test data from a collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            bool: True if cleared successfully, False otherwise.
        """
        return self.db_manager.db.clear_collection(collection_name)

    def count_documents(self, collection_name: str) -> int:
        """Count the number of documents in a collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            int: The number of documents in the collection.
        """
        return self.db_manager.db.count_documents(collection_name)

    def get_document(self, collection_name: str, key: str) -> dict[str, Any] | None:
        """Get a document by key.

        Args:
            collection_name: The name of the collection.
            key: The document key.

        Returns:
            Optional[Dict[str, Any]]: The document or None if not found.
        """
        return self.db_manager.db.get_document(collection_name, key)

    def execute_query(self, query: str, bind_vars: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute an AQL query and return the results as a list.

        Args:
            query: The AQL query to execute.
            bind_vars: The bind variables to use.

        Returns:
            List[Dict[str, Any]]: The query results.
        """
        cursor = self.db_manager.db.aql_query(query, bind_vars)
        return list(cursor) if cursor else []

    def assert_document_exists(self, collection_name: str, key: str) -> None:
        """Assert that a document exists in a collection.

        Args:
            collection_name: The name of the collection.
            key: The document key.
        """
        doc = self.get_document(collection_name, key)
        self.assertIsNotNone(doc, f"Document {key} does not exist in collection {collection_name}")

    def assert_document_count(self, collection_name: str, expected_count: int) -> None:
        """Assert that a collection contains the expected number of documents.

        Args:
            collection_name: The name of the collection.
            expected_count: The expected number of documents.
        """
        count = self.count_documents(collection_name)
        self.assertEqual(
            expected_count, count, f"Collection {collection_name} has {count} documents, expected {expected_count}",
        )

    def assert_query_results(
        self, query: str, bind_vars: dict[str, Any] | None = None, expected_count: int | None = None,
    ) -> list[dict[str, Any]]:
        """Assert that a query returns the expected number of results.

        Args:
            query: The AQL query to execute.
            bind_vars: The bind variables to use.
            expected_count: The expected number of results.

        Returns:
            List[Dict[str, Any]]: The query results.
        """
        results = self.execute_query(query, bind_vars)

        if expected_count is not None:
            self.assertEqual(
                expected_count, len(results), f"Query returned {len(results)} results, expected {expected_count}",
            )

        return results
