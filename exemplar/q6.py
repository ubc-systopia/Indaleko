"""Exemplar Query 6 - PDFs opened in the last week."""

import os
import sys

from typing import Self
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
from exemplar.qbase import ExemplarQueryBase, exemplar_main
from exemplar.reference_date import reference_date
from storage.i_object import IndalekoObject
from storage.known_attributes import KnownStorageAttributes
# pylint: enable=wrong-import-position


class ExemplarQuery6(ExemplarQueryBase):
    """Exemplar Query 6 - Search for PDFs opened in the last week."""

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return "Find PDFs I opened in the last week."

    def _get_setup_aql(self: Self) -> str:
        """Return the setup AQL query."""
        return """
        LET end_time = @reference_time
        LET start_time = DATE_ROUND(DATE_SUBTRACT(end_time, 1, "week"), 1, "day")
        """

    def _get_core_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return """
        FOR doc in @@collection
            SEARCH doc[@mime_type] == "application/pdf" OR doc[@semantic_mimetype] == "application/pdf"
            FILTER ((doc[@creation_timestamp] >= start_time AND doc[@creation_timestamp] <= end_time) OR
                    (doc[@modified_timestamp] >= start_time AND doc[@modified_timestamp] <= end_time) OR
                    (doc[@changed_timestamp] >= start_time AND doc[@changed_timestamp] <= end_time))
        """

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query with LIMIT and RETURN."""
        return f"""
            {self._get_setup_aql()}
            {self._get_core_aql()}
            RETURN doc
        """

    def _get_aql_query_limit(self: Self) -> str:
        """Return the AQL query with limit."""
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}

            LIMIT @limit
            RETURN doc
        """

    def _get_aql_query_no_limit(self: Self) -> str:
        """Return the AQL query without limit."""
        return f"""
            {self._get_setup_aql()}

            {self._get_core_aql()}
        """ + """
            RETURN {
                "ObjectIdentifier": doc.ObjectIdentifier,
                "Path": doc.Path,
                "Label": doc.Label,
            }
        """

    def _get_aql_count_query(self: Self) -> str:
        """Return the AQL count query."""
        return f"""
            {self._get_setup_aql()}
            RETURN LENGTH(
                {self._get_core_aql()}
                RETURN 1
            )
        """


    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "@collection": IndalekoDBCollections.Indaleko_Objects_MimeType_View,
            "reference_time": reference_date,
            "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,
            "semantic_mimetype": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
            "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
            "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
            "changed_timestamp": IndalekoObject.CHANGE_TIMESTAMP,
        }


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery6)


if __name__ == "__main__":
    main()
