"""Pytest fixtures for the ablation framework."""

import random
from collections.abc import Generator
from typing import Any

import pytest

from ..db.collections import AblationCollections
from ..db.database import AblationDatabase, AblationDatabaseManager
from ..error import AblationErrorHandler
from ..models.activity import ActivityType
from .test_utils import random_activity_data, random_truth_data


@pytest.fixture(scope="session")
def database_manager() -> AblationDatabaseManager:
    """Provide the database manager for tests.

    Returns:
        AblationDatabaseManager: The database manager.
    """
    manager = AblationDatabaseManager()
    # Ensure collections exist
    manager.ensure_collections()
    return manager


@pytest.fixture(scope="session")
def database(database_manager: AblationDatabaseManager) -> AblationDatabase:
    """Provide the database instance for tests.

    Args:
        database_manager: The database manager.

    Returns:
        AblationDatabase: The database instance.
    """
    return database_manager.db


@pytest.fixture(scope="function")
def error_handler() -> AblationErrorHandler:
    """Provide the error handler for tests.

    Returns:
        AblationErrorHandler: The error handler.
    """
    return AblationErrorHandler()


@pytest.fixture(scope="function")
def random_seed() -> Generator[None, None, None]:
    """Set a fixed random seed for deterministic tests.

    Yields:
        None
    """
    random.seed(42)
    yield
    # Reset seed to random
    random.seed()


@pytest.fixture(scope="function")
def clean_collections(database: AblationDatabase) -> Generator[None, None, None]:
    """Clean collections before and after tests.

    Args:
        database: The database instance.

    Yields:
        None
    """
    # Clean collections before test
    for collection_name in AblationCollections.get_all_collections():
        database.clear_collection(collection_name)

    yield

    # Clean collections after test
    for collection_name in AblationCollections.get_all_collections():
        database.clear_collection(collection_name)


@pytest.fixture(scope="function")
def restore_ablated_collections(database_manager: AblationDatabaseManager) -> Generator[None, None, None]:
    """Restore any ablated collections after tests.

    Args:
        database_manager: The database manager.

    Yields:
        None
    """
    yield

    # Restore any ablated collections
    database_manager.restore_all_collections()


@pytest.fixture()
def music_activity_data(random_seed: None) -> dict[str, Any]:
    """Generate random music activity data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random music activity data.
    """
    return random_activity_data(ActivityType.MUSIC)


@pytest.fixture()
def location_activity_data(random_seed: None) -> dict[str, Any]:
    """Generate random location activity data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random location activity data.
    """
    return random_activity_data(ActivityType.LOCATION)


@pytest.fixture()
def task_activity_data(random_seed: None) -> dict[str, Any]:
    """Generate random task activity data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random task activity data.
    """
    return random_activity_data(ActivityType.TASK)


@pytest.fixture()
def collaboration_activity_data(random_seed: None) -> dict[str, Any]:
    """Generate random collaboration activity data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random collaboration activity data.
    """
    return random_activity_data(ActivityType.COLLABORATION)


@pytest.fixture()
def storage_activity_data(random_seed: None) -> dict[str, Any]:
    """Generate random storage activity data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random storage activity data.
    """
    return random_activity_data(ActivityType.STORAGE)


@pytest.fixture()
def media_activity_data(random_seed: None) -> dict[str, Any]:
    """Generate random media activity data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random media activity data.
    """
    return random_activity_data(ActivityType.MEDIA)


@pytest.fixture()
def truth_data(random_seed: None) -> dict[str, Any]:
    """Generate random truth data.

    Args:
        random_seed: The random seed fixture.

    Returns:
        Dict[str, Any]: Random truth data.
    """
    return random_truth_data([ActivityType.MUSIC, ActivityType.LOCATION])


@pytest.fixture()
def sample_music_collection(
    database: AblationDatabase,
    random_seed: None,
    clean_collections: None,
) -> list[str]:
    """Create a sample music activity collection.

    Args:
        database: The database instance.
        random_seed: The random seed fixture.
        clean_collections: The clean collections fixture.

    Returns:
        List[str]: The keys of the inserted documents.
    """
    # Insert 10 random music activities
    data = [random_activity_data(ActivityType.MUSIC) for _ in range(10)]
    return database.insert_batch(AblationCollections.Indaleko_Ablation_Music_Activity_Collection, data)


@pytest.fixture()
def sample_all_collections(
    database: AblationDatabase,
    random_seed: None,
    clean_collections: None,
) -> dict[str, list[str]]:
    """Create sample data in all activity collections.

    Args:
        database: The database instance.
        random_seed: The random seed fixture.
        clean_collections: The clean collections fixture.

    Returns:
        Dict[str, List[str]]: Dictionary mapping collection names to lists of inserted document keys.
    """
    result = {}

    # Insert 5 random activities for each activity type
    for activity_type in ActivityType:
        collection_name = getattr(
            AblationCollections, f"Indaleko_Ablation_{activity_type.name.capitalize()}_Activity_Collection",
        )
        data = [random_activity_data(activity_type) for _ in range(5)]
        keys = database.insert_batch(collection_name, data)
        result[collection_name] = keys

    # Insert 3 random truth data records
    truth_data_list = [random_truth_data() for _ in range(3)]
    keys = database.insert_batch(AblationCollections.Indaleko_Ablation_Truth_Collection, truth_data_list)
    result[AblationCollections.Indaleko_Ablation_Truth_Collection] = keys

    return result
