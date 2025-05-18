"""Collection constants and utilities for the ablation framework."""


from pydantic import BaseModel

from db.db_collections import IndalekoDBCollections


class AblationCollections:
    """Collection names for the ablation framework.

    All collection names should be defined here as constants to avoid hardcoding
    names throughout the codebase. These collections are accessed through
    the IndalekoDBCollections class at runtime.
    """

    # Activity collections
    Indaleko_Ablation_Music_Activity_Collection = "AblationMusicActivity"
    Indaleko_Ablation_Location_Activity_Collection = "AblationLocationActivity"
    Indaleko_Ablation_Task_Activity_Collection = "AblationTaskActivity"
    Indaleko_Ablation_Collaboration_Activity_Collection = "AblationCollaborationActivity"
    Indaleko_Ablation_Storage_Activity_Collection = "AblationStorageActivity"
    Indaleko_Ablation_Media_Activity_Collection = "AblationMediaActivity"

    # Truth data collection - stores which entities should match each query
    Indaleko_Ablation_Query_Truth_Collection = "AblationQueryTruth"

    # Named entity collection - using the standard Indaleko collection
    Indaleko_Named_Entity_Collection = IndalekoDBCollections.Indaleko_Named_Entity_Collection

    # Ablation results collection - stores the results of the ablation tests
    Indaleko_Ablation_Results_Collection = "AblationResults"

    # Test metadata collection - stores metadata about the tests
    Indaleko_Ablation_Test_Metadata_Collection = "AblationTestMetadata"

    @classmethod
    def get_activity_collections(cls) -> list[str]:
        """Get all activity collection names.

        Returns:
            List[str]: List of activity collection names.
        """
        return [
            cls.Indaleko_Ablation_Music_Activity_Collection,
            cls.Indaleko_Ablation_Location_Activity_Collection,
            cls.Indaleko_Ablation_Task_Activity_Collection,
            cls.Indaleko_Ablation_Collaboration_Activity_Collection,
            cls.Indaleko_Ablation_Storage_Activity_Collection,
            cls.Indaleko_Ablation_Media_Activity_Collection,
        ]

    @classmethod
    def get_all_collections(cls) -> list[str]:
        """Get all collection names used by the ablation framework.

        Returns:
            List[str]: List of all collection names.
        """
        return cls.get_activity_collections() + [
            cls.Indaleko_Ablation_Query_Truth_Collection,
            cls.Indaleko_Named_Entity_Collection,
            cls.Indaleko_Ablation_Results_Collection,
            cls.Indaleko_Ablation_Test_Metadata_Collection,
        ]


class CollectionSchema(BaseModel):
    """Schema definition for a collection.

    This model defines the schema for a collection, including required fields
    and indexes. It is used to ensure consistent collection creation and
    management.
    """

    name: str
    type: str = "document"  # "document" or "edge"
    indexes: list[dict] = []  # List of index definitions

    class Config:
        frozen = False


def get_default_collection_schemas() -> list[CollectionSchema]:
    """Get default collection schemas for all ablation collections.

    Returns:
        List[CollectionSchema]: List of default collection schemas.
    """
    schemas = []

    # Activity collections
    for collection_name in AblationCollections.get_activity_collections():
        schemas.append(
            CollectionSchema(
                name=collection_name,
                type="document",
                indexes=[
                    # Persistent index on created_at for time-based queries
                    {
                        "type": "persistent",
                        "fields": ["created_at"],
                        "sparse": False,
                        "unique": False,
                    },
                    # Persistent index on id for fast lookups
                    {
                        "type": "persistent",
                        "fields": ["id"],
                        "sparse": False,
                        "unique": True,
                    },
                    # Persistent index on activity_type for filtering
                    {
                        "type": "persistent",
                        "fields": ["activity_type"],
                        "sparse": False,
                        "unique": False,
                    },
                ],
            ),
        )

    # Truth data collection
    schemas.append(
        CollectionSchema(
            name=AblationCollections.Indaleko_Ablation_Query_Truth_Collection,
            type="document",
            indexes=[
                # Persistent index on query_id for fast lookups
                {
                    "type": "persistent",
                    "fields": ["query_id"],
                    "sparse": False,
                    "unique": True,
                },
                # Persistent index on activity_types for filtering
                {
                    "type": "persistent",
                    "fields": ["activity_types"],
                    "sparse": False,
                    "unique": False,
                },
            ],
        ),
    )

    # Note: We don't need to create the Named Entity collection schema since we're using
    # the standard Indaleko NamedEntities collection from the main database

    # Ablation results collection
    schemas.append(
        CollectionSchema(
            name=AblationCollections.Indaleko_Ablation_Results_Collection,
            type="document",
            indexes=[
                # Persistent index on query_id for fast lookups
                {
                    "type": "persistent",
                    "fields": ["query_id"],
                    "sparse": False,
                    "unique": False,
                },
                # Persistent index on ablated_collection for filtering
                {
                    "type": "persistent",
                    "fields": ["ablated_collection"],
                    "sparse": False,
                    "unique": False,
                },
                # Combined index for unique query+collection
                {
                    "type": "persistent",
                    "fields": ["query_id", "ablated_collection"],
                    "sparse": False,
                    "unique": True,
                },
            ],
        ),
    )

    # Test metadata collection
    schemas.append(
        CollectionSchema(
            name=AblationCollections.Indaleko_Ablation_Test_Metadata_Collection,
            type="document",
            indexes=[
                # Persistent index on test_id for fast lookups
                {
                    "type": "persistent",
                    "fields": ["test_id"],
                    "sparse": False,
                    "unique": True,
                },
                # Persistent index on test_name for filtering
                {
                    "type": "persistent",
                    "fields": ["test_name"],
                    "sparse": False,
                    "unique": False,
                },
                # Persistent index on timestamp for time-based queries
                {
                    "type": "persistent",
                    "fields": ["timestamp"],
                    "sparse": False,
                    "unique": False,
                },
            ],
        ),
    )

    return schemas
