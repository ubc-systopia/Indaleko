"""
Enhanced cloud storage activity generator for Indaleko.

This module provides comprehensive cloud storage activity generation,
including Google Drive and Dropbox activities with realistic patterns
and temporal consistency.
"""

import os
import sys
import uuid
import random
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta
import json

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tool interface
from tools.data_generator_enhanced.agents.data_gen.core.tools import Tool

# Import generators
from tools.data_generator_enhanced.agents.data_gen.tools.named_entity_generator import (
    EntityNameGenerator, IndalekoNamedEntityType
)

# Import semantic attribute registry and data models
try:
    # Try to import real registry and data models
    from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
    from data_models.base import IndalekoBaseModel
    from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
    from data_models.i_uuid import IndalekoUUIDDataModel
    from activity.collectors.storage.data_models.storage_activity_data_model import (
        BaseStorageActivityData, CloudStorageActivityData, GoogleDriveStorageActivityData,
        DropboxStorageActivityData, StorageActivityType, StorageItemType, StorageProviderType
    )
    from activity.collectors.storage.semantic_attributes import (
        StorageActivityAttributes, ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE,
        PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE, ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE,
        get_semantic_attributes_for_activity
    )
    from db.db_collections import IndalekoDBCollections
    from db.db_config import IndalekoDBConfig
    HAS_DB = True
