"""
Script to fix views in ArangoDB for Indaleko.

This script forcibly recreates all required views.
"""

import contextlib
import logging
import os
import sys

from pathlib import Path


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig


# pylint: enable=wrong-import-position

def fix_views(verbose:bool = True) -> None:  # noqa: FBT001, FBT002
    """
    Forcibly recreate all views.

    Args:
        verbose: Whether to print verbose output

    Returns:
        bool: True if views were successfully created, False otherwise
    """
    logging.basicConfig(level=logging.DEBUG)

    if verbose:
        pass
    db_config = IndalekoDBConfig()
    db_config.start()
    db = db_config.get_arangodb()


    # First delete all existing views
    # Use db directly to list and delete views
    views_list = db.views()

    for view in views_list:
        view_name = view.get("name", "Unknown")
        with contextlib.suppress(Exception):
            db.delete_view(view_name)

    # Now create views one by one directly using the database API

    # ObjectsTextView
    objects_view = {
        "name": IndalekoDBCollections.Indaleko_Objects_Text_View,
        "type": "arangosearch",
        "links": {
            IndalekoDBCollections.Indaleko_Object_Collection: {
                "analyzers": ["text_en", "Indaleko::indaleko_camel_case",
                               "Indaleko::indaleko_snake_case", "Indaleko::indaleko_filename"],
                "includeAllFields": False,
                "storeValues": "id",
                "fields": {
                    "Label": {
                        "analyzers": ["text_en", "Indaleko::indaleko_camel_case",
                                      "Indaleko::indaleko_snake_case",
                                      "Indaleko::indaleko_filename"],
                    },
                    "Record.Attributes.URI": {
                        "analyzers": ["text_en"],
                    },
                    "Record.Attributes.Description": {
                        "analyzers": ["text_en"],
                    },
                },
            },
        },
    }

    # ActivityTextView
    activity_view = {
        "name": IndalekoDBCollections.Indaleko_Activity_Text_View,
        "type": "arangosearch",
        "links": {
            IndalekoDBCollections.Indaleko_ActivityContext_Collection: {
                "analyzers": ["text_en"],
                "includeAllFields": False,
                "storeValues": "id",
                "fields": {
                    "Description": {
                        "analyzers": ["text_en"],
                    },
                    "Location": {
                        "analyzers": ["text_en"],
                    },
                    "Notes": {
                        "analyzers": ["text_en"],
                    },
                    "Tags": {
                        "analyzers": ["text_en"],
                    },
                },
            },
        },
    }

    # NamedEntityTextView
    entity_view = {
        "name": IndalekoDBCollections.Indaleko_Named_Entity_Text_View,
        "type": "arangosearch",
        "links": {
            IndalekoDBCollections.Indaleko_Named_Entity_Collection: {
                "analyzers": ["text_en"],
                "includeAllFields": False,
                "storeValues": "id",
                "fields": {
                    "name": {
                        "analyzers": ["text_en"],
                    },
                    "description": {
                        "analyzers": ["text_en"],
                    },
                    "address": {
                        "analyzers": ["text_en"],
                    },
                    "tags": {
                        "analyzers": ["text_en"],
                    },
                },
            },
        },
    }

    # EntityEquivalenceTextView
    equiv_view = {
        "name": IndalekoDBCollections.Indaleko_Entity_Equivalence_Text_View,
        "type": "arangosearch",
        "links": {
            IndalekoDBCollections.Indaleko_Entity_Equivalence_Node_Collection: {
                "analyzers": ["text_en"],
                "includeAllFields": False,
                "storeValues": "id",
                "fields": {
                    "name": {
                        "analyzers": ["text_en"],
                    },
                    "context": {
                        "analyzers": ["text_en"],
                    },
                },
            },
        },
    }

    # KnowledgeTextView
    knowledge_view = {
        "name": IndalekoDBCollections.Indaleko_Knowledge_Text_View,
        "type": "arangosearch",
        "links": {
            IndalekoDBCollections.Indaleko_Learning_Event_Collection: {
                "analyzers": ["text_en"],
                "includeAllFields": False,
                "storeValues": "id",
                "fields": {
                    "content": {
                        "analyzers": ["text_en"],
                    },
                    "source": {
                        "analyzers": ["text_en"],
                    },
                    "metadata": {
                        "analyzers": ["text_en"],
                    },
                },
            },
        },
    }

    views = [objects_view, activity_view, entity_view, equiv_view, knowledge_view]

    for view in views:
        view_name = view["name"]

        # Create the view with just the name and type first
        db.create_arangosearch_view(
            name=view_name,
            properties={"type": "arangosearch"},
        )

        # Now update the view with proper links
        links = view.get("links", {})
        if links:
            properties = {
                "links": links,
            }
            db.update_view(view_name, properties)


    # Verify collections exist for the links
    for view in views:
        for collection_name in view.get("links", {}):
            if db.has_collection(collection_name):
                pass
            else:
                pass


if __name__ == "__main__":
    fix_views()
