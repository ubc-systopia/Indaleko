"""Exemplar Query 2 - Documents edited on my phone."""

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

from typing import Self

# pylint: disable=wrong-import-position
from data_models.named_entity import IndalekoNamedEntityType
from db.db_collections import IndalekoDBCollections
from exemplar.qbase import ExemplarQueryBase, exemplar_main
from exemplar.reference_date import reference_date
from storage.known_attributes import KnownStorageAttributes
from storage.i_object import IndalekoObject
# pylint: enable=wrong-import-position


class ExemplarQuery2(ExemplarQueryBase):
    """Exemplar Query 2 - Search for documents edited on my phone."""

    def __init__(self: Self, *, limit: int | str = ExemplarQueryBase.DEFAULT_LIMIT) -> None:
        """Initialize the exemplar query."""
        # Define document formats before calling parent init
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
        super().__init__(limit=limit)

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return 'Show me documents with "report" in their titles.'

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return f"""
            LET doc_format = {self._doc_format}
            LET start_time = DATE_ROUND(DATE_SUBTRACT(@reference_time, 1, "week"), 1, "day")
            // This simulates the results of files on the phone that have been edited in the
            // last month of travel.
            LET files_edited_on_phone = [
                "458357ae-867c-41d3-b958-740f3bf14aaf",
                "d5c15c99-82f4-48fb-8b75-1b63a0ccd427",
                "02e1b2ac-7fbf-4e00-9d7b-c1191a080f31",
                "5a4af4d3-ca7f-4b46-91d6-a21dc8312419",
                "b8b471d6-9628-45c5-9a9e-ec8d85f4c3a6",
                "efc73465-dea7-4ef2-85d3-b55f39937abc",
                "a6ef9f99-4eae-4a38-9ede-c1959d388cd1"
            ]
            FOR doc IN @@collection
                SEARCH
                (doc[@mime_type] IN doc_format OR doc[@semantic_mime_type] IN doc_format)
                AND doc.ObjectIdentifier in files_edited_on_phone AND
                    ((doc[@creation_timestamp] >= start_time AND doc[@creation_timestamp] <= @reference_time) OR
                        (doc[@modified_timestamp] >= start_time AND doc[@modified_timestamp] <= @reference_time))
            """

    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "@collection": IndalekoDBCollections.Indaleko_Objects_Essential_View,
            "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
            "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
            "semantic_mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
            "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,  # windows GPS
            "reference_time": reference_date,   # Reference date for the query
        }

    def _get_named_entities(self: Self) -> list:
        """Return named entities used in this query."""
        return [
            {
                "name": "my phone",
                "category": IndalekoNamedEntityType.item,
            },
        ]


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery2)


if __name__ == "__main__":
    main()
