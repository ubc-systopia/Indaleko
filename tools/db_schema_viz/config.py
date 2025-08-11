"""
Configuration module for the Indaleko database schema visualization tool.

This module provides functions to load and save configuration information,
as well as default configuration values.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import logging
import os

from typing import Any


# Default collection groupings, based on the tikz diagram
DEFAULT_GROUPS = {
    "Core Storage": [
        "Objects",
        "SemanticData",
        "NamedEntities",
        "Relationships",
    ],
    "Activity Context": [
        "ActivityContext",
        "TempActivityContext",
        "GeoActivityContext",
        "MusicActivityContext",
        "ActivityProviderData_*",  # Wildcard to match all provider data collections
    ],
    "Entity Equivalence": [
        "EntityEquivalenceGroups",
        "EntityEquivalenceNodes",
        "EntityEquivalenceRelations",
    ],
    "System Management": [
        "QueryHistory",
        "ActivityDataProviders",
        "Services",
        "MachineConfig",
        "Users",
        "IdentityDomains",
        "CollectionMetadata",
    ],
    "Learning & Feedback": [
        "PerformanceData",
        "FeedbackRecords",
        "LearningEvents",
        "KnowledgePatterns",
        "ArchivistMemory",
    ],
}


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file. If None, default configuration is used.

    Returns:
        A dictionary containing the configuration
    """
    if not config_path:
        logging.info("Using default configuration")
        return {"groups": DEFAULT_GROUPS}

    try:
        logging.info(f"Loading configuration from {config_path}")
        with open(config_path) as f:
            config = json.load(f)

        # Ensure the configuration has the expected structure
        if "groups" not in config:
            logging.warning("Configuration file missing 'groups' key, using default groups")
            config["groups"] = DEFAULT_GROUPS

        return config

    except Exception as e:
        logging.exception(f"Error loading configuration from {config_path}: {e}")
        logging.info("Falling back to default configuration")
        return {"groups": DEFAULT_GROUPS}


def save_config(config: dict[str, Any], config_path: str) -> bool:
    """
    Save configuration to a JSON file.

    Args:
        config: The configuration to save
        config_path: Path to save the configuration to

    Returns:
        True if the configuration was saved successfully, False otherwise
    """
    try:
        logging.info(f"Saving configuration to {config_path}")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        return True

    except Exception as e:
        logging.exception(f"Error saving configuration to {config_path}: {e}")
        return False
