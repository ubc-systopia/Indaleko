"""Exemplar Query 4 - Files created while on vacation in Bali."""

from datetime import UTC, datetime
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
from exemplar.location_documents import get_location_name_coordinates
from exemplar.qbase import ExemplarQueryBase, exemplar_main
from exemplar.reference_date import reference_date
from storage.i_object import IndalekoObject
# pylint: enable=wrong-import-position


class ExemplarQuery4(ExemplarQueryBase):
    """Exemplar Query 4 - Search for files created while on vacation in Bali."""

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return "Show me files I created while on vacation in Bali last June."

    def _get_setup_aql(self: Self) -> str:
        return """
        LET now = @reference_date
        LET vacation_year = DATE_YEAR(now) - 1
        LET vacation_month = 6 // June
        LET june_start = DATE_ISO8601(vacation_year, vacation_month, 1)
        LET july_start = DATE_ADD(june_start, 1, "months")

        // Note: the following query is now being simulated with a date range.
        // the following information shows how we would do this from a
        // real dataset
        // Retrieve the Bali location entity
        //LET bali = FIRST(
        //FOR doc IN @@named_entities
        //    FILTER doc.category == @category_type AND doc.name == "Bali"
        //    RETURN doc
        //)

        // Retrieve the "home" coordinates
        // LET base_coords = FIRST(
        //    FOR entity IN @@named_entities
        //        FILTER (entity.name == @basename OR @basename IN entity.aliases)
        //        AND entity.category == @category_type
        //        RETURN entity.gis_location
        //)

        // Define a reasonable radius around Bali (e.g., 50 kilometers)
        // LET bali_radius = 50000  // in meters (50 km radius)

        // Find all location logs near Bali during June
        // LET bali_locations_in_june = (
        //    FOR loc IN @@location_collection
        //    FILTER loc.timestamp >= june_start AND loc.timestamp < july_start
        //    FILTER GEO_DISTANCE(loc.coordinates, bali.gis_location) <= bali_radius
        //    SORT loc.timestamp ASC
        //   RETURN loc
        //)

        // Identify the first and last Bali timestamps during this period
        // LET first_bali_entry = FIRST(bali_locations_in_june)
        // LET last_bali_entry = LAST(bali_locations_in_june)

        // Find the last home entry BEFORE arriving in Bali (vacation start)
        // LET vacation_start_entry = FIRST(
        // FOR loc IN @@location_collection
        //    FILTER loc.timestamp < first_bali_entry.timestamp
        //    FILTER GEO_CONTAINS(base_coords, loc.coordinates)
        //    SORT loc.timestamp DESC
        //    LIMIT 1
        //    RETURN loc
        //)

        // Find the first home entry AFTER leaving Bali (vacation end)
        // LET vacation_end_entry = FIRST(
        // FOR loc IN @@location_collection
        //    FILTER loc.timestamp > last_bali_entry.timestamp
        //    FILTER GEO_CONTAINS(base_coords, loc.coordinates)
        //    SORT loc.timestamp ASC
        //    LIMIT 1
        //   RETURN loc
        // )
        // LET vacation_start = vacation_start_entry.timestamp
        // LET vacation_end = vacation_end_entry.timestamp

        // Define the vacation start and end dates for test/eval purposes
        LET vacation_start = "2024-06-13T03:19:21+08:00"
        LET vacation_end = "2024-06-27T22:41:16-07:00"

        """

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query"""
        return f"""
        {self._get_setup_aql()}

        {self._get_core_aql()}

        RETURN file
        """

    def _get_core_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return f"""\n
        // Now retrieve files created within the computed "vacation" timeframe
        FOR file IN @@file_collection
            SEARCH (
                (file[@creation_timestamp] >= vacation_start
                AND
                file[@creation_timestamp] <= vacation_end) OR
                (file[@modification_timestamp] >= vacation_start AND
                file[@modification_timestamp] <= vacation_end)
            )
        """

    def _get_aql_query_limit(self: Self) -> str:
        """Return the AQL query with limit."""
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}

            LIMIT @limit
            RETURN file
        """

    def _get_aql_query_no_limit(self: Self) -> str:
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}
        """ + """
            RETURN {
                "ObjectIdentifier": file.ObjectIdentifier,
                "Path": file.Path,
                "Label": file.Label,
            }
        """

    def _get_aql_count_query(self: Self) -> str:
        return f"""\n
            {self._get_setup_aql()}

            RETURN LENGTH(
                {self._get_core_aql()}
                RETURN 1
            )
        """


    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "reference_date": reference_date,
            # "@named_entities": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
            # "@location_collection": "ActivityProviderData_7e85669b-ecc7-4d57-8b51-8d325ea84930",
            "@file_collection": IndalekoDBCollections.Indaleko_Objects_Essential_View,
            # "category_type": IndalekoNamedEntityType.location,
            # "basename": "home",
            "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
            "modification_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
        }

    def _get_named_entities(self: Self) -> list:
        """Return named entities used in this query."""
        bali_coordinates = get_location_name_coordinates("Bali, Indonesia")
        return [
            {
                "name": "Bali",
                "aliases": ["Island of Bali", "Bali Island", "Bali, Indonesia"],
                "category": IndalekoNamedEntityType.location,
                "gis_location": {
                    "latitude": bali_coordinates[0],
                    "longitude": bali_coordinates[1],
                    "timestamp": datetime.now(UTC),
                    "source": "Nominatim",
                },
            },
            {
                "name": "home",
                "aliases": ["home", "my house"],
                "category": IndalekoNamedEntityType.location,
                "gis_location":  {
                    "latitude": 19.35342765009892,
                    "longitude": -99.15753546299241,
                    "timestamp": datetime.now(UTC),
                    "source": "WindowsGPS",},
            },
            {
                "name": "Bali vacation",
                "category": IndalekoNamedEntityType.event,
            },
        ]


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery4)


if __name__ == "__main__":
    main()
