"""Exemplar Query 2 - Refactored to use base class"""

from typing import Self, Any

from data_models.named_entity import IndalekoNamedEntityType
from db.db_collections import IndalekoDBCollections
from db.qbase import ExemplarQueryBase, standard_main
from exemplar.reference_date import reference_date
from storage.i_object import IndalekoObject
from storage.known_attributes import KnownStorageAttributes


class ExemplarQuery2(ExemplarQueryBase):
    """Exemplar Query 2 - Find documents edited on phone."""
    
    def _initialize_query_components(self: Self) -> None:
        """Initialize query-specific components."""
        self._query = 'Show me documents with "report" in their titles.'
        
        # Document formats to search for
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
        
        self._named_entities = [
            {
                "name": "my phone",
                "category": IndalekoNamedEntityType.item,
            },
        ]
    
    def _build_base_bind_variables(self: Self) -> dict[str, Any]:
        """Build the base bind variables for the query."""
        return {
            "modified_timestamp": IndalekoObject.MODIFICATION_TIMESTAMP,
            "creation_timestamp": IndalekoObject.CREATION_TIMESTAMP,
            "semantic_mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIME_TYPE,
            "mime_type": KnownStorageAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX,  # windows GPS
            "reference_time": reference_date,   # Reference date for the query
        }
    
    def _get_collection(self: Self) -> str:
        """Override to use timestamp view instead of text view."""
        return IndalekoDBCollections.Indaleko_Objects_Timestamp_View


def main():
    """Main function for testing functionality."""
    standard_main(ExemplarQuery2)


if __name__ == "__main__":
    main()