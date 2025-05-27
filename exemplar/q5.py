"""Exemplar Query 5 - Photos taken within 16 kilometers of my house."""

import os
import sys

from typing import Self
from pathlib import Path

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.named_entity import IndalekoNamedEntityType
from db.db_collections import IndalekoDBCollections
from exemplar.qbase import ExemplarQueryBase, exemplar_main
from storage.known_attributes import KnownStorageAttributes
# pylint: enable=wrong-import-position


class ExemplarQuery5(ExemplarQueryBase):
    """Exemplar Query 5 - Search for photos taken within 16 kilometers of home."""

    def __init__(self: Self, *, limit: int | str = ExemplarQueryBase.DEFAULT_LIMIT) -> None:
        """Initialize the exemplar query."""
        # Define photo mime types before calling parent init
        self._photo_mime_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/tiff",
            "image/webp",
            "image/svg+xml",
            "image/heif",
            "image/heic",
        ]
        super().__init__(limit=limit)

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return "Show me photos taken within 16 kilometers of my house."

    def _get_setup_aql(self: Self) -> str:
        """Return the setup AQL query to define home coordinates."""
        return f"""
        LET photo_mime_types = {self._photo_mime_types}

        LET home_coords = FIRST(
            FOR entity IN @@named_entities
            FILTER (
                entity.name == @home_location OR
                @home_location IN entity.aliases
            ) AND
            entity.type == @home_entity_type
            RETURN entity.gis_location
        )

        LET distance_limit = 16000 // 16 kilometers in meters
        """

    def _get_core_aql(self: Self) -> str:
        """Return the core AQL query to find photos within distance limit."""
        return f"""
        FOR doc IN @@collection
            SEARCH (doc[@suffix_mimetype] IN photo_mime_types OR doc[@semantic_mimetype] IN photo_mime_types)
            // FILTER GEO_DISTANCE(doc.gis_location, home_coords) <= distance_limit
        """

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}

            RETURN doc
        """

    def _get_aql_query_limit(self: Self) -> str:
        """Return the AQL query with limit."""
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}

            LIMIT @limit
            RETURN doc
        """

    def _get_aql_query_no_limit(self: Self) -> str:
        """Return the AQL query with limit."""
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}

        """ + """
            RETURN {
                "ObjectIdentifier": doc.ObjectIdentifier,
                "Path": doc.Path,
                "Label": doc.Label,
            }
        """

    def _get_aql_count_query(self: Self) -> str:
        """Return the AQL count query."""
        return f"""
            {self._get_setup_aql()}
            RETURN LENGTH(
                {self._get_core_aql()}
                RETURN 1
            )
        """

    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "suffix_mimetype": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
            "semantic_mimetype": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
            "home_entity_type": IndalekoNamedEntityType.location,
            "@named_entities": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
            "@collection": IndalekoDBCollections.Indaleko_Objects_Essential_View,
            "home_location": "home",
        }

    def _get_named_entities(self: Self) -> list:
        """Return named entities used in this query."""
        return [
            {
                "name": "home",
                "aliases": ["home", "my house"],
                "category": IndalekoNamedEntityType.location,
            },
        ]


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery5)


if __name__ == "__main__":
    main()
