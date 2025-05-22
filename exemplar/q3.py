"""Exemplar Query 3"""

import os
import sys

from pathlib import Path


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.named_entity import IndalekoNamedEntityType
from exemplar.exemplar_data_model import ExemplarQuery


# pylint: enable=wrong-import-position

class ExemplarQuery3(ExemplarQuery):
    """Exemplar Query 3."""
    query = "Get documents I exchanged with Dr. Okafor regarding the conference paper.",
    aql_query = """
        LET person1_ids = (
            FOR entity in @@colleague_collection
                FILTER en
        )
        FIRST(
            FOR entity IN @@entity_collection,
                FILTER (entity.name == @person_name OR
                @person_name IN entity.aliases) AND
                FILTER entity.type == "@entity_type"
                RETURN entity
            )
        )
        LET conference_event = (
            FOR entity IN @@event_collection
                FILTER (entity.name == "ICCS 2025 Conference" OR
                "ICCS 2025" IN entity.aliases) AND
                FILTER entity.type == "@event_type"
                RETURN entity
            )
        )
        LET conference_paper = (
            FOR doc IN @@collection
                FILTER doc.type == "conference_paper" AND
                doc.timestamp >= conference_event.start_date AND
                doc.timestamp <= conference_event.end_date
                RETURN doc
        )
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
    bind_variables = None

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery3.query,
            aql_query=ExemplarQuery3.aql_query,
            aql_count_query=ExemplarQuery3.aql_count_query,
            named_entities=ExemplarQuery3.named_entities,
            bind_variables=ExemplarQuery3.bind_variables,
        )
