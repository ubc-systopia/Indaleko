"""
Indaleko Database Collections.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
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
from activity.context.data_models.context_data_model import (
    IndalekoActivityContextDataModel,
)
from activity.data_model.activity import IndalekoActivityDataModel
from data_models import (
    IndalekoActivityDataRegistrationDataModel,
    IndalekoCollectionMetadataDataModel,
    IndalekoIdentityDomainDataModel,
    IndalekoMachineConfigDataModel,
    IndalekoObjectDataModel,
    IndalekoPerformanceDataModel,
    IndalekoQueryHistoryDataModel,
    IndalekoRelationshipDataModel,
    IndalekoServiceDataModel,
    IndalekoUserDataModel,
)
from data_models.named_entity import IndalekoNamedEntityDataModel
from semantic.data_models.base_data_model import BaseSemanticDataModel

# Import the Archivist memory model if available
try:
    from query.memory.archivist_memory import IndalekoArchivistMemoryModel

    HAS_ARCHIVIST_MEMORY = True
except ImportError:
    HAS_ARCHIVIST_MEMORY = False

# Import the Entity Equivalence models if available
try:
    from archivist.entity_equivalence import (
        EntityEquivalenceGroup,
        EntityEquivalenceNode,
        EntityEquivalenceRelation,
    )

    HAS_ENTITY_EQUIVALENCE = True
except ImportError:
    HAS_ENTITY_EQUIVALENCE = False

# Import the Knowledge Base models if available
try:
    from archivist.knowledge_base.data_models import (
        FeedbackRecordDataModel,
        KnowledgePatternDataModel,
        LearningEventDataModel,
    )

    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False

# pylint: enable=wrong-import-position


class IndalekoDBCollections:
    """Defines the set of well-known collections used by Indaleko."""

    Indaleko_Object_Collection = "Objects"
    Indaleko_Relationship_Collection = "Relationships"
    Indaleko_Service_Collection = "Services"
    Indaleko_MachineConfig_Collection = "MachineConfig"
    Indaleko_ActivityDataProvider_Collection = "ActivityDataProviders"
    Indaleko_ActivityContext_Collection = "ActivityContext"
    Indaleko_MusicActivityData_Collection = "MusicActivityContext"
    Indaleko_TempActivityData_Collection = "TempActivityContext"
    Indaleko_GeoActivityData_Collection = "GeoActivityContext"
    Indaleko_Identity_Domain_Collection = "IdentityDomains"
    Indaleko_User_Collection = "Users"
    Indaleko_User_Relationship_Collection = "UserRelationships"
    Indaleko_Performance_Data_Collection = "PerformanceData"
    Indaleko_Query_History_Collection = "QueryHistory"
    Indaleko_SemanticData_Collection = "SemanticData"
    Indaleko_Named_Entity_Collection = "NamedEntities"
    Indaleko_Collection_Metadata = "CollectionMetadata"
    Indaleko_Archivist_Memory_Collection = "ArchivistMemory"

    # Entity Equivalence Collections
    Indaleko_Entity_Equivalence_Node_Collection = "EntityEquivalenceNodes"
    Indaleko_Entity_Equivalence_Relation_Collection = "EntityEquivalenceRelations"
    Indaleko_Entity_Equivalence_Group_Collection = "EntityEquivalenceGroups"

    # Knowledge Base collections
    Indaleko_Learning_Event_Collection = "LearningEvents"
    Indaleko_Knowledge_Pattern_Collection = "KnowledgePatterns"
    Indaleko_Feedback_Record_Collection = "FeedbackRecords"

    # Define view names
    Indaleko_Objects_Text_View = "ObjectsTextView"
    Indaleko_Objects_Text_View_Legacy = "ObjectsTextViewLegacy"
    Indaleko_Named_Entity_Text_View = "NamedEntityTextView"
    Indaleko_Activity_Text_View = "ActivityTextView"
    Indaleko_Entity_Equivalence_Text_View = "EntityEquivalenceTextView"
    Indaleko_Knowledge_Text_View = "KnowledgeTextView"

    Collections = {  # noqa: RUF012
        Indaleko_Object_Collection: {
            "internal": False,
            "schema": IndalekoObjectDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "URI": {"fields": ["URI"], "unique": True, "type": "persistent"},
                "file identity": {
                    "fields": ["ObjectIdentifier"],
                    "unique": True,
                    "type": "persistent",
                },
                "local identity": {
                    # Question: should this be combined with other info to allow uniqueness?
                    "fields": ["LocalIdentifier"],
                    "unique": False,
                    "type": "persistent",
                },
                "file name": {
                    "fields": ["Label"],
                    "unique": False,
                    "type": "persistent",
                },
                "timestamps": {
                    "fields": ["Timestamps.Label[*].Value"],
                    "unique": False,
                    "type": "persistent",
                },
                "semantic_attributes": {
                    "field" : ["SemanticAttributes[*]"],
                    "unqiue": False,
                    "type": "persistent",
                },
                "semantic_attributes_inverted": {
                    "fields": ["SemanticAttributes[*].Value"],
                    "unique": False,
                    "type": "inverted",
                },
                "sizes": {
                    "fields": ["Size"],
                    "unique": False,
                    "type": "persistent",
                    "sparse": True,
                }
            },
            "views": [
                {
                    "name": Indaleko_Objects_Text_View,
                    "fields": {
                        "Label": [
                            "text_en",
                            "indaleko_snake_case",
                        ],
                        "URI": ["text_en"],
                        "LocalPath": ["text_en"],
                        # Timestamps promoted to top-level fields explicitly
                        "434f7ac1-f71a-4cea-a830-e2ea9a47db5a": [],  # Modified
                        "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6": [],  # Created
                        "581b5332-4d37-49c7-892a-854824f5d66f": [],  # Accessed
                        "3bdc4130-774f-4e99-914e-0bec9ee47aab": [],  # Changed
                        # Size for numeric range queries
                        "Size": [],
                        # Semantic Attributes (e.g., MIME type, file suffix)
                        "8aeb9b5a-3d08-4d1f-9921-0795343d9eb3": ["text_en"],  # MIME type
                        "f980b0c8-3d24-4a77-b985-5e945803991f": ["text_en"],  # File suffix
                    },
                    "stored_values": ["_key", "Label", "Size", "LocalPath"],
                },
                {
                    "name": Indaleko_Objects_Text_View_Legacy,
                    "fields": {
                        "Label": [
                            "text_en",
                            "indaleko_camel_case",
                            "indaleko_snake_case",
                            "indaleko_filename",
                        ],
                        "Record.Attributes.URI": ["text_en"],
                        "Record.Attributes.Description": ["text_en"],
                        "Tags": ["text_en"],
                    },
                    "stored_values": ["_key", "Label"],
                },
            ],
        },
        Indaleko_Relationship_Collection: {
            "internal": False,
            "schema": IndalekoRelationshipDataModel.get_arangodb_schema(),
            "edge": True,
            "indices": {
                "relationship": {
                    "fields": ["relationship"],
                    "unique": False,
                    "type": "persistent",
                },
                "vertex1": {
                    "fields": ["object1"],
                    "unique": False,
                    "type": "persistent",
                },
                "vertex2": {
                    "fields": ["object2"],
                    "unique": False,
                    "type": "persistent",
                },
                "edge": {
                    "fields": ["object1", "object2"],
                    "unique": False,
                    "type": "persistent",
                },
            },
        },
        Indaleko_Service_Collection: {
            "internal": True,  # registration for various services, not generally useful for querying
            "schema": IndalekoServiceDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "identifier": {
                    "fields": ["Name"],
                    "unique": True,
                    "type": "persistent",
                },
            },
        },
        Indaleko_MachineConfig_Collection: {
            "internal": False,
            "schema": IndalekoMachineConfigDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_ActivityDataProvider_Collection: {
            "internal": True,  # registration for various activity data providers, not generally useful for querying
            "schema": IndalekoActivityDataRegistrationDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_ActivityContext_Collection: {
            "internal": False,
            "schema": IndalekoActivityContextDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "handle": {
                    "fields": ["Handle"],
                    "unique": True,
                    "type": "persistent",
                },
                "timestamp": {
                    "fields": ["Timestamp"],
                    "unique": True,
                    "type": "persistent",
                },
                "cursors": {
                    "fields": ["Cursors"],
                    "unique": True,
                    "type": "persistent",
                },
            },
            "views": [
                {
                    "name": Indaleko_Activity_Text_View,
                    "fields": ["Description", "Location", "Notes", "Tags"],
                    "analyzers": ["text_en"],
                    "stored_values": ["_key", "ActivityType", "Timestamp"],
                },
            ],
        },
        Indaleko_MusicActivityData_Collection: {
            "internal": False,
            "schema": IndalekoActivityDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_GeoActivityData_Collection: {
            "internal": False,
            "schema": IndalekoActivityDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_TempActivityData_Collection: {
            "internal": True,  # temporary storage for activity data, not generally useful for querying
            "schema": IndalekoActivityDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_SemanticData_Collection: {
            "schema": BaseSemanticDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "source identity": {
                    "fields": ["ObjectIdentifier"],
                    "unique": True,
                    "type": "persistent",
                },
            },
        },
        Indaleko_Identity_Domain_Collection: {
            "schema": IndalekoIdentityDomainDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_User_Collection: {
            "internal": False,
            "schema": IndalekoUserDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "identifier": {
                    "fields": ["Identifier"],
                    "unique": True,
                    "type": "persistent",
                },
            },
        },
        # Indaleko_User_Relationship_Collection:  'This needs to be tied into NER work'
        Indaleko_Performance_Data_Collection: {
            "internal": True,  # performance data is not generally useful for querying
            "schema": IndalekoPerformanceDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_Query_History_Collection: {
            "internal": False,
            "schema": IndalekoQueryHistoryDataModel.get_arangodb_schema(),
            "edge": False,
            "geoJson": True,
            "indices": {},
        },
        Indaleko_Named_Entity_Collection: {
            "internal": False,
            "schema": IndalekoNamedEntityDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "Name": {"fields": ["name"], "unique": True, "type": "persistent"},
                "Location": {
                    "fields": ["gis_location"],
                    "type": "geo",
                    "unique": False,
                    "geo_json": True,
                },
                "Device": {
                    "fields": ["device_id"],
                    "unique": True,
                    "type": "persistent",
                    "sparse": True,
                },
            },
            "views": [
                {
                    "name": Indaleko_Named_Entity_Text_View,
                    "fields": ["name", "description", "address", "tags"],
                    "analyzers": ["text_en"],
                    "stored_values": ["_key", "name", "entity_type"],
                },
            ],
        },
        Indaleko_Collection_Metadata: {
            "internal": True,  # metadata about collections, not generally useful for querying
            "schema": IndalekoCollectionMetadataDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {},
        },
        Indaleko_Archivist_Memory_Collection: {
            "internal": True,  # archivist memory is not generally useful for user queries
            "schema": (IndalekoArchivistMemoryModel.get_arangodb_schema() if HAS_ARCHIVIST_MEMORY else {}),
            "edge": False,
            "indices": {
                "timestamp": {
                    "fields": ["Record.Timestamp"],
                    "unique": False,
                    "type": "persistent",
                },
            },
        },
        Indaleko_Entity_Equivalence_Node_Collection: {
            "internal": False,
            "schema": (EntityEquivalenceNode.get_arangodb_schema() if HAS_ENTITY_EQUIVALENCE else {}),
            "edge": False,
            "indices": {
                "name": {
                    "fields": ["name"],
                    "unique": False,
                    "type": "persistent",
                },
                "entity_type": {
                    "fields": ["entity_type"],
                    "unique": False,
                    "type": "persistent",
                },
                "canonical": {
                    "fields": ["canonical"],
                    "unique": False,
                    "type": "persistent",
                },
            },
            "views": [
                {
                    "name": Indaleko_Entity_Equivalence_Text_View,
                    "fields": ["name", "context"],
                    "analyzers": ["text_en"],
                    "stored_values": ["_key", "name", "entity_id", "canonical"],
                },
            ],
        },
        Indaleko_Entity_Equivalence_Relation_Collection: {
            "internal": False,
            "schema": (EntityEquivalenceRelation.get_arangodb_schema() if HAS_ENTITY_EQUIVALENCE else {}),
            "edge": True,
            "indices": {
                "source": {
                    "fields": ["source_id"],
                    "unique": False,
                    "type": "persistent",
                },
                "target": {
                    "fields": ["target_id"],
                    "unique": False,
                    "type": "persistent",
                },
                "relation_type": {
                    "fields": ["relation_type"],
                    "unique": False,
                    "type": "persistent",
                },
                "confidence": {
                    "fields": ["confidence"],
                    "unique": False,
                    "type": "persistent",
                },
            },
        },
        Indaleko_Entity_Equivalence_Group_Collection: {
            "internal": False,
            "schema": (EntityEquivalenceGroup.get_arangodb_schema() if HAS_ENTITY_EQUIVALENCE else {}),
            "edge": False,
            "indices": {
                "canonical_id": {
                    "fields": ["canonical_id"],
                    "unique": False,
                    "type": "persistent",
                },
                "entity_type": {
                    "fields": ["entity_type"],
                    "unique": False,
                    "type": "persistent",
                },
            },
        },
        Indaleko_Learning_Event_Collection: {
            "internal": False,
            "schema": (LearningEventDataModel.get_arangodb_schema() if HAS_KNOWLEDGE_BASE else {}),
            "edge": False,
            "indices": {
                "event_type": {
                    "fields": ["event_type"],
                    "unique": False,
                    "type": "persistent",
                },
                "timestamp": {
                    "fields": ["timestamp"],
                    "unique": False,
                    "type": "persistent",
                },
            },
            "views": [
                {
                    "name": Indaleko_Knowledge_Text_View,
                    "fields": ["content", "source", "metadata"],
                    "analyzers": ["text_en"],
                    "stored_values": ["_key", "event_type", "timestamp"],
                },
            ],
        },
        Indaleko_Knowledge_Pattern_Collection: {
            "internal": False,
            "schema": (KnowledgePatternDataModel.get_arangodb_schema() if HAS_KNOWLEDGE_BASE else {}),
            "edge": False,
            "indices": {
                "pattern_type": {
                    "fields": ["pattern_type"],
                    "unique": False,
                    "type": "persistent",
                },
                "confidence": {
                    "fields": ["confidence"],
                    "unique": False,
                    "type": "persistent",
                },
                "usage_count": {
                    "fields": ["usage_count"],
                    "unique": False,
                    "type": "persistent",
                },
            },
        },
        Indaleko_Feedback_Record_Collection: {
            "internal": False,
            "schema": (FeedbackRecordDataModel.get_arangodb_schema() if HAS_KNOWLEDGE_BASE else {}),
            "edge": False,
            "indices": {
                "feedback_type": {
                    "fields": ["feedback_type"],
                    "unique": False,
                    "type": "persistent",
                },
                "timestamp": {
                    "fields": ["timestamp"],
                    "unique": False,
                    "type": "persistent",
                },
                "feedback_strength": {
                    "fields": ["feedback_strength"],
                    "unique": False,
                    "type": "persistent",
                },
            },
        },
    }


def main():
    """Main entry point for the script."""
    ic("Indaleko Database Collections")
    verbose = False
    for collection in IndalekoDBCollections.Collections:
        ic(f"Collection: {collection}")
        if verbose:
            for key, value in IndalekoDBCollections.Collections[collection].items():
                if key == "schema":
                    schema = json.dumps(value, indent=4)
                    print(f"Schema: {schema}")
                else:
                    ic(f"  {key}: {value}")
        print("\n")


if __name__ == "__main__":
    main()
