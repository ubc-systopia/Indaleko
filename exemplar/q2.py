"""Exemplar Query 2"""

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
from storage.i_object import IndalekoObject
from storage.known_attributes import KnownStorageAttributes


# pylint: enable=wrong-import-position

class ExemplarQuery2:
    """Exemplar Query 2."""
    query = "Find files I edited on my phone while traveling last month."
    aql_query = """
        LET start_time = DATE_ROUND(DATE_SUBTRACT(@reference_time, 1, "week"), 1, "day")
        LET doc_format = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  // .docx
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        // .xlsx
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation", // .pptx
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
            "application/json",
            "application/xml",
            "application/vnd.apple.keynote",
            "application/vnd.apple.numbers",
            "application/vnd.apple.pages",
        ]
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
            SEARCH (doc[@mime_type] IN doc_format OR doc[@semantic_mime_type] IN doc_format) AND NOT ANALYZER(PHRASE(doc.URI, "Volume"), "text_en")
            FILTER doc.ObjectIdentifier in files_edited_on_phone AND
                ((doc[@creation_timestamp] >= start_time AND doc[@creation_timestamp] <= @reference_time) OR
                    (doc[@modified_timestamp] >= start_time AND doc[@modified_timestamp] <= @reference_time))
            LIMIT 50
            return doc
    """
    aql_count_query = None
    named_entities = [
        {
            "name": "my phone",
            "category": IndalekoNamedEntityType.item,
        },
    ]
    bind_variables = {
        "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
        "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
        "semantic_mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
        "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX, # windows GPS
        "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
        "reference_time": reference_date,
    }

    exemplar_query = ExemplarQuery(
        query=query,
        aql_query=aql_query,
        aql_count_query=aql_count_query,
        named_entities=named_entities,
        bind_variables=bind_variables,
    )


    @staticmethod
    def get_exemplar_query() -> ExemplarQuery:
        """Get the query object."""
        return ExemplarQuery(
            query=ExemplarQuery2.query,
            aql_query=ExemplarQuery2.aql_query,
            aql_count_query=ExemplarQuery2.aql_count_query,
            named_entities=ExemplarQuery2.named_entities,
            bind_variables=ExemplarQuery2.bind_variables,
        )

def main():
    """Main function for testing functionality."""
    # Example usage
    exemplar_query = ExemplarQuery2.get_exemplar_query()
    ic(exemplar_query)
    result = TimedAQLExecute(
        query=exemplar_query.aql_query,
        count_query=exemplar_query.aql_count_query,
        bind_vars=exemplar_query.bind_variables,
    )
    ic(result.get_data())
    ic(len(list(result.get_cursor())))

if __name__ == "__main__":
    main()
