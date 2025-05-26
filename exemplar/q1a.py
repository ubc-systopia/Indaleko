"""Exemplar Query 1"""

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
from db.db_collections import IndalekoDBCollections
from db.utils.query_performance import TimedAQLExecute
from exemplar.exemplar_data_model import ExemplarQuery
from storage.known_attributes import KnownStorageAttributes


# pylint: enable=wrong-import-position

class ExemplarQuery1a:
    """Exemplar Query 1."""
    query = 'Show me docx documents with "report" in their titles.'
    aql_query = """
        LET doc_format = [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  // .docx
        ]

        FOR doc IN @@collection
            SEARCH (doc[@mime_type] IN doc_format OR doc[@semantic_mime_type] IN doc_format) AND
            (ANALYZER(LIKE(doc.Label, @name), "text_en") OR
             ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case"))
        LIMIT 50
        RETURN doc
    """
    aql_count_query = """
        LET doc_format = [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  // .docx
        ]

        RETURN LENGTH(
        FOR doc IN @@collection
            SEARCH (doc[@mime_type] IN doc_format OR doc[@semantic_mime_type] IN doc_format) AND
            (ANALYZER(LIKE(doc.Label, @name), "text_en") OR
             ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case"))
        RETURN 1
        )
    """
    named_entities = []
    bind_variables = {
        "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
        "name": "%report%",
        "semantic_mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
        "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX, # windows GPS
    }

    exemplar_query = ExemplarQuery(
        user_query=query,
        aql_query_with_limits=aql_query,
        aql_count_query=aql_count_query,
        named_entities=named_entities,
        bind_variables_with_limits=bind_variables,
    )
    """Exemplar query object."""

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            user_query=ExemplarQuery1a.query,
            aql_query_with_limits=ExemplarQuery1a.aql_query,
            aql_count_query=ExemplarQuery1a.aql_count_query,
            named_entities=ExemplarQuery1a.named_entities,
            bind_variables_with_limits=ExemplarQuery1a.bind_variables,
        )

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery1a.get_exemplar_query()
    ic(exemplar_query)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query_with_limits,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables_with_limits,
    )
    ic(result.get_data())

if __name__ == "__main__":
    main()
