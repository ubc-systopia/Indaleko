"""
Semantic attributes module for the model-based data generator.

This module provides dynamic management of semantic attributes with UUIDs,
following the pattern used in the main Indaleko codebase.
"""

import uuid
from typing import Dict, List, Optional, Set, Any

# Import Indaleko data models
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel

class SemanticAttributeRegistry:
    """Registry for semantic attributes used in data generation."""

    # Static registry of attributes by domain and name
    _attributes: Dict[str, Dict[str, str]] = {}

    # Registry of attribute UUIDs to human-readable names
    _uuid_to_name: Dict[str, str] = {}

    # Prefixes for attribute names
    _short_prefix = "DG_"  # Data Generator prefix
    _full_prefix = "DATA_GENERATOR"

    # Common domains for attributes
    DOMAIN_STORAGE = "storage"
    DOMAIN_ACTIVITY = "activity"
    DOMAIN_SEMANTIC = "semantic"
    DOMAIN_RELATIONSHIP = "relationship"
    DOMAIN_MACHINE = "machine"

    @classmethod
    def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
        """Register a semantic attribute and get its UUID.

        Args:
            domain: Domain for the attribute (storage, activity, etc.)
            name: Short name for the attribute
            attribute_id: Optional UUID to use (generates one if not provided)

        Returns:
            UUID string for the attribute
        """
        if domain not in cls._attributes:
            cls._attributes[domain] = {}

        full_name = f"{cls._full_prefix}_{domain.upper()}_{name.upper()}"

        # If already registered, return existing UUID
        if full_name in cls._attributes[domain]:
            return cls._attributes[domain][full_name]

        # Generate UUID if not provided
        if attribute_id is None:
            attribute_id = str(uuid.uuid4())

        # Register the attribute
        cls._attributes[domain][full_name] = attribute_id
        cls._uuid_to_name[attribute_id] = full_name

        return attribute_id

    @classmethod
    def get_attribute_id(cls, domain: str, name: str) -> str:
        """Get an attribute ID for a registered attribute.

        Args:
            domain: Domain for the attribute
            name: Short name for the attribute

        Returns:
            UUID string for the attribute
        """
        full_name = f"{cls._full_prefix}_{domain.upper()}_{name.upper()}"

        # Create if it doesn't exist
        if domain not in cls._attributes or full_name not in cls._attributes[domain]:
            return cls.register_attribute(domain, name)

        return cls._attributes[domain][full_name]

    @classmethod
    def get_attribute_name(cls, attribute_id: str) -> Optional[str]:
        """Get the human-readable name for an attribute ID.

        Args:
            attribute_id: UUID string for the attribute

        Returns:
            Human-readable name or None if not found
        """
        return cls._uuid_to_name.get(attribute_id)

    @classmethod
    def create_attribute(cls, domain: str, name: str, value: Any) -> IndalekoSemanticAttributeDataModel:
        """Create a semantic attribute model with proper ID.

        Args:
            domain: Domain for the attribute
            name: Short name for the attribute
            value: Value for the attribute

        Returns:
            IndalekoSemanticAttributeDataModel instance
        """
        attribute_id = cls.get_attribute_id(domain, name)

        return IndalekoSemanticAttributeDataModel(
            Identifier=attribute_id,
            Value=value
        )

    @classmethod
    def get_all_attributes(cls) -> Dict[str, Dict[str, str]]:
        """Get all registered attributes by domain.

        Returns:
            Dictionary of domains mapping to attribute names and UUIDs
        """
        return cls._attributes

    @classmethod
    def get_all_mappings(cls) -> Dict[str, str]:
        """Get mappings from UUID to human-readable names.

        Returns:
            Dictionary mapping UUIDs to human-readable names
        """
        return cls._uuid_to_name


