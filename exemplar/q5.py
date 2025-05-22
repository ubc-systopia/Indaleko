"""Exemplar Query 5."""

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
from storage.known_attributes import KnownStorageAttributes


# pylint: enable=wrong-import-position

class ExemplarQuery5(ExemplarQuery):
    """Exemplar Query 5."""
    query = "Show me files I created while on vacation in Bali last June.",
    aql_query = """
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
                doc.SemanticAttributes[@suffix_mimetype] IN photo_mime_types #  suffix based MIME type
                OR
                doc.SemanticAttributes[@semantic_mimetype] IN photo_mime_types #  suffix based MIME type
            )
            LET distance = GEO_DISTANCE(
                [doc.longitude, doc.latitude],
                [home_coords.longitude, home_coords.latitude]
            )
            FILTER distance <= 16000
            RETURN doc
    """
    aql_count_query = None  # TODO
    named_entities = [
        {
            "name": "home",
            "aliases": ["home", "my house"],
            "category": IndalekoNamedEntityType.location,
        },
    ]
    bind_variables = {
        "reference_date": reference_date,
        "suffix_mimetype": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
        "semantic_mimetype" : KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
    }

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery5.query,
            aql_query=ExemplarQuery5.aql_query,
            aql_count_query=ExemplarQuery5.aql_count_query,
            named_entities=ExemplarQuery5.named_entities,
            bind_variables=ExemplarQuery5.bind_variables,
        )
