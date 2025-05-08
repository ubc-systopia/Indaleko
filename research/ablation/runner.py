"""Test runner for the ablation framework."""

import argparse
import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from .db.collections import AblationCollections
from .db.database import AblationDatabase, AblationDatabaseManager
from .db.registration import register_ablation_collections
from .error import AblationErrorHandler
from .models.activity import ActivityType

logger = logging.getLogger(__name__)


class AblationTestResult:
    """Result of an ablation test."""

    def __init__(self, test_id: str, test_name: str, timestamp: datetime, results: list[dict[str, Any]]):
        """Initialize the test result.

        Args:
            test_id: The test ID.
            test_name: The test name.
            timestamp: The test timestamp.
            results: The test results.
        """
        self.test_id = test_id
        self.test_name = test_name
        self.timestamp = timestamp
        self.results = results

    def to_dict(self) -> dict[str, Any]:
        """Convert the test result to a dictionary.

        Returns:
            Dict[str, Any]: The test result dictionary.
        """
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "timestamp": self.timestamp.isoformat(),
            "results": self.results,
        }

    def to_json(self, pretty: bool = False) -> str:
        """Convert the test result to a JSON string.

        Args:
            pretty: Whether to format the JSON string for readability.

        Returns:
            str: The test result as a JSON string.
        """
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, file_path: str) -> None:
        """Save the test result to a file.

        Args:
            file_path: The file path.
        """
        with open(file_path, "w") as f:
            f.write(self.to_json(pretty=True))

    def save_to_database(self, database: AblationDatabase) -> str | None:
        """Save the test result to the database.

        Args:
            database: The database instance.

        Returns:
            Optional[str]: The document key if successful, None otherwise.
        """
        return database.insert_document(
            AblationCollections.Indaleko_Ablation_Results_Collection,
            self.to_dict(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AblationTestResult":
        """Create a test result from a dictionary.

        Args:
            data: The dictionary.

        Returns:
            AblationTestResult: The test result.
        """
        return cls(
            test_id=data["test_id"],
            test_name=data["test_name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            results=data["results"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AblationTestResult":
        """Create a test result from a JSON string.

        Args:
            json_str: The JSON string.

        Returns:
            AblationTestResult: The test result.
        """
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, file_path: str) -> "AblationTestResult":
        """Create a test result from a file.

        Args:
            file_path: The file path.

        Returns:
            AblationTestResult: The test result.
        """
        with open(file_path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_database(cls, database: AblationDatabase, test_id: str) -> Optional["AblationTestResult"]:
        """Create a test result from the database.

        Args:
            database: The database instance.
            test_id: The test ID.

        Returns:
            Optional[AblationTestResult]: The test result if found, None otherwise.
        """
        # Query the database
        query = f"""
        FOR doc IN {AblationCollections.Indaleko_Ablation_Results_Collection}
        FILTER doc.test_id == @test_id
        LIMIT 1
        RETURN doc
        """
        cursor = database.aql_query(query, {"test_id": test_id})

        # Check if we found a result
        if not cursor:
            return None

        # Get the first result
        try:
            result = next(cursor)
            return cls.from_dict(result)
        except StopIteration:
            return None


class AblationTestRunner:
    """Test runner for the ablation framework."""

    def __init__(
        self,
        test_name: str | None = None,
        activity_types: list[ActivityType] | None = None,
        error_handler: AblationErrorHandler | None = None,
    ):
        """Initialize the test runner.

        Args:
            test_name: The name of the test.
            activity_types: The activity types to test.
            error_handler: The error handler to use.
        """
        self.test_id = str(uuid.uuid4())
        self.test_name = test_name or f"ablation_test_{int(time.time())}"
        self.timestamp = datetime.now(UTC)
        self.activity_types = activity_types or list(ActivityType)
        self.error_handler = error_handler or AblationErrorHandler()

        # Initialize database manager
        self.db_manager = AblationDatabaseManager()

        # Register collections
        register_ablation_collections()

        # Ensure collections exist
        self.db_manager.ensure_collections()

    def run_test(self) -> AblationTestResult:
        """Run the ablation test.

        Returns:
            AblationTestResult: The test result.
        """
        logger.info(f"Running ablation test {self.test_name} with ID {self.test_id}")

        # Store the test metadata
        self._store_test_metadata()

        # List of results for each ablated collection
        results = []

        # Get the activity collection names
        activity_collections = []
        for activity_type in self.activity_types:
            collection_name = getattr(
                AblationCollections, f"Indaleko_Ablation_{activity_type.name.capitalize()}_Activity_Collection",
            )
            activity_collections.append(collection_name)

        # TODO: Implement actual ablation testing logic:
        # 1. Set up control (no ablation) test
        # 2. For each activity type, ablate the collection and measure results
        # 3. Compare results to control and calculate impact

        # For now, just return a placeholder result
        for collection_name in activity_collections:
            result = {
                "ablated_collection": collection_name,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "impact": 0.0,
                "execution_time_ms": 0,
                "result_count": 0,
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0,
            }
            results.append(result)

        logger.info(f"Ablation test {self.test_name} completed with {len(results)} results")

        return AblationTestResult(
            test_id=self.test_id,
            test_name=self.test_name,
            timestamp=self.timestamp,
            results=results,
        )

    def _store_test_metadata(self) -> str | None:
        """Store test metadata in the database.

        Returns:
            Optional[str]: The document key if successful, None otherwise.
        """
        metadata = {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "timestamp": self.timestamp.isoformat(),
            "activity_types": [at.name for at in self.activity_types],
            "status": "running",
        }

        return self.db_manager.db.insert_document(
            AblationCollections.Indaleko_Ablation_Test_Metadata_Collection,
            metadata,
        )

    def _update_test_metadata(self, status: str) -> bool:
        """Update test metadata in the database.

        Args:
            status: The test status.

        Returns:
            bool: True if successful, False otherwise.
        """
        # Query for the test metadata
        query = f"""
        FOR doc IN {AblationCollections.Indaleko_Ablation_Test_Metadata_Collection}
        FILTER doc.test_id == @test_id
        LIMIT 1
        RETURN doc
        """
        cursor = self.db_manager.db.aql_query(query, {"test_id": self.test_id})

        # Check if we found a result
        if not cursor:
            return False

        # Get the first result
        try:
            result = next(cursor)
            key = result["_key"]

            # Update the status
            return self.db_manager.db.update_document(
                AblationCollections.Indaleko_Ablation_Test_Metadata_Collection,
                key,
                {"status": status},
            )
        except StopIteration:
            return False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Run ablation tests")
    parser.add_argument("--test-name", help="Name of the test")
    parser.add_argument(
        "--activity-types", nargs="+", choices=[at.name for at in ActivityType], help="Activity types to test",
    )
    parser.add_argument("--output-file", help="Output file path")
    parser.add_argument("--save-to-db", action="store_true", help="Save results to database")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser.parse_args()


def main() -> None:
    """Run the ablation test."""
    # Parse command line arguments
    args = parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Convert activity types
    activity_types = None
    if args.activity_types:
        activity_types = [ActivityType[at] for at in args.activity_types]

    # Create and run the test
    runner = AblationTestRunner(
        test_name=args.test_name,
        activity_types=activity_types,
    )

    try:
        # Run the test
        result = runner.run_test()

        # Update test metadata
        runner._update_test_metadata("completed")

        # Save results to file if requested
        if args.output_file:
            result.save_to_file(args.output_file)
            print(f"Results saved to {args.output_file}")

        # Save results to database if requested
        if args.save_to_db:
            key = result.save_to_database(runner.db_manager.db)
            if key:
                print(f"Results saved to database with key {key}")
            else:
                print("Failed to save results to database")

        # Print results
        print(result.to_json(pretty=True))

    except Exception as e:
        # Update test metadata
        runner._update_test_metadata("failed")

        # Log the error
        logger.exception(f"Error running ablation test: {e}")

        # Exit with error code
        sys.exit(1)


if __name__ == "__main__":
    main()
