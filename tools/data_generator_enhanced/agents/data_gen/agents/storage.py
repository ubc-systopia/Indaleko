"""
Storage metadata generator agent.

This module provides an agent for generating realistic storage
metadata records for the Indaleko system.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.db_collections import IndalekoDBCollections
from data_models.base import IndalekoBaseModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel

from ..core.llm import LLMProvider
from ..core.tools import ToolRegistry
from .base import DomainAgent


class StorageGeneratorAgent(DomainAgent):
    """Agent for generating storage metadata."""

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the storage generator agent.

        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = IndalekoDBCollections.Indaleko_Object_Collection
        self.logger = logging.getLogger(self.__class__.__name__)

        # Common file extensions and their probabilities
        self.file_extensions = {
            ".txt": 0.15,
            ".pdf": 0.15,
            ".docx": 0.10,
            ".xlsx": 0.10,
            ".pptx": 0.05,
            ".jpg": 0.15,
            ".png": 0.10,
            ".mp4": 0.05,
            ".mp3": 0.05,
            ".zip": 0.02,
            ".html": 0.03,
            ".css": 0.01,
            ".js": 0.01,
            ".json": 0.01,
            ".xml": 0.01,
            ".md": 0.01,
            ".csv": 0.01
        }

        # Initialize path generators based on operating systems
        self.os_paths = {
            "windows": ["C:\\Users\\{user}\\", "D:\\Projects\\", "C:\\Data\\"],
            "macos": ["/Users/{user}/", "/Applications/", "/Library/"],
            "linux": ["/home/{user}/", "/opt/", "/var/", "/tmp/"],
        }

        # Sample usernames for path generation
        self.usernames = ["alice", "bob", "charlie", "david", "emma", "frank", "grace", "henry"]

    def generate(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate storage metadata records.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Generating {count} storage metadata records")

        # Use direct generation for small counts or when specified in config
        if count <= 100 or self.config.get("direct_generation", False):
            return self._direct_generation(count, criteria)

        # Use LLM-powered generation for larger counts or complex criteria
        instruction = f"Generate {count} realistic storage metadata records"
        if criteria:
            instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria or {},
            "config": self.config,
            "collection_name": self.collection_name
        }

        results = []
        batch_size = min(count, 1000)
        remaining = count

        # Generate in batches to avoid overwhelming the LLM
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            self.logger.info(f"Generating batch of {current_batch} storage records")

            # Update input data for this batch
            batch_input = input_data.copy()
            batch_input["count"] = current_batch

            # Run the agent
            response = self.run(instruction, batch_input)

            # Extract the generated records
            if "actions" in response:
                for action in response["actions"]:
                    if action["tool"] == "file_metadata_generator":
                        results.extend(action.get("result", {}).get("records", []))
                    elif action["tool"] == "database_bulk_insert":
                        # If records were inserted directly, we need to query them
                        # This could be optimized by returning the records from database_bulk_insert
                        tool = self.tools.get_tool("database_query")
                        if tool:
                            query_result = tool.execute({
                                "query": f"FOR doc IN {self.collection_name} SORT doc.Created DESC LIMIT {current_batch} RETURN doc"
                            })
                            results.extend(query_result)

            remaining -= current_batch

        return results

    def _direct_generation(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate storage metadata records directly without LLM.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Direct generation of {count} storage records")

        tool = self.tools.get_tool("file_metadata_generator")
        if not tool:
            self.logger.warning("File metadata generator tool not available")
            return []

        result = tool.execute({
            "count": count,
            "criteria": criteria or {}
        })

        records = result.get("records", [])

        # Transform the records into the format expected by the database
        transformed_records = [self._transform_to_db_format(record) for record in records]

        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": transformed_records
                })

        return transformed_records

    def _transform_to_db_format(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a generated record to the database format.

        Args:
            record: Generated record

        Returns:
            Transformed record in database format
        """
        # Check if this is already an IndalekoObjectDataModel record format
        if "Record" in record and "Timestamps" in record and "URI" in record:
            # Record is already in IndalekoObjectDataModel format, return as is
            self.logger.debug("Record is already in database format")
            return record

        # Otherwise, generate a unique ID if not provided
        object_id = record.get("ObjectIdentifier", str(uuid.uuid4()))

        # Create timestamps
        timestamps = []
        for label, value in [
            ("Created", record.get("Created")),
            ("Modified", record.get("Modified")),
            ("Accessed", record.get("Accessed"))
        ]:
            if value:
                # Ensure ISO format with timezone
                if isinstance(value, str) and 'Z' not in value and '+' not in value:
                    value = f"{value}Z"
                timestamps.append({
                    "Label": label,
                    "Value": value
                })

        # Create the record in the database format
        db_record = {
            "ObjectIdentifier": object_id,
            "URI": f"file://{record.get('Path')}/{record.get('Name')}",
            "Label": record.get("Name", ""),
            "Timestamps": timestamps,
            "Record": {
                "Type": "StorageObject",
                "Format": "File",
                "Attributes": {
                    "Extension": record.get("Extension", ""),
                    "Size": record.get("Size", 0),
                    "Path": record.get("Path", ""),
                    "Metadata": {}
                }
            }
        }

        # Add any additional attributes
        for key, value in record.items():
            if key not in ["Name", "Path", "Size", "Created", "Modified", "Accessed", "Extension", "ObjectIdentifier"]:
                db_record["Record"]["Attributes"]["Metadata"][key] = value

        return db_record

    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth storage records with specific characteristics.

        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy

        Returns:
            List of generated truth records
        """
        self.logger.info(f"Generating {count} truth storage records with criteria: {criteria}")

        # Always use direct generation for truth records to ensure they match criteria exactly
        records = self._direct_generation(count, criteria)

        # Track the truth records
        for record in records:
            self.truth_list.append(record.get("ObjectIdentifier"))

        # Store truth characteristics for later verification
        self.state["truth_criteria"] = criteria
        self.state["truth_count"] = count
        self.state["truth_ids"] = self.truth_list

        return records

    def _build_context(self, instruction: str, input_data: Optional[Dict[str, Any]] = None) -> str:
        """Build the context for the LLM.

        Args:
            instruction: The instruction for the agent
            input_data: Optional input data

        Returns:
            Context string for the LLM
        """
        context = f"""
        You are a specialized agent for generating realistic file and directory metadata.

        Your task: {instruction}

        Generate metadata that follows these guidelines:
        1. Create realistic file paths, names, and extensions
        2. Assign appropriate timestamps for creation, modification, and access
        3. Include file sizes that follow typical statistical distributions
        4. Ensure all records have required fields for database insertion
        5. Generated data should be diverse and representative of real file systems

        Metadata should include the following fields:
        - Name: The file or directory name
        - Path: The path to the file or directory
        - Size: The size of the file in bytes
        - Created: Creation timestamp in ISO format with timezone
        - Modified: Modification timestamp in ISO format with timezone
        - Accessed: Access timestamp in ISO format with timezone
        - Extension: File extension (for files)
        - ObjectIdentifier: Unique identifier for the object

        """

        if input_data:
            context += f"Input data: {json.dumps(input_data, indent=2)}\n\n"

        # Add tips for specific criteria if provided
        if input_data and "criteria" in input_data and input_data["criteria"]:
            context += "Special instructions for the criteria:\n"

            for key, value in input_data["criteria"].items():
                if key == "extension":
                    context += f"- All files must have the extension '{value}'\n"
                elif key == "name_pattern":
                    context += f"- File names should follow the pattern '{value}'\n"
                elif key == "size_range":
                    min_size, max_size = value
                    context += f"- File sizes should be between {min_size} and {max_size} bytes\n"
                elif key == "path_prefix":
                    context += f"- All paths should start with '{value}'\n"
                elif key == "days_ago":
                    context += f"- Files should have been created approximately {value} days ago\n"
                else:
                    context += f"- Apply the criterion '{key}': '{value}'\n"

        # If generating truth records, add special instructions
        if input_data and input_data.get("truth", False):
            context += "\nIMPORTANT: You are generating TRUTH records. These records must EXACTLY match the criteria provided. These records will be used for testing and validation, so their properties must match the criteria precisely.\n"

        return context