except ImportError:
    # Create mock classes for testing
    HAS_DB = False
    
    class SemanticAttributeRegistry:
        """Mock registry for semantic attributes."""
        
        # Common domains for attributes
        DOMAIN_STORAGE = "storage"
        DOMAIN_ACTIVITY = "activity"
        DOMAIN_SEMANTIC = "semantic"
        
        @classmethod
        def get_attribute_id(cls, domain: str, name: str) -> str:
            """Get an attribute ID for a registered attribute."""
            return f"{domain}_{name}_id"
        
        @classmethod
        def get_attribute_name(cls, attribute_id: str) -> str:
            """Get the human-readable name for an attribute ID."""
            return attribute_id.replace("_id", "")
        
        @classmethod
        def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
            """Register an attribute."""
            return cls.get_attribute_id(domain, name)
    
    class IndalekoBaseModel:
        """Mock base model for testing."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self):
            """Convert model to dictionary."""
            return self.__dict__
    
    class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
        """Mock semantic attribute data model for testing."""
        pass
    
    class IndalekoUUIDDataModel(IndalekoBaseModel):
        """Mock UUID data model for testing."""
        pass
    
    class StorageActivityType(str, Enum):
        """Types of storage activities that are tracked across providers."""
        CREATE = "create"
        MODIFY = "modify"
        DELETE = "delete"
        RENAME = "rename"
        MOVE = "move"
        COPY = "copy"
        SECURITY_CHANGE = "security"
        ATTRIBUTE_CHANGE = "attribute"
        SHARE = "share"
        UNSHARE = "unshare"
        READ = "read"
        CLOSE = "close"
        DOWNLOAD = "download"
        UPLOAD = "upload"
        SYNC = "sync"
        VERSION = "version"
        RESTORE = "restore"
        TRASH = "trash"
        OTHER = "other"
    
    class StorageProviderType(str, Enum):
        """Types of storage providers."""
        LOCAL_NTFS = "ntfs"
        DROPBOX = "dropbox"
        ONEDRIVE = "onedrive"
        GOOGLE_DRIVE = "gdrive"
        ICLOUD = "icloud"
        NETWORK_SHARE = "network"
        AWS_S3 = "s3"
        AZURE_BLOB = "azure_blob"
        OTHER = "other"
    
    class StorageItemType(str, Enum):
        """Types of storage items."""
        FILE = "file"
        DIRECTORY = "directory"
        SYMLINK = "symlink"
        SHORTCUT = "shortcut"
        VIRTUAL = "virtual"
        OTHER = "other"
    
    class BaseStorageActivityData(IndalekoBaseModel):
        """Base data model for all storage activity records."""
        activity_id: uuid.UUID = uuid.uuid4()
        timestamp: datetime = datetime.now(timezone.utc)
        activity_type: StorageActivityType = StorageActivityType.CREATE
        item_type: StorageItemType = StorageItemType.FILE
        file_name: str = "test.txt"
        file_path: Optional[str] = None
        file_id: Optional[str] = None
        provider_type: StorageProviderType = StorageProviderType.GOOGLE_DRIVE
        provider_id: uuid.UUID = uuid.uuid4()
        user_id: Optional[str] = None
        user_name: Optional[str] = None
        attributes: Optional[Dict[str, Any]] = None
    
    class CloudStorageActivityData(BaseStorageActivityData):
        """Base model for cloud storage activity data."""
        cloud_item_id: str = "cloud_item_id"
        cloud_parent_id: Optional[str] = None
        shared: Optional[bool] = None
        web_url: Optional[str] = None
        mime_type: Optional[str] = None
        size: Optional[int] = None
        is_directory: bool = False
        created_time: Optional[datetime] = None
        modified_time: Optional[datetime] = None
    
    class GoogleDriveStorageActivityData(CloudStorageActivityData):
        """Google Drive-specific storage activity data."""
        file_id: str = "file_id"
        drive_id: Optional[str] = None
        parents: Optional[List[str]] = None
        spaces: Optional[List[str]] = None
        version: Optional[str] = None
    
    class DropboxStorageActivityData(CloudStorageActivityData):
        """Dropbox-specific storage activity data."""
        dropbox_file_id: str = "dropbox_file_id"
        revision: Optional[str] = None
        shared_folder_id: Optional[str] = None
    
    class StorageActivityAttributes:
        """Mock storage activity attributes."""
        STORAGE_ACTIVITY = uuid.uuid4()
        
        # Activity types
        FILE_CREATE = uuid.uuid4()
        FILE_MODIFY = uuid.uuid4()
        FILE_DELETE = uuid.uuid4()
        FILE_RENAME = uuid.uuid4()
        FILE_MOVE = uuid.uuid4()
        FILE_COPY = uuid.uuid4()
        FILE_SECURITY_CHANGE = uuid.uuid4()
        FILE_ATTRIBUTE_CHANGE = uuid.uuid4()
        FILE_SHARE = uuid.uuid4()
        FILE_UNSHARE = uuid.uuid4()
        FILE_READ = uuid.uuid4()
        FILE_CLOSE = uuid.uuid4()
        FILE_DOWNLOAD = uuid.uuid4()
        FILE_UPLOAD = uuid.uuid4()
        FILE_SYNC = uuid.uuid4()
        FILE_VERSION = uuid.uuid4()
        FILE_RESTORE = uuid.uuid4()
        FILE_TRASH = uuid.uuid4()
        
        # Provider types
        PROVIDER_LOCAL_NTFS = uuid.uuid4()
        PROVIDER_DROPBOX = uuid.uuid4()
        PROVIDER_ONEDRIVE = uuid.uuid4()
        PROVIDER_GOOGLE_DRIVE = uuid.uuid4()
        PROVIDER_ICLOUD = uuid.uuid4()
        PROVIDER_NETWORK_SHARE = uuid.uuid4()
        PROVIDER_S3 = uuid.uuid4()
        PROVIDER_AZURE_BLOB = uuid.uuid4()
        
        # Storage-specific
        STORAGE_NTFS = uuid.uuid4()
        STORAGE_DROPBOX = uuid.uuid4()
        STORAGE_ONEDRIVE = uuid.uuid4()
        STORAGE_GDRIVE = uuid.uuid4()
        STORAGE_ICLOUD = uuid.uuid4()
        STORAGE_SHARED = uuid.uuid4()
        
        # Item types
        ITEM_FILE = uuid.uuid4()
        ITEM_DIRECTORY = uuid.uuid4()
        ITEM_SYMLINK = uuid.uuid4()
        ITEM_SHORTCUT = uuid.uuid4()
        ITEM_VIRTUAL = uuid.uuid4()
        
        # File metadata
        FILE_NAME = uuid.uuid4()
        FILE_PATH = uuid.uuid4()
        FILE_SIZE = uuid.uuid4()
        FILE_CREATION_TIME = uuid.uuid4()
        FILE_MODIFICATION_TIME = uuid.uuid4()
        FILE_ACCESS_TIME = uuid.uuid4()
        FILE_MIME_TYPE = uuid.uuid4()
        FILE_EXTENSION = uuid.uuid4()
    
    # Mock mapping dictionaries
    ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE = {
        StorageActivityType.CREATE: StorageActivityAttributes.FILE_CREATE,
        StorageActivityType.MODIFY: StorageActivityAttributes.FILE_MODIFY,
        StorageActivityType.DELETE: StorageActivityAttributes.FILE_DELETE,
        StorageActivityType.RENAME: StorageActivityAttributes.FILE_RENAME,
        StorageActivityType.MOVE: StorageActivityAttributes.FILE_MOVE,
        StorageActivityType.COPY: StorageActivityAttributes.FILE_COPY,
        StorageActivityType.SECURITY_CHANGE: StorageActivityAttributes.FILE_SECURITY_CHANGE,
        StorageActivityType.ATTRIBUTE_CHANGE: StorageActivityAttributes.FILE_ATTRIBUTE_CHANGE,
        StorageActivityType.SHARE: StorageActivityAttributes.FILE_SHARE,
        StorageActivityType.UNSHARE: StorageActivityAttributes.FILE_UNSHARE,
        StorageActivityType.READ: StorageActivityAttributes.FILE_READ,
        StorageActivityType.CLOSE: StorageActivityAttributes.FILE_CLOSE,
        StorageActivityType.DOWNLOAD: StorageActivityAttributes.FILE_DOWNLOAD,
        StorageActivityType.UPLOAD: StorageActivityAttributes.FILE_UPLOAD,
        StorageActivityType.SYNC: StorageActivityAttributes.FILE_SYNC,
        StorageActivityType.VERSION: StorageActivityAttributes.FILE_VERSION,
        StorageActivityType.RESTORE: StorageActivityAttributes.FILE_RESTORE,
        StorageActivityType.TRASH: StorageActivityAttributes.FILE_TRASH,
    }
    
    PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE = {
        StorageProviderType.LOCAL_NTFS: StorageActivityAttributes.PROVIDER_LOCAL_NTFS,
        StorageProviderType.DROPBOX: StorageActivityAttributes.PROVIDER_DROPBOX,
        StorageProviderType.ONEDRIVE: StorageActivityAttributes.PROVIDER_ONEDRIVE,
        StorageProviderType.GOOGLE_DRIVE: StorageActivityAttributes.PROVIDER_GOOGLE_DRIVE,
        StorageProviderType.ICLOUD: StorageActivityAttributes.PROVIDER_ICLOUD,
        StorageProviderType.NETWORK_SHARE: StorageActivityAttributes.PROVIDER_NETWORK_SHARE,
        StorageProviderType.AWS_S3: StorageActivityAttributes.PROVIDER_S3,
        StorageProviderType.AZURE_BLOB: StorageActivityAttributes.PROVIDER_AZURE_BLOB,
    }
    
    ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE = {
        StorageItemType.FILE: StorageActivityAttributes.ITEM_FILE,
        StorageItemType.DIRECTORY: StorageActivityAttributes.ITEM_DIRECTORY,
        StorageItemType.SYMLINK: StorageActivityAttributes.ITEM_SYMLINK,
        StorageItemType.SHORTCUT: StorageActivityAttributes.ITEM_SHORTCUT,
        StorageItemType.VIRTUAL: StorageActivityAttributes.ITEM_VIRTUAL,
    }
    
    def get_semantic_attributes_for_activity(activity_data: Dict[str, Any]) -> List[IndalekoSemanticAttributeDataModel]:
        """Mock function to get semantic attributes for activity."""
        return []

# Fix missing enum import if needed
if 'Enum' not in globals():
    from enum import Enum


class CloudStorageFileType(str, Enum):
    """Enum for cloud storage file types."""
    
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    FORM = "form"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    PDF = "pdf"
    ARCHIVE = "archive"
    CODE = "code"
    FOLDER = "folder"
    SHORTCUT = "shortcut"
    UNKNOWN = "unknown"


class CloudStorageWorkflowGenerator:
    """Generator for realistic cloud storage workflows."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the workflow generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        self.name_generator = EntityNameGenerator(seed)
        
        # MIME types for different file types
        self.mime_types = {
            CloudStorageFileType.DOCUMENT: [
                "application/vnd.google-apps.document",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain"
            ],
            CloudStorageFileType.SPREADSHEET: [
                "application/vnd.google-apps.spreadsheet",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ],
            CloudStorageFileType.PRESENTATION: [
                "application/vnd.google-apps.presentation",
                "application/vnd.ms-powerpoint",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ],
            CloudStorageFileType.FORM: [
                "application/vnd.google-apps.form"
            ],
            CloudStorageFileType.IMAGE: [
                "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp"
            ],
            CloudStorageFileType.VIDEO: [
                "video/mp4", "video/quicktime", "video/x-matroska", "video/webm"
            ],
            CloudStorageFileType.AUDIO: [
                "audio/mpeg", "audio/mp4", "audio/wav", "audio/x-m4a"
            ],
            CloudStorageFileType.PDF: [
                "application/pdf"
            ],
            CloudStorageFileType.ARCHIVE: [
                "application/zip", "application/x-rar-compressed", "application/x-tar"
            ],
            CloudStorageFileType.CODE: [
                "text/x-python", "text/javascript", "text/html", "text/css", "application/json"
            ],
            CloudStorageFileType.FOLDER: [
                "application/vnd.google-apps.folder",
                "folder/directory"
            ],
            CloudStorageFileType.SHORTCUT: [
                "application/vnd.google-apps.shortcut",
                "application/x-ms-shortcut"
            ]
        }
        
        # File extensions for different file types
        self.file_extensions = {
            CloudStorageFileType.DOCUMENT: ["doc", "docx", "txt", "rtf"],
            CloudStorageFileType.SPREADSHEET: ["xls", "xlsx", "csv"],
            CloudStorageFileType.PRESENTATION: ["ppt", "pptx"],
            CloudStorageFileType.FORM: ["form"],
            CloudStorageFileType.IMAGE: ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
            CloudStorageFileType.VIDEO: ["mp4", "mov", "mkv", "webm"],
            CloudStorageFileType.AUDIO: ["mp3", "m4a", "wav"],
            CloudStorageFileType.PDF: ["pdf"],
            CloudStorageFileType.ARCHIVE: ["zip", "rar", "tar", "gz"],
            CloudStorageFileType.CODE: ["py", "js", "html", "css", "json"]
        }
        
        # Project names and topics for file naming
        self.project_names = [
            "Atlas", "Phoenix", "Voyager", "Horizon", "Nexus", "Odyssey", "Polaris",
            "Quantum", "Sentinel", "Titan", "Aurora", "Cascade", "Ember", "Fusion"
        ]
        
        self.topics = [
            "Marketing", "Finance", "HR", "Product", "Sales", "Engineering", "Design",
            "Research", "Strategy", "Operations", "Legal", "Customer Support"
        ]
        
        # Document types for naming
        self.document_types = [
            "Report", "Proposal", "Plan", "Analysis", "Summary", "Brief", 
            "Presentation", "Spreadsheet", "Budget", "Roadmap", "Survey", "Contract"
        ]
        
        # File size ranges (in bytes) for different file types
        self.file_size_ranges = {
            CloudStorageFileType.DOCUMENT: (10_000, 5_000_000),
            CloudStorageFileType.SPREADSHEET: (20_000, 10_000_000),
            CloudStorageFileType.PRESENTATION: (500_000, 20_000_000),
            CloudStorageFileType.FORM: (5_000, 100_000),
            CloudStorageFileType.IMAGE: (200_000, 5_000_000),
            CloudStorageFileType.VIDEO: (5_000_000, 2_000_000_000),
            CloudStorageFileType.AUDIO: (1_000_000, 50_000_000),
            CloudStorageFileType.PDF: (100_000, 20_000_000),
            CloudStorageFileType.ARCHIVE: (1_000_000, 100_000_000),
            CloudStorageFileType.CODE: (1_000, 500_000)
        }
        
        # Folder structure templates
        self.folder_templates = [
            # Project folder structure
            [
                "Projects/{project}",
                "Projects/{project}/Documentation",
                "Projects/{project}/Resources",
                "Projects/{project}/Meetings",
                "Projects/{project}/Deliverables"
            ],
            # Department folder structure
            [
                "{department}",
                "{department}/Reports",
                "{department}/Templates",
                "{department}/Shared",
                "{department}/Archive"
            ],
            # Personal folder structure
            [
                "Personal",
                "Personal/Documents",
                "Personal/Photos",
                "Personal/Videos",
                "Personal/Finance"
            ]
        ]
    
    def generate_file_name(self, file_type: CloudStorageFileType) -> str:
        """Generate a realistic file name based on file type.
        
        Args:
            file_type: Type of file to generate name for
            
        Returns:
            Generated file name with extension
        """
        if file_type == CloudStorageFileType.FOLDER:
            # Folders don't have extensions
            folder_types = ["Project", "Team", "Department", "Client", "Resources", "Archive"]
            names = [self.random.choice(self.project_names), self.random.choice(self.topics)]
            return f"{self.random.choice(folder_types)} - {self.random.choice(names)}"
        
        # For files, generate a base name and add an extension
        project = self.random.choice(self.project_names)
        topic = self.random.choice(self.topics)
        
        # Different naming patterns based on file type
        if file_type in [CloudStorageFileType.DOCUMENT, CloudStorageFileType.PDF]:
            doc_type = self.random.choice(self.document_types)
            base_name = f"{topic} {doc_type} - {project}"
        
        elif file_type == CloudStorageFileType.SPREADSHEET:
            prefix = self.random.choice(["Budget", "Metrics", "Analysis", "Data", "Tracker"])
            # Add a version or date sometimes
            if self.random.random() < 0.3:
                month = self.random.choice(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
                year = str(datetime.now().year)
                base_name = f"{project} {prefix} {month} {year}"
            else:
                base_name = f"{project} {prefix}"
        
        elif file_type == CloudStorageFileType.PRESENTATION:
            doc_type = self.random.choice(["Presentation", "Slides", "Deck", "Overview", "Update"])
            base_name = f"{project} {doc_type} - {topic}"
        
        elif file_type in [CloudStorageFileType.IMAGE, CloudStorageFileType.VIDEO, CloudStorageFileType.AUDIO]:
            # Media files often have numeric naming
            media_prefix = {
                CloudStorageFileType.IMAGE: ["IMG", "Photo", "Image"],
                CloudStorageFileType.VIDEO: ["VID", "Video", "Recording"],
                CloudStorageFileType.AUDIO: ["Audio", "Recording", "Sound"]
            }.get(file_type, ["File"])
            
            number = str(self.random.randint(1000, 9999))
            prefix = self.random.choice(media_prefix)
            base_name = f"{prefix}_{number}"
        
        elif file_type == CloudStorageFileType.CODE:
            code_types = ["script", "module", "component", "utils", "helpers", "class", "interface"]
            code_type = self.random.choice(code_types)
            base_name = f"{code_type}_{project.lower().replace(' ', '_')}"
        
        else:
            # Generic naming for other file types
            base_name = f"{project} {topic} File"
        
        # Add an extension if the file type has extensions
        if file_type in self.file_extensions:
            extension = self.random.choice(self.file_extensions[file_type])
            return f"{base_name}.{extension}"
        
        return base_name
    
    def generate_mime_type(self, file_type: CloudStorageFileType) -> str:
        """Generate a MIME type for the given file type.
        
        Args:
            file_type: Type of file
            
        Returns:
            MIME type string
        """
        if file_type in self.mime_types:
            return self.random.choice(self.mime_types[file_type])
        return "application/octet-stream"
    
    def generate_file_size(self, file_type: CloudStorageFileType) -> int:
        """Generate a realistic file size for the given file type.
        
        Args:
            file_type: Type of file
            
        Returns:
            File size in bytes
        """
        if file_type == CloudStorageFileType.FOLDER:
            return 0
        
        if file_type in self.file_size_ranges:
            min_size, max_size = self.file_size_ranges[file_type]
            # Use a weighted distribution to favor smaller files
            weight = self.random.random() ** 2  # Square to bias toward smaller files
            return int(min_size + weight * (max_size - min_size))
        
        # Default case
        return self.random.randint(1000, 10_000_000)
    
    def generate_web_url(self, provider_type: StorageProviderType, file_id: str, file_name: str) -> str:
        """Generate a web URL for accessing the file in a browser.
        
        Args:
            provider_type: Cloud provider type
            file_id: File ID
            file_name: File name
            
        Returns:
            Web URL string
        """
        if provider_type == StorageProviderType.GOOGLE_DRIVE:
            return f"https://drive.google.com/file/d/{file_id}/view"
        elif provider_type == StorageProviderType.DROPBOX:
            sanitized_name = file_name.replace(" ", "-").lower()
            return f"https://www.dropbox.com/s/{file_id}/{sanitized_name}"
        return ""
    
    def generate_file_path(self, provider_type: StorageProviderType, folder_structure: List[Dict[str, Any]], file_id: str) -> str:
        """Generate a file path based on the folder structure.
        
        Args:
            provider_type: Cloud provider type
            folder_structure: List of folder data
            file_id: File ID to locate in the structure
            
        Returns:
            File path string
        """
        # Find the file or its parent in the folder structure
        file_item = None
        parent_path = None
        
        for item in folder_structure:
            if item.get("file_id") == file_id:
                file_item = item
                break
            # If this is a parent folder
            elif item.get("item_type") == StorageItemType.DIRECTORY and item.get("children") and file_id in item["children"]:
                parent_path = item.get("path", item.get("file_name", ""))
                break
        
        if file_item and "path" in file_item:
            return file_item["path"]
        
        if parent_path:
            for item in folder_structure:
                if item.get("file_id") == file_id:
                    return f"{parent_path}/{item.get('file_name', '')}"
        
        # Default case if path can't be determined
        return ""
    
    def generate_folder_structure(self, 
                                 provider_type: StorageProviderType, 
                                 user_email: str,
                                 count: int = 10) -> List[Dict[str, Any]]:
        """Generate a realistic folder structure for cloud storage.
        
        Args:
            provider_type: Cloud provider type
            user_email: User email for the owner
            count: Number of files/folders to generate
            
        Returns:
            List of folder/file data dictionaries
        """
        # Start with some template folders
        template = self.random.choice(self.folder_templates)
        folders = []
        
        # Replace placeholders
        project = self.random.choice(self.project_names)
        department = self.random.choice(self.topics)
        
        for folder_template in template:
            folder_path = folder_template.format(project=project, department=department)
            folder_name = folder_path.split("/")[-1]
            
            folder_id = str(uuid.uuid4()).replace("-", "")[:28]
            parent_id = None
            
            # Check if this has a parent folder
            if "/" in folder_path:
                parent_path = "/".join(folder_path.split("/")[:-1])
                # Find the parent folder ID
                for f in folders:
                    if f.get("path") == parent_path:
                        parent_id = f.get("file_id")
                        # Add this folder to parent's children
                        if "children" not in f:
                            f["children"] = []
                        f["children"].append(folder_id)
                        break
            
            folders.append({
                "file_id": folder_id,
                "cloud_item_id": folder_id,
                "file_name": folder_name,
                "path": folder_path,
                "item_type": StorageItemType.DIRECTORY,
                "is_directory": True,
                "provider_type": provider_type,
                "cloud_parent_id": parent_id,
                "children": [],
                "created_time": datetime.now(timezone.utc) - timedelta(days=self.random.randint(30, 365)),
                "modified_time": datetime.now(timezone.utc) - timedelta(days=self.random.randint(0, 30)),
                "shared": False,
                "user_email": user_email,
                "mime_type": self.generate_mime_type(CloudStorageFileType.FOLDER)
            })
        
        # Now generate files and put them in the folders
        remaining_count = count - len(folders)
        
        for _ in range(remaining_count):
            # Choose a random file type
            file_type = self.random.choice(list(CloudStorageFileType))
            if file_type == CloudStorageFileType.FOLDER:
                # Skip folders as we already created the structure
                file_type = self.random.choice([t for t in CloudStorageFileType if t != CloudStorageFileType.FOLDER])
            
            # Generate file properties
            file_name = self.generate_file_name(file_type)
            file_id = str(uuid.uuid4()).replace("-", "")[:28]
            mime_type = self.generate_mime_type(file_type)
            size = self.generate_file_size(file_type)
            
            # Choose a random parent folder
            parent_folder = self.random.choice([f for f in folders if f["item_type"] == StorageItemType.DIRECTORY])
            parent_id = parent_folder["file_id"]
            
            # Add to parent's children
            parent_folder["children"].append(file_id)
            
            # Create file record
            file_path = f"{parent_folder['path']}/{file_name}"
            
            file = {
                "file_id": file_id,
                "cloud_item_id": file_id,
                "file_name": file_name,
                "path": file_path,
                "item_type": StorageItemType.FILE,
                "is_directory": False,
                "provider_type": provider_type,
                "cloud_parent_id": parent_id,
                "created_time": datetime.now(timezone.utc) - timedelta(days=self.random.randint(1, 180)),
                "modified_time": datetime.now(timezone.utc) - timedelta(days=self.random.randint(0, 30)),
                "size": size,
                "shared": self.random.random() < 0.2,  # 20% chance of being shared
                "user_email": user_email,
                "mime_type": mime_type,
                "web_url": self.generate_web_url(provider_type, file_id, file_name)
            }
            
            # For Google Drive, add additional fields
            if provider_type == StorageProviderType.GOOGLE_DRIVE:
                file["drive_id"] = "0ADxkfjd83jfkJDkslf"  # Mock drive ID
                file["spaces"] = ["drive"]
                file["parents"] = [parent_id]
                file["version"] = "1"
            
            # For Dropbox, add additional fields
            elif provider_type == StorageProviderType.DROPBOX:
                file["dropbox_file_id"] = file_id
                file["revision"] = self.random.choice(["1a2b3c4d", "5e6f7g8h", "9i10j11k"])
                if file.get("shared"):
                    file["shared_folder_id"] = parent_id
            
            folders.append(file)
        
        return folders
    
    def generate_activity_sequence(self, 
                                  file_data: Dict[str, Any], 
                                  user_email: str,
                                  start_time: datetime,
                                  end_time: datetime,
                                  count: int = 5) -> List[Dict[str, Any]]:
        """Generate a sequence of activities for a file.
        
        Args:
            file_data: File data dictionary
            user_email: User email for the activities
            start_time: Start time for activity sequence
            end_time: End time for activity sequence
            count: Number of activities to generate
            
        Returns:
            List of activity data dictionaries
        """
        activities = []
        is_directory = file_data.get("is_directory", False)
        provider_type = file_data.get("provider_type", StorageProviderType.GOOGLE_DRIVE)
        
        # Set up the time range
        time_range = (end_time - start_time).total_seconds()
        
        # Determine the file's age relative to the activity range
        file_created = file_data.get("created_time", start_time)
        file_modified = file_data.get("modified_time", end_time)
        
        # Ensure file_created is not after start_time
        if file_created > start_time:
            file_created = start_time - timedelta(days=self.random.randint(1, 10))
        
        # Create the initial creation activity (outside the requested count)
        creation_activity = {
            "activity_id": str(uuid.uuid4()),
            "timestamp": file_created,
            "activity_type": StorageActivityType.CREATE,
            "item_type": StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE,
            "file_name": file_data.get("file_name", ""),
            "file_path": file_data.get("path", ""),
            "file_id": file_data.get("file_id", ""),
            "provider_type": provider_type,
            "provider_id": str(uuid.uuid4()),
            "user_id": user_email,
            "user_name": user_email.split("@")[0].replace(".", " ").title(),
            "cloud_item_id": file_data.get("cloud_item_id", ""),
            "cloud_parent_id": file_data.get("cloud_parent_id", ""),
            "shared": file_data.get("shared", False),
            "web_url": file_data.get("web_url", ""),
            "mime_type": file_data.get("mime_type", ""),
            "size": file_data.get("size", 0),
            "is_directory": is_directory,
            "created_time": file_created,
            "modified_time": file_created
        }
        
        # Add provider-specific fields
        if provider_type == StorageProviderType.GOOGLE_DRIVE:
            creation_activity["drive_id"] = file_data.get("drive_id", "")
            creation_activity["parents"] = file_data.get("parents", [])
            creation_activity["spaces"] = file_data.get("spaces", [])
            creation_activity["version"] = "1"
        elif provider_type == StorageProviderType.DROPBOX:
            creation_activity["dropbox_file_id"] = file_data.get("dropbox_file_id", "")
            creation_activity["revision"] = "1"
            creation_activity["shared_folder_id"] = file_data.get("shared_folder_id", "")
        
        activities.append(creation_activity)
        
        # Generate subsequent activities
        for i in range(count):
            # Calculate activity time
            progress = i / count
            activity_time = start_time + timedelta(seconds=progress * time_range)
            
            # Ensure activities happen in order and after file creation
            activity_time = max(activity_time, file_created + timedelta(minutes=10))
            
            # Choose activity type based on file type and previous activities
            if is_directory:
                # Folders have limited activity types
                activity_types = [
                    StorageActivityType.RENAME,
                    StorageActivityType.SECURITY_CHANGE,
                    StorageActivityType.SHARE,
                    StorageActivityType.UNSHARE
                ]
                # Limit to one rename
                if StorageActivityType.RENAME in [a.get("activity_type") for a in activities]:
                    activity_types.remove(StorageActivityType.RENAME)
            else:
                # Regular files have more activity types
                activity_types = [
                    StorageActivityType.MODIFY,
                    StorageActivityType.RENAME,
                    StorageActivityType.COPY,
                    StorageActivityType.SECURITY_CHANGE,
                    StorageActivityType.ATTRIBUTE_CHANGE,
                    StorageActivityType.SHARE,
                    StorageActivityType.UNSHARE,
                    StorageActivityType.READ,
                    StorageActivityType.DOWNLOAD,
                    StorageActivityType.UPLOAD,
                    StorageActivityType.VERSION
                ]
                # Weight toward more common activities
                weights = [
                    0.3,  # MODIFY
                    0.05,  # RENAME
                    0.05,  # COPY
                    0.05,  # SECURITY_CHANGE
                    0.05,  # ATTRIBUTE_CHANGE
                    0.1,   # SHARE
                    0.05,  # UNSHARE
                    0.2,   # READ
                    0.1,   # DOWNLOAD
                    0.05,  # UPLOAD
                    0.05   # VERSION
                ]
                activity_type = self.random.choices(activity_types, weights=weights, k=1)[0]
            
            if not activity_types:
                # No valid activity types left
                continue
            
            # If no weights were used above, choose randomly
            if 'activity_type' not in locals():
                activity_type = self.random.choice(activity_types)
            
            # Create the activity
            activity = {
                "activity_id": str(uuid.uuid4()),
                "timestamp": activity_time,
                "activity_type": activity_type,
                "item_type": StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE,
                "file_name": file_data.get("file_name", ""),
                "file_path": file_data.get("path", ""),
                "file_id": file_data.get("file_id", ""),
                "provider_type": provider_type,
                "provider_id": creation_activity["provider_id"],
                "user_id": user_email,
                "user_name": creation_activity["user_name"],
                "cloud_item_id": file_data.get("cloud_item_id", ""),
                "cloud_parent_id": file_data.get("cloud_parent_id", ""),
                "shared": file_data.get("shared", False),
                "web_url": file_data.get("web_url", ""),
                "mime_type": file_data.get("mime_type", ""),
                "size": file_data.get("size", 0),
                "is_directory": is_directory,
                "created_time": file_created,
                "modified_time": activity_time
            }
            
            # Add provider-specific fields
            if provider_type == StorageProviderType.GOOGLE_DRIVE:
                activity["drive_id"] = file_data.get("drive_id", "")
                activity["parents"] = file_data.get("parents", [])
                activity["spaces"] = file_data.get("spaces", [])
                
                # Increment version for relevant activity types
                if activity_type in [StorageActivityType.MODIFY, StorageActivityType.VERSION]:
                    latest_version = max(
                        [int(a.get("version", "0")) for a in activities if "version" in a], 
                        default=0
                    )
                    activity["version"] = str(latest_version + 1)
                else:
                    activity["version"] = activities[-1].get("version", "1")
            
            elif provider_type == StorageProviderType.DROPBOX:
                activity["dropbox_file_id"] = file_data.get("dropbox_file_id", "")
                
                # Increment revision for relevant activity types
                if activity_type in [StorageActivityType.MODIFY, StorageActivityType.VERSION]:
                    # Create a new revision ID
                    activity["revision"] = ''.join(self.random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                else:
                    activity["revision"] = activities[-1].get("revision", "1")
                
                activity["shared_folder_id"] = file_data.get("shared_folder_id", "")
            
            # Add activity-specific fields
            if activity_type == StorageActivityType.RENAME:
                previous_name = activity["file_name"]
                activity["previous_file_name"] = previous_name
                
                # Generate a new name
                base_name, *extension = previous_name.split(".")
                if extension:
                    extension = "." + ".".join(extension)
                else:
                    extension = ""
                
                # Common rename patterns
                rename_patterns = [
                    f"{base_name} (Updated){extension}",
                    f"{base_name} (New){extension}",
                    f"{base_name} (Renamed){extension}",
                    f"{base_name} (Copy){extension}",
                    f"{base_name}_v2{extension}",
                    f"{base_name.replace(' ', '_')}{extension}"
                ]
                
                activity["file_name"] = self.random.choice(rename_patterns)
                activity["file_path"] = activity["file_path"].replace(previous_name, activity["file_name"])
            
            elif activity_type == StorageActivityType.SHARE:
                activity["shared"] = True
                # Add more share-specific details here
            
            elif activity_type == StorageActivityType.UNSHARE:
                activity["shared"] = False
                # Add more unshare-specific details here
            
            elif activity_type == StorageActivityType.MODIFY:
                # Increase size slightly for modifications
                if not is_directory:
                    activity["size"] = int(file_data.get("size", 0) * (1 + self.random.uniform(0.01, 0.1)))
            
            activities.append(activity)
        
        # Sort activities by timestamp
        activities.sort(key=lambda a: a["timestamp"])
        
        return activities


class CloudStorageActivityGenerator:
    """Generator for cloud storage activities."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        self.workflow_generator = CloudStorageWorkflowGenerator(seed)
        
        # Provider types supported by this generator
        self.providers = [
            StorageProviderType.GOOGLE_DRIVE,
            StorageProviderType.DROPBOX
        ]
    
    def generate_activities(self, 
                           count: int,
                           user_email: str,
                           start_time: datetime,
                           end_time: datetime,
                           provider_type: Optional[StorageProviderType] = None,
                           calendar_events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate cloud storage activities.
        
        Args:
            count: Number of activities to generate
            user_email: User email for the activities
            start_time: Start time for activity sequence
            end_time: End time for activity sequence
            provider_type: Optional provider type (Google Drive, Dropbox, etc.)
            calendar_events: Optional calendar events to align activities with
            
        Returns:
            Dictionary with generated files and activities
        """
        # Choose provider type if not specified
        if provider_type is None:
            provider_type = self.random.choice(self.providers)
        
        if isinstance(provider_type, str):
            # Convert string to enum if needed
            try:
                provider_type = StorageProviderType(provider_type)
            except (ValueError, TypeError):
                provider_type = StorageProviderType.GOOGLE_DRIVE
        
        # Generate folder structure (files and folders)
        folder_count = max(5, count // 10)  # At least 5 folders
        file_count = count // 2  # Number of files to create
        
        folder_structure = self.workflow_generator.generate_folder_structure(
            provider_type=provider_type,
            user_email=user_email,
            count=folder_count + file_count
        )
        
        # Generate activities for each file and folder
        all_activities = []
        
        # Process each file/folder
        for item in folder_structure:
            # Determine number of activities for this item
            if item.get("is_directory", False):
                # Folders have fewer activities
                item_activity_count = self.random.randint(0, 3)
            else:
                # Files have more activities
                item_activity_count = self.random.randint(1, 10)
            
            # Generate activities for this item
            item_activities = self.workflow_generator.generate_activity_sequence(
                file_data=item,
                user_email=user_email,
                start_time=start_time,
                end_time=end_time,
                count=item_activity_count
            )
            
            all_activities.extend(item_activities)
        
        # If calendar events are provided, align some activities with them
        if calendar_events:
            self._align_with_calendar_events(all_activities, calendar_events, folder_structure)
        
        # Ensure we have the requested number of activities
        if len(all_activities) < count:
            # Generate more activities for random files
            files = [f for f in folder_structure if not f.get("is_directory", False)]
            
            while len(all_activities) < count and files:
                file = self.random.choice(files)
                extra_activities = self.workflow_generator.generate_activity_sequence(
                    file_data=file,
                    user_email=user_email,
                    start_time=start_time,
                    end_time=end_time,
                    count=self.random.randint(1, 3)
                )
                all_activities.extend(extra_activities)
        
        # Sort all activities by timestamp
        all_activities.sort(key=lambda a: a["timestamp"])
        
        # Limit to requested count
        if len(all_activities) > count:
            all_activities = all_activities[:count]
        
        # Add semantic attributes to each activity
        for activity in all_activities:
            activity["SemanticAttributes"] = self._generate_semantic_attributes(activity)
        
        return {
            "files": folder_structure,
            "activities": all_activities,
            "provider_type": provider_type
        }
    
    def _align_with_calendar_events(self, 
                                   activities: List[Dict[str, Any]], 
                                   calendar_events: List[Dict[str, Any]],
                                   folder_structure: List[Dict[str, Any]]) -> None:
        """Align some activities with calendar events for contextual realism.
        
        Args:
            activities: List of activities to modify
            calendar_events: Calendar events to align with
            folder_structure: File and folder structure
            
        This function modifies the activities list in-place.
        """
        # Get non-directory files
        files = [f for f in folder_structure if not f.get("is_directory", False)]
        if not files:
            return
        
        # For each calendar event, consider creating an activity
        for event in calendar_events:
            if self.random.random() < 0.3:  # 30% chance of activity per event
                # Get event times
                try:
                    if isinstance(event["start_time"], str):
                        event_start = datetime.fromisoformat(event["start_time"])
                    else:
                        event_start = event["start_time"]
                    
                    if isinstance(event["end_time"], str):
                        event_end = datetime.fromisoformat(event["end_time"])
                    else:
                        event_end = event["end_time"]
                    
                    # Choose a random time during the event
                    event_duration = (event_end - event_start).total_seconds()
                    activity_time = event_start + timedelta(seconds=self.random.uniform(0, event_duration))
                    
                    # Choose a random file related to the event subject
                    candidates = []
                    for file in files:
                        # Check if file name has any word from event subject
                        if "subject" in event:
                            subject_words = event["subject"].lower().split()
                            file_name = file.get("file_name", "").lower()
                            
                            if any(word in file_name for word in subject_words if len(word) > 3):
                                candidates.append(file)
                    
                    # If no candidates, choose random files
                    if not candidates:
                        # Prefer document-like files
                        document_files = [
                            f for f in files 
                            if f.get("mime_type", "").endswith(("document", "sheet", "presentation", "pdf"))
                        ]
                        
                        if document_files:
                            candidates = document_files
                        else:
                            candidates = files
                    
                    # Choose a random file
                    file = self.random.choice(candidates)
                    
                    # Determine activity type
                    activity_probs = [
                        (StorageActivityType.READ, 0.5),
                        (StorageActivityType.MODIFY, 0.3),
                        (StorageActivityType.SHARE, 0.1),
                        (StorageActivityType.DOWNLOAD, 0.1)
                    ]
                    
                    activity_type = self.random.choices(
                        [a[0] for a in activity_probs],
                        weights=[a[1] for a in activity_probs],
                        k=1
                    )[0]
                    
                    # Create activity
                    activity = {
                        "activity_id": str(uuid.uuid4()),
                        "timestamp": activity_time,
                        "activity_type": activity_type,
                        "item_type": StorageItemType.FILE,
                        "file_name": file.get("file_name", ""),
                        "file_path": file.get("path", ""),
                        "file_id": file.get("file_id", ""),
                        "provider_type": file.get("provider_type", StorageProviderType.GOOGLE_DRIVE),
                        "provider_id": str(uuid.uuid4()),
                        "user_id": file.get("user_email", ""),
                        "user_name": file.get("user_email", "").split("@")[0].replace(".", " ").title(),
                        "cloud_item_id": file.get("cloud_item_id", ""),
                        "cloud_parent_id": file.get("cloud_parent_id", ""),
                        "shared": file.get("shared", False),
                        "web_url": file.get("web_url", ""),
                        "mime_type": file.get("mime_type", ""),
                        "size": file.get("size", 0),
                        "is_directory": False,
                        "created_time": file.get("created_time"),
                        "modified_time": activity_time,
                        "attributes": {
                            "related_calendar_event": event.get("event_id", ""),
                            "event_subject": event.get("subject", "")
                        }
                    }
                    
                    # Add provider-specific fields
                    if file.get("provider_type") == StorageProviderType.GOOGLE_DRIVE:
                        activity["drive_id"] = file.get("drive_id", "")
                        activity["parents"] = file.get("parents", [])
                        activity["spaces"] = file.get("spaces", [])
                        activity["version"] = file.get("version", "1")
                    elif file.get("provider_type") == StorageProviderType.DROPBOX:
                        activity["dropbox_file_id"] = file.get("dropbox_file_id", "")
                        activity["revision"] = file.get("revision", "")
                        activity["shared_folder_id"] = file.get("shared_folder_id", "")
                    
                    # Add to activities list
                    activities.append(activity)
                
                except (KeyError, ValueError, TypeError):
                    # Skip if event times can't be parsed
                    continue
    
    def _generate_semantic_attributes(self, activity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for an activity.
        
        Args:
            activity: Activity data
            
        Returns:
            List of semantic attribute dictionaries
        """
        # Use the real function if available
        if "get_semantic_attributes_for_activity" in globals() and callable(globals()["get_semantic_attributes_for_activity"]):
            try:
                return globals()["get_semantic_attributes_for_activity"](activity)
            except Exception:
                # Fall back to our implementation if the real one fails
                pass
        
        attributes = []
        
        # Add common storage activity attribute
        attributes.append({
            "Identifier": {
                "Identifier": str(StorageActivityAttributes.STORAGE_ACTIVITY),
                "Label": "STORAGE_ACTIVITY"
            },
            "Value": "true"
        })
        
        # Add activity type attribute
        activity_type = activity.get("activity_type")
        if activity_type and activity_type in ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE:
            attributes.append({
                "Identifier": {
                    "Identifier": str(ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE[activity_type]),
                    "Label": f"FILE_{activity_type.upper()}"
                },
                "Value": "true"
            })
        
        # Add provider type attribute
        provider_type = activity.get("provider_type")
        if provider_type and provider_type in PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE:
            attributes.append({
                "Identifier": {
                    "Identifier": str(PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE[provider_type]),
                    "Label": f"PROVIDER_{provider_type.upper()}"
                },
                "Value": "true"
            })
        
        # Add item type attribute
        item_type = activity.get("item_type")
        if item_type and item_type in ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE:
            attributes.append({
                "Identifier": {
                    "Identifier": str(ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE[item_type]),
                    "Label": f"ITEM_{item_type.upper()}"
                },
                "Value": "true"
            })
        
        # Add file name attribute if present
        if activity.get("file_name"):
            attributes.append({
                "Identifier": {
                    "Identifier": str(StorageActivityAttributes.FILE_NAME),
                    "Label": "FILE_NAME"
                },
                "Value": activity["file_name"]
            })
        
        # Add file path attribute if present
        if activity.get("file_path"):
            attributes.append({
                "Identifier": {
                    "Identifier": str(StorageActivityAttributes.FILE_PATH),
                    "Label": "FILE_PATH"
                },
                "Value": activity["file_path"]
            })
        
        # Add file size attribute if present
        if "size" in activity and activity["size"] is not None:
            attributes.append({
                "Identifier": {
                    "Identifier": str(StorageActivityAttributes.FILE_SIZE),
                    "Label": "FILE_SIZE"
                },
                "Value": str(activity["size"])
            })
        
        # Add file mime type attribute if present
        if activity.get("mime_type"):
            attributes.append({
                "Identifier": {
                    "Identifier": str(StorageActivityAttributes.FILE_MIME_TYPE),
                    "Label": "FILE_MIME_TYPE"
                },
                "Value": activity["mime_type"]
            })
        
        # Add file extension attribute if present
        if "file_name" in activity and activity["file_name"] and "." in activity["file_name"]:
            extension = activity["file_name"].split(".")[-1].lower()
            attributes.append({
                "Identifier": {
                    "Identifier": str(StorageActivityAttributes.FILE_EXTENSION),
                    "Label": "FILE_EXTENSION"
                },
                "Value": extension
            })
        
        # Add timestamp related attributes
        for time_field, attr in [
            ("timestamp", "ACTIVITY_TIME"),
            ("created_time", "FILE_CREATION_TIME"),
            ("modified_time", "FILE_MODIFICATION_TIME")
        ]:
            if time_field in activity and activity[time_field]:
                time_value = activity[time_field]
                if isinstance(time_value, datetime):
                    time_str = time_value.isoformat()
                else:
                    time_str = str(time_value)
                
                # For demonstration only - real code would use the actual attribute IDs
                attr_id = None
                if attr == "FILE_CREATION_TIME":
                    attr_id = StorageActivityAttributes.FILE_CREATION_TIME
                elif attr == "FILE_MODIFICATION_TIME":
                    attr_id = StorageActivityAttributes.FILE_MODIFICATION_TIME
                
                if attr_id:
                    attributes.append({
                        "Identifier": {
                            "Identifier": str(attr_id),
                            "Label": attr
                        },
                        "Value": time_str
                    })
        
        return attributes


class CloudStorageActivityGeneratorTool(Tool):
    """Tool to generate realistic cloud storage activities."""
    
    def __init__(self):
        """Initialize the cloud storage activity generator tool."""
        super().__init__(name="cloud_storage_generator", description="Generates realistic cloud storage activities")
        
        # Create the activity generator
        self.generator = CloudStorageActivityGenerator()
        
        # Initialize database connection if available
        self.db_config = None
        self.db = None
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                self.db = self.db_config.db
            except Exception:
                pass
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the cloud storage activity generator tool.
        
        Args:
            params: Parameters for execution
                count: Number of activities to generate
                criteria: Criteria for generation
                    user_email: User email
                    start_time: Optional start time for activity range
                    end_time: Optional end time for activity range
                    provider_type: Optional provider type (google_drive or dropbox)
                    calendar_events: Optional calendar events to align with
                    
        Returns:
            Dictionary with generated activities
        """
        count = params.get("count", 50)
        criteria = params.get("criteria", {})
        
        user_email = criteria.get("user_email", "user@example.com")
        
        # Default time range: last 90 days to current time
        now = datetime.now(timezone.utc)
        start_time = criteria.get("start_time", now - timedelta(days=90))
        end_time = criteria.get("end_time", now)
        
        # Convert timestamps to datetime if needed
        if isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time, timezone.utc)
        if isinstance(end_time, (int, float)):
            end_time = datetime.fromtimestamp(end_time, timezone.utc)
            
        provider_type = criteria.get("provider_type")
        calendar_events = criteria.get("calendar_events", [])
        
        # Generate activities
        result = self.generator.generate_activities(
            count=count,
            user_email=user_email,
            start_time=start_time,
            end_time=end_time,
            provider_type=provider_type,
            calendar_events=calendar_events
        )
        
        # Store in database if available
        if HAS_DB and self.db:
            self._store_activities(result["activities"])
        
        return result
    
    def _store_activities(self, activities: List[Dict[str, Any]]) -> bool:
        """Store activities in the database.
        
        Args:
            activities: List of activities to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
            
        try:
            # Define collection name for cloud storage activities
            provider_type = activities[0].get("provider_type") if activities else None
            
            if provider_type == StorageProviderType.GOOGLE_DRIVE:
                collection_name = IndalekoDBCollections.Indaleko_GoogleDriveActivity_Collection
            elif provider_type == StorageProviderType.DROPBOX:
                collection_name = IndalekoDBCollections.Indaleko_DropboxActivity_Collection
            else:
                collection_name = "CloudStorageActivities"
            
            # Check if collection exists, create if not
            if not self.db.has_collection(collection_name):
                self.db.create_collection(collection_name)
            
            # Get the collection
            collection = self.db.collection(collection_name)
            
            # Insert activities in batches
            batch_size = 20
            for i in range(0, len(activities), batch_size):
                batch = activities[i:i+batch_size]
                
                # Convert to JSON serializable format
                batch_json = []
                for activity in batch:
                    # Convert datetime objects to ISO format strings
                    activity_copy = activity.copy()
                    for key, value in activity_copy.items():
                        if isinstance(value, datetime):
                            activity_copy[key] = value.isoformat()
                    batch_json.append(activity_copy)
                
                collection.import_bulk(batch_json)
            
            return True
        except Exception:
            return False


if __name__ == "__main__":
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Simple test
    tool = CloudStorageActivityGeneratorTool()
    
    result = tool.execute({
        "count": 10,
        "criteria": {
            "user_email": "test.user@example.com",
            "provider_type": "google_drive"
        }
    })
    
    # Print sample activity
    if result["activities"]:
        sample = result["activities"][0].copy()
        
        if "SemanticAttributes" in sample:
            sample["SemanticAttributes"] = f"[{len(sample['SemanticAttributes'])} attributes]"
        
        print(json.dumps(sample, indent=2, default=str))