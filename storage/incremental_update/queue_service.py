"""
Queue service for entity resolution requests.

This module provides the core functionality for managing the
entity resolution queue, including enqueueing, dequeueing,
and updating the status of resolution requests.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from data_models.db_config import IndalekoDBConfiguration
from db.i_collections import IndalekoCollections
from storage.incremental_update.models import (
    EntityInfo,
    EntityType,
    ResolutionRequest,
    ResolutionStatus
)
from utils.i_logging import get_logger


logger = get_logger(__name__)


class EntityResolutionQueue:
    """
    Manages the queue of entity resolution requests.
    
    This class provides methods to enqueue, dequeue, and update
    entity resolution requests stored in ArangoDB.
    """
    
    COLLECTION_NAME = "EntityResolutionQueue"
    
    def __init__(self, db_config: IndalekoDBConfiguration):
        """
        Initialize the entity resolution queue.
        
        Args:
            db_config: Database configuration
        """
        self.db_config = db_config
        self._collections = IndalekoCollections(db_config)
        self._ensure_collection()
        
    def _ensure_collection(self) -> None:
        """
        Ensure the queue collection exists and has the necessary indices.
        """
        db = self._collections.get_db()
        
        # Create collection if it doesn't exist
        if not self._collections.collection_exists(self.COLLECTION_NAME):
            self._collections.create_collection(self.COLLECTION_NAME)
            logger.info(f"Created collection {self.COLLECTION_NAME}")
            
        # Ensure indices for efficient queue operations
        collection = self._collections.get_collection(self.COLLECTION_NAME)
        
        # Index for finding pending items by machine_id and status
        if not collection.has_index(["machine_id", "status"]):
            collection.add_index(["machine_id", "status"])
            logger.info(f"Created index on machine_id and status for {self.COLLECTION_NAME}")
            
        # Index for finding pending items by entity_type and path_depth (for ordering)
        if not collection.has_index(["status", "entity_type", "path_depth"]):
            collection.add_index(["status", "entity_type", "path_depth"])
            logger.info(f"Created index on status, entity_type and path_depth for {self.COLLECTION_NAME}")
        
    def enqueue(
        self,
        machine_id: str,
        entity_info: Union[EntityInfo, Dict],
        entity_type: Union[EntityType, str] = EntityType.UNKNOWN,
        priority: int = 3
    ) -> str:
        """
        Add an entity resolution request to the queue.
        
        Args:
            machine_id: Identifier for the machine this entity belongs to
            entity_info: Information about the entity to resolve
            entity_type: Type of entity (file, directory, etc.)
            priority: Priority (1-5, where 1 is highest)
            
        Returns:
            The queue entry ID
        """
        # Convert dict to EntityInfo if needed
        if isinstance(entity_info, dict):
            entity_info = EntityInfo(**entity_info)
            
        # Convert string to EntityType if needed
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)
            
        # Check if a similar request already exists to avoid duplicates
        existing = self._find_existing_request(machine_id, entity_info)
        if existing:
            logger.debug(f"Request for entity {entity_info.frn} already exists with ID {existing}")
            return existing
            
        # Create the resolution request
        request = ResolutionRequest(
            machine_id=machine_id,
            entity_info=entity_info,
            entity_type=entity_type,
            priority=priority
        )
        
        # Insert into database
        collection = self._collections.get_collection(self.COLLECTION_NAME)
        result = collection.insert(request.model_dump())
        
        logger.info(f"Enqueued entity resolution request {result['_key']} for {entity_info.frn}")
        return result["_key"]
        
    def _find_existing_request(
        self,
        machine_id: str,
        entity_info: EntityInfo
    ) -> Optional[str]:
        """
        Check if a resolution request already exists for this entity.
        
        Args:
            machine_id: Machine identifier
            entity_info: Entity information
            
        Returns:
            The request ID if found, None otherwise
        """
        db = self._collections.get_db()
        
        # Query for pending or processing requests for this entity
        bind_vars = {
            "machine_id": machine_id,
            "volume_guid": entity_info.volume_guid,
            "frn": entity_info.frn
        }
        
        query = """
        FOR doc IN @@collection
            FILTER doc.machine_id == @machine_id
            AND doc.entity_info.volume_guid == @volume_guid
            AND doc.entity_info.frn == @frn
            AND (doc.status == "pending" OR doc.status == "processing")
            LIMIT 1
            RETURN doc._key
        """
        
        cursor = db.aql.execute(
            query,
            bind_vars=bind_vars,
            bind_vars_names={"@collection": self.COLLECTION_NAME}
        )
        
        result = list(cursor)
        return result[0] if result else None
        
    def dequeue(
        self,
        machine_id: str,
        batch_size: int = 10,
        prefer_directories: bool = True
    ) -> List[Dict]:
        """
        Get and mark as processing a batch of pending resolution requests.
        
        Args:
            machine_id: Only dequeue requests for this machine
            batch_size: Maximum number of requests to dequeue
            prefer_directories: If True, prioritize directories over files
            
        Returns:
            List of resolution requests that are now marked as processing
        """
        db = self._collections.get_db()
        
        # First, try to get directories if preferred
        if prefer_directories:
            directory_batch = self._dequeue_by_type(
                machine_id, 
                EntityType.DIRECTORY,
                batch_size
            )
            
            # If we got a full batch of directories, return it
            if len(directory_batch) >= batch_size:
                return directory_batch
                
            # Otherwise, get some files to fill the batch
            remaining = batch_size - len(directory_batch)
            file_batch = self._dequeue_by_type(
                machine_id,
                EntityType.FILE,
                remaining
            )
            
            return directory_batch + file_batch
        
        # If not prioritizing directories, just get the next batch by path depth
        return self._dequeue_batch(machine_id, batch_size)
        
    def _dequeue_by_type(
        self,
        machine_id: str,
        entity_type: EntityType,
        batch_size: int
    ) -> List[Dict]:
        """
        Dequeue requests of a specific entity type.
        
        Args:
            machine_id: Machine identifier
            entity_type: Type of entity to dequeue
            batch_size: Maximum number of requests
            
        Returns:
            List of dequeued requests
        """
        db = self._collections.get_db()
        
        bind_vars = {
            "machine_id": machine_id,
            "entity_type": entity_type.value,
            "status": ResolutionStatus.PENDING.value,
            "processing_status": ResolutionStatus.PROCESSING.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "batch_size": batch_size
        }
        
        query = """
        FOR doc IN @@collection
            FILTER doc.machine_id == @machine_id
            AND doc.entity_type == @entity_type
            AND doc.status == @status
            SORT doc.priority ASC, doc.path_depth ASC, doc.timestamp ASC
            LIMIT @batch_size
            
            UPDATE doc WITH { 
                status: @processing_status,
                last_attempt_time: @timestamp,
                attempts: doc.attempts + 1
            } IN @@collection
            
            RETURN NEW
        """
        
        cursor = db.aql.execute(
            query,
            bind_vars=bind_vars,
            bind_vars_names={"@collection": self.COLLECTION_NAME}
        )
        
        return list(cursor)
        
    def _dequeue_batch(self, machine_id: str, batch_size: int) -> List[Dict]:
        """
        Dequeue a batch of requests ordered by path depth.
        
        Args:
            machine_id: Machine identifier
            batch_size: Maximum number of requests
            
        Returns:
            List of dequeued requests
        """
        db = self._collections.get_db()
        
        bind_vars = {
            "machine_id": machine_id,
            "status": ResolutionStatus.PENDING.value,
            "processing_status": ResolutionStatus.PROCESSING.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "batch_size": batch_size
        }
        
        query = """
        FOR doc IN @@collection
            FILTER doc.machine_id == @machine_id
            AND doc.status == @status
            SORT doc.priority ASC, doc.path_depth ASC, doc.timestamp ASC
            LIMIT @batch_size
            
            UPDATE doc WITH { 
                status: @processing_status,
                last_attempt_time: @timestamp,
                attempts: doc.attempts + 1
            } IN @@collection
            
            RETURN NEW
        """
        
        cursor = db.aql.execute(
            query,
            bind_vars=bind_vars,
            bind_vars_names={"@collection": self.COLLECTION_NAME}
        )
        
        return list(cursor)
    
    def update_status(
        self,
        request_id: str,
        status: Union[ResolutionStatus, str],
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of a resolution request.
        
        Args:
            request_id: The queue entry ID
            status: New status
            error_message: Optional error message for failed requests
            
        Returns:
            True if update successful, False otherwise
        """
        # Convert string to ResolutionStatus if needed
        if isinstance(status, str):
            status = ResolutionStatus(status)
            
        collection = self._collections.get_collection(self.COLLECTION_NAME)
        
        update_data = {
            "status": status.value
        }
        
        if error_message is not None:
            update_data["last_error"] = error_message
            
        try:
            collection.update(request_id, update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update status for request {request_id}: {e}")
            return False
    
    def get_queue_stats(self, machine_id: Optional[str] = None) -> Dict:
        """
        Get statistics about the current queue state.
        
        Args:
            machine_id: If provided, only count requests for this machine
            
        Returns:
            Dictionary with queue statistics
        """
        db = self._collections.get_db()
        
        # Build the query based on whether machine_id is provided
        filter_clause = ""
        bind_vars = {}
        
        if machine_id:
            filter_clause = "FILTER doc.machine_id == @machine_id"
            bind_vars["machine_id"] = machine_id
        
        query = f"""
        LET stats = (
            FOR doc IN @@collection
                {filter_clause}
                COLLECT status = doc.status, entity_type = doc.entity_type
                AGGREGATE count = COUNT()
                RETURN {{
                    status: status,
                    entity_type: entity_type,
                    count: count
                }}
        )
        
        LET pending_count = SUM(
            FOR s IN stats
            FILTER s.status == "pending"
            RETURN s.count
        )
        
        LET processing_count = SUM(
            FOR s IN stats
            FILTER s.status == "processing"
            RETURN s.count
        )
        
        LET completed_count = SUM(
            FOR s IN stats
            FILTER s.status == "completed"
            RETURN s.count
        )
        
        LET failed_count = SUM(
            FOR s IN stats
            FILTER s.status == "failed"
            RETURN s.count
        )
        
        RETURN {{
            total: pending_count + processing_count + completed_count + failed_count,
            pending: pending_count,
            processing: processing_count,
            completed: completed_count,
            failed: failed_count,
            details: stats
        }}
        """
        
        cursor = db.aql.execute(
            query,
            bind_vars=bind_vars,
            bind_vars_names={"@collection": self.COLLECTION_NAME}
        )
        
        # Return the first (and only) result
        result = list(cursor)
        return result[0] if result else {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "details": []
        }