"""Exemplar query 6."""

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
from exemplar.reference_date import reference_date
from storage.i_object import IndalekoObject
from storage.known_attributes import KnownStorageAttributes


# pylint: enable=wrong-import-position

class ExemplarQuery6:
    """Exemplar Query 6."""
    query = "Find PDFs I opened in the last week."
    aql_query = """
        LET start_time = DATE_ROUND(DATE_SUBTRACT(@reference_time, 1, "week"), 1, "day")
        FOR doc in @@collection
            SEARCH doc[@mime_type] == "application/pdf" OR doc[@semantic_mimetype] == "application/pdf"
            FILTER ((doc[@creation_timestamp] >= start_time AND doc[@creation_timestamp] <= @reference_time) OR
                    (doc[@modified_timestamp] >= start_time AND doc[@modified_timestamp] <= @reference_time) OR
                    (doc[@changed_timestamp] >= start_time AND doc[@changed_timestamp] <= @reference_time))
        LIMIT @limit
        RETURN doc
    """
    aql_count_query = """
        LET start_time = DATE_ROUND(DATE_SUBTRACT(@reference_time, 1, "week"), 1, "day")

        FOR doc IN @@collection
            SEARCH doc[@mime_type] == "application/pdf" OR doc[@semantic_mimetype] == "application/pdf"
            FILTER (
                (doc[@creation_timestamp] >= start_time AND doc[@creation_timestamp] <= @reference_time) OR
                (doc[@modified_timestamp] >= start_time AND doc[@modified_timestamp] <= @reference_time) OR
                (doc[@changed_timestamp] >= start_time AND doc[@changed_timestamp] <= @reference_time)
            )
            COLLECT WITH COUNT INTO total
            RETURN total
    """
    named_entities = [
    ]
    limit = 50
    bind_variables = {
        "@collection": IndalekoDBCollections.Indaleko_Objects_MimeType_View,
        "reference_time": reference_date,
        "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
        "semantic_mimetype" : KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
        "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
        "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
        "changed_timestamp": IndalekoObject.CHANGE_TIMESTAMP,
        "limit": limit,
    }
    count_bind_variables = {
        "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
        "reference_time": reference_date,
        "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
        "semantic_mimetype" : KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
        "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
        "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
        "changed_timestamp": IndalekoObject.CHANGE_TIMESTAMP,
    }
    ic('creating exemplar query', count_bind_variables)
    exemplar_query = ExemplarQuery(
        user_query=query,
        aql_query_with_limits=aql_query,
        aql_count_query=aql_count_query,
        named_entities=named_entities,
        bind_variables_with_limits=bind_variables,
        count_bind_variables=count_bind_variables,
    )
    ic('exemplar query created', exemplar_query.count_bind_variables)

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            user_query=ExemplarQuery6.query,
            aql_query_with_limits=ExemplarQuery6.aql_query,
            aql_count_query=ExemplarQuery6.aql_count_query,
            named_entities=ExemplarQuery6.named_entities,
            bind_variables_with_limits=ExemplarQuery6.bind_variables,
            count_bind_variables=ExemplarQuery6.count_bind_variables,
        )


def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery6.get_exemplar_query()
    ic(exemplar_query)
    ic('main', exemplar_query.count_bind_variables)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query_with_limits,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables_with_limits,
        count_bind_vars=exemplar_query.count_bind_variables,
    )
    cursor = result.get_cursor()
    data = result.get_data()
    ic(data)


if __name__ == "__main__":
    main()
