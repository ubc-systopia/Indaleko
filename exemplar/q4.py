"""Exemplar Query 4."""

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
from exemplar.reference_date import reference_date


# pylint: enable=wrong-import-position

class ExemplarQuery4(ExemplarQuery):
    """Exemplar Query 4."""
    query = "Show me files I created while on vacation in Bali last June.",
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

        // Find all location logs in Bali intersecting with June
        LET bali_locations_in_june = (
        FOR loc IN @@location_collection
            FILTER loc.timestamp >= june_start AND loc.timestamp < july_start
            FILTER GEO_CONTAINS(bali.gis_location, loc.coordinates)
            SORT loc.timestamp ASC
            RETURN loc
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
            FILTER (
                file.Timestamps[@creation_timestamp] >= vacation_start_entry.timestamp
                AND
                file.Timestamps[@creation_timestamp] <= vacation_end_entry.timestamp
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
    }

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery4.query,
            aql_query=ExemplarQuery4.aql_query,
            aql_count_query=ExemplarQuery4.aql_count_query,
            named_entities=ExemplarQuery4.named_entities,
            bind_variables=ExemplarQuery4.bind_variables,
        )
