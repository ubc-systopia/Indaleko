"""Exemplar Query 4."""

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
from exemplar.reference_date import reference_date


# pylint: enable=wrong-import-position

class ExemplarQuery4:
    """Exemplar Query 4."""
    query = "Show me files I created while on vacation in Bali last June."
    aql_query = """
        LET now = @reference_date
        LET vacation_year = DATE_YEAR(now) - 1
        LET vacation_month = 6 // June
        LET june_start = DATE_ISO8601(vacation_year, vacation_month, 1)
        LET july_start = DATE_ADD(june_start, 1, "months")

        // Retrieve the Bali location entity
        LET bali = FIRST(
        FOR doc IN @@named_entities
            FILTER doc.category == @category_type AND doc.name == "Bali"
            RETURN doc
        )

        // Retrieve the "home" coordinates
        LET base_coords = FIRST(
            FOR entity IN @@named_entities
                FILTER (entity.name == @basename OR @basename IN entity.aliases)
                AND entity.category == @category_type
                RETURN entity.gis_location
        )

        // Define a reasonable radius around Bali (e.g., 50 kilometers)
        LET bali_radius = 50000  // in meters (50 km radius)

        // Find all location logs near Bali during June
        LET bali_locations_in_june = (
            FOR loc IN @@location_collection
            FILTER loc.timestamp >= june_start AND loc.timestamp < july_start
            FILTER GEO_DISTANCE(loc.coordinates, bali.gis_location) <= bali_radius
            SORT loc.timestamp ASC
            RETURN loc
        )

        // Identify the first and last Bali timestamps during this period
        LET first_bali_entry = FIRST(bali_locations_in_june)
        LET last_bali_entry = LAST(bali_locations_in_june)

        // Find the last home entry BEFORE arriving in Bali (vacation start)
        LET vacation_start_entry = FIRST(
        FOR loc IN @@location_collection
            FILTER loc.timestamp < first_bali_entry.timestamp
            FILTER GEO_CONTAINS(base_coords, loc.coordinates)
            SORT loc.timestamp DESC
            LIMIT 1
            RETURN loc
        )

        // Find the first home entry AFTER leaving Bali (vacation end)
        LET vacation_end_entry = FIRST(
        FOR loc IN @@location_collection
            FILTER loc.timestamp > last_bali_entry.timestamp
            FILTER GEO_CONTAINS(base_coords, loc.coordinates)
            SORT loc.timestamp ASC
            LIMIT 1
            RETURN loc
        )

        // Now retrieve files created within the computed "vacation" timeframe
        LET vacation_files = (
        FOR file IN @@file_collection
            SEARCH (
                file[@creation_timestamp] >= vacation_start_entry.timestamp
                AND
                file[@creation_timestamp] <= vacation_end_entry.timestamp
            )
            RETURN file
        )

        RETURN [
            vacation_start_entry.timestamp,
            vacation_end_entry.timestamp,
            vacation_files
        ]
    """
    aql_count_query = None  # TODO
    named_entities = [
        {
            "name": "Bali",
            "aliases": ["Island of Bali", "Bali Island","Bali, Indonesia"],
            "category": IndalekoNamedEntityType.location,
        },
        {
            "name": "home",
            "aliases": ["home", "my house"],
            "category": IndalekoNamedEntityType.location,
        },
        {
            "name": "Bali vacation",
            "category": IndalekoNamedEntityType.event,
        },
    ]
    bind_variables = {
        "reference_date": reference_date,
        "@named_entities": "NamedEntities",
        "@location_collection": "ActivityProviderData_7e85669b-ecc7-4d57-8b51-8d325ea84930",
        "@file_collection": "ObjectsTimestampView",
        "category_type": IndalekoNamedEntityType.location,
        "basename": "home",
        "creation_timestamp": "8aeb9b5a-3d08-4d1f-9921-0795343d9eb3",
    }

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            user_query=ExemplarQuery4.query,
            aql_query_with_limits=ExemplarQuery4.aql_query,
            aql_count_query=ExemplarQuery4.aql_count_query,
            named_entities=ExemplarQuery4.named_entities,
            bind_variables_with_limits=ExemplarQuery4.bind_variables,
        )

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery4.get_exemplar_query()
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
