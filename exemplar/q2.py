"""Exemplar Query 2"""

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
from db.db_collections import IndalekoDBCollections
from db.utils.query_performance import TimedAQLExecute
from exemplar.exemplar_data_model import ExemplarQuery
from exemplar.reference_date import reference_date


# pylint: enable=wrong-import-position

class ExemplarQuery2:
    """Exemplar Query 2."""
    query = "Find files I edited on my phone while traveling last month."
    aql_query = """
        // Map the device name to its identity information
        LET device_id = FIRST(
            FOR entity IN @@named_entities
                FILTER entity.category == @device_entity_type
                FILTER LOWER(@device_name) IN (
                FOR alias in entity.aliases
                RETURN LOWER(alias)
                ) OR
                LOWER(@device_name) == LOWER(entity.name)
            RETURN entity
        )
        LET home_coords = FIRST(
            FOR entity IN @@named_entities
            FILTER entity.category == @home_entity_type
            FILTER LOWER(@device_name) IN (
            FOR alias in entity.aliases
                RETURN LOWER(alias)
            ) OR
            LOWER(@device_name) == LOWER(entity.name)
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
        LET edited_files = (
            FOR doc IN @@collection
                FILTER doc.Timestamps[@change_time] >= start_date AND doc.Timestamps[@change_time] <= end_date
                FILTER doc.Timestamps[@modify_time] >= start_date AND doc.Timestamps[@modify_time] <= end_date
                FILTER doc.Timestamps[@create_time] >= start_date AND doc.Timestamps[@create_time] <= end_date
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
            "category": IndalekoNamedEntityType.item,
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
        "reference_date": reference_date,
    }

    exemplar_query = ExemplarQuery(
        query=query,
        aql_query=aql_query,
        aql_count_query=aql_count_query,
        named_entities=named_entities,
        bind_variables=bind_variables,
    )


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

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery2.get_exemplar_query()
    ic(exemplar_query)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables,
    )
    ic(result.get_data())

if __name__ == "__main__":
    main()
