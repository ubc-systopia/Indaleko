"""
Patch for adding semantic attributes to FileMetadataGeneratorTool.

This patch adds proper semantic attribute generation to the FileMetadataGeneratorTool class.
The current implementation initializes semantic_attributes but doesn't populate it,
which leads to objects without semantic attributes in the database.

To apply this patch:
1. Add import for SemanticAttributeRegistry
2. Add _generate_semantic_attributes method to FileMetadataGeneratorTool
3. Call _generate_semantic_attributes in file model generation
"""

import sys
import os

# Setup path for imports
current_path = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
    current_path = os.path.dirname(current_path)
sys.path.append(current_path)

from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry

def generate_semantic_attributes_for_file(file_model):
    """Generate semantic attributes for a file model.

    Args:
        file_model: File model dictionary

    Returns:
        List of semantic attributes
    """
    semantic_attributes = []

    # Add file name attribute
    if "Label" in file_model:
        file_name_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_NAME"),
            "Value": file_model["Label"]
        }
        semantic_attributes.append(file_name_attr)

    # Add file path attribute
    if "LocalPath" in file_model:
        file_path_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_PATH"),
            "Value": file_model["LocalPath"]
        }
        semantic_attributes.append(file_path_attr)

    # Add file size attribute
    if "Size" in file_model:
        file_size_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_SIZE"),
            "Value": file_model["Size"]
        }
        semantic_attributes.append(file_size_attr)

    # Add file extension attribute if available
    if "Label" in file_model and "." in file_model["Label"]:
        extension = file_model["Label"].split(".")[-1]
        file_ext_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_EXTENSION"),
            "Value": extension
        }
        semantic_attributes.append(file_ext_attr)

    # Add MIME type as a semantic attribute
    mime_types = {
        "txt": "text/plain",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "jpg": "image/jpeg",
        "png": "image/png",
        "mp4": "video/mp4",
        "mp3": "audio/mpeg",
        "zip": "application/zip",
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript",
        "json": "application/json",
        "xml": "application/xml",
        "md": "text/markdown",
        "csv": "text/csv"
    }

    if "Label" in file_model and "." in file_model["Label"]:
        extension = file_model["Label"].split(".")[-1].lower()
        if extension in mime_types:
            mime_attr = {
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SEMANTIC, "MIME_TYPE"),
                "Value": mime_types[extension]
            }
            semantic_attributes.append(mime_attr)

    return semantic_attributes

# Example patch method for FileMetadataGeneratorTool class
def _generate_semantic_attributes(self, file_path, file_name, file_size):
    """Generate semantic attributes for a file.

    Args:
        file_path: File path
        file_name: File name
        file_size: File size

    Returns:
        List of semantic attributes
    """
    semantic_attributes = []

    # Add file name attribute
    file_name_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_NAME"),
        Value=file_name
    )
    semantic_attributes.append(file_name_attr)

    # Add file path attribute
    file_path_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_PATH"),
        Value=file_path
    )
    semantic_attributes.append(file_path_attr)

    # Add file size attribute
    file_size_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_SIZE"),
        Value=file_size
    )
    semantic_attributes.append(file_size_attr)

    # Add file extension attribute if available
    if "." in file_name:
        extension = file_name.split(".")[-1]
        file_ext_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_EXTENSION"),
            Value=extension
        )
        semantic_attributes.append(file_ext_attr)

        # Add MIME type as a semantic attribute
        mime_types = {
            "txt": "text/plain",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "jpg": "image/jpeg",
            "png": "image/png",
            "mp4": "video/mp4",
            "mp3": "audio/mpeg",
            "zip": "application/zip",
            "html": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "json": "application/json",
            "xml": "application/xml",
            "md": "text/markdown",
            "csv": "text/csv"
        }

        extension_lower = extension.lower()
        if extension_lower in mime_types:
            mime_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SEMANTIC, "MIME_TYPE"),
                Value=mime_types[extension_lower]
            )
            semantic_attributes.append(mime_attr)

    return semantic_attributes"""
Patch for adding semantic attributes to FileMetadataGeneratorTool.

This patch adds proper semantic attribute generation to the FileMetadataGeneratorTool class.
The current implementation initializes semantic_attributes but doesn't populate it,
which leads to objects without semantic attributes in the database.

To apply this patch:
1. Add import for SemanticAttributeRegistry
2. Add _generate_semantic_attributes method to FileMetadataGeneratorTool
3. Call _generate_semantic_attributes in file model generation
"""

