"""
Producer mixin for entity resolution requests.

This module provides a mixin class that can be used by recorders
to enqueue entity resolution requests when they encounter entities
that don't exist in the database.
"""


from storage.incremental_update.models import EntityInfo, EntityType
from storage.incremental_update.queue_service import EntityResolutionQueue
from utils.i_logging import get_logger

logger = get_logger(__name__)


class EntityResolutionProducer:
    """
    Mixin for enqueuing entity resolution requests.

    This mixin should be used by recorder classes that need to
    request resolution of entities that don't exist in the database.

    Example usage:
    ```python
    class MyRecorder(BaseRecorder, EntityResolutionProducer):
        def process_activity(self, activity):
            entity = self.find_entity(activity.entity_id)
            if entity is None:
                # Entity doesn't exist, queue it for resolution
                self.enqueue_entity_resolution(
                    volume_guid=activity.volume,
                    frn=activity.frn,
                    file_path=activity.path,
                    entity_type="file"
                )

            # Continue with other processing
    ```
    """

    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        self._resolution_queue = None
        self._machine_id = None

    def _get_resolution_queue(self) -> EntityResolutionQueue:
        """
        Get or create the entity resolution queue instance.

        Returns:
            EntityResolutionQueue instance

        Raises:
            AttributeError: If db_config is not available in the class
        """
        if self._resolution_queue is None:
            if not hasattr(self, "db_config"):
                raise AttributeError(
                    "db_config not found. The EntityResolutionProducer mixin "
                    "requires the class to have a db_config attribute.",
                )

            self._resolution_queue = EntityResolutionQueue(self.db_config)

        return self._resolution_queue

    def _get_machine_id(self) -> str:
        """
        Get the machine ID for resolution requests.

        Returns:
            Machine identifier string

        Raises:
            AttributeError: If machine_id cannot be determined
        """
        if self._machine_id is None:
            # Try different ways to get the machine ID
            if hasattr(self, "machine_id"):
                self._machine_id = self.machine_id
            elif hasattr(self, "machine_config") and hasattr(self.machine_config, "machine_id"):
                self._machine_id = self.machine_config.machine_id
            else:
                # Use a default as last resort
                import socket

                self._machine_id = socket.gethostname()
                logger.warning(
                    f"Using hostname {self._machine_id} as machine_id for "
                    "entity resolution requests. Consider setting machine_id explicitly.",
                )

        return self._machine_id

    def enqueue_entity_resolution(
        self,
        volume_guid: str,
        frn: str,
        file_path: str | None = None,
        entity_type: EntityType | str = EntityType.UNKNOWN,
        priority: int = 3,
    ) -> str:
        """
        Enqueue an entity for resolution.

        Args:
            volume_guid: Volume identifier (e.g., 'C:')
            frn: File Reference Number or equivalent identifier
            file_path: Optional file path
            entity_type: Type of entity ('file', 'directory', 'unknown')
            priority: Priority (1-5, where 1 is highest)

        Returns:
            The queue entry ID
        """
        # Create entity info from parameters
        entity_info = EntityInfo(volume_guid=volume_guid, frn=frn, file_path=file_path)

        # Get queue and machine ID
        queue = self._get_resolution_queue()
        machine_id = self._get_machine_id()

        # Enqueue the resolution request
        request_id = queue.enqueue(
            machine_id=machine_id, entity_info=entity_info, entity_type=entity_type, priority=priority,
        )

        logger.debug(f"Enqueued entity resolution request {request_id} for {entity_type}:{volume_guid}:{frn}")

        return request_id
