"""Named entity recognition for ablation testing."""

from uuid import UUID

from ..utils.uuid_utils import generate_uuid_for_entity


class NamedEntityManager:
    """Manager for named entities used in ablation testing.

    This class handles the creation, lookup, and management of named entities
    like locations, artists, and other domain-specific entities.
    """

    def __init__(self):
        """Initialize the named entity manager."""
        self.entities: dict[str, dict[str, UUID]] = {
            "location": {},
            "artist": {},
            "application": {},
            "device": {},
            "file_type": {},
        }

        # Initialize with common entities
        self._initialize_common_entities()

    def _initialize_common_entities(self) -> None:
        """Initialize common named entities for testing."""
        # Locations
        for location in ["home", "work", "coffee shop", "library", "gym"]:
            self.register_entity("location", location)

        # Artists
        for artist in ["Taylor Swift", "The Beatles", "Beyoncé", "Drake", "Ed Sheeran"]:
            self.register_entity("artist", artist)

        # Applications
        for app in ["Microsoft Word", "Google Chrome", "Visual Studio Code", "Photoshop", "Excel"]:
            self.register_entity("application", app)

        # Devices
        for device in ["laptop", "desktop", "phone", "tablet"]:
            self.register_entity("device", device)

        # File types
        for file_type in ["document", "spreadsheet", "image", "video", "code"]:
            self.register_entity("file_type", file_type)

    def register_entity(self, entity_type: str, entity_name: str) -> UUID:
        """Register a named entity and get its UUID.

        If the entity already exists, its existing UUID is returned.

        Args:
            entity_type: The type of entity (e.g., 'location', 'artist', etc.)
            entity_name: The name of the entity.

        Returns:
            UUID: The UUID for the entity.
        """
        if entity_type not in self.entities:
            self.entities[entity_type] = {}

        if entity_name not in self.entities[entity_type]:
            entity_id = generate_uuid_for_entity(entity_type, entity_name)
            self.entities[entity_type][entity_name] = entity_id

        return self.entities[entity_type][entity_name]

    def get_entity_id(self, entity_type: str, entity_name: str) -> UUID | None:
        """Get the UUID for a named entity.

        Args:
            entity_type: The type of entity (e.g., 'location', 'artist', etc.)
            entity_name: The name of the entity.

        Returns:
            Optional[UUID]: The UUID for the entity, or None if not found.
        """
        if entity_type not in self.entities:
            return None

        return self.entities[entity_type].get(entity_name)

    def get_entities_by_type(self, entity_type: str) -> dict[str, UUID]:
        """Get all entities of a specific type.

        Args:
            entity_type: The type of entity (e.g., 'location', 'artist', etc.)

        Returns:
            Dict[str, UUID]: A dictionary mapping entity names to UUIDs.
        """
        if entity_type not in self.entities:
            return {}

        return self.entities[entity_type].copy()
