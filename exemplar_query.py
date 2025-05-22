"""This handles creating the data needed for the exemplar query set."""

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
from data_models.named_entity import IndalekoNamedEntityDataModel, IndalekoNamedEntityType
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from storage.known_attributes import KnownStorageAttributes

# pylint: enable=wrong-import-position


exemplar_queries: tuple = (
    'Show me documents with "report" in their titles.',
    "Find files I edited on my phone while traveling last month.",
    "Get documents I exchanged with Dr. Okafor regarding the conference paper.",
    "Show me files I created while on vacation in Bali last June.",
    "Show me photos taken within 16 kilometers of my house.",
    "Find PDFs I opened in the last week.",
)

named_entity_data = (
    {
        "name": "Tony's iPhone",
        "category": IndalekoNamedEntityType.item,
        "description": "Primary mobile device",
        "device_id": "74701283-5604-43fe-8606-ed5830b9e6b8",
        "aliases": ["my phone", "my iPhone", "phone", "mobile", "authenticator"],
    },
    {
        "name": "Dr. Aki Okafor",
        "category": IndalekoNamedEntityType.person,
        "description": "Research collaborator",
        "aliases": ["Dr. Okafor", "Doctor Okafor", "Aki", "Doctor O"],
    },
    {   "name": "Home",
        "category": IndalekoNamedEntityType.location,
        "description":"Primary residence",
        "gis_location": {
            "source": "user_defined",
            "timestamp": datetime.now(UTC),
            "latitude": 49.2827,    # Coordinates for Vancouver, BC
            "longitude": -123.1207,
        },
        "aliases": ["my house", "home", "residence", "house"],
    },
    {
        "name": "Bali Vacation June 2024",
        "category": IndalekoNamedEntityType.event,
        "description": "Vacation to Bali in June 2024",
        "aliases": ["bali trip", "indonesia vacation", "bali vacation"],
    },
    {
        "name": "ICCS 2025 Conference",
        "category": IndalekoNamedEntityType.event,
        "description": "International Conference on Computational Science 2025",
        "aliases": ["ICCS 2025", "conference", "ICCS"],
    },
    {
        "name": "Vancouver, BC",
        "category": IndalekoNamedEntityType.location,
        "description": "City in Canada",
        "gis_location": {
            "source": "user_defined",
            "timestamp": datetime.now(UTC),
            "latitude": 49.2827,
            "longitude": -123.1207,
        },
        "aliases": ["vancouver", "vancouver bc", "vancouver city"],
    },
    {
        "name": "Coyoacan, Mexico City",
        "category": IndalekoNamedEntityType.location,
        "description": "Neighborhood in Mexico City",
        "gis_location": {
            "source": "WindowsGPS",
            "timestamp": "2025-05-15T22:42:09.806482Z",
            "latitude": 19.353394203724292,
            "longitude": -99.15747714554567,
        },
        "aliases": ["coyoacan", "mexico city", "mexico", "cdmx", "del carmen", "malintzin"],
    },
)


named_entities = (
    IndalekoNamedEntityDataModel(**entity) for entity in named_entity_data
)

class ExemplarQuery(BaseModel):
    """Data model for exemplar queries."""
    query: str
    aql_query: str | None = None
    aql_count_query: str | None = None
    named_entities: list[IndalekoNamedEntityDataModel] | None = None
    bind_variables: dict[str, str] | None = None


