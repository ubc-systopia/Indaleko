"""
Statistical tools for data generation agents.

This module provides tools for generating data following
statistical distributions and patterns.
"""

import datetime
import json
import logging
import math
import random
import uuid
from typing import Any, Dict, List, Optional, Union

import numpy as np

from ..core.tools import Tool
from ..core.semantic_attributes import SemanticAttributeRegistry

# Import Indaleko data models
from data_models.source_identifier import IndalekoSourceIdentifierDataModel


class StatisticalDistributionTool(Tool):
    """Tool for generating values following statistical distributions."""

    def __init__(self):
        """Initialize the statistical distribution tool."""
        super().__init__(
            name="statistical_distribution",
            description="Generate values following statistical distributions"
        )

    def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - distribution: Distribution type
                - count: Number of values to generate
                - parameters: Distribution parameters

        Returns:
            Generated values
        """
        distribution = parameters.get("distribution")
        if not distribution:
            raise ValueError("Distribution parameter is required")

        count = parameters.get("count", 1)
        dist_params = parameters.get("parameters", {})

        self.logger.debug(f"Generating {count} values from {distribution} distribution")

        if distribution == "normal":
            return self._generate_normal(count, dist_params)
        elif distribution == "uniform":
            return self._generate_uniform(count, dist_params)
        elif distribution == "lognormal":
            return self._generate_lognormal(count, dist_params)
        elif distribution == "exponential":
            return self._generate_exponential(count, dist_params)
        elif distribution == "pareto":
            return self._generate_pareto(count, dist_params)
        elif distribution == "poisson":
            return self._generate_poisson(count, dist_params)
        elif distribution == "weighted":
            return self._generate_weighted_choice(count, dist_params)
        elif distribution == "datetime":
            return self._generate_datetime(count, dist_params)
        elif distribution == "uuid":
            return self._generate_uuid(count)
        else:
            raise ValueError(f"Unknown distribution: {distribution}")

    def _generate_normal(self, count: int, params: Dict[str, Any]) -> List[float]:
        """Generate values from a normal distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (mean, std)

        Returns:
            Generated values
        """
        mean = params.get("mean", 0)
        std = params.get("std", 1)

        return list(np.random.normal(mean, std, count))

    def _generate_uniform(self, count: int, params: Dict[str, Any]) -> List[float]:
        """Generate values from a uniform distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (min, max)

        Returns:
            Generated values
        """
        min_val = params.get("min", 0)
        max_val = params.get("max", 1)

        return list(np.random.uniform(min_val, max_val, count))

    def _generate_lognormal(self, count: int, params: Dict[str, Any]) -> List[float]:
        """Generate values from a lognormal distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (mu, sigma)

        Returns:
            Generated values
        """
        mu = params.get("mu", 0)
        sigma = params.get("sigma", 1)

        return list(np.random.lognormal(mu, sigma, count))

    def _generate_exponential(self, count: int, params: Dict[str, Any]) -> List[float]:
        """Generate values from an exponential distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (scale)

        Returns:
            Generated values
        """
        scale = params.get("scale", 1)

        return list(np.random.exponential(scale, count))

    def _generate_pareto(self, count: int, params: Dict[str, Any]) -> List[float]:
        """Generate values from a Pareto distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (alpha)

        Returns:
            Generated values
        """
        alpha = params.get("alpha", 1)

        return list(np.random.pareto(alpha, count) + 1)  # Adding 1 to shift the distribution

    def _generate_poisson(self, count: int, params: Dict[str, Any]) -> List[int]:
        """Generate values from a Poisson distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (lam)

        Returns:
            Generated values
        """
        lam = params.get("lam", 1)

        return list(np.random.poisson(lam, count))

    def _generate_weighted_choice(self, count: int, params: Dict[str, Any]) -> List[Any]:
        """Generate values from a weighted choice distribution.

        Args:
            count: Number of values to generate
            params: Distribution parameters (values, weights)

        Returns:
            Generated values
        """
        values = params.get("values", [])
        weights = params.get("weights", None)

        if not values:
            raise ValueError("Values parameter is required for weighted choice")

        # If values is a dictionary of value -> weight
        if isinstance(values, dict):
            items = list(values.keys())
            weights = [values[item] for item in items]
            return random.choices(items, weights=weights, k=count)

        # If values is a list and weights is a list
        if weights and len(weights) != len(values):
            raise ValueError("Weights must have the same length as values")

        return random.choices(values, weights=weights, k=count)

    def _generate_datetime(self, count: int, params: Dict[str, Any]) -> List[str]:
        """Generate datetime values.

        Args:
            count: Number of values to generate
            params: Distribution parameters (start, end, format)

        Returns:
            Generated datetime strings
        """
        start_str = params.get("start")
        end_str = params.get("end")
        format_str = params.get("format", "%Y-%m-%dT%H:%M:%S.%fZ")

        now = datetime.datetime.now()

        # Parse start date
        if start_str:
            if start_str.startswith("now-"):
                days = int(start_str[4:-1])
                start = now - datetime.timedelta(days=days)
            else:
                try:
                    start = datetime.datetime.strptime(start_str, format_str)
                except ValueError:
                    start = now - datetime.timedelta(days=30)
        else:
            start = now - datetime.timedelta(days=30)

        # Parse end date
        if end_str:
            if end_str.startswith("now-"):
                days = int(end_str[4:-1])
                end = now - datetime.timedelta(days=days)
            else:
                try:
                    end = datetime.datetime.strptime(end_str, format_str)
                except ValueError:
                    end = now
        else:
            end = now

        # Generate random datetimes
        timestamps = []
        for _ in range(count):
            timestamp = start + (end - start) * random.random()
            timestamps.append(timestamp.strftime(format_str))

        return timestamps

    def _generate_uuid(self, count: int) -> List[str]:
        """Generate UUID values.

        Args:
            count: Number of values to generate

        Returns:
            Generated UUID strings
        """
        return [str(uuid.uuid4()) for _ in range(count)]

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "distribution": {
                            "type": "string",
                            "description": "Distribution type (normal, uniform, lognormal, exponential, pareto, poisson, weighted, datetime, uuid)",
                            "enum": ["normal", "uniform", "lognormal", "exponential", "pareto", "poisson", "weighted", "datetime", "uuid"]
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of values to generate",
                            "default": 1
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Distribution parameters"
                        }
                    },
                    "required": ["distribution"]
                }
            }
        }


class FileMetadataGeneratorTool(Tool):
    """Tool for generating realistic file metadata."""

    def __init__(self):
        """Initialize the file metadata generator tool."""
        super().__init__(
            name="file_metadata_generator",
            description="Generate realistic file metadata"
        )

        # Import models
        import sys
        import os

        # Setup path for imports
        if os.environ.get("INDALEKO_ROOT") is None:
            current_path = os.path.dirname(os.path.abspath(__file__))
            while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
                current_path = os.path.dirname(current_path)
            os.environ["INDALEKO_ROOT"] = current_path
            sys.path.append(current_path)

        # Import Indaleko data models
        from data_models.record import IndalekoRecordDataModel
        from data_models.timestamp import IndalekoTimestampDataModel
        from data_models.i_object import IndalekoObjectDataModel
        from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel

        # Store model classes
        self.RecordDataModel = IndalekoRecordDataModel
        self.TimestampDataModel = IndalekoTimestampDataModel
        self.ObjectDataModel = IndalekoObjectDataModel
        self.SemanticAttributeDataModel = IndalekoSemanticAttributeDataModel

        # Constants for timestamp labels (from IndalekoObject)
        self.CREATION_TIMESTAMP = "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6"
        self.MODIFICATION_TIMESTAMP = "434f7ac1-f71a-4cea-a830-e2ea9a47db5a"
        self.ACCESS_TIMESTAMP = "581b5332-4d37-49c7-892a-854824f5d66f"
        self.CHANGE_TIMESTAMP = "3bdc4130-774f-4e99-914e-0bec9ee47aab"

        # Common file extensions and their frequencies
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

        # Common file size ranges by extension (in bytes)
        self.file_size_ranges = {
            ".txt": (1_000, 100_000),
            ".pdf": (100_000, 10_000_000),
            ".docx": (50_000, 5_000_000),
            ".xlsx": (50_000, 2_000_000),
            ".pptx": (1_000_000, 20_000_000),
            ".jpg": (50_000, 5_000_000),
            ".png": (10_000, 2_000_000),
            ".mp4": (10_000_000, 500_000_000),
            ".mp3": (1_000_000, 15_000_000),
            ".zip": (1_000_000, 100_000_000),
            ".html": (5_000, 500_000),
            ".css": (1_000, 100_000),
            ".js": (5_000, 500_000),
            ".json": (1_000, 100_000),
            ".xml": (5_000, 500_000),
            ".md": (1_000, 100_000),
            ".csv": (10_000, 1_000_000)
        }

        # Common directory names
        self.common_directories = [
            "Documents",
            "Pictures",
            "Music",
            "Videos",
            "Downloads",
            "Desktop",
            "Projects",
            "Work",
            "Personal",
            "Backups",
            "Archive",
            "Code",
            "Data",
            "Presentations",
            "Reports"
        ]

        # Common file name prefixes
        self.file_name_prefixes = [
            "Report_",
            "Document_",
            "Presentation_",
            "Meeting_",
            "Invoice_",
            "Project_",
            "Analysis_",
            "Summary_",
            "Data_",
            "Chart_",
            "Image_",
            "Photo_",
            "Screenshot_",
            "Backup_",
            "Draft_",
            "Final_"
        ]

        # File attribute types
        self.posix_file_attributes = [
            "S_IFREG",  # Regular file
            "S_IFDIR",  # Directory
            "S_IFLNK",  # Symbolic link
            "S_IFBLK",  # Block device
            "S_IFCHR",  # Character device
            "S_IFIFO",  # FIFO
            "S_IFSOCK"  # Socket
        ]

        self.windows_file_attributes = [
            "FILE_ATTRIBUTE_ARCHIVE",
            "FILE_ATTRIBUTE_HIDDEN",
            "FILE_ATTRIBUTE_NORMAL",
            "FILE_ATTRIBUTE_READONLY",
            "FILE_ATTRIBUTE_SYSTEM",
            "FILE_ATTRIBUTE_TEMPORARY",
            "FILE_ATTRIBUTE_COMPRESSED",
            "FILE_ATTRIBUTE_ENCRYPTED"
        ]

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - count: Number of file metadata records to generate
                - criteria: Optional criteria for generation

        Returns:
            Generated file metadata
        """
        count = parameters.get("count", 1)
        criteria = parameters.get("criteria", {})

        extension = criteria.get("extension")
        path_prefix = criteria.get("path_prefix", "")
        name_pattern = criteria.get("name_pattern", "")
        size_range = criteria.get("size_range")

        self.logger.debug(f"Generating {count} file metadata records")

        records = []
        for _ in range(count):
            # Generate file model
            model = self._generate_file_model(
                extension=extension,
                path_prefix=path_prefix,
                name_pattern=name_pattern,
                size_range=size_range,
                criteria=criteria
            )
            records.append(model)

        # Return records in dictionary format for compatibility with other tools
        return {
            "records": [record.dict() for record in records],
            "count": len(records)
        }

    def _generate_semantic_attributes(self, file_path: str, file_name: str, file_size: int) -> List[Any]:
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

    def _generate_file_model(self, extension: str = None, path_prefix: str = "",
                           name_pattern: str = "", size_range: List[int] = None,
                           criteria: Dict[str, Any] = None) -> Any:
        """Generate a single file metadata model.

        Args:
            extension: File extension to use
            path_prefix: Path prefix for the file
            name_pattern: Pattern for file name
            size_range: Size range in bytes [min, max]
            criteria: Additional criteria for generation

        Returns:
            File metadata model (IndalekoObjectDataModel)
        """
        criteria = criteria or {}

        # Generate file extension
        if extension:
            file_ext = extension
        else:
            # Select random extension based on frequencies
            file_ext = random.choices(
                list(self.file_extensions.keys()),
                weights=list(self.file_extensions.values()),
                k=1
            )[0]

        # Generate file size
        if size_range:
            size = random.randint(size_range[0], size_range[1])
        else:
            size_min, size_max = self.file_size_ranges.get(file_ext, (1000, 1000000))
            # Use lognormal distribution for file sizes
            mu = math.log(size_min) + 0.5 * (math.log(size_max) - math.log(size_min))
            sigma = 0.5 * (math.log(size_max) - math.log(size_min)) / 3
            size = int(math.exp(random.normalvariate(mu, sigma)))

        # Generate file name
        if name_pattern:
            if "%" in name_pattern:
                # Replace % with random number or characters
                name = name_pattern.replace("%", str(random.randint(100, 999)))
            else:
                name = name_pattern
        else:
            prefix = random.choice(self.file_name_prefixes)
            suffix = datetime.datetime.now().strftime("%Y%m%d")
            name = f"{prefix}{suffix}{file_ext}"

        # Generate file path
        if path_prefix:
            path = path_prefix
        else:
            # Generate random path with 2-3 directory levels
            levels = random.randint(2, 3)
            path_parts = []
            for _ in range(levels):
                path_parts.append(random.choice(self.common_directories))

            # Format path based on OS
            if random.random() < 0.5:  # Windows path
                path = "C:\\" + "\\".join(path_parts)
            else:  # Unix path
                path = "/" + "/".join(path_parts)

        # Generate timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        created_days_ago = random.randint(30, 365)
        modified_days_ago = random.randint(0, created_days_ago)
        accessed_days_ago = random.randint(0, modified_days_ago)

        created = (now - datetime.timedelta(days=created_days_ago))
        modified = (now - datetime.timedelta(days=modified_days_ago))
        accessed = (now - datetime.timedelta(days=accessed_days_ago))

        # Generate unique identifier
        obj_id = str(uuid.uuid4())

        # Create volume UUID if Windows path
        volume_id = None
        if "\\" in path:
            volume_id = str(uuid.uuid4())

        # Create URI
        if "\\" in path:
            uri = f"\\\\?\\Volume{{{volume_id}}}\\{path.replace('C:\\', '')}\\{name}"
        else:
            uri = f"file://{path}/{name}"

        # Generate timestamp objects
        timestamps = [
            self.TimestampDataModel(
                Label=self.CREATION_TIMESTAMP,
                Value=created,
                Description="Created"
            ),
            self.TimestampDataModel(
                Label=self.MODIFICATION_TIMESTAMP,
                Value=modified,
                Description="Modified"
            ),
            self.TimestampDataModel(
                Label=self.ACCESS_TIMESTAMP,
                Value=accessed,
                Description="Accessed"
            ),
            self.TimestampDataModel(
                Label=self.CHANGE_TIMESTAMP,
                Value=created,  # Same as creation for simplicity
                Description="Changed"
            )
        ]

        # Create record with source identifier
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=uuid.uuid4(),
            Version="1.0",
            Description="Generated by model-based data generator"
        )

        record = self.RecordDataModel(
            SourceIdentifier=source_identifier
        )

        # Generate file attributes based on path
        posix_attr = random.choice(self.posix_file_attributes)
        windows_attr = random.choice(self.windows_file_attributes)

        # Generate semantic attributes
        semantic_attributes = self._generate_semantic_attributes(
            file_path=path,
            file_name=name,
            file_size=size
        )

        # Generate local identifier (inode or equivalent)
        local_id = random.randint(10000000, 9999999999)

        # Create the file metadata model
        file_model = self.ObjectDataModel(
            Record=record,
            URI=uri,
            ObjectIdentifier=obj_id,
            Timestamps=timestamps,
            Size=size,
            Label=name,
            LocalPath=path,
            LocalIdentifier=str(local_id),
            Volume=volume_id,
            PosixFileAttributes=posix_attr if "/" in path else None,
            WindowsFileAttributes=windows_attr if "\\" in path else None,
            SemanticAttributes=semantic_attributes
        )

        # Add additional fields based on criteria
        extra_data = {}
        for key, value in criteria.items():
            if key not in ["extension", "path_prefix", "name_pattern", "size_range"]:
                extra_data[key] = value

        # Store additional data in the model's extra fields
        if extra_data:
            # Log the extra data since the model doesn't have an extra field
            self.logger.debug(f"Extra file data (not used): {extra_data}")

        return file_model

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of file metadata records to generate",
                            "default": 1
                        },
                        "criteria": {
                            "type": "object",
                            "description": "Criteria for generation",
                            "properties": {
                                "extension": {
                                    "type": "string",
                                    "description": "File extension (e.g., .pdf, .docx)"
                                },
                                "path_prefix": {
                                    "type": "string",
                                    "description": "Path prefix for the file"
                                },
                                "name_pattern": {
                                    "type": "string",
                                    "description": "Pattern for file name (% will be replaced with random number)"
                                },
                                "size_range": {
                                    "type": "array",
                                    "description": "Size range in bytes [min, max]",
                                    "items": {
                                        "type": "integer"
                                    },
                                    "minItems": 2,
                                    "maxItems": 2
                                }
                            }
                        }
                    },
                    "required": ["count"]
                }
            }
        }


