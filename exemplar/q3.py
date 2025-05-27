"""Exemplar Query 3 - Documents exchanged with Dr. Okafor regarding conference paper."""

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
from storage.i_object import IndalekoObject
# pylint: enable=wrong-import-position


class ExemplarQuery3(ExemplarQueryBase):
    """Exemplar Query 3 - Search for documents exchanged with Dr. Okafor regarding conference paper."""

        # these are overrides for this case
    def _get_aql_query_limit(self: Self) -> str:
        """Return the AQL query with limit."""
        return f"""
            {self._base_aql}
            LIMIT @limit
            RETURN conference_paper
        """

    def _get_aql_query_no_limit(self: Self) -> str:
        return f"""
            {self._base_aql}
            RETURN conference_paper
        """

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return "Get documents I exchanged with Dr. Okafor regarding the conference paper."

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return """
        LET person1_ids = (
            FOR entity in @@entity_collection
                FILTER entity.name == @person_name OR @person_name IN entity.aliases
                RETURN entity.uuid
        )
        LET conference_event = (
            FOR entity IN @@entity_collection
                FILTER (entity.name == "ICCS 2025 Conference" OR
                "ICCS 2025" IN entity.aliases) AND
                entity.type == "@event_type"
                RETURN entity
        )
        LET conference_paper = FIRST(
            FOR doc IN @@collection
                SEARCH doc[@create_timestamp] >= conference_event.start_date AND
                doc[@create_timestamp] <= conference_event.end_date
                FILTER doc[@mime_type] == "application/pdf"
                RETURN doc
        )
        // Get the list of documents exchanged with Dr. Okafor
        //FOR doc IN @@exchange_collection
        //    FILTER doc.type == "email" AND
        //        doc.timestamp >= conference_paper.timestamp AND
        //        doc.timestamp <= @reference_time AND
        //        (doc.sender IN person1_ids OR doc.recipient IN person1_ids)
        //    RETURN doc
    """

    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "@entity_collection": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
            "@collection": IndalekoDBCollections.Indaleko_Objects_Timestamp_View,
            "person_name": "Dr. Okafor",
            "create_timestamp": IndalekoObject.CREATION_TIMESTAMP,
            "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
        }

    def _get_named_entities(self: Self) -> list:
        """Return named entities used in this query."""
        return [
            {
                "name": "Dr. Aki Okafor",
                "aliases": ["Dr. Okafor", "Doctor Okafor", "Aki", "Doctor O"],
                "uuid": "c096e365-16a1-45e8-8e3f-051b401ad84e",
                "collection": "@@colleague_collection",
                "category": IndalekoNamedEntityType.person,
            },
            {
                "name": "ICCS 2025 Conference",
                "aliases": ["ICCS 2025", "conference", "ICCS"],
                "uuid": "44c42df6-5320-4f9d-aeb1-202b77642164",
                "category": IndalekoNamedEntityType.event,
            },
        ]


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery3)


if __name__ == "__main__":
    main()