import sys
import os

# Setup path for imports
current_path = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
    current_path = os.path.dirname(current_path)
sys.path.append(current_path)

from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry

def generate_semantic_attributes_for_file(file_model):
    """Generate semantic attributes for a file model.

    Args:
        file_model: File model dictionary

    Returns:
        List of semantic attributes
    """
    semantic_attributes = []

    # Add file name attribute
    if "Label" in file_model:
        file_name_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_NAME"),
            "Value": file_model["Label"]
        }
        semantic_attributes.append(file_name_attr)

    # Add file path attribute
    if "LocalPath" in file_model:
        file_path_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_PATH"),
            "Value": file_model["LocalPath"]
        }
        semantic_attributes.append(file_path_attr)

    # Add file size attribute
    if "Size" in file_model:
        file_size_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_SIZE"),
            "Value": file_model["Size"]
        }
        semantic_attributes.append(file_size_attr)

    # Add file extension attribute if available
    if "Label" in file_model and "." in file_model["Label"]:
        extension = file_model["Label"].split(".")[-1]
        file_ext_attr = {
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_EXTENSION"),
            "Value": extension
        }
        semantic_attributes.append(file_ext_attr)

    # Add MIME type as a semantic attribute
    mime_types = {
        "txt": "text/plain",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "jpg": "image/jpeg",
        "png": "image/png",
        "mp4": "video/mp4",
        "mp3": "audio/mpeg",
        "zip": "application/zip",
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript",
        "json": "application/json",
        "xml": "application/xml",
        "md": "text/markdown",
        "csv": "text/csv"
    }

    if "Label" in file_model and "." in file_model["Label"]:
        extension = file_model["Label"].split(".")[-1].lower()
        if extension in mime_types:
            mime_attr = {
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SEMANTIC, "MIME_TYPE"),
                "Value": mime_types[extension]
            }
            semantic_attributes.append(mime_attr)

    return semantic_attributes

# Example patch method for FileMetadataGeneratorTool class
def _generate_semantic_attributes(self, file_path, file_name, file_size):
    """Generate semantic attributes for a file.

    Args:
        file_path: File path
        file_name: File name
        file_size: File size

    Returns:
        List of semantic attributes
    """
    semantic_attributes = []

    # Add file name attribute
    file_name_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_NAME"),
        Value=file_name
    )
    semantic_attributes.append(file_name_attr)

    # Add file path attribute
    file_path_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_PATH"),
        Value=file_path
    )
    semantic_attributes.append(file_path_attr)

    # Add file size attribute
    file_size_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_SIZE"),
        Value=file_size
    )
    semantic_attributes.append(file_size_attr)

    # Add file extension attribute if available
    if "." in file_name:
        extension = file_name.split(".")[-1]
        file_ext_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_EXTENSION"),
            Value=extension
        )
        semantic_attributes.append(file_ext_attr)

        # Add MIME type as a semantic attribute
        mime_types = {
            "txt": "text/plain",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "jpg": "image/jpeg",
            "png": "image/png",
            "mp4": "video/mp4",
            "mp3": "audio/mpeg",
            "zip": "application/zip",
            "html": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "json": "application/json",
            "xml": "application/xml",
            "md": "text/markdown",
            "csv": "text/csv"
        }

        extension_lower = extension.lower()
        if extension_lower in mime_types:
            mime_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SEMANTIC, "MIME_TYPE"),
                Value=mime_types[extension_lower]
            )
            semantic_attributes.append(mime_attr)

    return semantic_attributes
