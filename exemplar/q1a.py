"""Exemplar Query 1a - Word documents with 'report' in their titles."""

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
from storage.known_attributes import KnownStorageAttributes
# pylint: enable=wrong-import-position


class ExemplarQuery1a(ExemplarQueryBase):
    """Exemplar Query 1a - Search for Word documents with 'report' in titles."""

    def __init__(self: Self, *, limit: int | str = ExemplarQueryBase.DEFAULT_LIMIT) -> None:
        """Initialize the exemplar query."""
        # Define document formats before calling parent init
        self._doc_format = [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        ]
        super().__init__(limit=limit)

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return 'Show me docx documents with "report" in their titles.'

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return f"""
        LET doc_format = {self._doc_format}

        FOR doc IN @@collection
            SEARCH (doc[@mime_type] IN doc_format OR doc[@semantic_mime_type] IN doc_format) AND
            (ANALYZER(LIKE(doc.Label, @name), "text_en") OR
             ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case"))
        """

    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
            "name": "%report%",
            "semantic_mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
            "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,  # windows GPS
        }


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery1a)


if __name__ == "__main__":
    main()
