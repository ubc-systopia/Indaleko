"""Exemplar Query 2"""

import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from arango.exceptions import DocumentInsertError
from arango import ArangoClient
from db.utils.query_performance import timed_aql_execute, TimedAQLExecute

from icecream import ic
from pydantic import BaseModel


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db.db_collections import IndalekoDBCollections
from data_models.named_entity import IndalekoNamedEntityDataModel, IndalekoNamedEntityType
from exemplar.exemplar_data_model import ExemplarQuery
from exemplar.reference_date import reference_date

# pylint: enable=wrong-import-position

class ExemplarQuery2(ExemplarQuery):
    """Exemplar Query 2."""
    query = "Find files I edited on my phone while traveling last month."
    aql_query = """
        // Map the device name to its identity information
        LET device_id = FIRST(
            FOR entity IN @@named_entities
                FILTER entity.category == @entity_category
                FILTER LOWER(@entity_name) IN (
                FOR alias in entity.aliases
                RETURN LOWER(alias)
                ) OR
                LOWER(@entity_name) == LOWER(entity.name)
            RETURN entity
        )
        LET home_coords = FIRST(
            FOR entity IN @@named_entities
            FILTER entity.category == @home_entity_type
            FILTER LOWER(@entity_name) IN (
            FOR alias in entity.aliases
                RETURN LOWER(alias)
            ) OR
            LOWER(@entity_name) == LOWER(entity.name)
            RETURN entity
        )
        LET start_date = DATE_TRUNC(DATE_SUBTRACT(@reference_date, 1, "month"), "month")
        LET end_date = DATE_TRUNC(DATE_ISO8601(@reference_date), "month")
        LET travel_locations = (
            FOR loc IN @@location_activity_collection
                FILTER loc.timestamp >= start_date AND loc.timestamp <= end_date
                LET distance = GEO_DISTANCE(
                    [loc.longitude, loc.latitude],
                    [home_coords.longitude, home_coords.latitude]
                )
                RETURN {
                    timestamp: loc.timestamp,
                    away: distance > 16000
                }
        )
        LET travel_intervals = (
            FOR i IN 0..LENGTH(travel_locations)-2
                LET current = travel_locations[i]
                LET next = travel_locations[i+1]
                FILTER current.away == true
                RETURN {
                    start: current.timestamp,
                    end: next.timestamp
                }
        )
        LET edited_files_while_traveling = (
            FOR file IN edited_files
                FILTER LENGTH(
                    FOR interval IN travel_intervals
                        FILTER file.timestamp >= interval.start AND file.timestamp <= interval.end
                        RETURN 1
                ) > 0
                RETURN file
        )
        FOR file IN edited_files_while_traveling
            FOR doc IN @@collection
                FILTER doc._id == file.file_id
                RETURN doc
    """
    aql_count_query = """
        RETURN LENGTH(
        FOR doc IN @@collection
            SEARCH
            ANALYZER(LIKE(doc.Label, @name), "text_en") OR
            ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case")
        RETURN 1
        )
    """
    named_entities = [
        {
            "name": "my phone",
            "category": IndalekoNamedEntityType.item
        },
    ]
    bind_variables = {
        "@named_entities": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
        "device_name": "my phone",
        "device_entity_type": IndalekoNamedEntityType.item,
        "home_location": "home",
        "home_entity_type": IndalekoNamedEntityType.location,
        "@location_activity_collection": "ActivityProviderData_7e85669b-ecc7-4d57-8b51-8d325ea84930", # windows GPS
        "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
        "@reference_date": reference_date,
    }

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery2.query,
            aql_query=ExemplarQuery2.aql_query,
            aql_count_query=ExemplarQuery2.aql_count_query,
            named_entities=ExemplarQuery2.named_entities,
            bind_variables=ExemplarQuery2.bind_variables,
        )