class SemanticMetadataGeneratorTool(Tool):
    """Tool for generating realistic semantic metadata."""

    def __init__(self):
        """Initialize the semantic metadata generator tool."""
        super().__init__(
            name="semantic_metadata_generator",
            description="Generate realistic semantic metadata for files"
        )

        # MIME type mappings for common file extensions
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
            ".js": "application/javascript",
            ".json": "application/json",
            ".xml": "application/xml",
            ".md": "text/markdown",
            ".csv": "text/csv"
        }

        # Document-related words for content generation
        self.document_words = [
            "analysis", "report", "summary", "project", "data", "research", "meeting", "review",
            "presentation", "document", "plan", "proposal", "strategy", "policy", "procedure",
            "quarterly", "annual", "monthly", "weekly", "daily", "update", "overview", "guide",
            "manual", "handbook", "reference", "specification", "requirements", "design", "implementation",
            "testing", "deployment", "maintenance", "budget", "forecast", "financial", "marketing",
            "sales", "operations", "development", "management", "team", "client", "customer", "vendor",
            "partner", "stakeholder", "executive", "board", "committee", "department", "division"
        ]

        # Image-related concepts
        self.image_concepts = [
            "landscape", "portrait", "nature", "urban", "architecture", "people", "animals", "food",
            "travel", "event", "product", "abstract", "black and white", "colorful", "macro",
            "night", "day", "outdoor", "indoor", "aerial", "underwater", "sport", "art", "document"
        ]

        # Video-related concepts
        self.video_concepts = [
            "tutorial", "presentation", "interview", "demonstration", "recording", "event", "lecture",
            "training", "promotional", "documentary", "animation", "screencast", "vlog", "review",
            "highlight", "behind-the-scenes", "announcement", "commercial", "discussion", "explainer"
        ]

        # Audio-related concepts
        self.audio_concepts = [
            "music", "speech", "podcast", "interview", "sound effect", "recording", "voice over",
            "narration", "meeting", "call", "lecture", "audio book", "ambient", "notification",
            "song", "instrumental", "discussion", "presentation", "conference", "instructional"
        ]

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - count: Number of semantic metadata records to generate
                - criteria: Optional criteria for generation

        Returns:
            Generated semantic metadata
        """
        count = parameters.get("count", 1)
        criteria = parameters.get("criteria", {})

        # Handle storage objects if provided in criteria
        storage_objects = criteria.get("storage_objects", [])
        if storage_objects and len(storage_objects) > 0:
            # Generate semantic metadata for each storage object
            records = self._generate_from_storage_objects(storage_objects, criteria)
            # Limit to requested count
            records = records[:count]
        else:
            # Generate standalone semantic metadata
            records = self._generate_semantic_records(count, criteria)

        self.logger.debug(f"Generated {len(records)} semantic metadata records")

        return {
            "records": records,
            "count": len(records)
        }

    def _generate_from_storage_objects(self, storage_objects: List[Dict[str, Any]],
                                       criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic metadata based on storage objects.

        Args:
            storage_objects: List of storage object metadata
            criteria: Additional criteria for generation

        Returns:
            Generated semantic metadata records
        """
        records = []

        for storage_obj in storage_objects:
            # Extract object info
            obj_id = storage_obj.get("ObjectIdentifier")
            extension = storage_obj.get("Extension", "")

            # Generate metadata for this object
            mime_type = self.mime_types.get(extension, "application/octet-stream")

            # Generate checksum
            checksum = self._generate_checksum()

            # Generate content metadata based on file type
            content = self._generate_content_metadata(mime_type, storage_obj, criteria)

            # Create semantic record
            record = {
                "ObjectIdentifier": obj_id,
                "MIMEType": mime_type,
                "Checksum": checksum,
                "Content": content,
                "ExtractedDate": datetime.datetime.now().isoformat(),
                "Tags": self._generate_tags(mime_type, content)
            }

            # Add additional fields based on criteria
            for key, value in criteria.items():
                if key not in ["storage_objects", "mime_type", "content_category"]:
                    record[key] = value

            records.append(record)

        return records

    def _generate_semantic_records(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate standalone semantic metadata records.

        Args:
            count: Number of records to generate
            criteria: Criteria for generation

        Returns:
            Generated semantic metadata records
        """
        records = []

        mime_type = criteria.get("mime_type")

        for _ in range(count):
            # Generate random object ID
            obj_id = str(uuid.uuid4())

            # Select or use provided MIME type
            if mime_type:
                record_mime_type = mime_type
            else:
                # Select random MIME type
                record_mime_type = random.choice(list(self.mime_types.values()))

            # Generate checksum
            checksum = self._generate_checksum()

            # Generate content metadata
            content = self._generate_content_metadata(record_mime_type, None, criteria)

            # Create semantic record
            record = {
                "ObjectIdentifier": obj_id,
                "MIMEType": record_mime_type,
                "Checksum": checksum,
                "Content": content,
                "ExtractedDate": datetime.datetime.now().isoformat(),
                "Tags": self._generate_tags(record_mime_type, content)
            }

            # Add additional fields based on criteria
            for key, value in criteria.items():
                if key not in ["storage_objects", "mime_type", "content_category"]:
                    record[key] = value

            records.append(record)

        return records

    def _generate_checksum(self) -> str:
        """Generate a realistic file checksum.

        Returns:
            Hexadecimal checksum string
        """
        # Generate MD5 or SHA-like hash
        hash_type = random.choice(["md5", "sha1", "sha256"])

        if hash_type == "md5":
            # 32 characters (128 bits)
            return ''.join(random.choice("0123456789abcdef") for _ in range(32))
        elif hash_type == "sha1":
            # 40 characters (160 bits)
            return ''.join(random.choice("0123456789abcdef") for _ in range(40))
        else:  # sha256
            # 64 characters (256 bits)
            return ''.join(random.choice("0123456789abcdef") for _ in range(64))

    def _generate_content_metadata(self, mime_type: str, storage_obj: Optional[Dict[str, Any]],
                                  criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content metadata based on MIME type.

        Args:
            mime_type: MIME type of the file
            storage_obj: Optional storage object metadata
            criteria: Additional criteria for generation

        Returns:
            Content metadata
        """
        content_category = criteria.get("content_category")

        # If content category is specified, use that instead of inferring from MIME type
        if content_category:
            category = content_category
        else:
            # Determine category from MIME type
            if mime_type.startswith("text/") or mime_type.startswith("application/pdf") or \
               mime_type.startswith("application/vnd.openxmlformats-officedocument.wordprocessing"):
                category = "document"
            elif mime_type.startswith("image/"):
                category = "image"
            elif mime_type.startswith("video/"):
                category = "video"
            elif mime_type.startswith("audio/"):
                category = "audio"
            elif mime_type.startswith("application/json") or mime_type.startswith("application/xml"):
                category = "structured_data"
            else:
                category = "binary"

        # Generate content based on category
        if category == "document":
            return self._generate_document_content(storage_obj, mime_type)
        elif category == "image":
            return self._generate_image_content(storage_obj)
        elif category == "video":
            return self._generate_video_content(storage_obj)
        elif category == "audio":
            return self._generate_audio_content(storage_obj)
        elif category == "structured_data":
            return self._generate_structured_data_content(storage_obj, mime_type)
        else:
            return {"type": "binary", "analyzable": False}

    def _generate_document_content(self, storage_obj: Optional[Dict[str, Any]],
                                  mime_type: str) -> Dict[str, Any]:
        """Generate document content metadata.

        Args:
            storage_obj: Optional storage object metadata
            mime_type: MIME type of the document

        Returns:
            Document content metadata
        """
        # Use file name if available to influence content
        if storage_obj and storage_obj.get("Name"):
            name = storage_obj.get("Name", "")
            title = name.split(".")[0].replace("_", " ").title()
        else:
            # Generate random title using document words
            words = random.sample(self.document_words, 3)
            title = " ".join(word.title() for word in words)

        # Generate author
        authors = ["John Smith", "Jane Doe", "Alice Johnson", "Bob Brown",
                  "Emma Wilson", "Michael Davis", "Sarah Miller", "David Lee"]
        author = random.choice(authors)

        # Generate page count based on file size if available
        if storage_obj and storage_obj.get("Size"):
            size = storage_obj.get("Size", 0)
            # Rough approximation: ~3KB per page for text/doc files
            page_count = max(1, int(size / (3 * 1024)))
        else:
            page_count = random.randint(1, 50)

        # Generate content extract
        paragraphs = []
        for _ in range(min(3, random.randint(1, 5))):
            # Generate a paragraph with 3-8 sentences
            sentences = []
            for _ in range(random.randint(3, 8)):
                # Generate a sentence with 5-15 words
                words = random.sample(self.document_words, random.randint(5, 15))
                sentence = " ".join(words).capitalize() + "."
                sentences.append(sentence)

            paragraph = " ".join(sentences)
            paragraphs.append(paragraph)

        content_extract = "\n\n".join(paragraphs)

        # Create document metadata
        return {
            "type": "document",
            "title": title,
            "author": author,
            "page_count": page_count,
            "extract": content_extract,
            "format": mime_type.split("/")[1],
            "language": "en"
        }

    def _generate_image_content(self, storage_obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate image content metadata.

        Args:
            storage_obj: Optional storage object metadata

        Returns:
            Image content metadata
        """
        # Generate image dimensions
        width = random.randint(800, 4000)
        height = random.randint(600, 3000)

        # Generate image concept/subject
        concepts = random.sample(self.image_concepts, random.randint(1, 3))
        description = ", ".join(concepts)

        # Generate color mode and bit depth
        color_mode = random.choice(["RGB", "RGBA", "sRGB", "grayscale"])
        bit_depth = random.choice([8, 16, 24, 32])

        # Create image metadata
        return {
            "type": "image",
            "width": width,
            "height": height,
            "description": description,
            "color_mode": color_mode,
            "bit_depth": bit_depth,
            "has_exif": random.choice([True, False]),
            "extracted_text": "" if random.random() < 0.8 else "Some text found in the image."
        }

    def _generate_video_content(self, storage_obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate video content metadata.

        Args:
            storage_obj: Optional storage object metadata

        Returns:
            Video content metadata
        """
        # Generate video duration (in seconds)
        duration = random.randint(30, 7200)

        # Generate video dimensions
        resolutions = [(1280, 720), (1920, 1080), (3840, 2160), (854, 480)]
        width, height = random.choice(resolutions)

        # Generate frame rate
        frame_rates = [24, 25, 30, 60]
        frame_rate = random.choice(frame_rates)

        # Generate codec
        codecs = ["H.264", "H.265", "VP9", "AV1"]
        codec = random.choice(codecs)

        # Generate concept/subject
        concepts = random.sample(self.video_concepts, random.randint(1, 2))
        description = ", ".join(concepts)

        # Create video metadata
        return {
            "type": "video",
            "duration": duration,
            "width": width,
            "height": height,
            "frame_rate": frame_rate,
            "codec": codec,
            "description": description,
            "has_audio": random.choice([True, False]),
            "has_subtitles": random.choice([True, False])
        }

    def _generate_audio_content(self, storage_obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate audio content metadata.

        Args:
            storage_obj: Optional storage object metadata

        Returns:
            Audio content metadata
        """
        # Generate audio duration (in seconds)
        duration = random.randint(30, 7200)

        # Generate audio characteristics
        sample_rates = [44100, 48000, 96000]
        sample_rate = random.choice(sample_rates)

        bit_rates = [96, 128, 192, 256, 320]
        bit_rate = random.choice(bit_rates)

        channels = [1, 2]
        channel_count = random.choice(channels)

        # Generate codec
        codecs = ["MP3", "AAC", "FLAC", "WAV", "Opus"]
        codec = random.choice(codecs)

        # Generate concept/subject
        concepts = random.sample(self.audio_concepts, random.randint(1, 2))
        description = ", ".join(concepts)

        # Create audio metadata
        return {
            "type": "audio",
            "duration": duration,
            "sample_rate": sample_rate,
            "bit_rate": bit_rate,
            "channels": channel_count,
            "codec": codec,
            "description": description,
            "has_speech": random.choice([True, False]),
            "transcript": "" if random.random() < 0.8 else "Partial transcript of the audio content."
        }

    def _generate_structured_data_content(self, storage_obj: Optional[Dict[str, Any]],
                                         mime_type: str) -> Dict[str, Any]:
        """Generate structured data content metadata.

        Args:
            storage_obj: Optional storage object metadata
            mime_type: MIME type of the file

        Returns:
            Structured data content metadata
        """
        # Determine format from MIME type
        if "json" in mime_type:
            format_type = "JSON"
        elif "xml" in mime_type:
            format_type = "XML"
        else:
            format_type = "unknown"

        # Generate element count
        element_count = random.randint(10, 1000)

        # Create structured data metadata
        return {
            "type": "structured_data",
            "format": format_type,
            "element_count": element_count,
            "schema_valid": random.choice([True, False]),
            "has_schema": random.choice([True, False]),
            "extract": "{...}" if format_type == "JSON" else "<...>...</...>"
        }

    def _generate_tags(self, mime_type: str, content: Dict[str, Any]) -> List[str]:
        """Generate tags based on content and MIME type.

        Args:
            mime_type: MIME type of the file
            content: Content metadata

        Returns:
            List of tags
        """
        tags = []

        # Add mime type category tag
        if mime_type.startswith("text/"):
            tags.append("text")
        elif mime_type.startswith("image/"):
            tags.append("image")
        elif mime_type.startswith("video/"):
            tags.append("video")
        elif mime_type.startswith("audio/"):
            tags.append("audio")
        elif mime_type.startswith("application/pdf"):
            tags.append("document")
            tags.append("pdf")
        elif "word" in mime_type or "officedocument.wordprocessing" in mime_type:
            tags.append("document")
            tags.append("word")
        elif "excel" in mime_type or "spreadsheet" in mime_type:
            tags.append("spreadsheet")
            tags.append("excel")
        elif "powerpoint" in mime_type or "presentation" in mime_type:
            tags.append("presentation")
            tags.append("powerpoint")

        # Add content-specific tags
        content_type = content.get("type")
        if content_type == "document":
            if "title" in content:
                # Extract keywords from title
                for word in content["title"].lower().split():
                    if word in self.document_words and word not in tags:
                        tags.append(word)

            # Add author tag if available
            if "author" in content:
                tags.append(f"author:{content['author'].split()[0].lower()}")

        elif content_type == "image" and "description" in content:
            # Add description concepts as tags
            for concept in content["description"].split(", "):
                if concept not in tags:
                    tags.append(concept.lower())

        elif content_type == "video" and "description" in content:
            # Add description concepts as tags
            for concept in content["description"].split(", "):
                if concept not in tags:
                    tags.append(concept.lower())

        elif content_type == "audio" and "description" in content:
            # Add description concepts as tags
            for concept in content["description"].split(", "):
                if concept not in tags:
                    tags.append(concept.lower())

        # Add some common categorical tags
        if random.random() < 0.3:
            common_tags = ["work", "personal", "shared", "important", "archived"]
            tags.append(random.choice(common_tags))

        return tags

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of semantic metadata records to generate",
                            "default": 1
                        },
                        "criteria": {
                            "type": "object",
                            "description": "Criteria for generation",
                            "properties": {
                                "storage_objects": {
                                    "type": "array",
                                    "description": "Storage objects to generate semantic metadata for",
                                    "items": {
                                        "type": "object"
                                    }
                                },
                                "mime_type": {
                                    "type": "string",
                                    "description": "MIME type for the content"
                                },
                                "content_category": {
                                    "type": "string",
                                    "description": "Category of content (document, image, video, audio, structured_data, binary)",
                                    "enum": ["document", "image", "video", "audio", "structured_data", "binary"]
                                }
                            }
                        }
                    },
                    "required": ["count"]
                }
            }
        }


class ActivityGeneratorTool(Tool):
    """Tool for generating realistic activity metadata."""

    def __init__(self):
        """Initialize the activity generator tool."""
        super().__init__(
            name="activity_generator",
            description="Generate realistic activity metadata records"
        )

        # Import models
        import sys
        import os

        # Setup path for imports
        if os.environ.get("INDALEKO_ROOT") is None:
            current_path = os.path.dirname(os.path.abspath(__file__))
            while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
                current_path = os.path.dirname(current_path)
            os.environ["INDALEKO_ROOT"] = current_path
            sys.path.append(current_path)

        # Import Indaleko data models
        from data_models.record import IndalekoRecordDataModel
        from data_models.source_identifier import IndalekoSourceIdentifierDataModel
        from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
        from activity.data_model.activity import IndalekoActivityDataModel

        # Store model classes
        self.RecordDataModel = IndalekoRecordDataModel
        self.SourceIdentifierDataModel = IndalekoSourceIdentifierDataModel
        self.SemanticAttributeDataModel = IndalekoSemanticAttributeDataModel
        self.ActivityDataModel = IndalekoActivityDataModel

        # Activity types
        self.activity_types = {
            "create": 0.25,    # 25% create events
            "modify": 0.40,    # 40% modify events
            "read": 0.30,      # 30% read events
            "delete": 0.05     # 5% delete events
        }

        # Application names by platform
        self.applications = {
            "windows": [
                "Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint",
                "Notepad", "Visual Studio Code", "Chrome", "Edge", "Firefox",
                "Adobe Photoshop", "Adobe Acrobat", "File Explorer", "Outlook",
                "Teams", "Slack", "Zoom", "Windows Media Player", "VLC"
            ],
            "macos": [
                "Pages", "Numbers", "Keynote", "TextEdit", "Visual Studio Code",
                "Safari", "Chrome", "Firefox", "Adobe Photoshop", "Adobe Acrobat",
                "Finder", "Mail", "Messages", "Slack", "Zoom", "QuickTime Player", "iTunes"
            ],
            "linux": [
                "LibreOffice Writer", "LibreOffice Calc", "LibreOffice Impress",
                "Gedit", "Visual Studio Code", "Chrome", "Firefox", "GIMP",
                "Evince", "Nautilus", "Thunderbird", "Slack", "Zoom", "VLC"
            ]
        }

        # Activity domains
        self.activity_domains = [
            "storage", "collaboration", "location", "ambient", "task_activity"
        ]

        # Provider types by domain
        self.provider_types = {
            "storage": ["ntfs", "dropbox", "gdrive"],
            "collaboration": ["outlook", "calendar", "discord"],
            "location": ["ip_location", "wifi_location", "windows_gps_location"],
            "ambient": ["smart_thermostat", "spotify", "youtube"],
            "task_activity": ["windows_task"]
        }

        # Common users
        self.users = [
            "user1@example.com", "john.doe@company.com", "alice.smith@org.net",
            "rjohnson@domain.com", "sarah.wilson@business.io", "local-admin",
            "guest-user", "system", "david.miller@enterprise.com"
        ]

        # Devices
        self.devices = [
            "DESKTOP-A12BCD", "LAPTOP-XYZ123", "MacBook-Pro-2",
            "ubuntu-server-01", "surface-pro-7", "thinkpad-t14",
            "iPhone-12", "Galaxy-S21", "iPad-Air"
        ]

        # Common paths for activities
        self.common_paths = [
            "/Users/username/Documents",
            "/Users/username/Pictures",
            "/Users/username/Downloads",
            "C:\\Users\\username\\Documents",
            "C:\\Users\\username\\Pictures",
            "C:\\Users\\username\\Downloads",
            "/home/username/Documents",
            "/home/username/Pictures",
            "/home/username/Downloads",
            "/data/projects",
            "/data/shared",
            "C:\\Projects",
            "C:\\SharedData"
        ]

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - count: Number of activity records to generate
                - criteria: Optional criteria for generation

        Returns:
            Generated activity metadata
        """
        count = parameters.get("count", 1)
        criteria = parameters.get("criteria", {})

        # Handle storage objects if provided in criteria
        storage_objects = criteria.get("storage_objects", [])
        if storage_objects and len(storage_objects) > 0:
            # Generate activity records based on storage objects
            records = self._generate_from_storage_objects(storage_objects, criteria)
            # Limit to requested count
            records = records[:count]
        else:
            # Generate standalone activity records
            records = self._generate_activity_records(count, criteria)

        self.logger.debug(f"Generated {len(records)} activity records")

        # Return records in dictionary format for compatibility with other tools
        return {
            "records": [record.dict() for record in records],
            "count": len(records)
        }

    def _generate_from_storage_objects(self, storage_objects: List[Dict[str, Any]],
                                      criteria: Dict[str, Any]) -> List[Any]:
        """Generate activity records based on storage objects.

        Args:
            storage_objects: List of storage object metadata
            criteria: Additional criteria for generation

        Returns:
            Generated activity record models
        """
        records = []

        # Set up timeline (from oldest creation to most recent access)
        now = datetime.datetime.now(datetime.timezone.utc)
        earliest_date = now - datetime.timedelta(days=365)  # Up to 1 year ago

        domain = criteria.get("domain", random.choice(self.activity_domains))
        provider_type = criteria.get("provider_type")
        if not provider_type:
            provider_type = random.choice(self.provider_types.get(domain, ["generic"]))

        for storage_obj in storage_objects:
            # Extract object info
            obj_id = storage_obj.get("ObjectIdentifier")
            path = storage_obj.get("Path", "")
            name = storage_obj.get("Name", "")

            # Get or generate timestamps
            try:
                created = datetime.datetime.fromisoformat(storage_obj.get("Created", earliest_date.isoformat()))
                # Add timezone if missing
                if created.tzinfo is None:
                    created = created.replace(tzinfo=datetime.timezone.utc)
            except (ValueError, TypeError):
                created = earliest_date

            try:
                modified = datetime.datetime.fromisoformat(storage_obj.get("Modified", created.isoformat()))
                # Add timezone if missing
                if modified.tzinfo is None:
                    modified = modified.replace(tzinfo=datetime.timezone.utc)
            except (ValueError, TypeError):
                modified = created

            try:
                accessed = datetime.datetime.fromisoformat(storage_obj.get("Accessed", modified.isoformat()))
                # Add timezone if missing
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=datetime.timezone.utc)
            except (ValueError, TypeError):
                accessed = modified

            # For each storage object, generate 1-3 activity records
            activity_count = random.randint(1, 3)

            for i in range(activity_count):
                # Determine activity type based on timestamps
                if i == 0 and random.random() < 0.8:
                    # First activity is likely creation
                    activity_type = "create"
                    timestamp = created
                elif i == activity_count - 1 and random.random() < 0.6:
                    # Last activity is often access
                    activity_type = "read"
                    timestamp = accessed
                else:
                    # Middle activities are often modifications
                    if random.random() < 0.7:
                        activity_type = "modify"
                        # Modification time between creation and access
                        delta = (accessed - created).total_seconds()
                        modified_offset = random.uniform(0, delta)
                        timestamp = created + datetime.timedelta(seconds=modified_offset)
                    else:
                        activity_type = random.choices(
                            list(self.activity_types.keys()),
                            weights=list(self.activity_types.values()),
                            k=1
                        )[0]
                        # Random time between creation and access
                        delta = (accessed - created).total_seconds()
                        activity_offset = random.uniform(0, delta)
                        timestamp = created + datetime.timedelta(seconds=activity_offset)

                # Create activity record model
                record = self._create_activity_record_model(
                    obj_id=obj_id,
                    path=path,
                    name=name,
                    timestamp=timestamp,
                    activity_type=activity_type,
                    domain=domain,
                    provider_type=provider_type,
                    criteria=criteria
                )

                records.append(record)

        # Sort records by timestamp
        records.sort(key=lambda x: x.Timestamp)

        return records

    def _generate_activity_records(self, count: int, criteria: Dict[str, Any]) -> List[Any]:
        """Generate standalone activity records.

        Args:
            count: Number of records to generate
            criteria: Criteria for generation

        Returns:
            Generated activity record models
        """
        records = []

        # Set up timeline
        now = datetime.datetime.now(datetime.timezone.utc)
        earliest_date = now - datetime.timedelta(days=criteria.get("max_age_days", 90))

        # Get domain and provider type from criteria or choose randomly
        domain = criteria.get("domain")
        provider_type = criteria.get("provider_type")

        if not domain:
            domain = random.choice(self.activity_domains)

        if not provider_type:
            provider_type = random.choice(self.provider_types.get(domain, ["generic"]))

        # Generate records
        for _ in range(count):
            # Generate random object ID if not provided
            obj_id = criteria.get("object_id", str(uuid.uuid4()))

            # Generate random path
            path = criteria.get("path", random.choice(self.common_paths))
            if "%username%" in path:
                username = random.choice(["john", "alice", "bob", "sarah", "david"])
                path = path.replace("%username%", username)

            # Generate random name
            if not criteria.get("name"):
                extensions = [".txt", ".pdf", ".docx", ".xlsx", ".jpg", ".png", ".mp4"]
                name = f"file_{random.randint(1000, 9999)}{random.choice(extensions)}"
            else:
                name = criteria.get("name")

            # Generate random timestamp
            time_range = (now - earliest_date).total_seconds()
            random_seconds = random.uniform(0, time_range)
            timestamp = earliest_date + datetime.timedelta(seconds=random_seconds)

            # Determine activity type
            if not criteria.get("activity_type"):
                # Choose based on probabilities
                activity_type = random.choices(
                    list(self.activity_types.keys()),
                    weights=list(self.activity_types.values()),
                    k=1
                )[0]
            else:
                activity_type = criteria.get("activity_type")

            # Create activity record model
            record = self._create_activity_record_model(
                obj_id=obj_id,
                path=path,
                name=name,
                timestamp=timestamp,
                activity_type=activity_type,
                domain=domain,
                provider_type=provider_type,
                criteria=criteria
            )

            records.append(record)

        # Sort records by timestamp
        records.sort(key=lambda x: x.Timestamp)

        return records

    def _create_activity_record_model(self, obj_id: str, path: str, name: str,
                                    timestamp: datetime.datetime, activity_type: str,
                                    domain: str, provider_type: str,
                                    criteria: Dict[str, Any]) -> Any:
        """Create a single activity record model.

        Args:
            obj_id: Object identifier
            path: File path
            name: File name
            timestamp: Activity timestamp
            activity_type: Type of activity
            domain: Activity domain
            provider_type: Provider type
            criteria: Additional criteria

        Returns:
            Activity record model (IndalekoActivityDataModel)
        """
        # Generate a Record object with UUID and source identifier
        source_identifier = self._generate_source_identifier(domain, provider_type)

        record = self.RecordDataModel(
            RecordIdentifier=str(uuid.uuid4()),
            SourceIdentifier=source_identifier
        )

        # Generate platform information
        platform = criteria.get("platform", random.choice(["windows", "macos", "linux"]))

        # Determine the app based on platform
        app = criteria.get("application")
        if not app:
            app = random.choice(self.applications.get(platform, ["Unknown Application"]))

        # Determine the user
        user = criteria.get("user")
        if not user:
            user = random.choice(self.users)

        # Determine the device
        device = criteria.get("device")
        if not device:
            device = random.choice(self.devices)

        # Ensure timestamp has timezone
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)

        # Generate semantic attributes based on activity type and domain
        semantic_attributes = self._generate_semantic_attributes(
            activity_type=activity_type,
            domain=domain,
            provider_type=provider_type,
            obj_id=obj_id,
            path=path,
            name=name,
            user=user,
            app=app,
            device=device,
            platform=platform
        )

        # Create the activity data model
        activity_model = self.ActivityDataModel(
            Record=record,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes
        )

        # Add extra fields as additional data if needed
        extra_data = {}
        for key, value in criteria.items():
            if key not in ["object_id", "path", "name", "activity_type", "domain",
                          "provider_type", "user", "application", "device", "platform"]:
                extra_data[key] = value

        if extra_data:
            # Log extra data since the model doesn't have an extra field
            self.logger.debug(f"Extra activity data (not stored): {extra_data}")

        return activity_model

    def _generate_source_identifier(self, domain: str, provider_type: str) -> IndalekoSourceIdentifierDataModel:
        """Generate a source identifier for the activity.

        Args:
            domain: Activity domain
            provider_type: Provider type

        Returns:
            Source identifier object
        """
        # Create a structured source identifier object
        return IndalekoSourceIdentifierDataModel(
            Identifier=uuid.uuid4(),
            Version="1.0",
            Description=f"Generated {domain} activity from {provider_type} by model-based data generator"
        )

    def _generate_semantic_attributes(self, activity_type: str, domain: str,
                                     provider_type: str, obj_id: str, path: str,
                                     name: str, user: str, app: str, device: str,
                                     platform: str) -> List[Any]:
        """Generate semantic attributes for the activity.

        Args:
            activity_type: Type of activity
            domain: Activity domain
            provider_type: Provider type
            obj_id: Object identifier
            path: File path
            name: File name
            user: User identifier
            app: Application name
            device: Device identifier
            platform: Platform type

        Returns:
            List of semantic attribute models
        """
        attributes = []

        # Common attributes for all activities
        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "ACTIVITY_TYPE",
            activity_type.upper()
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "OBJECT_ID",
            obj_id
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "DATA_PATH",
            path
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "DATA_NAME",
            name
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "DATA_USER",
            user
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "DATA_APPLICATION",
            app
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "DATA_DEVICE",
            device
        ))

        attributes.append(SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            "DATA_PLATFORM",
            platform
        ))

        # Domain-specific attributes
        if domain == "storage":
            if activity_type == "create":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_CREATE",
                    "True"
                ))
            elif activity_type == "modify":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_MODIFY",
                    "True"
                ))
                # Add some details about what was modified
                modifications = random.choice(["content", "permissions", "metadata", "rename"])
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_MODIFY_TYPE",
                    modifications
                ))
            elif activity_type == "read":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_READ",
                    "True"
                ))
            elif activity_type == "delete":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_DELETE",
                    "True"
                ))

            # Add provider-specific attributes
            if provider_type == "ntfs":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_VOLUME",
                    random.choice(["C:", "D:", "E:"])
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_USN",
                    str(random.randint(10000, 999999))
                ))
            elif provider_type == "gdrive":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_CLOUD_ID",
                    f"gdrive:{uuid.uuid4()}"
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_SHARING",
                    random.choice(["private", "shared", "public"])
                ))
            elif provider_type == "dropbox":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_CLOUD_ID",
                    f"dropbox:{uuid.uuid4()}"
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "STORAGE_SHARING",
                    random.choice(["private", "shared", "public"])
                ))

        elif domain == "collaboration":
            attributes.append(SemanticAttributeRegistry.create_attribute(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                "COLLABORATION_TYPE",
                provider_type
            ))

            if provider_type == "outlook":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "COLLABORATION_EMAIL_SUBJECT",
                    f"Email about {name}"
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "COLLABORATION_PARTICIPANTS",
                    ",".join(random.sample(self.users, random.randint(1, 3)))
                ))
            elif provider_type == "calendar":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "COLLABORATION_EVENT_TITLE",
                    f"Meeting about {name}"
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "COLLABORATION_DURATION",
                    str(random.choice([30, 60, 90, 120]))
                ))
            elif provider_type == "discord":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "COLLABORATION_CHANNEL",
                    random.choice(["general", "project-updates", "team-chat"])
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "COLLABORATION_MENTIONS",
                    str(random.randint(0, 5))
                ))

        elif domain == "location":
            attributes.append(SemanticAttributeRegistry.create_attribute(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                "LOCATION_TYPE",
                provider_type
            ))

            if provider_type == "ip_location":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_IP",
                    f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}"
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_COUNTRY",
                    random.choice(["US", "CA", "UK", "DE", "FR", "JP", "AU"])
                ))
            elif provider_type == "wifi_location":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_SSID",
                    random.choice(["HomeWiFi", "OfficeNetwork", "CoffeeShop", "GuestWiFi"])
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_SIGNAL_STRENGTH",
                    str(random.randint(-90, -30))
                ))
            elif provider_type == "windows_gps_location":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_LATITUDE",
                    str(random.uniform(25.0, 48.0))
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_LONGITUDE",
                    str(random.uniform(-125.0, -70.0))
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "LOCATION_ACCURACY",
                    str(random.randint(1, 30))
                ))

        elif domain == "ambient":
            attributes.append(SemanticAttributeRegistry.create_attribute(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                "AMBIENT_TYPE",
                provider_type
            ))

            if provider_type == "smart_thermostat":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "AMBIENT_TEMPERATURE",
                    str(random.uniform(18.0, 25.0))
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "AMBIENT_HUMIDITY",
                    str(random.uniform(30.0, 60.0))
                ))
            elif provider_type == "spotify":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "AMBIENT_SONG",
                    random.choice(["Song A", "Song B", "Song C", "Song D"])
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "AMBIENT_ARTIST",
                    random.choice(["Artist X", "Artist Y", "Artist Z"])
                ))
            elif provider_type == "youtube":
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "AMBIENT_VIDEO",
                    random.choice(["Tutorial", "Music Video", "Documentary", "Vlog"])
                ))
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "AMBIENT_DURATION",
                    str(random.randint(60, 3600))
                ))

        elif domain == "task_activity":
            attributes.append(SemanticAttributeRegistry.create_attribute(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                "TASK_TYPE",
                activity_type
            ))

            attributes.append(SemanticAttributeRegistry.create_attribute(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                "TASK_PID",
                str(random.randint(1000, 9999))
            ))

            attributes.append(SemanticAttributeRegistry.create_attribute(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                "TASK_COMMAND",
                f"{app} {path}/{name}"
            ))

            if random.random() < 0.3:
                attributes.append(SemanticAttributeRegistry.create_attribute(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
                    "TASK_PARENT_PID",
                    str(random.randint(100, 999))
                ))

        return attributes

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of activity records to generate",
                            "default": 1
                        },
                        "criteria": {
                            "type": "object",
                            "description": "Criteria for generation",
                            "properties": {
                                "storage_objects": {
                                    "type": "array",
                                    "description": "Storage objects to generate activity for",
                                    "items": {
                                        "type": "object"
                                    }
                                },
                                "domain": {
                                    "type": "string",
                                    "description": "Activity domain (storage, collaboration, location, ambient, task_activity)",
                                    "enum": ["storage", "collaboration", "location", "ambient", "task_activity"]
                                },
                                "provider_type": {
                                    "type": "string",
                                    "description": "Provider type within the domain"
                                },
                                "activity_type": {
                                    "type": "string",
                                    "description": "Type of activity (create, modify, read, delete)",
                                    "enum": ["create", "modify", "read", "delete"]
                                },
                                "max_age_days": {
                                    "type": "integer",
                                    "description": "Maximum age of generated activities in days",
                                    "default": 90
                                },
                                "platform": {
                                    "type": "string",
                                    "description": "Platform (windows, macos, linux)",
                                    "enum": ["windows", "macos", "linux"]
                                }
                            }
                        }
                    },
                    "required": ["count"]
                }
            }
        }


