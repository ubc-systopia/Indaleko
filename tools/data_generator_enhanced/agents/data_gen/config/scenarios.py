#!/usr/bin/env python3
"""
Predefined generation scenarios for the enhanced data generator.
"""

from typing import Dict, Any

# Predefined generation scenarios
SCENARIOS: Dict[str, Dict[str, Any]] = {
    # Basic scenario with small dataset for quick testing
    "basic": {
        "description": "Small dataset for quick testing",
        "storage_count": 50,
        "semantic_count": 40,
        "activity_count": 25,
        "relationship_count": 75,
        "machine_config_count": 2,
        "distributions": {
            "file_types": {
                "document": 0.3,
                "spreadsheet": 0.2,
                "image": 0.2,
                "code": 0.1,
                "media": 0.1,
                "other": 0.1
            }
        }
    },
    
    # Medium-sized realistic dataset
    "realistic": {
        "description": "Medium-sized realistic dataset with balanced distribution",
        "storage_count": 500,
        "semantic_count": 400,
        "activity_count": 300,
        "relationship_count": 800,
        "machine_config_count": 5,
        "distributions": {
            "file_types": {
                "document": 0.25,
                "spreadsheet": 0.15,
                "image": 0.2,
                "code": 0.1,
                "media": 0.15,
                "config": 0.05,
                "archive": 0.05,
                "other": 0.05
            }
        }
    },
    
    # Large dataset for performance testing
    "large": {
        "description": "Large dataset for performance testing",
        "storage_count": 5000,
        "semantic_count": 4000,
        "activity_count": 3000,
        "relationship_count": 8000,
        "machine_config_count": 10,
        "execution": {
            "batch_size": 100  # Process in larger batches
        }
    },
    
    # Dataset focused on document search testing
    "document_focused": {
        "description": "Dataset focused on document formats for content search testing",
        "storage_count": 300,
        "semantic_count": 280,
        "activity_count": 150,
        "relationship_count": 450,
        "machine_config_count": 3,
        "distributions": {
            "file_types": {
                "document": 0.6,  # Heavy emphasis on documents
                "spreadsheet": 0.2,
                "image": 0.05,
                "code": 0.05,
                "media": 0.05,
                "other": 0.05
            }
        },
        "truth": {
            "enabled": True,
            "query": "Find all PDF files containing information about climate change",
            "count": 15
        }
    },
    
    # Dataset focused on activity and relationship testing
    "activity_focused": {
        "description": "Dataset focused on activity patterns for temporal query testing",
        "storage_count": 200,
        "semantic_count": 160,
        "activity_count": 300,  # More activities than storage records
        "relationship_count": 500,
        "machine_config_count": 4,
        "distributions": {
            "activity_types": {
                "create": 0.15,
                "modify": 0.4,
                "read": 0.35,
                "delete": 0.05,
                "rename": 0.05
            }
        },
        "truth": {
            "enabled": True,
            "query": "Find all files I worked on yesterday afternoon across all my devices",
            "count": 15
        }
    },
    
    # Dataset simulating a multi-device user environment
    "multi_device": {
        "description": "Dataset simulating usage across multiple devices (desktop, laptop, mobile)",
        "storage_count": 400,
        "semantic_count": 320,
        "activity_count": 250,
        "relationship_count": 600,
        "machine_config_count": 8,  # More device configurations
        "truth": {
            "enabled": True,
            "query": "Find the document I started on my laptop and finished on my desktop",
            "count": 10
        }
    },
    
    # Dataset for testing cross-object relationships
    "relationship_focused": {
        "description": "Dataset with complex object relationships for graph query testing",
        "storage_count": 250,
        "semantic_count": 200,
        "activity_count": 150,
        "relationship_count": 800,  # Many more relationships
        "machine_config_count": 3,
        "distributions": {
            "relationship_types": {
                "CONTAINS": 0.2,
                "IS_CONTAINED_BY": 0.2,
                "DERIVED_FROM": 0.2,
                "MODIFIED_BY": 0.2,
                "ACCESSED_BY": 0.1,
                "CREATED_BY": 0.05,
                "IS_RELATED_TO": 0.05
            }
        },
        "truth": {
            "enabled": True,
            "query": "Find all documents that were derived from the quarterly report",
            "count": 15
        }
    },
    
    # Minimal dataset for quick development testing
    "minimal": {
        "description": "Minimal dataset for quick development testing",
        "storage_count": 10,
        "semantic_count": 8,
        "activity_count": 5,
        "relationship_count": 15,
        "machine_config_count": 1,
        "generation": {
            "direct_generation": True  # Skip LLM to speed up generation
        }
    }
}