"""
Tests for the entity resolution queue service.
"""

from unittest.mock import MagicMock, patch

import pytest

from storage.incremental_update.models import EntityInfo, EntityType, ResolutionStatus
from storage.incremental_update.queue_service import EntityResolutionQueue


@pytest.fixture
def mock_db_config():
    """Create a mock database configuration."""
    return MagicMock()


@pytest.fixture
def mock_collections():
    """Create a mock collections instance."""
    mock = MagicMock()
    mock.collection_exists.return_value = True
    return mock


@pytest.fixture
def queue_service(mock_db_config, mock_collections):
    """Create a queue service with mocked dependencies."""
    with patch("storage.incremental_update.queue_service.IndalekoCollections", return_value=mock_collections):
        return EntityResolutionQueue(mock_db_config)


def test_enqueue(queue_service, mock_collections):
    """Test enqueueing a resolution request."""
    # Setup
    mock_collection = MagicMock()
    mock_collection.insert.return_value = {"_key": "test_key"}
    mock_collections.get_collection.return_value = mock_collection

    # Execute
    entity_info = EntityInfo(volume_guid="C:", frn="123456", file_path="/test/file.txt")

    result = queue_service.enqueue(
        machine_id="test-machine",
        entity_info=entity_info,
        entity_type=EntityType.FILE,
        priority=2,
    )

    # Verify
    assert result == "test_key"
    mock_collection.insert.assert_called_once()
    inserted_data = mock_collection.insert.call_args[0][0]
    assert inserted_data["machine_id"] == "test-machine"
    assert inserted_data["entity_info"]["volume_guid"] == "C:"
    assert inserted_data["entity_info"]["frn"] == "123456"
    assert inserted_data["entity_type"] == "file"
    assert inserted_data["priority"] == 2


def test_find_existing_request(queue_service, mock_collections):
    """Test finding an existing request."""
    # Setup
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = ["existing_key"]
    mock_db.aql.execute.return_value = mock_cursor
    mock_collections.get_db.return_value = mock_db

    # Execute
    entity_info = EntityInfo(volume_guid="C:", frn="123456", file_path="/test/file.txt")

    result = queue_service._find_existing_request("test-machine", entity_info)

    # Verify
    assert result == "existing_key"
    mock_db.aql.execute.assert_called_once()
    bind_vars = mock_db.aql.execute.call_args[1]["bind_vars"]
    assert bind_vars["machine_id"] == "test-machine"
    assert bind_vars["volume_guid"] == "C:"
    assert bind_vars["frn"] == "123456"


def test_dequeue(queue_service, mock_collections):
    """Test dequeueing requests."""
    # Setup
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = [
        {"_key": "item1", "entity_type": "directory"},
        {"_key": "item2", "entity_type": "file"},
    ]
    mock_db.aql.execute.return_value = mock_cursor
    mock_collections.get_db.return_value = mock_db

    # Execute
    result = queue_service.dequeue("test-machine", batch_size=2)

    # Verify
    assert len(result) == 2
    assert result[0]["_key"] == "item1"
    assert result[1]["_key"] == "item2"
    assert mock_db.aql.execute.call_count > 0


def test_update_status(queue_service, mock_collections):
    """Test updating request status."""
    # Setup
    mock_collection = MagicMock()
    mock_collections.get_collection.return_value = mock_collection

    # Execute
    result = queue_service.update_status("test_key", ResolutionStatus.COMPLETED)

    # Verify
    assert result is True
    mock_collection.update.assert_called_once_with("test_key", {"status": "completed"})


def test_update_status_with_error(queue_service, mock_collections):
    """Test updating request status with error message."""
    # Setup
    mock_collection = MagicMock()
    mock_collections.get_collection.return_value = mock_collection

    # Execute
    result = queue_service.update_status("test_key", ResolutionStatus.FAILED, "Test error message")

    # Verify
    assert result is True
    mock_collection.update.assert_called_once_with("test_key", {"status": "failed", "last_error": "Test error message"})


def test_get_queue_stats(queue_service, mock_collections):
    """Test getting queue statistics."""
    # Setup
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = [
        {"total": 10, "pending": 5, "processing": 2, "completed": 2, "failed": 1, "details": []},
    ]
    mock_db.aql.execute.return_value = mock_cursor
    mock_collections.get_db.return_value = mock_db

    # Execute
    result = queue_service.get_queue_stats("test-machine")

    # Verify
    assert result["total"] == 10
    assert result["pending"] == 5
    assert result["processing"] == 2
    assert result["completed"] == 2
    assert result["failed"] == 1
    mock_db.aql.execute.assert_called_once()
    bind_vars = mock_db.aql.execute.call_args[1]["bind_vars"]
    assert bind_vars["machine_id"] == "test-machine"
