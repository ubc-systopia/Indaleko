"""Exemplar query 6."""

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

class ExemplarQuery6(ExemplarQuery):
    """Exemplar Query 6."""
    query = "Find PDFs I opened in the last week.",
    aql_query = """
        FOR doc IN @@collection
            FILTER (
                (
                    doc.SemanticAttributes[@suffix_mimetype] == "application/pdf" #  suffix based MIME type
                    OR
                    doc.SemanticAttributes[@semantic_mimetype] == "application/pdf" #  suffix based MIME type
                ) AND
                doc.timestamp >= DATE_SUBTRACT(@reference_date, 7, "days")
            )
            RETURN doc
    """
    aql_count_query = None  # TODO
    named_entities = [
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
            query=ExemplarQuery6.query,
            aql_query=ExemplarQuery6.aql_query,
            aql_count_query=ExemplarQuery6.aql_count_query,
            named_entities=ExemplarQuery6.named_entities,
            bind_variables=ExemplarQuery6.bind_variables,
        )