aql_queries = (
    {
        "query": exemplar_queries[0],
        "aql_query": """
            FOR doc IN @@collection
              SEARCH
                ANALYZER(LIKE(doc.Label, @name), "text_en") or
                ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case")
            LIMIT 50
            RETURN doc""",
        "aql_count_query": """
            RETURN LENGTH(
            FOR doc IN @@collection
                SEARCH
                ANALYZER(LIKE(doc.Label, @name), "text_en") OR
                ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case")
            RETURN 1
            )
        """,
        "named_entities": [],
        "bind_variables": {
            "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
            "name": "%report%",
        },
    },
    {
        # "Find files I edited on my phone while traveling last month.",

        "query": exemplar_queries[1],
        "aql_query": """
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
            LET start_date = DATE_TRUNC(DATE_SUBTRACT(DATE_NOW(), 1, "month"), "month")
            LET end_date = DATE_TRUNC(DATE_ISO8601(DATE_NOW()), "month")
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
        """,
        "named_entities": [
            {
                "name": "my phone",
                "category": IndalekoNamedEntityType.item
            },
        ],
        "bind_variables": {
            "@named_entities": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
            "device_name": "my phone",
            "device_entity_type": IndalekoNamedEntityType.item,
            "home_location": "home",
            "home_entity_type": IndalekoNamedEntityType.location,
            "@location_activity_collection": "ActivityProviderData_7e85669b-ecc7-4d57-8b51-8d325ea84930", # windows GPS
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
        }
    },
    {
        # "Get documents I exchanged with Dr. Okafor regarding the conference paper.",
        "query": exemplar_queries[2],
        "aql_query": """
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
        """,
        "named_entities": [
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
        ],
    },
    {
        # "Show me files I created while on vacation in Bali last June.",
        "query": exemplar_queries[3],
        "aql_query": """
            LET now = DATE_NOW()
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
        """,
        "named_entities": [],
    },
    {
        # "Show me photos taken within 16 kilometers of my house.",
        "query": exemplar_queries[4],
        "aql_query": f"""
            LET home_coords = FIRST(
                FOR entity IN @@named_entities
                FILTER (entity.name == "home OR
                @home_location IN entity.aliases) AND
                FILTER entity.type == "@home_entity_type"
                RETURN entity.gis_location
            )
            LET photo_mime_types = [
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
            FOR doc IN @@collection
                FILTER (
                    doc.SemanticAttributes["{KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX}"] in photo_mime_types #  suffix based MIME type
                    OR
                    doc.SemanticAttributes["{KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE}"] IN photo_mime_types #  suffix based MIME type
                )
                LET distance = GEO_DISTANCE(
                    [doc.longitude, doc.latitude],
                    [home_coords.longitude, home_coords.latitude]
                )
                FILTER distance <= 16000
                RETURN doc
        """,
        "named_entities": [],
    },
    {
        # "Find PDFs I opened in the last week.",
        "query": exemplar_queries[5],
        "aql_query": f"""
            FOR doc IN @@collection
                FILTER (
                    (
                        doc.SemanticAttributes["{KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX}"] == "application/pdf" #  suffix based MIME type
                        OR
                        doc.SemanticAttributes["{KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE}"] == "application/pdf" #  suffix based MIME type
                    ) AND
                    doc.timestamp >= DATE_SUBTRACT(DATE_NOW(), 7, "days")
                )
                RETURN doc
            """,
        "named_entities": [],
        "bind_variables": {
            "@collection": "Objects",
        },
    },
)


sample = """
    // Clean out TestObjects (if needed)
    LET cleanup_results = (
    FOR test_object IN TestObjects
        REMOVE test_object IN TestObjects
    )

    // Pick test data from Objets.
    LET samples = (
    FOR value IN 1..@sample_size
        LET doc = FIRST(FOR node IN Objects
            SORT RAND()
            LIMIT 1
            RETURN node
        )
        RETURN doc
    )

    for sample in samples
    INSERT sample INTO TestObjects


  """

def build_ner_documents() -> None:
    """Build the NER documents."""
    cleanup_aql_query = """
        FOR doc IN @@collection
            REMOVE doc IN @@collection
    """
    db = IndalekoDBConfig()
    IndalekoDBCollections()
    ner_collection = IndalekoDBConfig().get_collection(IndalekoDBCollections.Indaleko_Named_Entity_Collection)
    cleanup_aql_query = """
        FOR doc IN @@collection
            REMOVE doc IN @@collection
    """
    bind_vars = {
        "@collection": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
    }
    db.get_arangodb().aql.execute(cleanup_aql_query, bind_vars=bind_vars)
    for entity in named_entities:
        ic(entity)
        try:
            doc = ner_collection.insert(entity.serialize())
        except DocumentInsertError as error:
            ic(error)
            doc = ner_collection.get({"_key" : str(entity.uuid)})
        ic(doc)

def run_aql_query(query : ExemplarQuery) -> None:
    """Run the AQL query."""
    ic(query.aql_query, query.bind_variables)
    timed_aql = TimedAQLExecute(
        query=query.aql_query,
        count_query=query.aql_count_query,
        bind_vars=query.bind_variables,
    )
    cursor = timed_aql.get_cursor()
    results = list(cursor)
    count = len(results)
    if len(results) > 49 and query.aql_count_query:
        cursor = timed_aql_execute(
            query.aql_count_query,
            bind_vars=query.bind_variables,
        )
        count = list(cursor)[0]
    ic(count, " results found")
    if count < 10:
        ic(results)
    ic(timed_aql.get_data())

def build_aql_queries() -> None:
    """Build the AQL queries."""
    master_query_list = list(
        ExemplarQuery(**query) for query in aql_queries
    )
    # try the first query
    run_aql_query(master_query_list[0])
    run_aql_query(master_query_list[1])

def main() -> None:
    """Main function to run the exemplar query."""
    # Build the NER documents
    IndalekoDBConfig()
    build_ner_documents()
    build_aql_queries()

if __name__ == "__main__":
    main()
