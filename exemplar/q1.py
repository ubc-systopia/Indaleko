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


# pylint: enable=wrong-import-position

class ExemplarQuery1:
    """Exemplar Query 1."""
    query = 'Show me documents with "report" in their titles.'
    aql_query = """
        FOR doc IN @@collection
            SEARCH
            ANALYZER(LIKE(doc.Label, @name), "text_en") OR
            ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case")
        LIMIT 50
        RETURN doc
    """
    aql_count_query = """
            RETURN LENGTH(
            FOR doc IN @@collection
                SEARCH
                ANALYZER(LIKE(doc.Label, @name), "text_en") OR
                ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case")
            RETURN 1
            )
    """
    named_entities = []
    bind_variables = {
        "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
        "name": "%report%",
    }

    exemplar_query = ExemplarQuery(
        query=query,
        aql_query=aql_query,
        aql_count_query=aql_count_query,
        named_entities=named_entities,
        bind_variables=bind_variables,
    )
    """Exemplar query object."""

    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery1.query,
            aql_query=ExemplarQuery1.aql_query,
            aql_count_query=ExemplarQuery1.aql_count_query,
            named_entities=ExemplarQuery1.named_entities,
            bind_variables=ExemplarQuery1.bind_variables,
        )

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery1.get_exemplar_query()
    ic(exemplar_query)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables,
    )
    ic(result.get_data())

if __name__ == "__main__":
    main()
