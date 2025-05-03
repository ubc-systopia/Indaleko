"""
Semantic metadata generator agent.

This module provides an agent for generating realistic semantic
metadata records for the Indaleko system, including MIME types,
checksums, and extracted content information.
"""

import json
import logging
import random
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from db.db_collections import IndalekoDBCollections
from semantic.data_models.base_data_model import BaseSemanticDataModel

from ..core.llm import LLMProvider
from ..core.tools import ToolRegistry
from .base import DomainAgent


class SemanticGeneratorAgent(DomainAgent):
    """Agent for generating semantic metadata."""

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the semantic generator agent.

        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = IndalekoDBCollections.Indaleko_SemanticData_Collection
        self.logger = logging.getLogger(self.__class__.__name__)

        # MIME type mapping by file extension
        self.mime_types = {
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".zip": "application/zip",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "text/javascript",
            ".json": "application/json",
            ".xml": "application/xml",
            ".md": "text/markdown",
            ".csv": "text/csv"
        }

        # Content type categories
        self.content_categories = {
            "text/plain": ["document", "note", "code", "log"],
            "application/pdf": ["document", "report", "manual", "presentation"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ["document", "report", "letter"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ["spreadsheet", "data", "financial"],
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ["presentation", "slides"],
            "image/jpeg": ["photo", "image", "scan"],
            "image/png": ["diagram", "screenshot", "image"],
            "image/gif": ["animation", "image"],
            "video/mp4": ["video", "recording", "movie"],
            "audio/mpeg": ["audio", "music", "podcast"],
            "audio/wav": ["audio", "recording", "sound"],
            "application/zip": ["archive", "backup", "compressed"],
            "text/html": ["webpage", "document"],
            "text/css": ["stylesheet", "code"],
            "text/javascript": ["code", "script"],
            "application/json": ["data", "configuration"],
            "application/xml": ["data", "configuration"],
            "text/markdown": ["document", "note"],
            "text/csv": ["data", "spreadsheet"]
        }

        # Common text content generators for various file types
        self.content_generators = {
            "text/plain": self._generate_text_content,
            "application/pdf": self._generate_document_content,
            "text/html": self._generate_html_content,
            "text/markdown": self._generate_markdown_content,
            "application/json": self._generate_json_content,
            "text/csv": self._generate_csv_content
        }

        # Checksum algorithms
        self.checksum_algorithms = ["MD5", "SHA1", "SHA256"]

    def generate(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate semantic metadata records.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Generating {count} semantic metadata records")

        # If criteria includes reference to storage objects, use those
        if criteria and "storage_objects" in criteria:
            storage_objects = criteria["storage_objects"]
            self.logger.info(f"Using {len(storage_objects)} existing storage objects")

            # Generate semantic records for each storage object
            return self._generate_from_storage_objects(storage_objects, criteria)

        # Otherwise, use the agent to generate semantic records
        instruction = f"Generate {count} realistic semantic metadata records"
        if criteria:
            instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria or {},
            "config": self.config,
            "collection_name": self.collection_name
        }

        # If we need to generate storage objects first, do that
        if not criteria or "generate_storage" in criteria:
            self.logger.info("Generating storage objects first")

            # Get the storage generator agent
            storage_agent = self._get_storage_agent()
            if storage_agent:
                # Generate storage objects
                storage_objects = storage_agent.generate(count, criteria.get("storage_criteria") if criteria else None)
                self.logger.info(f"Generated {len(storage_objects)} storage objects")

                # Add storage objects to input data
                input_data["storage_objects"] = storage_objects

                # Generate semantic records for each storage object
                return self._generate_from_storage_objects(storage_objects, criteria)

        # Use LLM-powered generation
        response = self.run(instruction, input_data)

        results = []

        # Extract the generated records
        if "actions" in response:
            for action in response["actions"]:
                if action["tool"] == "database_insert" or action["tool"] == "database_bulk_insert":
                    # If records were inserted directly, we need to query them
                    tool = self.tools.get_tool("database_query")
                    if tool:
                        query_result = tool.execute({
                            "query": f"FOR doc IN {self.collection_name} SORT doc.Timestamp DESC LIMIT {count} RETURN doc"
                        })
                        results.extend(query_result)

        return results

    def _get_storage_agent(self):
        """Get the storage generator agent if available."""
        from importlib import import_module
        try:
            storage_module = import_module("..storage", package=__name__)
            return storage_module.StorageGeneratorAgent(self.llm, self.tools, self.config)
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Error importing storage agent: {e}")
            return None

    def _generate_from_storage_objects(self, storage_objects: List[Dict[str, Any]], criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate semantic metadata records from storage objects.

        Args:
            storage_objects: List of storage objects
            criteria: Optional criteria for generation

        Returns:
            List of generated semantic records
        """
        self.logger.info(f"Generating semantic metadata for {len(storage_objects)} storage objects")

        # Try to use the model-based semantic generator tool
        tool = self.tools.get_tool("semantic_metadata_generator")
        if tool:
            self.logger.info("Using model-based semantic metadata generator tool")
            result = tool.execute({
                "storage_objects": storage_objects,
                "criteria": criteria or {}
            })
            
            semantic_records = result.get("records", [])
            
            # Transform the records into the format expected by the database
            transformed_records = [self._transform_to_db_format(record) for record in semantic_records]
            
            # Store the records if needed
            if self.config.get("store_directly", False):
                bulk_tool = self.tools.get_tool("database_bulk_insert")
                if bulk_tool:
                    bulk_tool.execute({
                        "collection": self.collection_name,
                        "documents": transformed_records
                    })
            
            return transformed_records
        
        # Fall back to legacy generation if tool is not available
        self.logger.warning("Semantic metadata generator tool not available, using legacy generation")
        
        semantic_records = []

        for storage_obj in storage_objects:
            # Extract file extension
            file_name = storage_obj.get("Label", "")
            extension = self._get_extension(file_name)
            if not extension:
                # Try to get extension from Record.Attributes
                if "Record" in storage_obj and "Attributes" in storage_obj["Record"]:
                    extension = storage_obj["Record"]["Attributes"].get("Extension", "")

            # Generate semantic record
            semantic_record = self._generate_semantic_record(storage_obj, extension, criteria)
            semantic_records.append(semantic_record)

        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": semantic_records
                })

        return semantic_records

    def _get_extension(self, file_name: str) -> str:
        """Extract file extension from file name.

        Args:
            file_name: File name

        Returns:
            File extension
        """
        if not file_name:
            return ""

        parts = file_name.split(".")
        if len(parts) > 1:
            return f".{parts[-1].lower()}"

        return ""

    def _generate_semantic_record(self, storage_obj: Dict[str, Any], extension: str, criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a semantic record for a storage object.

        Args:
            storage_obj: Storage object
            extension: File extension
            criteria: Optional criteria for generation

        Returns:
            Semantic record
        """
        # Get MIME type from extension
        mime_type = self.mime_types.get(extension, "application/octet-stream")

        # Generate checksum
        checksum = self._generate_checksum(storage_obj)

        # Generate content metadata based on MIME type
        content_metadata = self._generate_content_metadata(mime_type, storage_obj, criteria)

        # Get object identifier from storage object
        object_id = storage_obj.get("ObjectIdentifier", str(uuid.uuid4()))

        # Create semantic record
        semantic_record = {
            "ObjectIdentifier": object_id,
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "MIMEType": mime_type,
            "Checksum": checksum,
            "Content": content_metadata,
            "RecordType": "SemanticData",
            "Tags": self._generate_tags(mime_type, content_metadata)
        }

        # Apply any specific criteria
        if criteria:
            if "tags" in criteria:
                semantic_record["Tags"] = criteria["tags"]
            if "content_type" in criteria:
                semantic_record["Content"]["Type"] = criteria["content_type"]

        return semantic_record

    def _generate_checksum(self, storage_obj: Dict[str, Any]) -> Dict[str, str]:
        """Generate checksum data for a storage object.

        Args:
            storage_obj: Storage object

        Returns:
            Checksum data
        """
        checksums = {}

        # Use object ID as the basis for checksums
        data = storage_obj.get("ObjectIdentifier", str(uuid.uuid4())).encode()

        # Generate checksums using different algorithms
        for algorithm in self.checksum_algorithms:
            if algorithm == "MD5":
                checksums[algorithm] = hashlib.md5(data).hexdigest()
            elif algorithm == "SHA1":
                checksums[algorithm] = hashlib.sha1(data).hexdigest()
            elif algorithm == "SHA256":
                checksums[algorithm] = hashlib.sha256(data).hexdigest()

        return checksums

    def _generate_content_metadata(self, mime_type: str, storage_obj: Dict[str, Any], criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate content metadata based on MIME type.

        Args:
            mime_type: MIME type
            storage_obj: Storage object
            criteria: Optional criteria for generation

        Returns:
            Content metadata
        """
        # Get content category based on MIME type
        categories = self.content_categories.get(mime_type, ["unknown"])
        category = random.choice(categories)

        # Override category if specified in criteria
        if criteria and "content_category" in criteria:
            category = criteria["content_category"]

        # Base content metadata
        content_metadata = {
            "Type": category,
            "Language": "en",
            "Format": mime_type
        }

        # Generate content extract if applicable
        if mime_type in self.content_generators:
            content_extract = self.content_generators[mime_type](storage_obj)
            content_metadata["Extract"] = content_extract

        # Add specific metadata based on content type
        if "image" in category:
            content_metadata["Dimensions"] = self._generate_image_dimensions()
            content_metadata["ColorSpace"] = random.choice(["RGB", "sRGB", "CMYK", "Grayscale"])
        elif "video" in category:
            content_metadata["Duration"] = self._generate_video_duration()
            content_metadata["Resolution"] = self._generate_video_resolution()
        elif "audio" in category:
            content_metadata["Duration"] = self._generate_audio_duration()
            content_metadata["BitRate"] = random.randint(128, 320)
            content_metadata["SampleRate"] = random.choice([44100, 48000, 96000])

        return content_metadata

    def _generate_text_content(self, storage_obj: Dict[str, Any]) -> str:
        """Generate text content extract.

        Args:
            storage_obj: Storage object

        Returns:
            Text content extract
        """
        file_name = storage_obj.get("Label", "")

        # Generate lorem ipsum-like text
        sentences = [
            f"This is a text file named {file_name}.",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed ut perspiciatis unde omnis iste natus error sit voluptatem.",
            "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.",
            "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet.",
            "Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis.",
            "Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse."
        ]

        # Randomly select a subset of sentences
        num_sentences = random.randint(3, len(sentences))
        selected_sentences = random.sample(sentences, num_sentences)

        return " ".join(selected_sentences)

    def _generate_document_content(self, storage_obj: Dict[str, Any]) -> str:
        """Generate document content extract.

        Args:
            storage_obj: Storage object

        Returns:
            Document content extract
        """
        file_name = storage_obj.get("Label", "")

        # Generate document-like content with headings and paragraphs
        content = [
            f"Title: {file_name.split('.')[0]}",
            "Abstract:",
            "This document provides an overview of the topic and discusses key findings.",
            "Introduction:",
            "The purpose of this document is to outline the approach and methodology used in the study.",
            "Key Findings:",
            "1. Finding one related to the primary research question",
            "2. Secondary finding with supporting data",
            "3. Tertiary observation with implications for future work",
            "Conclusion:",
            "The results suggest that further investigation is warranted in this area."
        ]

        return "\n".join(content)

    def _generate_html_content(self, storage_obj: Dict[str, Any]) -> str:
        """Generate HTML content extract.

        Args:
            storage_obj: Storage object

        Returns:
            HTML content extract
        """
        file_name = storage_obj.get("Label", "")
        title = file_name.split('.')[0]

        # Generate HTML-like content
        content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>{title}</h1>
            <p>This is a sample HTML page with some content.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
        </body>
        </html>
        """

        return content

    def _generate_markdown_content(self, storage_obj: Dict[str, Any]) -> str:
        """Generate Markdown content extract.

        Args:
            storage_obj: Storage object

        Returns:
            Markdown content extract
        """
        file_name = storage_obj.get("Label", "")
        title = file_name.split('.')[0]

        # Generate Markdown-like content
        content = f"""
        # {title}

        ## Introduction

        This is a sample Markdown document with various elements.

        ## Features

        * Feature 1
        * Feature 2
        * Feature 3

        ## Code Example

        ```python
        def example():
            print("Hello, world!")
        ```

        ## Conclusion

        Thank you for reading this document.
        """

        return content

    def _generate_json_content(self, storage_obj: Dict[str, Any]) -> str:
        """Generate JSON content extract.

        Args:
            storage_obj: Storage object

        Returns:
            JSON content extract
        """
        # Generate JSON-like content
        data = {
            "id": str(uuid.uuid4()),
            "name": storage_obj.get("Label", "").split('.')[0],
            "attributes": {
                "created": datetime.now().isoformat(),
                "version": "1.0.0",
                "tags": ["sample", "json", "data"]
            },
            "metadata": {
                "description": "Sample JSON data",
                "owner": "user123",
                "permissions": ["read", "write"]
            }
        }

        return json.dumps(data, indent=2)

    def _generate_csv_content(self, storage_obj: Dict[str, Any]) -> str:
        """Generate CSV content extract.

        Args:
            storage_obj: Storage object

        Returns:
            CSV content extract
        """
        # Generate CSV-like content
        content = [
            "id,name,value,date",
            "1,Item 1,42.5,2023-01-15",
            "2,Item 2,37.2,2023-02-20",
            "3,Item 3,19.8,2023-03-10",
            "4,Item 4,55.3,2023-04-05",
            "5,Item 5,28.7,2023-05-22"
        ]

        return "\n".join(content)

    def _generate_image_dimensions(self) -> str:
        """Generate random image dimensions.

        Returns:
            Image dimensions as string (e.g., "1920x1080")
        """
        widths = [800, 1024, 1280, 1920, 2560, 3840]
        heights = [600, 768, 720, 1080, 1440, 2160]

        width = random.choice(widths)
        height = random.choice(heights)

        return f"{width}x{height}"

    def _generate_video_duration(self) -> str:
        """Generate random video duration.

        Returns:
            Video duration as string (e.g., "00:05:32")
        """
        hours = random.randint(0, 1)
        minutes = random.randint(0, 59)
        seconds = random.randint(0, 59)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _generate_video_resolution(self) -> str:
        """Generate random video resolution.

        Returns:
            Video resolution as string (e.g., "1920x1080")
        """
        resolutions = ["1280x720", "1920x1080", "2560x1440", "3840x2160"]
        return random.choice(resolutions)

    def _generate_audio_duration(self) -> str:
        """Generate random audio duration.

        Returns:
            Audio duration as string (e.g., "00:03:45")
        """
        minutes = random.randint(0, 10)
        seconds = random.randint(0, 59)

        return f"00:{minutes:02d}:{seconds:02d}"

    def _generate_tags(self, mime_type: str, content_metadata: Dict[str, Any]) -> List[str]:
        """Generate tags based on content metadata.

        Args:
            mime_type: MIME type
            content_metadata: Content metadata

        Returns:
            List of tags
        """
        tags = []

        # Add MIME type category
        mime_category = mime_type.split('/')[0]
        tags.append(mime_category)

        # Add content type
        content_type = content_metadata.get("Type", "")
        if content_type:
            tags.append(content_type)

        # Add language if available
        language = content_metadata.get("Language", "")
        if language:
            tags.append(f"lang:{language}")

        # Add additional tags based on content type
        if "image" in content_type:
            tags.extend(["visual", "image"])
            color_space = content_metadata.get("ColorSpace", "")
            if color_space:
                tags.append(color_space.lower())
        elif "video" in content_type:
            tags.extend(["media", "video"])
            resolution = content_metadata.get("Resolution", "")
            if "1080" in resolution:
                tags.append("HD")
            elif "2160" in resolution:
                tags.append("4K")
        elif "audio" in content_type:
            tags.extend(["media", "audio"])
            bit_rate = content_metadata.get("BitRate", 0)
            if bit_rate >= 256:
                tags.append("high-quality")
        elif "document" in content_type:
            tags.extend(["document", "text"])
        elif "spreadsheet" in content_type:
            tags.extend(["data", "spreadsheet"])

        return tags
        
    def _transform_to_db_format(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a generated record to the database format.

        Args:
            record: Generated record from semantic metadata generator tool

        Returns:
            Transformed record in database format
        """
        # Check if this is already in BaseSemanticDataModel format
        if (isinstance(record, dict) and "ObjectIdentifier" in record and "MIMEType" in record 
                and "Content" in record and "RecordType" in record and record.get("RecordType") == "SemanticData"):
            # Record is already in correct format, return as is
            self.logger.debug("Record is already in database format")
            return record
            
        # For other formats, convert to the expected database format
        # Get object identifier
        object_id = record.get("ObjectIdentifier", str(uuid.uuid4()))
        
        # Get timestamp, ensure ISO format with timezone
        timestamp = record.get("Timestamp", datetime.now(timezone.utc).isoformat())
        if isinstance(timestamp, str) and 'Z' not in timestamp and '+' not in timestamp:
            timestamp = f"{timestamp}Z"
            
        # Get MIME type or use default
        mime_type = record.get("MIMEType", "application/octet-stream")
        
        # Generate checksums if not provided
        checksums = record.get("Checksum", {})
        if not checksums:
            # Use object ID as the basis for checksums
            data = object_id.encode()
            checksums = {
                "MD5": hashlib.md5(data).hexdigest(),
                "SHA1": hashlib.sha1(data).hexdigest(),
                "SHA256": hashlib.sha256(data).hexdigest()
            }
            
        # Get or create content metadata
        content = record.get("Content", {})
        if not content:
            content = {
                "Type": "unknown",
                "Format": mime_type,
                "Language": "en"
            }
            
        # Get or generate tags
        tags = record.get("Tags", [])
        if not tags:
            tags = self._generate_tags(mime_type, content)
            
        # Create the record in the database format
        db_record = {
            "ObjectIdentifier": object_id,
            "Timestamp": timestamp,
            "MIMEType": mime_type,
            "Checksum": checksums,
            "Content": content,
            "RecordType": "SemanticData",
            "Tags": tags
        }
        
        return db_record

    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth semantic records with specific characteristics.

        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy

        Returns:
            List of generated truth records
        """
        self.logger.info(f"Generating {count} truth semantic records with criteria: {criteria}")

        # If storage objects are provided, use them
        if "storage_objects" in criteria:
            storage_objects = criteria["storage_objects"]
            self.logger.info(f"Using {len(storage_objects)} provided storage objects for truth records")

            # Generate semantic records for provided storage objects
            semantic_records = self._generate_from_storage_objects(storage_objects, criteria)

            # Track the truth records
            for record in semantic_records:
                self.truth_list.append(record.get("ObjectIdentifier"))

            # Store truth characteristics for later verification
            self.state["truth_criteria"] = criteria
            self.state["truth_count"] = len(semantic_records)
            self.state["truth_ids"] = self.truth_list

            return semantic_records

        # If we need to generate storage objects first
        if "generate_storage" in criteria:
            self.logger.info("Generating storage objects for truth records")

            # Get the storage generator agent
            storage_agent = self._get_storage_agent()
            if storage_agent:
                # Generate truth storage objects
                storage_truth = storage_agent.generate_truth(count, criteria.get("storage_criteria", {}))
                self.logger.info(f"Generated {len(storage_truth)} truth storage objects")

                # Generate semantic records for these storage objects
                criteria["storage_objects"] = storage_truth
                return self.generate_truth(count, criteria)

        # Otherwise, generate directly
        instruction = f"Generate {count} truth semantic metadata records"
        instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria,
            "config": self.config,
            "collection_name": self.collection_name,
            "truth": True
        }

        response = self.run(instruction, input_data)

        semantic_records = []

        # Extract the generated records
        if "actions" in response:
            for action in response["actions"]:
                if action["tool"] == "database_insert" or action["tool"] == "database_bulk_insert":
                    # If records were inserted directly, we need to query them
                    tool = self.tools.get_tool("database_query")
                    if tool:
                        query_result = tool.execute({
                            "query": f"FOR doc IN {self.collection_name} SORT doc.Timestamp DESC LIMIT {count} RETURN doc"
                        })
                        semantic_records.extend(query_result)

        # Track the truth records
        for record in semantic_records:
            self.truth_list.append(record.get("ObjectIdentifier"))

        # Store truth characteristics for later verification
        self.state["truth_criteria"] = criteria
        self.state["truth_count"] = len(semantic_records)
        self.state["truth_ids"] = self.truth_list

        return semantic_records

    def _build_context(self, instruction: str, input_data: Optional[Dict[str, Any]] = None) -> str:
        """Build the context for the LLM.

        Args:
            instruction: The instruction for the agent
            input_data: Optional input data

        Returns:
            Context string for the LLM
        """
        context = f"""
        You are a specialized agent for generating realistic semantic metadata for files and documents.

        Your task: {instruction}

        Generate semantic metadata that follows these guidelines:
        1. Create realistic MIME types for different file extensions
        2. Include appropriate checksums (MD5, SHA1, SHA256)
        3. Generate content extracts that match the file type
        4. Include appropriate tags and classifications
        5. Ensure all records have required fields for database insertion

        Semantic metadata should include the following fields:
        - ObjectIdentifier: ID matching the source storage object
        - Timestamp: Current timestamp in ISO format with timezone
        - MIMEType: MIME type of the content (e.g., "application/pdf")
        - Checksum: Dictionary of checksum values by algorithm
        - Content: Metadata about the content, including extracts if applicable
        - RecordType: Always "SemanticData"
        - Tags: List of relevant tags for the content

        """

        if input_data:
            # Don't include the full storage objects in the context to avoid token limits
            input_data_copy = input_data.copy()
            if "storage_objects" in input_data_copy:
                storage_count = len(input_data_copy["storage_objects"])
                input_data_copy["storage_objects"] = f"[{storage_count} storage objects available]"

            context += f"Input data: {json.dumps(input_data_copy, indent=2)}\n\n"

        # Add tips for specific criteria if provided
        if input_data and "criteria" in input_data and input_data["criteria"]:
            context += "Special instructions for the criteria:\n"

            for key, value in input_data["criteria"].items():
                if key == "mime_type":
                    context += f"- All records must have MIME type '{value}'\n"
                elif key == "content_category":
                    context += f"- All content should be categorized as '{value}'\n"
                elif key == "tags":
                    context += f"- Include these specific tags: {value}\n"
                elif key == "storage_criteria":
                    context += f"- Storage objects have these criteria: {value}\n"
                elif key != "storage_objects" and key != "generate_storage":
                    context += f"- Apply the criterion '{key}': '{value}'\n"

        # If we have storage objects, provide instructions for using them
        if input_data and "storage_objects" in input_data:
            context += "\nYou have storage objects available. For each storage object, you should:\n"
            context += "1. Extract the file extension from the Label or Record.Attributes.Extension\n"
            context += "2. Determine the appropriate MIME type for the extension\n"
            context += "3. Generate checksums based on the ObjectIdentifier\n"
            context += "4. Create appropriate content metadata based on the file type\n"
            context += "5. Make sure the ObjectIdentifier in the semantic record matches the storage object\n"

            # Provide a sample of one storage object if available
            if isinstance(input_data["storage_objects"], list) and len(input_data["storage_objects"]) > 0:
                sample_obj = input_data["storage_objects"][0]
                context += f"\nHere's a sample storage object:\n{json.dumps(sample_obj, indent=2)}\n"

        # If generating truth records, add special instructions
        if input_data and input_data.get("truth", False):
            context += "\nIMPORTANT: You are generating TRUTH records. These records must EXACTLY match the criteria provided. These records will be used for testing and validation, so their properties must match the criteria precisely.\n"

        return context
