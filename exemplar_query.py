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
from activity.recorders.storage.ntfs.data_models.ntfs_storage_data_model import (
    NTFSStorageActivityDataModel,
)
from data_models.i_object import IndalekoObjectDataModel
from data_models.named_entity import IndalekoNamedEntityDataModel, IndalekoNamedEntityType
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from exemplar.exemplar_data_model import ExemplarQuery
from exemplar.reference_date import reference_date
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

storage_activity_data = (
    {
    },

)

usable_mime_types = (
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
    "text/plain",
    "text/csv",
    "text/markdown",
    "text/html",
    "application/rtf",
    "application/epub+zip",
    "application/x-7z-compressed",
    "application/zip",
    "application/x-tar",
    "application/x-rar-compressed",
    "application/x-bzip2",
    "application/x-gzip",
    "application/json",
    "application/xml",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
    "image/svg+xml",
    "image/heif",
    "image/heic",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/ogg",
    "audio/flac",
    "video/mp4",
    "video/x-matroska",  # .mkv
    "video/x-msvideo",   # .avi
    "video/quicktime",   # .mov
    "video/webm",
    "application/vnd.apple.keynote",
    "application/vnd.apple.numbers",
    "application/vnd.apple.pages",
)

def pick_random_files(
        *,
        size: int = 7,
        collection: str = IndalekoDBCollections.Indaleko_Object_Collection,
        directory_ok: bool = False,
) -> list[IndalekoObjectDataModel]:
    """
    Pick random files from the collection.

    Args:
        size (int): Number of random files to pick.
        collection (str): Collection name to pick from.
        directory_ok (bool): If True, include directories.
    """
    """Pick one random file from the collection."""
    random_files = []
    file_ids = []
    while len(random_files) < size:
        db = IndalekoDBConfig().get_arangodb()
        cursor = db.aql.execute(
            f"""
                LET tonyfiles = (
                FOR object in @@collection
                    SEARCH ANALYZER(LIKE(object.Label, "%tony%"), "text_en")
                    RETURN object
                )
                LET samples = (
                FOR value IN 1..@sample_size
                    LET doc = FIRST(FOR node IN tonyfiles
                        SORT RAND()
                        LIMIT 1
                        RETURN node
                    )
                    RETURN doc
                )
                FOR value in samples
                RETURN value
            """,
            bind_vars={
                "@collection": collection,
                "sample_size": 100,
            },
        )
        for candidate in list(cursor):
            doc = IndalekoObjectDataModel(**candidate)
            # don't take directories
            if not directory_ok and "S_IFDIR" in doc.PosixFileAttributes:
                continue
            # don't take duplicates
            if doc.ObjectIdentifier in file_ids:
                continue
            # filter on MIME types
            for attr in doc.SemanticAttributes:
                if attr.Identifier != "8aeb9b5a-3d08-4d1f-9921-0795343d9eb3":
                    continue
                if attr.Value is None or len(attr.Value) == 0:
                    continue
                if attr.Value not in usable_mime_types:
                    continue
            random_files.append(doc)
            file_ids.append(doc.ObjectIdentifier)
            break
    return random_files

random_files = (
    UUID('2284eae3-6c49-4eff-8e5f-0d14c92bc76b'),
    UUID('5060d458-eb3a-4e51-a38c-b61f71e52ae4'),
    UUID('7400625e-033b-4ef9-90a9-4dba495a6411'),
    UUID('cf0d5028-99f7-4c09-8223-5d85b7cfe065'),
    UUID('1dd6f0b7-b84f-4ff4-9b65-1102e77f87ca'),
    UUID('7f640177-2028-4c2b-891b-538311064895'),
    UUID('66ba76d6-6b0d-491e-9e8d-1a8154f1eded'),
    UUID('1d99e901-61f3-432d-aa90-df6e039e2718'),
    UUID('1d400cce-f329-417c-b8d8-187a37de81fd'),
    UUID('35ddee0b-eb7f-4bc3-9edc-e059ec30d9e4'),
    UUID('ec534710-8884-4fc5-9c66-910afb7859f0'),
    UUID('de6e1941-f2c2-4e2a-a39b-1755e1e3abff'),
    UUID('4d43c3d6-ea77-4b23-b02d-cd8eee14ad05'),
    UUID('a0bffdf9-eee8-4524-967f-fe928350c80c'),
    UUID('97e53c13-21d3-4b99-b616-0c8e7857850c'),
    UUID('9f5eed64-f7c2-4433-9b55-edb7deae0367'),
    UUID('c6a23bb9-ff82-4541-a345-dbc4c4b3e6bb'),
    UUID('8cb3f6d0-723a-4d96-b401-0c213438f30e'),
    UUID('1208e075-c989-4fce-a5ca-f9491f4b6a55'),
    UUID('1a6b4413-e99b-4bc5-8694-bde10cd9ef6a'),
    UUID('c438cee2-9e4a-4304-9ab1-ca6cdb2d4538'),
    UUID('22fc2ca9-0349-4974-a83b-431f89141f85'),
    UUID('c564ffd9-011d-4fdb-bc84-89020a8393c2'),
    UUID('268b0c61-0e9c-46ba-b4a9-7ffcd0961b43'),
    UUID('9be65231-73d6-4d82-be45-2be3fa11ec4a'),
    UUID('b445ea5c-087e-462f-850b-258c5c67bb7b'),
    UUID('27bd2a85-6d50-4f32-b4c6-ba264c431ac6'),
    UUID('baa919d3-c09b-472f-b7a0-ae2b1a1814fe'),
    UUID('23ecd2e4-3649-415e-af8b-71212051f52f'),
    UUID('5aa31075-92cc-4832-8636-a948448120c4'),
    UUID('18ccd7c6-9267-4ce4-81cc-c14fbf101c00'),
    UUID('e5c9d387-1034-4674-b05b-59cb60d128ea'),
    UUID('684f3233-dbcc-444a-9d6f-db0531c471f0'),
    UUID('a160d499-e5a1-428e-9618-67fb2c032902'),
    UUID('5c10ceed-5d00-45e2-aebd-25cd0fad7bb0'),
    UUID('984fc9fd-13ec-40f9-9893-460804f4e5f3'),
    UUID('5be5ef14-180a-4df6-9b12-eef65f3163a1'),
    UUID('844ddbc4-6b0c-4cde-9b06-0e36f5f135c1'),
    UUID('8b81e897-cae1-49d2-96ae-d938c336cf69'),
    UUID('5c934520-2fb8-4821-8772-0ba67c0cf6f3'),
    UUID('25e17f30-8f4b-47c5-a113-2aafcf78b89f'),
    UUID('9cbc4353-f20a-475b-b098-83c786ba2be7'),
    UUID('280aa257-27f6-4770-8934-14a3c67928d9'),
    UUID('4aff45e8-91ae-433c-b77b-213559322143'),
    UUID('df098313-58a2-4d2d-a4fb-c8cbc430e46f'),
    UUID('738ac31c-5716-490f-aafa-0fbf715f3c8c'),
    UUID('efc8c065-95e5-4f0e-abba-b674b91d344e'),
    UUID('d0cfcdb3-acc8-4ee3-b570-db2da8484538'),
    UUID('00b42813-9c00-4cea-815c-6c94538fdcb3'),
)

