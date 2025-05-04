#!/usr/bin/env python3
"""
Default configuration values for the enhanced data generator.
"""

from typing import Dict, Any

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    # Database connection settings
    "database": {
        "url": "http://localhost:8529",
        "username": "root",
        "password": "",
        "database": "Indaleko",
        "collections": {
            "storage": "Objects",
            "semantic": "SemanticData",
            "activity": "ActivityData",
            "relationship": "Relationships",
            "machine_config": "MachineConfigurations"
        }
    },

    # LLM provider settings
    "llm": {
        "provider": "openai",  # openai, anthropic, mock
        "models": {
            "openai": "gpt-4-turbo",
            "anthropic": "claude-3-opus-20240229"
        },
        "temperature": 0.2,
        "max_tokens": 2000,
        "api_keys": {
            # Will be loaded from environment variables or config file
            "openai": "",
            "anthropic": ""
        }
    },

    # Generation settings
    "generation": {
        "storage_count": 100,
        "semantic_count": 80,  # 80% of storage count
        "activity_count": 50,  # 50% of storage count
        "relationship_count": 150,  # 1.5x storage count
        "machine_config_count": 5,
        "batch_size": 20,  # Process in batches to avoid memory issues
        "direct_generation": False,  # Use LLM by default
        "constraints": {
            "max_file_size": 1024 * 1024 * 100,  # 100 MB
            "max_path_length": 260,  # Windows MAX_PATH
            "max_filename_length": 255,  # Common filesystem limit
        }
    },

    # Truth dataset generation
    "truth": {
        "enabled": False,  # Generate truth records for testing
        "query": "Find all PDF documents related to machine learning that I accessed last week",
        "count": 10,  # Number of truth records to generate
        "marker": "_TRUTH_RECORD_",  # Marker to identify truth records
        "verification": {
            "calculate_metrics": True,  # Calculate precision, recall, F1
            "export_results": True  # Export verification results
        }
    },

    # Execution settings
    "execution": {
        "dry_run": False,  # Don't actually write to database
        "log_level": "info",  # debug, info, warning, error
        "store_artifacts": True,  # Save generation artifacts
        "artifact_path": "./artifacts"
    },

    # Data distributions
    "distributions": {
        "file_types": {
            "document": 0.25,  # Word, PDF, etc.
            "spreadsheet": 0.15,  # Excel, CSV, etc.
            "image": 0.2,  # JPEG, PNG, etc.
            "code": 0.1,  # Python, JS, etc.
            "media": 0.15,  # MP3, MP4, etc.
            "config": 0.05,  # JSON, YAML, etc.
            "archive": 0.05,  # ZIP, TAR, etc.
            "other": 0.05  # Miscellaneous
        },
        "activity_types": {
            "create": 0.2,
            "modify": 0.4,
            "read": 0.3,
            "delete": 0.05,
            "rename": 0.05
        },
        "relationship_types": {
            "CONTAINS": 0.3,
            "IS_CONTAINED_BY": 0.3,
            "DERIVED_FROM": 0.1,
            "MODIFIED_BY": 0.1,
            "ACCESSED_BY": 0.1,
            "CREATED_BY": 0.05,
            "IS_RELATED_TO": 0.05
        }
    }
}
