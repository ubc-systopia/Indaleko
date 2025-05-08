"""Basic unit tests for the ablation framework."""

import unittest
from uuid import uuid4

import pytest

from ...base import AblationResult
from ...db.collections import AblationCollections
from ...db.database import AblationDatabase, AblationDatabaseManager
from ...models.activity import ActivityType
from ..test_utils import AblationTestCase


class TestBasicFunctionality(AblationTestCase):
    """Test basic functionality of the ablation framework."""

    def test_ablation_result_model(self) -> None:
        """Test the AblationResult model."""
        # Create an ablation result
        result = AblationResult(
            query_id=uuid4(),
            ablated_collection="TestCollection",
            precision=0.8,
            recall=0.7,
            f1_score=0.75,
            execution_time_ms=100,
            result_count=10,
            true_positives=8,
            false_positives=2,
            false_negatives=3,
        )

        # Check that the impact property is calculated correctly
        self.assertAlmostEqual(0.25, result.impact)

        # Check that the model can be converted to a dict
        result_dict = result.dict()
        self.assertEqual("TestCollection", result_dict["ablated_collection"])
        self.assertEqual(0.8, result_dict["precision"])
        self.assertEqual(0.7, result_dict["recall"])
        self.assertEqual(0.75, result_dict["f1_score"])
        self.assertEqual(100, result_dict["execution_time_ms"])
        self.assertEqual(10, result_dict["result_count"])
        self.assertEqual(8, result_dict["true_positives"])
        self.assertEqual(2, result_dict["false_positives"])
        self.assertEqual(3, result_dict["false_negatives"])

    def test_database_connection(self) -> None:
        """Test that the database connection works."""
        # Check that we have a database connection
        self.assertIsNotNone(self.db_manager.db)

        # Check that we can query the database
        result = self.db_manager.db.aql_query("RETURN 1")
        self.assertEqual([1], list(result))

    def test_collections_exist(self) -> None:
        """Test that all required collections exist."""
        # Check that all collections exist
        for collection_name in AblationCollections.get_all_collections():
            self.assertTrue(
                self.db_manager.db.collection_exists(collection_name),
                f"Collection {collection_name} does not exist",
            )

    def test_insert_and_query(self) -> None:
        """Test that we can insert and query data."""
        # Clear any existing data
        collection_name = AblationCollections.Indaleko_Ablation_Music_Activity_Collection
        self.db_manager.db.clear_collection(collection_name)

        # Create test data
        data = self.create_test_data(ActivityType.MUSIC, count=5)

        # Insert the data
        keys = self.insert_test_data(collection_name, data)

        # Check that the data was inserted
        self.assertEqual(5, len(keys))

        # Check the document count
        self.assert_document_count(collection_name, 5)

        # Query the data
        query = f"FOR doc IN {collection_name} RETURN doc"
        results = self.execute_query(query)

        # Check the results
        self.assertEqual(5, len(results))

    def test_ablate_and_restore(self) -> None:
        """Test that we can ablate and restore collections."""
        # Clear any existing data
        collection_name = AblationCollections.Indaleko_Ablation_Music_Activity_Collection
        self.db_manager.db.clear_collection(collection_name)

        # Create test data
        data = self.create_test_data(ActivityType.MUSIC, count=5)

        # Insert the data
        keys = self.insert_test_data(collection_name, data)

        # Check that the data was inserted
        self.assertEqual(5, len(keys))

        # Ablate the collection
        self.assertTrue(
            self.db_manager.ablate_collection(collection_name),
            f"Failed to ablate collection {collection_name}",
        )

        # Check that the collection no longer exists
        self.assertFalse(
            self.db_manager.db.collection_exists(collection_name),
            f"Collection {collection_name} still exists after ablation",
        )

        # Check that the ablated collection exists
        self.assertTrue(
            self.db_manager.db.collection_exists(f"{collection_name}_ABLATED"),
            f"Ablated collection {collection_name}_ABLATED does not exist",
        )

        # Restore the collection
        self.assertTrue(
            self.db_manager.restore_collection(collection_name),
            f"Failed to restore collection {collection_name}",
        )

        # Check that the collection exists again
        self.assertTrue(
            self.db_manager.db.collection_exists(collection_name),
            f"Collection {collection_name} does not exist after restoration",
        )

        # Check that the ablated collection no longer exists
        self.assertFalse(
            self.db_manager.db.collection_exists(f"{collection_name}_ABLATED"),
            f"Ablated collection {collection_name}_ABLATED still exists after restoration",
        )

        # Check that the data is still intact
        self.assert_document_count(collection_name, 5)


@pytest.mark.usefixtures("random_seed", "clean_collections", "restore_ablated_collections")
class TestPytestFixtures:
    """Test that the pytest fixtures work correctly."""

    def test_database_fixture(self, database: AblationDatabase) -> None:
        """Test that the database fixture works.

        Args:
            database: The database fixture.
        """
        # Check that we have a database connection
        assert database is not None

        # Check that we can query the database
        result = database.aql_query("RETURN 1")
        assert list(result) == [1]

    def test_collections_fixture(self, database: AblationDatabase) -> None:
        """Test that the collections fixture works.

        Args:
            database: The database fixture.
        """
        # Check that all collections exist
        for collection_name in AblationCollections.get_all_collections():
            assert database.collection_exists(collection_name), f"Collection {collection_name} does not exist"

    def test_sample_music_collection(self, database: AblationDatabase, sample_music_collection: list) -> None:
        """Test that the sample music collection fixture works.

        Args:
            database: The database fixture.
            sample_music_collection: The sample music collection fixture.
        """
        # Check that the fixture inserted data
        assert len(sample_music_collection) == 10

        # Check the document count
        collection_name = AblationCollections.Indaleko_Ablation_Music_Activity_Collection
        count = database.count_documents(collection_name)
        assert count == 10

    def test_sample_all_collections(self, database: AblationDatabase, sample_all_collections: dict) -> None:
        """Test that the sample all collections fixture works.

        Args:
            database: The database fixture.
            sample_all_collections: The sample all collections fixture.
        """
        # Check that the fixture inserted data in all collections
        for collection_name, keys in sample_all_collections.items():
            assert len(keys) > 0

            # Check the document count
            count = database.count_documents(collection_name)
            assert count == len(keys)

    def test_ablation_with_fixtures(
        self, database_manager: AblationDatabaseManager, sample_music_collection: list,
    ) -> None:
        """Test that we can ablate and restore collections with fixtures.

        Args:
            database_manager: The database manager fixture.
            sample_music_collection: The sample music collection fixture.
        """
        collection_name = AblationCollections.Indaleko_Ablation_Music_Activity_Collection

        # Ablate the collection
        assert database_manager.ablate_collection(collection_name), f"Failed to ablate collection {collection_name}"

        # Check that the collection no longer exists
        assert not database_manager.db.collection_exists(
            collection_name,
        ), f"Collection {collection_name} still exists after ablation"

        # Check that the ablated collection exists
        assert database_manager.db.collection_exists(
            f"{collection_name}_ABLATED",
        ), f"Ablated collection {collection_name}_ABLATED does not exist"

        # The restore_ablated_collections fixture will restore the collection after the test


if __name__ == "__main__":
    unittest.main()