class RelationshipGeneratorTool(Tool):
    """Tool for generating realistic relationship metadata."""

    def __init__(self):
        """Initialize the relationship generator tool."""
        super().__init__(
            name="relationship_generator",
            description="Generate realistic relationship metadata between objects"
        )

        # Import models
        import sys
        import os

        # Setup path for imports
        if os.environ.get("INDALEKO_ROOT") is None:
            current_path = os.path.dirname(os.path.abspath(__file__))
            while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
                current_path = os.path.dirname(current_path)
            os.environ["INDALEKO_ROOT"] = current_path
            sys.path.append(current_path)

        # Import Indaleko data models
        from data_models.record import IndalekoRecordDataModel
        from data_models.source_identifier import IndalekoSourceIdentifierDataModel
        from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
        from data_models.relationship import IndalekoRelationshipDataModel

        # Store model classes
        self.RecordDataModel = IndalekoRecordDataModel
        self.SourceIdentifierDataModel = IndalekoSourceIdentifierDataModel
        self.SemanticAttributeDataModel = IndalekoSemanticAttributeDataModel
        self.RelationshipDataModel = IndalekoRelationshipDataModel

        # Common relationship types
        self.relationship_types = {
            "storage": [
                "contains", "contained_by", "parent_of", "child_of",
                "previous_version_of", "next_version_of", "copy_of", "derived_from"
            ],
            "collaboration": [
                "shared_with", "modified_by", "owned_by", "created_by",
                "viewed_by", "commented_on_by", "referenced_by"
            ],
            "semantic": [
                "similar_to", "related_to", "same_author_as", "same_topic_as",
                "references", "cited_by", "mentions", "mentioned_by"
            ],
            "temporal": [
                "precedes", "follows", "created_before", "created_after",
                "modified_before", "modified_after", "accessed_before", "accessed_after"
            ],
            "spatial": [
                "near", "located_in", "co_located_with", "distant_from"
            ]
        }

        # Relationship strengths (0.0 to 1.0)
        self.relationship_strengths = {
            "contains": 1.0,         # Definite containment
            "contained_by": 1.0,     # Definite containment
            "parent_of": 1.0,        # Definite parentage
            "child_of": 1.0,         # Definite child
            "previous_version_of": 0.9,  # Previous version
            "next_version_of": 0.9,  # Next version
            "copy_of": 0.85,         # Copy
            "derived_from": 0.7,     # Derived work
            "shared_with": 0.8,      # Sharing
            "modified_by": 0.9,      # Modification
            "owned_by": 1.0,         # Ownership
            "created_by": 1.0,       # Creation
            "viewed_by": 0.6,        # Viewing
            "commented_on_by": 0.7,  # Commenting
            "referenced_by": 0.5,    # Reference
            "similar_to": 0.3,       # Similarity (can vary)
            "related_to": 0.2,       # General relation (can vary)
            "same_author_as": 0.7,   # Same author
            "same_topic_as": 0.5,    # Same topic
            "references": 0.4,       # Reference to another object
            "cited_by": 0.4,         # Citation
            "mentions": 0.3,         # Mention
            "mentioned_by": 0.3,     # Being mentioned
            "precedes": 0.6,         # Temporal precedence
            "follows": 0.6,          # Temporal following
            "created_before": 0.6,   # Created earlier
            "created_after": 0.6,    # Created later
            "modified_before": 0.5,  # Modified earlier
            "modified_after": 0.5,   # Modified later
            "accessed_before": 0.4,  # Accessed earlier
            "accessed_after": 0.4,   # Accessed later
            "near": 0.3,             # Spatial proximity
            "located_in": 0.7,       # Location containment
            "co_located_with": 0.5,  # Co-location
            "distant_from": 0.2      # Spatial distance
        }

        # Relationship bidirectionality mapping
        self.bidirectional_relationships = {
            "contains": "contained_by",
            "contained_by": "contains",
            "parent_of": "child_of",
            "child_of": "parent_of",
            "previous_version_of": "next_version_of",
            "next_version_of": "previous_version_of",
            "shared_with": "has_access_to",
            "modified_by": "modified",
            "owned_by": "owns",
            "created_by": "created",
            "viewed_by": "viewed",
            "commented_on_by": "commented_on",
            "referenced_by": "references",
            "similar_to": "similar_to",  # Symmetric
            "related_to": "related_to",  # Symmetric
            "same_author_as": "same_author_as",  # Symmetric
            "same_topic_as": "same_topic_as",  # Symmetric
            "references": "referenced_by",
            "cited_by": "cites",
            "mentions": "mentioned_by",
            "mentioned_by": "mentions",
            "precedes": "follows",
            "follows": "precedes",
            "created_before": "created_after",
            "created_after": "created_before",
            "modified_before": "modified_after",
            "modified_after": "modified_before",
            "accessed_before": "accessed_after",
            "accessed_after": "accessed_before",
            "near": "near",  # Symmetric
            "located_in": "contains_location",
            "co_located_with": "co_located_with",  # Symmetric
            "distant_from": "distant_from"  # Symmetric
        }

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - count: Number of relationship records to generate
                - criteria: Optional criteria for generation

        Returns:
            Generated relationship metadata
        """
        count = parameters.get("count", 1)
        criteria = parameters.get("criteria", {})

        # Get objects to relate
        source_objects = criteria.get("source_objects", [])
        target_objects = criteria.get("target_objects", source_objects)

        if not source_objects:
            # Generate standalone relationship records
            records = self._generate_relationship_records(count, criteria)
        else:
            # Generate relationships between provided objects
            records = self._generate_from_objects(source_objects, target_objects, count, criteria)

        self.logger.debug(f"Generated {len(records)} relationship records")

        # Return records in dictionary format for compatibility with other tools
        return {
            "records": [record.dict() for record in records],
            "count": len(records)
        }

    def _generate_from_objects(self, source_objects: List[Dict[str, Any]],
                              target_objects: List[Dict[str, Any]],
                              count: int, criteria: Dict[str, Any]) -> List[Any]:
        """Generate relationships between provided objects.

        Args:
            source_objects: Source objects for relationships
            target_objects: Target objects for relationships
            count: Maximum number of relationships to generate
            criteria: Additional criteria for generation

        Returns:
            Generated relationship record models
        """
        records = []
        num_relationships = min(count, len(source_objects) * 2)  # Limit total relationships

        # Determine relationship categories
        categories = criteria.get("categories", list(self.relationship_types.keys()))
        if isinstance(categories, str):
            categories = [categories]

        # Get specific relationship types if provided
        specific_types = criteria.get("relationship_types", [])

        # Create relationships
        relationships_created = 0

        # First create parent-child relationships for hierarchical structures if appropriate
        if "storage" in categories and len(source_objects) > 1:
            # Sort objects by path to identify potential parent-child relationships
            path_grouped_objects = {}
            for obj in source_objects:
                path = obj.get("Path", "")
                if path:
                    path_grouped_objects.setdefault(path, []).append(obj)

            # Create parent-child relationships
            for path, objects in path_grouped_objects.items():
                if len(objects) > 1 and relationships_created < num_relationships:
                    # Pick a random parent
                    parent = random.choice(objects)
                    parent_id = parent.get("ObjectIdentifier")

                    # Relate other objects as children
                    for obj in objects:
                        if obj != parent and relationships_created < num_relationships:
                            child_id = obj.get("ObjectIdentifier")
                            record = self._create_relationship_record_model(
                                source_id=parent_id,
                                target_id=child_id,
                                relationship_type="parent_of",
                                strength=self.relationship_strengths["parent_of"],
                                bidirectional=True,
                                metadata={"parent_path": path}
                            )
                            records.append(record)
                            relationships_created += 1

        # Create semantic relationships
        while relationships_created < num_relationships:
            # Select objects
            source_obj = random.choice(source_objects)
            target_obj = random.choice(target_objects)

            # Skip self-relations unless specifically allowed
            if source_obj == target_obj and not criteria.get("allow_self_relations", False):
                continue

            # Get object IDs
            source_id = source_obj.get("ObjectIdentifier")
            target_id = target_obj.get("ObjectIdentifier")

            # Select relationship category
            category = random.choice(categories)

            # Select relationship type
            if specific_types:
                # Use provided types if available
                relationship_type = random.choice(specific_types)
            else:
                # Select from category
                relationship_type = random.choice(self.relationship_types[category])

            # Get relationship strength
            strength = self.relationship_strengths.get(relationship_type, 0.5)

            # Create the relationship record
            record = self._create_relationship_record_model(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                strength=strength,
                bidirectional=criteria.get("bidirectional", True),
                metadata=self._generate_relationship_metadata(source_obj, target_obj, relationship_type)
            )

            records.append(record)
            relationships_created += 1

        return records

    def _generate_relationship_records(self, count: int, criteria: Dict[str, Any]) -> List[Any]:
        """Generate standalone relationship records.

        Args:
            count: Number of records to generate
            criteria: Criteria for generation

        Returns:
            Generated relationship record models
        """
        records = []

        # Determine relationship categories
        categories = criteria.get("categories", list(self.relationship_types.keys()))
        if isinstance(categories, str):
            categories = [categories]

        # Get specific relationship types if provided
        specific_types = criteria.get("relationship_types", [])

        for _ in range(count):
            # Generate random object IDs
            source_id = criteria.get("source_id", str(uuid.uuid4()))
            target_id = criteria.get("target_id", str(uuid.uuid4()))

            # Skip self-relations unless specifically allowed
            if source_id == target_id and not criteria.get("allow_self_relations", False):
                target_id = str(uuid.uuid4())

            # Select relationship category
            category = random.choice(categories)

            # Select relationship type
            if specific_types:
                # Use provided types if available
                relationship_type = random.choice(specific_types)
            else:
                # Select from category
                relationship_type = random.choice(self.relationship_types[category])

            # Get relationship strength
            strength = self.relationship_strengths.get(relationship_type, 0.5)

            # Adjust strength if specified in criteria
            if "min_strength" in criteria and "max_strength" in criteria:
                min_strength = criteria.get("min_strength")
                max_strength = criteria.get("max_strength")
                strength = min_strength + (max_strength - min_strength) * (strength / 1.0)

            # Create the relationship record
            record = self._create_relationship_record_model(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                strength=strength,
                bidirectional=criteria.get("bidirectional", True),
                metadata={}
            )

            records.append(record)

        return records

    def _create_relationship_record_model(self, source_id: str, target_id: str,
                                        relationship_type: str, strength: float,
                                        bidirectional: bool, metadata: Dict[str, Any]) -> Any:
        """Create a single relationship record model.

        Args:
            source_id: Source object identifier
            target_id: Target object identifier
            relationship_type: Type of relationship
            strength: Relationship strength (0.0 to 1.0)
            bidirectional: Whether to create bidirectional relationship
            metadata: Additional metadata for the relationship

        Returns:
            Relationship record model (IndalekoRelationshipDataModel)
        """
        # Generate a Record object with source identifier
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=uuid.uuid4(),
            Version="1.0",
            Description="Generated relationship by model-based data generator"
        )

        record = self.RecordDataModel(
            SourceIdentifier=source_identifier
        )

        # Create semantic attributes for the relationship
        relationships = []

        # Main relationship attribute
        relationships.append(self.SemanticAttributeDataModel(
            AttributeIdentifier=str(uuid.uuid4()),
            AttributeName=f"RELATIONSHIP_{relationship_type.upper()}",
            AttributeValue="True"
        ))

        # Strength attribute
        relationships.append(self.SemanticAttributeDataModel(
            AttributeIdentifier=str(uuid.uuid4()),
            AttributeName="RELATIONSHIP_STRENGTH",
            AttributeValue=str(strength)
        ))

        # Add timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        created = now - datetime.timedelta(days=random.randint(0, 30))

        relationships.append(self.SemanticAttributeDataModel(
            AttributeIdentifier=str(uuid.uuid4()),
            AttributeName="RELATIONSHIP_CREATED",
            AttributeValue=created.isoformat()
        ))

        # Add metadata attributes
        for key, value in metadata.items():
            relationships.append(self.SemanticAttributeDataModel(
                AttributeIdentifier=str(uuid.uuid4()),
                AttributeName=f"RELATIONSHIP_META_{key.upper()}",
                AttributeValue=str(value)
            ))

        # Create the relationship model
        relationship_model = self.RelationshipDataModel(
            Record=record,
            Objects=(source_id, target_id),
            Relationships=relationships
        )

        # Add extra data for reference (not part of the model's standard fields)
        extra_data = {
            "RelationshipType": relationship_type,
            "Strength": strength,
            "Created": created.isoformat(),
            "Bidirectional": bidirectional
        }

        # Add the reverse relationship info if bidirectional
        if bidirectional and relationship_type in self.bidirectional_relationships:
            extra_data["ReverseRelationship"] = self.bidirectional_relationships[relationship_type]

        # Store additional data in the model's extra fields
        relationship_model.extra = extra_data

        return relationship_model

    def _generate_relationship_metadata(self, source_obj: Dict[str, Any],
                                       target_obj: Dict[str, Any],
                                       relationship_type: str) -> Dict[str, Any]:
        """Generate metadata for a relationship based on object properties.

        Args:
            source_obj: Source object
            target_obj: Target object
            relationship_type: Type of relationship

        Returns:
            Relationship metadata
        """
        metadata = {}

        # Extract relevant properties based on relationship type
        if relationship_type in ["contains", "contained_by", "parent_of", "child_of"]:
            # Hierarchical relationships
            source_path = source_obj.get("Path", "")
            target_path = target_obj.get("Path", "")

            if source_path and target_path:
                metadata["source_path"] = source_path
                metadata["target_path"] = target_path

        elif relationship_type in ["previous_version_of", "next_version_of"]:
            # Version relationships
            source_modified = source_obj.get("Modified", "")
            target_modified = target_obj.get("Modified", "")

            if source_modified and target_modified:
                metadata["source_modified"] = source_modified
                metadata["target_modified"] = target_modified

        elif relationship_type in ["shared_with", "modified_by", "owned_by", "created_by"]:
            # Collaboration relationships
            if random.random() < 0.7:
                users = ["user1@example.com", "john.doe@company.com", "alice.smith@org.net"]
                metadata["user"] = random.choice(users)

                timestamp = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
                metadata["timestamp"] = timestamp.isoformat()

        # Add general metadata that applies to all relationships
        confidence = random.uniform(0.6, 1.0)
        metadata["confidence"] = round(confidence, 2)

        return metadata

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of relationship records to generate",
                            "default": 1
                        },
                        "criteria": {
                            "type": "object",
                            "description": "Criteria for generation",
                            "properties": {
                                "source_objects": {
                                    "type": "array",
                                    "description": "Source objects for relationships",
                                    "items": {
                                        "type": "object"
                                    }
                                },
                                "target_objects": {
                                    "type": "array",
                                    "description": "Target objects for relationships",
                                    "items": {
                                        "type": "object"
                                    }
                                },
                                "categories": {
                                    "type": "array",
                                    "description": "Relationship categories to use",
                                    "items": {
                                        "type": "string",
                                        "enum": ["storage", "collaboration", "semantic", "temporal", "spatial"]
                                    }
                                },
                                "relationship_types": {
                                    "type": "array",
                                    "description": "Specific relationship types to use",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "bidirectional": {
                                    "type": "boolean",
                                    "description": "Whether to create bidirectional relationships",
                                    "default": true
                                },
                                "min_strength": {
                                    "type": "number",
                                    "description": "Minimum relationship strength",
                                    "minimum": 0.0,
                                    "maximum": 1.0
                                },
                                "max_strength": {
                                    "type": "number",
                                    "description": "Maximum relationship strength",
                                    "minimum": 0.0,
                                    "maximum": 1.0
                                },
                                "allow_self_relations": {
                                    "type": "boolean",
                                    "description": "Whether to allow relationships from an object to itself",
                                    "default": false
                                }
                            }
                        }
                    },
                    "required": ["count"]
                }
            }
        }


class MachineConfigGeneratorTool(Tool):
    """Tool for generating realistic machine configuration metadata."""

    def __init__(self):
        """Initialize the machine configuration generator tool."""
        super().__init__(
            name="machine_config_generator",
            description="Generate realistic machine configuration metadata"
        )

        # Import models
        import sys
        import os

        # Setup path for imports
        if os.environ.get("INDALEKO_ROOT") is None:
            current_path = os.path.dirname(os.path.abspath(__file__))
            while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
                current_path = os.path.dirname(current_path)
            os.environ["INDALEKO_ROOT"] = current_path
            sys.path.append(current_path)

        # Import Indaleko data models
        from data_models.record import IndalekoRecordDataModel
        from platforms.data_models.hardware import Hardware
        from platforms.data_models.software import Software
        from platforms.data_models.machine_platform import MachinePlatform

        # Store model classes
        self.RecordDataModel = IndalekoRecordDataModel
        self.Hardware = Hardware
        self.Software = Software
        self.MachinePlatform = MachinePlatform

        # Common CPU architectures
        self.cpu_architectures = {
            "x86_64": 0.70,    # Most common
            "arm64": 0.15,     # Growing in usage
            "i686": 0.05,      # Older 32-bit
            "aarch64": 0.05,   # ARM 64-bit variant
            "ppc64le": 0.02,   # PowerPC
            "s390x": 0.02,     # IBM
            "mips": 0.01       # MIPS
        }

        # Common CPU brands and models
        self.cpu_models = {
            "x86_64": [
                "Intel(R) Core(TM) i9-12900K CPU @ 3.20GHz",
                "Intel(R) Core(TM) i7-11700K CPU @ 3.60GHz",
                "Intel(R) Core(TM) i5-10500 CPU @ 3.10GHz",
                "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz",
                "Intel(R) Xeon(R) E5-2680 v4 @ 2.40GHz",
                "AMD Ryzen 9 5950X 16-Core Processor",
                "AMD Ryzen 7 5800X 8-Core Processor",
                "AMD Ryzen 5 5600X 6-Core Processor",
                "AMD EPYC 7763 64-Core Processor",
                "AMD EPYC 7542 32-Core Processor"
            ],
            "arm64": [
                "Apple M1 Pro",
                "Apple M1 Max",
                "Apple M2",
                "Qualcomm Snapdragon 8 Gen 1",
                "Ampere Altra Q80-30",
                "AWS Graviton3",
                "NVIDIA Carmel"
            ],
            "i686": [
                "Intel(R) Core(TM) i3-3220 CPU @ 3.30GHz",
                "Intel(R) Pentium(R) CPU G4560 @ 3.50GHz",
                "AMD A8-7600 Radeon R7"
            ],
            "aarch64": [
                "ARM Cortex-A76",
                "AWS Graviton2",
                "Huawei Kunpeng 920"
            ],
            "ppc64le": [
                "IBM POWER9",
                "IBM POWER8"
            ],
            "s390x": [
                "IBM z15",
                "IBM z14"
            ],
            "mips": [
                "MIPS R4000",
                "MIPS R10000"
            ]
        }

        # Core and thread counts by CPU model pattern
        self.cpu_cores_threads = {
            "i9": {"cores": (8, 16), "threads": (16, 32)},
            "i7": {"cores": (6, 10), "threads": (12, 20)},
            "i5": {"cores": (4, 8), "threads": (4, 16)},
            "i3": {"cores": (2, 4), "threads": (4, 8)},
            "Xeon": {"cores": (8, 64), "threads": (16, 128)},
            "Ryzen 9": {"cores": (12, 16), "threads": (24, 32)},
            "Ryzen 7": {"cores": (8, 12), "threads": (16, 24)},
            "Ryzen 5": {"cores": (6, 8), "threads": (12, 16)},
            "EPYC": {"cores": (24, 64), "threads": (48, 128)},
            "M1": {"cores": (8, 10), "threads": (8, 10)},
            "M2": {"cores": (8, 12), "threads": (8, 12)},
            "Snapdragon": {"cores": (4, 8), "threads": (4, 8)},
            "Graviton": {"cores": (16, 64), "threads": (16, 64)},
            "POWER": {"cores": (8, 24), "threads": (32, 96)},
            "z1": {"cores": (12, 24), "threads": (24, 48)}
        }

        # Operating systems
        self.operating_systems = {
            "Windows": {
                "versions": [
                    "10 Pro 21H2 (19044.1706)",
                    "10 Enterprise 21H2 (19044.1706)",
                    "11 Pro 21H2 (22000.675)",
                    "11 Enterprise 21H2 (22000.675)",
                    "Server 2019 1809 (17763.2928)",
                    "Server 2022 21H2 (20348.707)"
                ],
                "architecture_match": ["x86_64", "i686"]
            },
            "Linux": {
                "versions": [
                    "5.15.0-1015-aws (Ubuntu 22.04 LTS)",
                    "5.10.109-104.500.amzn2.x86_64 (Amazon Linux 2)",
                    "5.16.11-200.fc35.x86_64 (Fedora 35)",
                    "5.14.21-150400.24.76-default (SUSE Linux Enterprise 15 SP4)",
                    "5.15.0-33-generic (Ubuntu 22.04 LTS)",
                    "4.18.0-372.9.1.el8_6.x86_64 (Red Hat Enterprise Linux 8.6)"
                ],
                "architecture_match": ["x86_64", "i686", "arm64", "aarch64", "ppc64le", "s390x", "mips"]
            },
            "macOS": {
                "versions": [
                    "12.3.1 (21E258) Monterey",
                    "12.4 (21F79) Monterey",
                    "11.6.6 (20G624) Big Sur",
                    "11.7 (20G817) Big Sur",
                    "13.0 (22A5352e) Ventura"
                ],
                "architecture_match": ["x86_64", "arm64"]
            },
            "FreeBSD": {
                "versions": [
                    "13.1-RELEASE",
                    "13.0-RELEASE",
                    "12.3-RELEASE",
                    "12.2-RELEASE"
                ],
                "architecture_match": ["x86_64", "i686", "arm64", "aarch64"]
            }
        }

        # Hostnames
        self.hostname_prefixes = [
            "desktop", "laptop", "server", "workstation",
            "dev", "test", "prod", "web", "db", "app",
            "compute", "vm", "container", "instance"
        ]

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - count: Number of machine configuration records to generate
                - criteria: Optional criteria for generation

        Returns:
            Generated machine configuration metadata
        """
        count = parameters.get("count", 1)
        criteria = parameters.get("criteria", {})

        records = []

        # Generate machine configuration records
        for _ in range(count):
            record = self._generate_machine_config_model(criteria)
            records.append(record)

        self.logger.debug(f"Generated {len(records)} machine configuration records")

        # Return records in dictionary format for compatibility with other tools
        return {
            "records": [record.dict() for record in records],
            "count": len(records)
        }

    def _generate_machine_config_model(self, criteria: Dict[str, Any]) -> Any:
        """Generate a single machine configuration record model.

        Args:
            criteria: Criteria for generation

        Returns:
            Machine configuration record model (MachinePlatform)
        """
        # Set or select CPU architecture
        cpu_architecture = criteria.get("cpu_architecture")
        if not cpu_architecture:
            # Select based on probabilities
            cpu_architecture = random.choices(
                list(self.cpu_architectures.keys()),
                weights=list(self.cpu_architectures.values()),
                k=1
            )[0]

        # Set or select operating system
        os_name = criteria.get("os")
        if not os_name:
            # Filter OS by architecture compatibility
            compatible_os = []
            for os_name, os_data in self.operating_systems.items():
                if cpu_architecture in os_data["architecture_match"]:
                    compatible_os.append(os_name)

            if not compatible_os:
                os_name = "Linux"  # Fallback
            else:
                os_name = random.choice(compatible_os)

        # Select OS version
        os_version = criteria.get("os_version")
        if not os_version:
            # Select random compatible version
            os_version = random.choice(self.operating_systems[os_name]["versions"])

        # Set or select CPU model
        cpu_model = criteria.get("cpu_model")
        if not cpu_model:
            # Select compatible model
            if cpu_architecture in self.cpu_models:
                cpu_model = random.choice(self.cpu_models[cpu_architecture])
            else:
                cpu_model = f"Generic {cpu_architecture} CPU"

        # Determine cores and threads based on CPU model
        cores = criteria.get("cores")
        threads = criteria.get("threads")

        if not cores or not threads:
            # Find matching pattern for CPU model
            core_thread_pattern = None
            for pattern, values in self.cpu_cores_threads.items():
                if pattern in cpu_model:
                    core_thread_pattern = values
                    break

            # Fallback pattern
            if not core_thread_pattern:
                core_thread_pattern = {"cores": (2, 8), "threads": (4, 16)}

            # Generate cores and threads
            if not cores:
                min_cores, max_cores = core_thread_pattern["cores"]
                cores = random.randint(min_cores, max_cores)

            if not threads:
                min_threads, max_threads = core_thread_pattern["threads"]
                # Ensure threads >= cores
                threads = max(cores, random.randint(min_threads, max_threads))

        # Generate hostname
        hostname = criteria.get("hostname")
        if not hostname:
            prefix = random.choice(self.hostname_prefixes)
            suffix = random.randint(1, 999)
            hostname = f"{prefix}-{suffix}"

        # Create hardware configuration
        hardware = self.Hardware(
            CPU=cpu_architecture,
            Version=cpu_model,
            Cores=cores,
            Threads=threads
        )

        # Create software configuration
        software = self.Software(
            OS=os_name,
            Version=os_version,
            Hostname=hostname,
            Architecture=cpu_architecture
        )

        # Create machine configuration model
        machine_model = self.MachinePlatform(
            Hardware=hardware,
            Software=software
        )

        # Add extra data for reference (not part of the model's standard fields)
        extra_data = {
            "Record": {
                "RecordIdentifier": str(uuid.uuid4()),
                "SourceIdentifier": f"machine_config.generator.{uuid.uuid4()}"
            },
            "MachineIdentifier": criteria.get("machine_id", str(uuid.uuid4())),
            "LastUpdated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Add any additional fields from criteria
        for key, value in criteria.items():
            if key not in ["cpu_architecture", "os", "os_version", "cpu_model",
                          "cores", "threads", "hostname", "machine_id"]:
                extra_data[key] = value

        # Just log the extra data since the model doesn't have an extra field
        self.logger.debug(f"Extra machine config data (not used): {extra_data}")

        return machine_model

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of machine configuration records to generate",
                            "default": 1
                        },
                        "criteria": {
                            "type": "object",
                            "description": "Criteria for generation",
                            "properties": {
                                "cpu_architecture": {
                                    "type": "string",
                                    "description": "CPU architecture",
                                    "enum": ["x86_64", "arm64", "i686", "aarch64", "ppc64le", "s390x", "mips"]
                                },
                                "os": {
                                    "type": "string",
                                    "description": "Operating system",
                                    "enum": ["Windows", "Linux", "macOS", "FreeBSD"]
                                },
                                "os_version": {
                                    "type": "string",
                                    "description": "Operating system version"
                                },
                                "cpu_model": {
                                    "type": "string",
                                    "description": "CPU model"
                                },
                                "cores": {
                                    "type": "integer",
                                    "description": "Number of CPU cores",
                                    "minimum": 1
                                },
                                "threads": {
                                    "type": "integer",
                                    "description": "Number of CPU threads",
                                    "minimum": 1
                                },
                                "hostname": {
                                    "type": "string",
                                    "description": "Machine hostname"
                                },
                                "machine_id": {
                                    "type": "string",
                                    "description": "Machine identifier"
                                }
                            }
                        }
                    },
                    "required": ["count"]
                }
            }
        }
