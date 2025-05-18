"""Enhanced named entity management for ablation testing."""

import logging
from uuid import UUID

from db.db_collections import IndalekoDBCollections

from ..error import AblationError, ErrorSeverity
from ..error.retry import retry
from ..models.named_entity import (
    EntityRelation,
    EntityRelationType,
    EntityType,
    NamedEntity,
)

logger = logging.getLogger(__name__)


class NamedEntityManager:
    """Manager for named entities used in ablation testing.

    This class handles the creation, lookup, and management of named entities
    like locations, artists, and other domain-specific entities.

    It provides both in-memory caching and database persistence for named entities.
    """

    def __init__(self, db: object | None = None):
        """Initialize the named entity manager.

        Args:
            db: The database connection. If None, only in-memory entities will be used.
        """
        self.db = db

        # In-memory cache of entities by type and name
        self.entities: dict[EntityType, dict[str, NamedEntity]] = {entity_type: {} for entity_type in EntityType}

        # In-memory cache of entities by ID
        self.entities_by_id: dict[UUID, NamedEntity] = {}

        # In-memory cache of entity relations
        self.relations: dict[UUID, EntityRelation] = {}

        # Determine collection name - use the standard Indaleko collection
        self.entity_collection = IndalekoDBCollections.Indaleko_Named_Entity_Collection
        self.relation_collection = f"{self.entity_collection}_Relations"

        # Load entities from the database if available
        if self.db:
            self._load_entities_from_db()

        # Initialize with common entities
        self._initialize_common_entities()

    @retry(max_retries=3)
    def _load_entities_from_db(self) -> None:
        """Load entities from the database."""
        if not self.db:
            return

        try:
            # Check if the collection exists
            collections = self.db.collections()
            collection_names = [c["name"] for c in collections]

            if self.entity_collection not in collection_names:
                logger.warning(f"Named entity collection {self.entity_collection} does not exist")
                return

            # Query all entities
            query = f"""
            FOR entity IN {self.entity_collection}
            RETURN entity
            """

            cursor = self.db.aql.execute(query)
            if not cursor:
                logger.warning("Failed to query named entities")
                return

            # Add each entity to the in-memory cache
            for entity_data in cursor:
                try:
                    entity = NamedEntity(
                        id=UUID(entity_data["id"]),
                        entity_type=EntityType(entity_data["entity_type"]),
                        name=entity_data["name"],
                        aliases=entity_data.get("aliases", []),
                        created_at=entity_data["created_at"],
                        modified_at=entity_data["modified_at"],
                        properties=entity_data.get("properties", {}),
                        related_entities=[UUID(rel_id) for rel_id in entity_data.get("related_entities", [])],
                    )

                    # Add to caches
                    self.entities[entity.entity_type][entity.name] = entity
                    self.entities_by_id[entity.id] = entity
                except NotImplementedError as e:
                    logger.error(f"Failed to parse entity data: {e}")

            # Query all relations
            if self.relation_collection in collection_names:
                query = f"""
                FOR relation IN {self.relation_collection}
                RETURN relation
                """

                cursor = self.db.aql.execute(query)
                if not cursor:
                    logger.warning("Failed to query entity relations")
                    return

                # Add each relation to the in-memory cache
                for relation_data in cursor:
                    try:
                        relation = EntityRelation(
                            id=UUID(relation_data["id"]),
                            source_entity_id=UUID(relation_data["source_entity_id"]),
                            target_entity_id=UUID(relation_data["target_entity_id"]),
                            relation_type=EntityRelationType(relation_data["relation_type"]),
                            created_at=relation_data["created_at"],
                            properties=relation_data.get("properties", {}),
                        )

                        # Add to cache
                        self.relations[relation.id] = relation
                    except NotImplementedError as e:
                        logger.error(f"Failed to parse relation data: {e}")

            logger.info(f"Loaded {len(self.entities_by_id)} entities and {len(self.relations)} relations from database")

        except NotImplementedError as e:
            logger.error(f"Failed to load entities from database: {e}")
            raise

    def _initialize_common_entities(self) -> None:
        """Initialize common named entities for testing."""
        # Locations
        locations = ["Home", "Work", "Coffee Shop", "Library", "Gym", "Airport", "School", "Park"]
        for location in locations:
            self.create_entity(EntityType.LOCATION, location)

        # Organizations
        organizations = ["Microsoft", "Google", "Apple", "Amazon", "Facebook", "Twitter", "Netflix"]
        for org in organizations:
            self.create_entity(EntityType.ORGANIZATION, org)

        # People (fiction and non-fiction)
        people = ["John Smith", "Jane Doe", "Taylor Swift", "Elon Musk", "Bill Gates", "Beyoncé"]
        for person in people:
            self.create_entity(EntityType.PERSON, person)

        # Events
        events = ["Meeting", "Conference", "Birthday Party", "Wedding", "Concert", "Lecture"]
        for event in events:
            self.create_entity(EntityType.EVENT, event)

        # Products
        products = ["iPhone", "MacBook", "Surface", "Echo", "PlayStation", "Xbox", "Chrome"]
        for product in products:
            self.create_entity(EntityType.PRODUCT, product)

        # Creative works
        works = ["Star Wars", "Harry Potter", "Game of Thrones", "Lord of the Rings", "The Matrix"]
        for work in works:
            self.create_entity(EntityType.WORK, work)

        # Create some relations
        # Microsoft -> owns -> GitHub
        microsoft = self.get_entity_by_name(EntityType.ORGANIZATION, "Microsoft")
        if microsoft:
            github = self.create_entity(EntityType.ORGANIZATION, "GitHub")
            self.create_relation(microsoft.id, github.id, EntityRelationType.OWNS)

        # New York City -> contains -> Central Park
        nyc = self.create_entity(EntityType.LOCATION, "New York City")
        central_park = self.create_entity(EntityType.LOCATION, "Central Park")
        self.create_relation(nyc.id, central_park.id, EntityRelationType.PARENT)

        # Add aliases
        nyc_entity = self.get_entity_by_name(EntityType.LOCATION, "New York City")
        if nyc_entity:
            self.add_entity_alias(nyc_entity.id, "NYC")
            self.add_entity_alias(nyc_entity.id, "The Big Apple")

    def create_entity(
        self,
        entity_type: EntityType,
        name: str,
        aliases: list[str] | None = None,
        properties: dict[str, str] | None = None,
    ) -> NamedEntity:
        """Create or retrieve a named entity.

        If an entity with the same type and name already exists, it will be updated with
        any new aliases or properties and then returned.

        Args:
            entity_type: The type of entity.
            name: The name of the entity.
            aliases: Optional list of aliases for the entity.
            properties: Optional dictionary of properties for the entity.

        Returns:
            NamedEntity: The created or retrieved entity.
        """
        # Check if the entity already exists
        existing_entity = self.get_entity_by_name(entity_type, name)
        if existing_entity:
            # Update existing entity with new aliases and properties
            if aliases:
                for alias in aliases:
                    existing_entity.add_alias(alias)

            if properties:
                for key, value in properties.items():
                    existing_entity.add_property(key, value)

            # Save the updated entity
            self._save_entity(existing_entity)

            return existing_entity

        # Create a new entity
        entity = NamedEntity(
            entity_type=entity_type,
            name=name,
            aliases=[{"name": alias} for alias in (aliases or [])],
            properties=properties or {},
        )

        # Add to caches
        self.entities[entity_type][name] = entity
        self.entities_by_id[entity.id] = entity

        # Save to database
        self._save_entity(entity)

        return entity

    @retry(max_retries=3)
    def _save_entity(self, entity: NamedEntity) -> str | None:
        """Save an entity to the database.

        Args:
            entity: The entity to save.

        Returns:
            Optional[str]: The document key if saved to the database, None otherwise.
        """
        if not self.db:
            return None

        try:
            # Convert entity to a dictionary
            entity_dict = entity.dict()

            # Convert UUID objects to strings
            entity_dict["id"] = str(entity_dict["id"])
            entity_dict["related_entities"] = [str(rel_id) for rel_id in entity_dict["related_entities"]]

            # Check if the entity already exists in the database
            query = f"""
            FOR e IN {self.entity_collection}
            FILTER e.id == @id
            RETURN e
            """
            cursor = self.db.aql.execute(query, bind_vars={"id": entity_dict["id"]})
            exists = len(list(cursor)) > 0

            if exists:
                # Update the entity
                query = f"""
                FOR e IN {self.entity_collection}
                FILTER e.id == @id
                UPDATE e WITH @data IN {self.entity_collection}
                RETURN NEW._key
                """
                cursor = self.db.aql.execute(query, bind_vars={"id": entity_dict["id"], "data": entity_dict})
                return next(cursor) if cursor else None
            else:
                # Insert the entity
                collection = self.db.collection(self.entity_collection)
                result = collection.insert(entity_dict)
                return result.get("_key") if result else None
        except NotImplementedError as e:
            logger.error(f"Failed to save entity to database: {e}")
            raise

    def get_entity_by_name(self, entity_type: EntityType, name: str) -> NamedEntity | None:
        """Get an entity by its type and name.

        Args:
            entity_type: The type of entity.
            name: The name of the entity.

        Returns:
            Optional[NamedEntity]: The entity, or None if not found.
        """
        return self.entities.get(entity_type, {}).get(name)

    def get_entity_by_id(self, entity_id: UUID) -> NamedEntity | None:
        """Get an entity by its ID.

        Args:
            entity_id: The ID of the entity.

        Returns:
            Optional[NamedEntity]: The entity, or None if not found.
        """
        return self.entities_by_id.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> dict[str, NamedEntity]:
        """Get all entities of a specific type.

        Args:
            entity_type: The type of entity.

        Returns:
            Dict[str, NamedEntity]: A dictionary mapping entity names to entities.
        """
        return self.entities.get(entity_type, {}).copy()

    def search_entities(self, query: str) -> list[NamedEntity]:
        """Search for entities by name or alias.

        Args:
            query: The search query.

        Returns:
            List[NamedEntity]: A list of matching entities.
        """
        query = query.lower()
        result = []

        # Search all entities
        for _, entities_by_name in self.entities.items():
            for entity in entities_by_name.values():
                # Check if the entity name matches
                if query in entity.name.lower():
                    result.append(entity)
                    continue

                # Check if any alias matches
                for alias in entity.aliases:
                    if query in alias.name.lower():
                        result.append(entity)
                        break

        return result

    def create_relation(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relation_type: EntityRelationType,
        properties: dict[str, str] | None = None,
    ) -> EntityRelation:
        """Create a relation between two entities.

        Args:
            source_entity_id: The ID of the source entity.
            target_entity_id: The ID of the target entity.
            relation_type: The type of relation.
            properties: Optional dictionary of properties for the relation.

        Returns:
            EntityRelation: The created relation.

        Raises:
            AblationError: If the source or target entity does not exist.
        """
        # Check if the source entity exists
        source_entity = self.get_entity_by_id(source_entity_id)
        if not source_entity:
            raise AblationError(
                message=f"Source entity with ID {source_entity_id} not found",
                severity=ErrorSeverity.ERROR,
            )

        # Check if the target entity exists
        target_entity = self.get_entity_by_id(target_entity_id)
        if not target_entity:
            raise AblationError(
                message=f"Target entity with ID {target_entity_id} not found",
                severity=ErrorSeverity.ERROR,
            )

        # Create the relation
        relation = EntityRelation(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
            properties=properties or {},
        )

        # Add to cache
        self.relations[relation.id] = relation

        # Add related entity references
        source_entity.add_related_entity(target_entity_id)
        self._save_entity(source_entity)

        # Save the relation to the database
        self._save_relation(relation)

        return relation

    @retry(max_retries=3)
    def _save_relation(self, relation: EntityRelation) -> str | None:
        """Save a relation to the database.

        Args:
            relation: The relation to save.

        Returns:
            Optional[str]: The document key if saved to the database, None otherwise.
        """
        if not self.db:
            return None

        try:
            # Convert relation to a dictionary
            relation_dict = relation.dict()

            # Convert UUID objects to strings
            relation_dict["id"] = str(relation_dict["id"])
            relation_dict["source_entity_id"] = str(relation_dict["source_entity_id"])
            relation_dict["target_entity_id"] = str(relation_dict["target_entity_id"])

            # Check if the relation collection exists
            collections = self.db.collections()
            collection_names = [c["name"] for c in collections]

            if self.relation_collection not in collection_names:
                # something is wrong.  We fail-stop, let the
                # user handle this.
                logger.error(f"Named entity relation collection {self.relation_collection} does not exist")
                raise AblationError(
                    message=f"Named entity relation collection {self.relation_collection} does not exist",
                    severity=ErrorSeverity.CRITICAL,
                )

            # Check if the relation already exists in the database
            query = f"""
            FOR r IN {self.relation_collection}
            FILTER r.id == @id
            RETURN r
            """
            cursor = self.db.aql.execute(query, bind_vars={"id": relation_dict["id"]})
            exists = len(list(cursor)) > 0

            if exists:
                # Update the relation
                query = f"""
                FOR r IN {self.relation_collection}
                FILTER r.id == @id
                UPDATE r WITH @data IN {self.relation_collection}
                RETURN NEW._key
                """
                cursor = self.db.aql.execute(query, bind_vars={"id": relation_dict["id"], "data": relation_dict})
                return next(cursor) if cursor else None
            else:
                # Insert the relation
                collection = self.db.collection(self.relation_collection)
                result = collection.insert(relation_dict)
                return result.get("_key") if result else None
        except NotImplementedError as e:
            logger.error(f"Failed to save relation to database: {e}")
            raise

    def get_relation(self, relation_id: UUID) -> EntityRelation | None:
        """Get a relation by its ID.

        Args:
            relation_id: The ID of the relation.

        Returns:
            Optional[EntityRelation]: The relation, or None if not found.
        """
        return self.relations.get(relation_id)

    def get_relations_for_entity(
        self, entity_id: UUID, relation_type: EntityRelationType | None = None, as_source: bool = True,
    ) -> list[EntityRelation]:
        """Get relations for an entity.

        Args:
            entity_id: The ID of the entity.
            relation_type: Optional type of relation to filter by.
            as_source: If True, return relations where the entity is the source,
                otherwise return relations where the entity is the target.

        Returns:
            List[EntityRelation]: A list of relations.
        """
        result = []

        for relation in self.relations.values():
            # Check if the entity is the source or target
            if as_source and relation.source_entity_id != entity_id:
                continue

            if not as_source and relation.target_entity_id != entity_id:
                continue

            # Check if the relation type matches
            if relation_type and relation.relation_type != relation_type:
                continue

            result.append(relation)

        return result

    def get_related_entities(
        self, entity_id: UUID, relation_type: EntityRelationType | None = None, as_source: bool = True,
    ) -> list[NamedEntity]:
        """Get entities related to the given entity.

        Args:
            entity_id: The ID of the entity.
            relation_type: Optional type of relation to filter by.
            as_source: If True, return entities that are targets of relations where
                the given entity is the source. If False, return entities that are
                sources of relations where the given entity is the target.

        Returns:
            List[NamedEntity]: A list of related entities.
        """
        result = []

        # Get relations for the entity
        relations = self.get_relations_for_entity(entity_id, relation_type, as_source)

        # Get the related entities
        for relation in relations:
            related_id = relation.target_entity_id if as_source else relation.source_entity_id
            related_entity = self.get_entity_by_id(related_id)
            if related_entity:
                result.append(related_entity)

        return result

    def add_entity_alias(self, entity_id: UUID, alias: str, language: str | None = None) -> bool:
        """Add an alias to an entity.

        Args:
            entity_id: The ID of the entity.
            alias: The alias to add.
            language: Optional language code for the alias.

        Returns:
            bool: True if the alias was added, False otherwise.

        Raises:
            AblationError: If the entity does not exist.
        """
        # Check if the entity exists
        entity = self.get_entity_by_id(entity_id)
        if not entity:
            raise AblationError(
                message=f"Entity with ID {entity_id} not found",
                severity=ErrorSeverity.ERROR,
            )

        # Add the alias
        entity.add_alias(alias, language)

        # Save the updated entity
        self._save_entity(entity)

        return True

    def add_entity_property(self, entity_id: UUID, key: str, value: str) -> bool:
        """Add a property to an entity.

        Args:
            entity_id: The ID of the entity.
            key: The property key.
            value: The property value.

        Returns:
            bool: True if the property was added, False otherwise.

        Raises:
            AblationError: If the entity does not exist.
        """
        # Check if the entity exists
        entity = self.get_entity_by_id(entity_id)
        if not entity:
            raise AblationError(
                message=f"Entity with ID {entity_id} not found",
                severity=ErrorSeverity.ERROR,
            )

        # Add the property
        entity.add_property(key, value)

        # Save the updated entity
        self._save_entity(entity)

        return True

    def add_relation_property(self, relation_id: UUID, key: str, value: str) -> bool:
        """Add a property to a relation.

        Args:
            relation_id: The ID of the relation.
            key: The property key.
            value: The property value.

        Returns:
            bool: True if the property was added, False otherwise.

        Raises:
            AblationError: If the relation does not exist.
        """
        # Check if the relation exists
        relation = self.get_relation(relation_id)
        if not relation:
            raise AblationError(
                message=f"Relation with ID {relation_id} not found",
                severity=ErrorSeverity.ERROR,
            )

        # Add the property
        relation.add_property(key, value)

        # Save the updated relation
        self._save_relation(relation)

        return True

    def extract_entities_from_text(self, text: str) -> list[tuple[NamedEntity, int, int]]:
        """Extract named entities from text.

        This method finds all entities that appear in the text and returns them
        along with their start and end positions.

        Args:
            text: The text to extract entities from.

        Returns:
            List[Tuple[NamedEntity, int, int]]: A list of tuples containing the entity,
                its start position, and its end position in the text.
        """
        result = []

        # Check all entities
        for _, entities_by_name in self.entities.items():
            for entity in entities_by_name.values():
                # Check the entity name
                start = text.lower().find(entity.name.lower())
                if start != -1:
                    end = start + len(entity.name)
                    result.append((entity, start, end))

                # Check aliases
                for alias in entity.aliases:
                    start = text.lower().find(alias.name.lower())
                    if start != -1:
                        end = start + len(alias.name)
                        result.append((entity, start, end))

        # Sort by start position
        result.sort(key=lambda x: x[1])

        return result
