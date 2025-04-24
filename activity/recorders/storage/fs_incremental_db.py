#!/usr/bin/env python3
"""
DB-backed recorder for the incremental file system indexer.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

# pylint: disable=wrong-import-position
from activity.recorders.storage.base import StorageActivityRecorder
from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
from data_models.record import IndalekoRecordDataModel
# pylint: enable=wrong-import-position


class FsIncrementalDbRecorder(StorageActivityRecorder):
    """
    Recorder that upserts incremental FS records into a dynamic ArangoDB collection.

    Each file event is stored as an IndalekoRecordDataModel document under a key
    derived from the file path (using deterministic UUID v5). Old records are
    overwritten in place for updated files.
    """
    DEFAULT_RECORDER_ID = uuid.UUID("de305d54-75b4-431b-adb2-eb6b9e546014")

    def __init__(
        self,
        ttl_days: int = 30,
        **kwargs: Any,
    ) -> None:
        # Prepare recorder registration parameters
        kwargs.setdefault("name", "FS Incremental DB Recorder")
        kwargs.setdefault("recorder_id", self.DEFAULT_RECORDER_ID)
        kwargs.setdefault("provider_type", "LocalFS")
        kwargs.setdefault("description", "Records incremental FS index into DB")
        kwargs.setdefault("ttl_days", ttl_days)
        # Call parent initializer
        super().__init__(**kwargs)
        # Resolve dynamic collection via registration service
        service = IndalekoActivityDataRegistrationService()
        provider_collection = service.lookup_provider_collection(str(self._recorder_id))
        self._collection = provider_collection
        self._logger = logging.getLogger("FsIncrementalDbRecorder")

    def store_activities(self, activities: List[Dict[str, Any]]) -> List[uuid.UUID]:
        """
        Upsert activities into the ArangoDB collection.

        Returns list of UUIDs (as keys) that were stored.
        """
        stored_ids: List[uuid.UUID] = []
        for act in activities:
            # Derive a stable key from file path
            path_str = act.get("file_path", "")
            if not path_str:
                continue
            key = uuid.uuid5(uuid.NAMESPACE_URL, path_str)
            # Build record document
            record = IndalekoRecordDataModel(
                SourceIdentifier=self.SourceIdentifier,
                Timestamp=datetime.now(timezone.utc),
            )
            doc = record.model_dump(mode='json')
            # Store raw activity under opaque Data field
            doc['Data'] = act
            # Upsert record
            try:
                self._collection.insert(doc, overwrite=True)
                stored_ids.append(key)
            except Exception as e:
                self._logger.error(f"Failed to upsert record for {path_str}: {e}")
                self._logger.debug(doc)
        return stored_ids