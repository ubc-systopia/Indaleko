"""Exemplar Query 3"""

import os
import sys

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
from db.utils.query_performance import TimedAQLExecute
from exemplar.exemplar_data_model import ExemplarQuery
from storage.known_attributes import KnownStorageAttributes
from storage.i_object import IndalekoObject


# pylint: enable=wrong-import-position

class ExemplarQuery3:
    """Exemplar Query 3."""
    query = "Get documents I exchanged with Dr. Okafor regarding the conference paper."
    aql_query = """
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
        RETURN conference_paper
        // Get the list of documents exchanged with Dr. Okafor
        //FOR doc IN @@exchange_collection
        //    FILTER doc.type == "email" AND
        //        doc.timestamp >= conference_paper.timestamp AND
        //        doc.timestamp <= @reference_time AND
        //        (doc.sender IN person1_ids OR doc.recipient IN person1_ids)
        //    RETURN doc
    """
    aql_count_query = None  # TODO
    named_entities = [
        {
            "name" : "Dr. Aki Okafor",
            "aliases" : ["Dr. Okafor", "Doctor Okafor", "Aki", "Doctor O"],
            "uuid" : "c096e365-16a1-45e8-8e3f-051b401ad84e",
            "collection" : "@@colleague_collection",
            "category": IndalekoNamedEntityType.person,
        },
        {
            "name" : "ICCS 2025 Conference",
            "aliases" : ["ICCS 2025", "conference", "ICCS"],
            "uuid" : "44c42df6-5320-4f9d-aeb1-202b77642164",
            "category" : IndalekoNamedEntityType.event,
        },
    ]
    from db.db_collections import IndalekoDBCollections

    bind_variables = {
        "@entity_collection": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
        "@collection": IndalekoDBCollections.Indaleko_Objects_Timestamp_View,
        "person_name": "Dr. Okafor",
        "create_timestamp": IndalekoObject.CREATION_TIMESTAMP,
        "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
    }

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            user_query=ExemplarQuery3.query,
            aql_query_with_limits=ExemplarQuery3.aql_query,
            aql_count_query=ExemplarQuery3.aql_count_query,
            named_entities=ExemplarQuery3.named_entities,
            bind_variables_with_limits=ExemplarQuery3.bind_variables,
        )

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery3.get_exemplar_query()
    ic(exemplar_query)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query_with_limits,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables_with_limits,
    )
    ic(result.get_data())
    ic(len(list(result.get_cursor())))

if __name__ == "__main__":
    main()
