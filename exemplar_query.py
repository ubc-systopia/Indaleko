"""This handles creating the data needed for the exemplar query set."""

import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

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
    named_entities: list[IndalekoNamedEntityDataModel] | None = None


aql_queries = (
    {
        "query": exemplar_queries[0],
        "aql_query": """
            FOR doc IN @@collection
              SEARCH
                ANALYZE(@name, "text_en") or
                ANALYZE(@name, "Indaleko::indaleko_snake_case")
            LIMIT 50
            RETURN doc""",
        "bind_variables" : {
            "@collection": "Objects",
        },
        "named_entities": [],
    },
    {
        # "Find files I edited on my phone while traveling last month.",

        "query": exemplar_queries[1],
        "aql_query": """
            LET device_id = FIRST(
                FOR entity IN @@named_entities
                    FILTER (entity.name == @device_name OR
                    @device_name IN entity.aliases) AND
                    FILTER entity.type == "@entity_type"
                    RETURN entity.device_id
                )
            )
            LET home_coords = FIRST(
                FOR entity IN @@named_entities
                FILTER (entity.name == "home OR
                @home_location IN entity.aliases) AND
                FILTER entity.type == "@home_entity_type"
                RETURN entity.gis_location
            )
            LET start_date = DATE_SUBTRACT(DATE_SUBTRACT(DATE_TRUNC(DATE_NOW()), 1, "month"), 1, "day")
            LET end_date = DATE_ADD(DATE_TRUNC(DATE_NOW()), 1, "day")
            LET travel_locations = (
                FOR loc IN @@location_activity_collection
                    FILTER loc.timestamp >= @start_date AND loc.timestamp <= @end_date
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
                "device_name": "my phone",
                "entity_type": "@entity1_type,"
            },
        ],
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
            LET conference_event =
        """,
        "named_entities": [
            {
                "collection" : "@@colleague_collection",
                "person_name": "Dr. Okafor",
                "entity_type": "@entity2_type",
            },
            {
                "collection" : "@@event_collection",
                "entity_type": "@event_type",
            },
        ],
    },
    {
        # "Show me files I created while on vacation in Bali last June.",
        "query": exemplar_queries[3],
        "aql_query": "'",
        "named_entities": [],
    },
    {
        # "Show me photos taken within 16 kilometers of my house.",
        "query": exemplar_queries[4],
        "aql_query": "",
        "named_entities": [],
    },
    {
        # "Find PDFs I opened in the last week.",
        "query": exemplar_queries[5],
        "aql_query": """
            FOR doc IN @@collection
                FILTER doc.type == "pdf" AND
                doc.timestamp >= DATE_SUBTRACT(DATE_NOW(), 7, "days")
                RETURN doc
            """,

        "named_entities": [],
    },
)

ic(list(named_entities))
my_phone = IndalekoNamedEntityDataModel(
    name="Tony's iPhone",
    category=IndalekoNamedEntityType.item,
    description="Primary mobile device",
    device_id=UUID("74701283-5604-43fe-8606-ed5830b9e6b8"),
    aliases=["my phone", "my iPhone", "phone", "mobile", "authenticator"],
)