# Register common attributes used in data generation
def register_common_attributes():
    """Register common semantic attributes used in data generation."""

    # Storage attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_NAME")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_PATH")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_SIZE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_EXTENSION")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_TYPE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "CREATION_TIME")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "MODIFICATION_TIME")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_STORAGE, "ACCESS_TIME")

    # Activity attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "ACTIVITY_TYPE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "USER_ID")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DEVICE_ID")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "APPLICATION")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "OPERATION")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "OBJECT_ID")

    # Activity data attributes with specific UUIDs
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PATH", "cf3c9dd4-64cc-471e-b15a-174387096c1a")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_NAME", "cc3544b9-08d9-4d07-bbff-f00e37c8d06d")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_USER", "83301374-047f-4991-967e-3bc0f9fb08db")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_APPLICATION", "663c5b11-38de-43b8-bf6d-ec769ce64467")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_DEVICE", "664587cd-443b-46ac-bd41-5f496470dd4f")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PLATFORM", "b1145632-d982-46ad-9d1e-b6cb97432334")

    # Storage activity attributes with specific UUIDs
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_CREATE", "11ab0a60-0dc2-460d-b4ee-ed03ff0a2242")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_MODIFY", "27a3cee5-e2dd-4e2a-9a3a-9d1ea76c2967")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_MODIFY_TYPE", "f5415f25-43ec-4549-9284-3779f32022fc")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_READ", "67e3697b-1ec2-470e-8fbb-c0b7d16bec13")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_DELETE", "5500f5d7-254e-48e8-8546-0feea6496374")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_VOLUME", "b30890ae-bb19-465a-982d-baa8d5ffd916")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_USN", "04965d6b-a4bd-46ca-9529-6774c1c0f50c")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_CLOUD_ID", "2c088475-6f60-4690-b000-3f445c412d67")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_SHARING", "aab21f35-68f2-435e-87e6-f8c496c143f5")

    # Collaboration activity attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_TYPE", "d213685a-9f27-44fd-b7be-db89589dcc5a")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_EMAIL_SUBJECT", "f54bb6a1-d894-4514-8ae2-0e117a25db9f")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_PARTICIPANTS", "a7247a59-8c35-4559-b89b-350581afd2b5")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_EVENT_TITLE", "0e145cbc-10f7-46f5-b1e2-8d58715f3beb")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_DURATION", "0826bc40-81e0-4a8b-9e7c-5bb0ef563628")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_CHANNEL", "e4837ec9-b621-47bb-83c1-45e3ac9f6ec7")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_MENTIONS", "c4f92e51-fbce-48f7-890e-6b32821655ea")

    # Location activity attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_TYPE", "18221360-a1af-4a9c-8fd0-c65fd8ce3e73")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_IP", "488a56b1-ca76-4923-912c-0157b64ea239")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_COUNTRY", "e6ecd0a3-6760-4cf9-bb7b-2fe6e9c36954")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_SSID", "3191481b-6124-46e9-a39e-2159f84593db")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_SIGNAL_STRENGTH", "7bc80841-2fc0-472e-b8f1-4ffc732486d1")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_LATITUDE", "f5aab374-67c3-4df1-963a-e8bcc29fa994")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_LONGITUDE", "70cb02f0-fd3d-42d2-81d1-b037a66316e5")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_ACCURACY", "c3c287b6-c871-444c-984c-d923df991727")

    # Ambient activity attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_TYPE", "77a5722b-c9da-4e46-81a2-1a2526a0c3fb")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_TEMPERATURE", "1855fcad-01b9-4562-9cd7-c93f9bcdf1fa")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_HUMIDITY", "64d9f921-a921-4523-ad1d-3e97f6ca1a3b")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_SONG", "bf875019-3b99-4c1f-ae9f-9a128f35285c")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_ARTIST", "a2a98047-ed2b-4d65-8527-c4c76fb21f58")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_VIDEO", "b1fe3bfb-f644-4ff4-8769-3864ab973ece")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "AMBIENT_DURATION", "5a654cd8-5f4c-4199-8465-fae41098a9a3")

    # Task activity attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "TASK_TYPE", "e16cbf13-67de-405e-9291-fa73d1e7b7b9")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "TASK_PID", "645027b6-730d-48ca-a864-5ddeee104f05")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "TASK_COMMAND", "31c909ab-a95d-4a99-b273-bb148c53c61d")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_ACTIVITY, "TASK_PARENT_PID", "69e8fbd2-c582-4662-8700-d98afbf8ea00")

    # Semantic attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_SEMANTIC, "MIME_TYPE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_SEMANTIC, "CONTENT_EXTRACT")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_SEMANTIC, "CHECKSUM")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_SEMANTIC, "LANGUAGE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_SEMANTIC, "AUTHOR")

    # Relationship attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_RELATIONSHIP, "RELATIONSHIP_TYPE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_RELATIONSHIP, "SOURCE_ROLE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_RELATIONSHIP, "TARGET_ROLE")

    # Machine attributes
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_MACHINE, "MACHINE_ID")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_MACHINE, "OS_TYPE")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_MACHINE, "OS_VERSION")
    SemanticAttributeRegistry.register_attribute(SemanticAttributeRegistry.DOMAIN_MACHINE, "HOSTNAME")


# Register common attributes when module is loaded
register_common_attributes()
