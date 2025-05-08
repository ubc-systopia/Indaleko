"""Collection registration for the ablation framework.

This module provides functions for registering ablation framework collections
with the Indaleko database collection registry.
"""

import logging

from db.db_collections import IndalekoDBCollections
from db.i_collections import ICollection

from .collections import AblationCollections

logger = logging.getLogger(__name__)


def register_ablation_collections() -> None:
    """Register the ablation collections with the IndalekoDBCollections class.

    This function adds the ablation framework collections to the IndalekoDBCollections
    class, making them available throughout the Indaleko system.
    """
    # Check if collections are already registered
    if hasattr(IndalekoDBCollections, AblationCollections.Indaleko_Ablation_Music_Activity_Collection):
        logger.info("Ablation collections already registered")
        return

    # Register all collections
    for collection_name in dir(AblationCollections):
        # Skip non-collection attributes
        if collection_name.startswith("_") or not collection_name.startswith("Indaleko_"):
            continue

        # Get the collection value
        collection_value = getattr(AblationCollections, collection_name)

        # Add the collection to IndalekoDBCollections
        setattr(IndalekoDBCollections, collection_name, collection_value)

    logger.info(f"Registered {len(AblationCollections.get_all_collections())} ablation collections")


def create_collection_interfaces() -> list[ICollection]:
    """Create collection interface objects for ablation collections.

    Returns:
        List[ICollection]: List of collection interface objects.
    """
    interfaces = []

    # Create interfaces for all collections
    for collection_name in dir(AblationCollections):
        # Skip non-collection attributes
        if collection_name.startswith("_") or not collection_name.startswith("Indaleko_"):
            continue

        # Get the collection value
        collection_value = getattr(AblationCollections, collection_name)

        # Create a collection interface
        interface = ICollection(
            name=collection_value,
            api_property=collection_name,
            api_object=AblationCollections.__name__,
            description=f"Ablation framework collection for {collection_name}",
        )

        interfaces.append(interface)

    return interfaces


def register_collections_with_db_setup() -> None:
    """Register collections with the database setup module.

    This function ensures that the ablation collections are created
    when the database is initialized.
    """
    from db.db_setup import register_collection_interfaces

    # Create the collection interfaces
    interfaces = create_collection_interfaces()

    # Register the interfaces
    register_collection_interfaces(interfaces)

    logger.info(f"Registered {len(interfaces)} ablation collection interfaces with db_setup")


def verify_collections_registered() -> bool:
    """Verify that ablation collections are registered.

    Returns:
        bool: True if all collections are registered, False otherwise.
    """
    # Check IndalekoDBCollections
    for collection_name in dir(AblationCollections):
        # Skip non-collection attributes
        if collection_name.startswith("_") or not collection_name.startswith("Indaleko_"):
            continue

        # Check if the collection is registered
        if not hasattr(IndalekoDBCollections, collection_name):
            logger.warning(f"Collection {collection_name} not registered in IndalekoDBCollections")
            return False

    # Check ICollection registration
    try:
        from db.db_setup import get_registered_collection_interfaces

        # Get registered interfaces
        interfaces = get_registered_collection_interfaces()

        # Check each collection
        ablation_collections = set(AblationCollections.get_all_collections())
        registered_collections = set(interface.name for interface in interfaces)

        # Check if all ablation collections are registered
        if not ablation_collections.issubset(registered_collections):
            missing = ablation_collections - registered_collections
            logger.warning(f"Collections {missing} not registered as ICollection")
            return False

    except ImportError:
        logger.warning("Could not import db_setup module")
        return False

    return True
