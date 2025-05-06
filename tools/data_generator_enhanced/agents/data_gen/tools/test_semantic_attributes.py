"""
Test semantic attribute generation to verify correct field names and UUID usage.

This script verifies that semantic attributes are created with the correct:
1. Field names (Identifier/Value instead of AttributeIdentifier/AttributeName/AttributeValue)
2. Static UUIDs that match the registry
"""

import json
import sys
import os
import logging

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko data models
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel

# Import local modules
from ..core.semantic_attributes import SemanticAttributeRegistry
from tools.data_generator_enhanced.agents.data_gen.tools.stats import ActivityGeneratorTool


def setup_logging():
    """Setup basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


def test_registry_attributes():
    """Test attributes created by SemanticAttributeRegistry."""
    logging.info("Testing SemanticAttributeRegistry attribute creation...")

    # Test creating an attribute
    attr = SemanticAttributeRegistry.create_attribute(
        SemanticAttributeRegistry.DOMAIN_ACTIVITY,
        "DATA_PATH",
        "/test/path"
    )

    # Verify it's the correct type
    assert isinstance(attr, IndalekoSemanticAttributeDataModel)

    # Verify it has the correct fields
    attr_dict = attr.dict()
    logging.info(f"Created attribute: {json.dumps(attr_dict, indent=2)}")

    # Check fields
    assert "Identifier" in attr_dict
    assert "Value" in attr_dict
    assert "AttributeIdentifier" not in attr_dict
    assert "AttributeName" not in attr_dict
    assert "AttributeValue" not in attr_dict

    # Verify static UUID for DATA_PATH
    expected_uuid = "cf3c9dd4-64cc-471e-b15a-174387096c1a"
    assert attr_dict["Identifier"] == expected_uuid

    # Verify value
    assert attr_dict["Value"] == "/test/path"

    logging.info("SemanticAttributeRegistry attribute creation test passed!")
    return True


def test_activity_generator():
    """Test attribute creation in ActivityGeneratorTool."""
    logging.info("Testing ActivityGeneratorTool semantic attribute creation...")

    # Create the tool
    activity_gen = ActivityGeneratorTool()

    # Generate some attributes
    obj_id = "test-object-id"
    path = "/test/path"
    name = "test-file.txt"
    user = "test-user"
    app = "test-app"
    device = "test-device"
    platform = "windows"

    # Create attributes for storage domain
    attributes = activity_gen._generate_semantic_attributes(
        activity_type="create",
        domain="storage",
        provider_type="ntfs",
        obj_id=obj_id,
        path=path,
        name=name,
        user=user,
        app=app,
        device=device,
        platform=platform
    )

    # Verify we got attributes
    assert len(attributes) > 0

    # Check the first few attributes
    for i, attr in enumerate(attributes[:5]):
        attr_dict = attr.dict()
        logging.info(f"Attribute {i}: {json.dumps(attr_dict, indent=2)}")

        # Check fields
        assert "Identifier" in attr_dict
        assert "Value" in attr_dict
        assert isinstance(attr_dict["Identifier"], str)
        assert "AttributeIdentifier" not in attr_dict
        assert "AttributeName" not in attr_dict
        assert "AttributeValue" not in attr_dict

    # Test a few specific attributes to verify correct UUIDs
    data_path_attr = next((a for a in attributes if a.dict()["Value"] == path), None)
    assert data_path_attr is not None
    assert data_path_attr.dict()["Identifier"] == "cf3c9dd4-64cc-471e-b15a-174387096c1a"

    data_name_attr = next((a for a in attributes if a.dict()["Value"] == name), None)
    assert data_name_attr is not None
    assert data_name_attr.dict()["Identifier"] == "cc3544b9-08d9-4d07-bbff-f00e37c8d06d"

    logging.info("ActivityGeneratorTool attribute creation test passed!")
    return True


def main():
    """Run tests for semantic attribute generation."""
    setup_logging()
    logging.info("Starting semantic attribute tests...")

    test_registry_attributes()
    test_activity_generator()

    logging.info("All semantic attribute tests passed successfully!")


if __name__ == "__main__":
    main()