def pick_enough_files():
    """
    Pick enough files to use for the exemplars
    """
    random_files = pick_random_files(
        size=49,
        collection=IndalekoDBCollections.Indaleko_Objects_Text_View
    )

named_entities = (
    IndalekoNamedEntityDataModel(**entity) for entity in named_entity_data
)


aql_queries = (
    {
        "query": exemplar_queries[0],
        "aql_query": """
            FOR doc IN @@collection
              SEARCH
                ANALYZER(LIKE(doc.Label, @name), "text_en") OR
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
            "@reference_date": reference_date,
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
        """,
        "named_entities": [],
        "bind_variables": {
            "reference_date": datetime(2025, 3, 25, 18, 33, 4, tzinfo=UTC),
        }
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

location_data = (
)

def build_location_documents() -> None:
    """Build the location documents."""

q2_storage_activity_documents = (
    {

    }
)

def build_storage_activity_documents() -> None:
    """Build the storage activity documents."""
    cleanup_aql_query = """
        FOR doc IN @@collection
            REMOVE doc IN @@collection
    """
    from activity.recorders.storage.ntfs.data_models.ntfs_storage_data_model import (
        NTFSStorageActivityDataModel
    )
    from activity.recorders.registration_service import (
        IndalekoActivityDataRegistrationService,
    )
    from activity.recorders.storage.data_models.storage_activity import (
        IndalekoStorageActivityDataModel,
    )
    from activity.recorders.storage.ntfs.recorder import NTFSStorageActivityRecorder
    registrar = IndalekoActivityDataRegistrationService()
    registration_data = registrar.lookup_provider_by_identifier(
        NTFSStorageActivityRecorder.identifier,
    )
    if registration_data is None:
        raise RuntimeError("Failed to get the registration data")
    ic("Registration data:", registration_data)
    storage_activity_collection = registrar.lookup_activity_provider_collection(
        NTFSStorageActivityRecorder.identifier,
    )
    ic("Storage activity collection:", storage_activity_collection, storage_activity_collection.collection_name)
    if storage_activity_collection is None:
        raise RuntimeError("Failed to get the storage activity collection")
    storage_activity_collection_schema = storage_activity_collection.get_schema()
    if storage_activity_collection_schema is None or len(storage_activity_collection_schema) == 0:
        ic("Collection schema is empty, creating it")
        json_schema = IndalekoStorageActivityDataModel.get_arangodb_schema()
        storage_activity_collection.add_schema(
            IndalekoStorageActivityDataModel.get_arangodb_schema()
        )
    else:
        ic("Collection schema:", storage_activity_collection_schema)
    # cleanup the collection
    bind_vars = {
        "@collection": storage_activity_collection.collection_name,
    }
    IndalekoDBConfig().get_arangodb().aql.execute(cleanup_aql_query, bind_vars=bind_vars)
    # create the documents
    bind_vars = {
        "@collection": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
    }
    timed_aql = TimedAQLExecute(
        query=cleanup_aql_query,
        bind_vars=bind_vars,
    )
    ic(timed_aql.get_data())
    # create the documents
    exit(0)

build_storage_activity_documents()

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
        timed_query = TimedAQLExecute(
            query=query.aql_count_query,
            bind_vars=query.bind_variables,
        )
        cursor = timed_query.get_cursor()
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
