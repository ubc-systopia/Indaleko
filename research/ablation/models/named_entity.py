"""Named entity models for the ablation framework."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class EntityType(str, Enum):
    """Enumeration of named entity types."""

    LOCATION = "location"
    PERSON = "person"
    ORGANIZATION = "organization"
    EVENT = "event"
    TIME = "time"
    PRODUCT = "product"
    WORK = "work"  # Creative work (book, song, movie, etc.)
    OTHER = "other"


class EntityAlias(BaseModel):
    """Model for entity aliases.

    Entities may have multiple aliases (e.g., "NYC" and "New York City").
    """

    name: str
    language: str | None = None

    class Config:
        frozen = False


class NamedEntity(BaseModel):
    """Model for named entities.

    Named entities provide a unified representation for common entities
    like locations, people, and organizations that appear across different
    activity types.
    """

    id: UUID = Field(default_factory=uuid4)
    entity_type: EntityType
    name: str
    aliases: list[EntityAlias] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    properties: dict[str, str] = Field(default_factory=dict)
    related_entities: list[UUID] = Field(default_factory=list)

    class Config:
        frozen = False

    @validator("name")
    def name_not_empty(cls, v):
        """Validate that the name is not empty."""
        if not v or not v.strip():
            raise ValueError("Entity name cannot be empty")
        return v

    def add_alias(self, name: str, language: str | None = None) -> None:
        """Add an alias for the entity.

        Args:
            name: The alias name.
            language: The language code (optional).
        """
        # Check if the alias already exists
        for alias in self.aliases:
            if alias.name == name and alias.language == language:
                return

        # Add the new alias
        self.aliases.append(EntityAlias(name=name, language=language))

    def add_property(self, key: str, value: str) -> None:
        """Add a property to the entity.

        Args:
            key: The property key.
            value: The property value.
        """
        self.properties[key] = value

    def add_related_entity(self, entity_id: UUID) -> None:
        """Add a related entity.

        Args:
            entity_id: The UUID of the related entity.
        """
        if entity_id not in self.related_entities:
            self.related_entities.append(entity_id)

    def matches(self, text: str) -> bool:
        """Check if the entity matches a text.

        The entity matches if the text contains the entity name or any of its aliases.

        Args:
            text: The text to check.

        Returns:
            bool: True if the entity matches, False otherwise.
        """
        if self.name.lower() in text.lower():
            return True

        for alias in self.aliases:
            if alias.name.lower() in text.lower():
                return True

        return False


class EntityRelationType(str, Enum):
    """Enumeration of entity relation types."""

    PARENT = "parent"  # Parent/child relationship (e.g., "New York" is parent of "Manhattan")
    PART_OF = "part-of"  # Part-of relationship (e.g., "CPU" is part of "Computer")
    RELATED = "related"  # Generic related relationship (e.g., "Microsoft" is related to "Windows")
    SYNONYM = "synonym"  # Synonym relationship (e.g., "Car" is synonym of "Automobile")
    ANTONYM = "antonym"  # Antonym relationship (e.g., "Hot" is antonym of "Cold")
    OWNS = "owns"  # Ownership relationship (e.g., "Microsoft" owns "GitHub")
    LOCATED_IN = "located-in"  # Location relationship (e.g., "Eiffel Tower" is located in "Paris")
    WORKS_FOR = "works-for"  # Employment relationship (e.g., "John" works for "Microsoft")
    CREATED_BY = "created-by"  # Creation relationship (e.g., "Windows" is created by "Microsoft")
    OTHER = "other"  # Other relationship type


class EntityRelation(BaseModel):
    """Model for entity relations.

    Entity relations connect named entities to form a graph of related entities.
    """

    id: UUID = Field(default_factory=uuid4)
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: EntityRelationType
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    properties: dict[str, str] = Field(default_factory=dict)

    class Config:
        frozen = False

    def add_property(self, key: str, value: str) -> None:
        """Add a property to the relation.

        Args:
            key: The property key.
            value: The property value.
        """
        self.properties[key] = value


class EntityReference(BaseModel):
    """Model for entity references in activity data.

    Entity references connect activity data to named entities.
    """

    id: UUID = Field(default_factory=uuid4)
    entity_id: UUID
    activity_id: UUID
    reference_type: str  # e.g., "location", "person", "source", etc.
    confidence: float = 1.0  # Confidence score (0.0 to 1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        frozen = False
