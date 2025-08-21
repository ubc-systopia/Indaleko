"""
Entity resolution service.

This module provides the service that processes the entity resolution queue,
invoking appropriate collectors and recorders to resolve missing entities.
"""

import socket
import time

from data_models.db_config import IndalekoDBConfiguration
from storage.incremental_update.models import ResolutionStatus
from storage.incremental_update.queue_service import EntityResolutionQueue
from utils.i_logging import get_logger


logger = get_logger(__name__)


class EntityResolutionService:
    """
    Service that processes entity resolution requests from the queue.

    This service:
    1. Dequeues pending resolution requests
    2. Invokes appropriate collectors to gather entity information
    3. Uses existing recorders to normalize and store the data
    4. Updates request status and handles retries
    """

    def __init__(
        self,
        db_config: IndalekoDBConfiguration,
        machine_id: str | None = None,
        batch_size: int = 10,
        max_retries: int = 3,
        sleep_interval: float = 5.0,
    ) -> None:
        """
        Initialize the entity resolution service.

        Args:
            db_config: Database configuration
            machine_id: Identifier for the machine to process. If None, uses hostname.
            batch_size: Number of requests to process in each batch
            max_retries: Maximum number of resolution attempts per entity
            sleep_interval: Seconds to sleep when queue is empty
        """
        self.db_config = db_config
        self.machine_id = machine_id or socket.gethostname()
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.sleep_interval = sleep_interval

        self.queue = EntityResolutionQueue(db_config)

        # These will be initialized on first use
        self._collectors = {}
        self._recorders = {}

        logger.info(
            f"Initialized EntityResolutionService for machine {self.machine_id} with batch size {batch_size}",
        )

    def run(self, single_batch: bool = False) -> int:
        """
        Process entity resolution requests from the queue.

        Args:
            single_batch: If True, process just one batch and return.
                          If False, run continuously.

        Returns:
            Number of requests processed
        """
        total_processed = 0

        logger.info(f"Starting entity resolution service for machine {self.machine_id}")

        try:
            while True:
                # Get stats before processing
                stats = self.queue.get_queue_stats(self.machine_id)
                logger.info(
                    f"Queue stats: {stats['pending']} pending, "
                    f"{stats['processing']} processing, "
                    f"{stats['completed']} completed, "
                    f"{stats['failed']} failed",
                )

                # Dequeue a batch of requests
                batch = self.queue.dequeue(self.machine_id, self.batch_size, prefer_directories=True)

                if not batch:
                    logger.debug("No pending requests in queue")
                    if single_batch:
                        break
                    time.sleep(self.sleep_interval)
                    continue

                # Process the batch
                processed = self._process_batch(batch)
                total_processed += processed

                logger.info(f"Processed {processed} entities in this batch")

                if single_batch:
                    break

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping service")

        logger.info(f"Entity resolution service finished, processed {total_processed} entities")
        return total_processed

    def _process_batch(self, batch: list[dict]) -> int:
        """
        Process a batch of resolution requests.

        Args:
            batch: List of resolution request documents

        Returns:
            Number of successfully processed requests
        """
        successful = 0

        for request in batch:
            request_id = request["_key"]

            try:
                # Skip if too many attempts
                if request["attempts"] > self.max_retries:
                    logger.warning(
                        f"Request {request_id} exceeded maximum retries ({self.max_retries}), marking as failed",
                    )
                    self.queue.update_status(
                        request_id,
                        ResolutionStatus.FAILED,
                        f"Exceeded maximum retries ({self.max_retries})",
                    )
                    continue

                # Process this request
                success = self._resolve_entity(request)

                if success:
                    self.queue.update_status(request_id, ResolutionStatus.COMPLETED)
                    successful += 1
                else:
                    self.queue.update_status(
                        request_id,
                        ResolutionStatus.PENDING,
                        "Resolution attempt failed, will retry",
                    )

            except Exception as e:
                logger.exception(f"Error processing request {request_id}: {e!s}")
                self.queue.update_status(request_id, ResolutionStatus.PENDING, f"Processing error: {e!s}")

        return successful

    def _resolve_entity(self, request: dict) -> bool:
        """
        Resolve a single entity by invoking appropriate collector and recorder.

        Args:
            request: Resolution request document

        Returns:
            True if resolution was successful, False otherwise
        """
        entity_info = request["entity_info"]
        entity_type = request["entity_type"]

        logger.info(f"Resolving {entity_type} entity: {entity_info['volume_guid']}:{entity_info['frn']}")

        # This is where we would implement the actual resolution logic:
        # 1. Determine which collector to use based on entity_type and volume_guid
        # 2. Invoke collector to get entity data
        # 3. Pass data to appropriate recorder

        # For now, just return placeholder
        logger.warning("Entity resolution not yet implemented")
        return False

    # TODO: Implement collector/recorder selection and invocation
    # These would be implemented in a real implementation:
