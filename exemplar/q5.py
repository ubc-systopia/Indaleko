"""Exemplar Query 5."""

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
from storage.known_attributes import KnownStorageAttributes


# pylint: enable=wrong-import-position

class ExemplarQuery5:
    """Exemplar Query 5."""
    query = "Show me photos taken within 16 kilometers of my house."
    aql_query = """
        LET home_coords = FIRST(
            FOR entity IN @@named_entities
            FILTER (
                entity.name == @home_location OR
                @home_location IN entity.aliases
            ) AND
            entity.type == @home_entity_type
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
            SEARCH (doc[@suffix_mimetype] IN photo_mime_types OR doc[@semantic_mimetype] IN photo_mime_types)
            LIMIT 50
            return doc
        //FOR doc IN @@collection
        //    FILTER (
        //        doc.SemanticAttributes[@suffix_mimetype] IN photo_mime_types #  suffix based MIME type
        //        OR
        //        doc.SemanticAttributes[@semantic_mimetype] IN photo_mime_types #  suffix based MIME type
        //    )
        //    LET distance = GEO_DISTANCE(
        //        [doc.longitude, doc.latitude],
        //        [home_coords.longitude, home_coords.latitude]
        //    )
        //    FILTER distance <= 16000
        //    RETURN doc
    """
    aql_count_query = """
        LET picture_format = [
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
        RETURN LENGTH(
        FOR doc IN @@collection
            SEARCH (doc[@suffix_mimetype] IN picture_format OR doc[@semantic_mimetype] IN picture_format)
            return 1
        )
    """
    named_entities = [
        {
            "name": "home",
            "aliases": ["home", "my house"],
            "category": IndalekoNamedEntityType.location,
        },
    ]
    bind_variables = {
        "suffix_mimetype": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
        "semantic_mimetype" : KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
        "home_entity_type": IndalekoNamedEntityType.location,
        "@named_entities": IndalekoDBCollections.Indaleko_Named_Entity_Collection,
        "@collection": IndalekoDBCollections.Indaleko_Objects_MimeType_View,
        "home_location": "home",
    }
    continue_bind_variables = bind_variables.copy()
    del continue_bind_variables["home_location"]
    del continue_bind_variables["home_entity_type"]
    del continue_bind_variables["@named_entities"]

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery5.query,
            aql_query=ExemplarQuery5.aql_query,
            aql_count_query=ExemplarQuery5.aql_count_query,
            named_entities=ExemplarQuery5.named_entities,
            bind_variables=ExemplarQuery5.bind_variables,
            count_bind_variables=ExemplarQuery5.continue_bind_variables,
        )

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery5.get_exemplar_query()
    ic(exemplar_query)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables,
        count_bind_vars=exemplar_query.count_bind_variables,
    )
    ic(result.get_data())
    ic(len(list(result.get_cursor())))

if __name__ == "__main__":
    main()
