"""This handles creating the named entiti data needed for the exemplar query set."""

import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from arango.exceptions import DocumentInsertError
from icecream import ic
from pydantic import AwareDatetime


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.location_data_model import LocationDataModel
from data_models.named_entity import IndalekoNamedEntityDataModel, IndalekoNamedEntityType
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoDBCollections
from db.utils.query_performance import TimedAQLExecute
from exemplar.location_documents import get_location_name_coordinates


# pylint: enable=wrong-import-position


class ExemplarNamedEntity:
    """Build named entity data for exemplar."""

    @staticmethod
    def lookup_entity_in_db(
        entity_name: str,
    ) -> IndalekoNamedEntityDataModel | None:
        """Lookup an entity in the database."""
        query = """
            FOR entity IN @@collection
                FILTER entity.name == @name OR @name IN entity.aliases
                RETURN entity
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
            "name": entity_name,
        }
        result = IndalekoDBConfig().get_arangodb().aql.execute(query, bind_vars=bind_vars)
        result = list(result)
        if len(result) == 0:
            return None
        ic(result)
        return IndalekoNamedEntityDataModel(**result[0])

    @staticmethod
    def add_entity_to_db(
            entity: IndalekoNamedEntityDataModel | dict[str, object],
    ) -> bool:
        """Add an entity to the database."""
        ner_collection = IndalekoDBConfig().get_collection(IndalekoDBCollections.Indaleko_Named_Entity_Collection)
        if isinstance(entity, dict):
            entity = IndalekoNamedEntityDataModel(**entity) # type: ignore
        try:
            ner_collection.insert(entity.serialize())
            return True
        except DocumentInsertError as error:
            ic(error)
            return False

    @staticmethod
    def add_person(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
    ) -> IndalekoNamedEntityDataModel | None:
        """Add a person to the named entity."""
        if isinstance(identifier, str):
            try:
                identifier = UUID(identifier)
            except ValueError as error:
                ic(f"Invalid UUID string: {identifier}. Error: {error}")
                raise
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.person,
            description=description,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add person entity to the database.")
            return None
        return entity


    @staticmethod
    def add_organization(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
    ) -> IndalekoNamedEntityDataModel | None:
        """Add an organization to the named entity."""
        if isinstance(identifier, str):
            try:
                identifier = UUID(identifier)
            except ValueError as error:
                ic(f"Invalid UUID string: {identifier}. Error: {error}")
                raise
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.organization,
            description=description,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add organization entity to the database.")
            return None
        return entity

    @staticmethod
    def add_location(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
            gis_location : LocationDataModel | tuple[float, float] | None = None,
    ) -> IndalekoNamedEntityDataModel | None:
        """Add a location to the named entity."""
        if gis_location is None:
            latitiude, longitude, altitude = get_location_name_coordinates(name)
            if latitiude is None or longitude is None:
                raise ValueError(f"Could not get coordinates for {name}")
            gis_location = LocationDataModel(
                latitude=latitiude,
                longitude=longitude,
                altitude=altitude,
            )
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.location,
            description=description,
            gis_location=gis_location,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add location entity to the database.")
            return None
        return entity

    @staticmethod
    def add_date(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
            timestamp: datetime | AwareDatetime | None = datetime.now(UTC),
    ) -> IndalekoNamedEntityDataModel | None:
        """Add a date to the named entity."""
        if isinstance(identifier, str):
            try:
                identifier = UUID(identifier)
            except ValueError as error:
                ic(f"Invalid UUID string: {identifier}. Error: {error}")
                raise
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.date,
            description=description,
            timestamp=timestamp,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add date entity to the database.")
            return None
        return entity

    @staticmethod
    def add_event(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
            timestamp: datetime | AwareDatetime | None = datetime.now(UTC),
    ) -> IndalekoNamedEntityDataModel:
        """Add an event to the named entity."""
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.event,
            description=description,
            timestamp=timestamp,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add event entity to the database.")
            return None
        return entity

    @staticmethod
    def add_product(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
    ) -> IndalekoNamedEntityDataModel:
        """Add a product to the named entity."""
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.product,
            description=description,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add product entity to the database.")
            return None
        return entity

    @staticmethod
    def add_item(
            name: str,
            *,
            description: str | None,
            identifier : str | UUID = uuid4(),
            aliase: list[str] = [],
    ) -> IndalekoNamedEntityDataModel:
        """Add an item to the named entity."""
        entity = IndalekoNamedEntityDataModel(
            name=name,
            entity_uuid=identifier,
            category=IndalekoNamedEntityType.item,
            description=description,
            aliases=aliase,
        )
        if not ExemplarNamedEntity.add_entity_to_db(entity):
            ic("Failed to add item entity to the database.")
            return None
        return entity

    @staticmethod
    def clean_ner_collection() -> None:
        """Clean the NER collection."""
        ner_collection = IndalekoDBConfig().get_collection(IndalekoDBCollections.Indaleko_Named_Entity_Collection)
        cleanup_aql_query = """
            FOR doc IN @@collection
                REMOVE doc IN @@collection
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
        }
        timed_operation = TimedAQLExecute(
            query=cleanup_aql_query,
            bind_vars=bind_vars,
        )
        ic("Cleaning NER collection: ", timed_operation.get_data())


def main():
    """Main function for testing functionality."""

if __name__ == "__main__":
    main()
