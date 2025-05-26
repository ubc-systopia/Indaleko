"""Exemplar Query 2"""

import os
import sys

from pathlib import Path
from typing import Self

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
from exemplar.exemplar_data_model import ExemplarAQLQuery, ExemplarQuery
from exemplar.reference_date import reference_date
from storage.i_object import IndalekoObject
from storage.known_attributes import KnownStorageAttributes


# pylint: enable=wrong-import-position

default_limit = 50

class ExemplarQuery2:
    """Exemplar Query 2."""

    def __init__(self: Self, *, limit: int | str = default_limit) -> None:
        """Initialize the exemplar query."""
        self._query = 'Show me documents with "report" in their titles.'
        self._limit = limit if isinstance(limit, int) else int(limit)  # type: ignore
        self._doc_format = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
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
        ]
        self._base_aql = """
            FOR doc IN @@collection
                SEARCH
                (doc[@mime_type] IN {doc_format} OR doc[@semantic_mime_type] IN {doc_format})
                FILTER doc.ObjectIdentifier in files_edited_on_phone AND
                    ((doc[@creation_timestamp] >= start_time AND doc[@creation_timestamp] <= @reference_time) OR
                        (doc[@modified_timestamp] >= start_time AND doc[@modified_timestamp] <= @reference_time))
            """
        self._aql_query_limit = f"""
            {self._base_aql}
            LIMIT @limit
            RETURN doc
        """
        self._aql_query_no_limit = f"""
            {self._base_aql}
            RETURN doc
        """
        self._aql_count_query = f"""
            RETURN LENGTH(
            {self._base_aql}
            RETURN 1
        )
        """
        self._named_entities = [
            {
                "name": "my phone",
                "category": IndalekoNamedEntityType.item,
            },
        ]
        self._base_bind_variables = {
            "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
            "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
            "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
            "semantic_mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
            "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,  # windows GPS
            "reference_time": reference_date,   # Reference date for the query
        }
        self._limit_bind_variables = self._base_bind_variables.copy()
        self._limit_bind_variables["limit"] = self._limit if isinstance(limit, int) else int(limit)
        self._no_limit_bind_variables = self._base_bind_variables
        self._exemplar_query = self._get_exemplar_query()
        self._named_entities = [
            {
                "name": "my phone",
                "category": IndalekoNamedEntityType.item,
            },
        ]

    def _get_exemplar_query(self: Self) -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
        user_query=self._query,
        aql_queries = {
            "with_limits": ExemplarAQLQuery(
                aql_query=self._aql_query_limit,
                bind_variables=self._limit_bind_variables, # type: ignore
            ),
            "no_limit": ExemplarAQLQuery(
                aql_query=self._aql_query_no_limit,
                bind_variables=self._no_limit_bind_variables, # type: ignore
            ),
            "count": ExemplarAQLQuery(
                aql_query=self._aql_count_query,
                bind_variables=self._no_limit_bind_variables, # type: ignore
            ),
        }
    )

    def get_exemplar_query(self: Self) -> ExemplarQuery | None:
        """Get the exemplar query."""
        if self._exemplar_query is None:
            ic("Exemplar query is None.")
            return None
        return self._exemplar_query

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query: ExemplarQuery | None = ExemplarQuery2().get_exemplar_query()
    if exemplar_query is None:
        ic("Exemplar query is None.")
        return
    result = {}
    for key, value in exemplar_query.aql_queries.items(): # type: ignore - this is not going to be None
        result[key] = TimedAQLExecute(
            description=f"{exemplar_query.user_query} - {key}",
            query=value.aql_query,
            bind_vars=value.bind_variables,
        )
    for key, timed_query in result.items():
        data = timed_query.get_data()
        ic(f"Query: {data['description']} (type {key})")
        results_cursor = list(timed_query.get_cursor())
        ic(f"Number of results: {len(results_cursor)}")
        if len(results_cursor) == 1:
            ic(f"Result: {results_cursor[0]}")
        query_time = data.get("query_time")
        if query_time is not None:
            ic(f"Query time: {query_time} seconds")

if __name__ == "__main__":
    main()
