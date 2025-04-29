#!/usr/bin/env python3
"""
Continuous Learning System for Indaleko Knowledge Base.

This module implements the continuous learning capabilities that enable
the Knowledge Base to automatically learn and improve from:
1. Query results and user interactions
2. Schema changes in the database
3. New collector/recorder registration
4. User feedback and behavior patterns

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

import importlib
import inspect
import logging
import os
import pkgutil
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from archivist.knowledge_base.data_models import (
    FeedbackType,
    KnowledgePatternType,
    LearningEventType,
)
from archivist.knowledge_base.knowledge_manager import KnowledgeBaseManager

# Not using collection_info since it doesn't have the right class
# from data_models.collection_info import CollectionInfo
from data_models.collection_metadata_data_model import (
    IndalekoCollectionMetadataDataModel,
)
from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.i_collections import IndalekoCollections

# pylint: enable=wrong-import-position


class ContinuousLearningSystem:
    """
    System for continuous learning and improvement of the Knowledge Base.

    This class provides the following capabilities:
    1. Automatic learning from query results and user interactions
    2. Schema evolution tracking and migration support
    3. Dynamic discovery of collectors and recorders
    4. Integration with feedback sources across the system
    """

    def __init__(
        self,
        kb_manager: KnowledgeBaseManager | None = None,
        db_config: IndalekoDBConfig | None = None,
        base_path: str | None = None,
        cache_duration: int = 3600,
    ):
        """
        Initialize the continuous learning system.

        Args:
            kb_manager: KnowledgeBaseManager instance or None to create a new one
            db_config: Database configuration
            base_path: Base path for the Indaleko project
            cache_duration: Time in seconds to cache results (default: 1 hour)
        """
        self.logger = logging.getLogger(__name__)
        self.db_config = db_config or IndalekoDBConfig()
        self.kb_manager = kb_manager or KnowledgeBaseManager(self.db_config)
        self.base_path = base_path or os.environ.get(
            "INDALEKO_ROOT",
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ),
        )
        self.cache_duration = cache_duration

        # We don't need a helper class for collection info in this implementation

        # Cache for collector/recorder discovery
        self._collector_cache = []
        self._recorder_cache = []
        self._collection_schema_cache = {}

        # Last time things were updated
        self._last_collector_discovery = None
        self._last_schema_analysis = None

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize the continuous learning system."""
        # Load current collection schemas
        self._load_collection_schemas()

    def _load_collection_schemas(self):
        """Load the current schemas for all collections."""
        try:
            collection = IndalekoCollections.get_collection(
                IndalekoDBCollections.Indaleko_Collection_Metadata,
            )._arangodb_collection

            # Load all collection metadata
            cursor = collection.all()
            for doc in cursor:
                metadata = IndalekoCollectionMetadataDataModel(**doc)
                collection_name = metadata.collection_name
                schema = metadata.schema

                # Store in cache
                self._collection_schema_cache[collection_name] = {
                    "schema": schema,
                    "last_updated": metadata.updated_at,
                    "metadata": metadata,
                }

            self.logger.info(
                f"Loaded schemas for {len(self._collection_schema_cache)} collections",
            )
        except Exception as e:
            self.logger.error(f"Error loading collection schemas: {e!s}")

    def _discover_classes(
        self,
        module_paths: list[str],
        base_class_names: list[str],
    ) -> list[dict[str, Any]]:
        """
        Discover classes of specific types in the given module paths.

        Args:
            module_paths: List of module paths to search
            base_class_names: Names of base classes to look for

        Returns:
            List of discovered classes
        """
        discovered_classes = []

        # Function to check if a class is a subclass of one of the base classes
        def is_subclass_of_interest(cls):
            for base_name in base_class_names:
                if base_name in str(cls.__bases__):
                    return True
            return False

        # Discover modules and classes
        for module_path in module_paths:
            try:
                # Try to import the module
                module = importlib.import_module(module_path)

                # Walk through the module and its submodules
                for _, name, is_pkg in pkgutil.walk_packages(
                    module.__path__,
                    module.__name__ + ".",
                ):
                    try:
                        # Skip __pycache__ directories
                        if "__pycache__" in name:
                            continue

                        # Import the module
                        submodule = importlib.import_module(name)

                        # Get all classes in the module
                        for attr_name in dir(submodule):
                            try:
                                attr = getattr(submodule, attr_name)

                                # Check if it's a class and not imported from elsewhere
                                if inspect.isclass(attr) and attr.__module__ == submodule.__name__:

                                    # Check if it's a class of interest
                                    if is_subclass_of_interest(attr):
                                        discovered_classes.append(
                                            {
                                                "class_name": attr_name,
                                                "module": submodule.__name__,
                                                "path": (
                                                    os.path.abspath(submodule.__file__)
                                                    if hasattr(submodule, "__file__")
                                                    else None
                                                ),
                                                "class": attr,
                                            },
                                        )
                            except (ImportError, AttributeError) as e:
                                self.logger.debug(
                                    f"Error checking attribute {attr_name} in {name}: {e!s}",
                                )
                    except (ImportError, AttributeError) as e:
                        self.logger.debug(f"Error importing {name}: {e!s}")
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Error importing {module_path}: {e!s}")

        return discovered_classes

    def discover_collectors_and_recorders(self, force: bool = False) -> dict[str, Any]:
        """
        Discover all collectors and recorders in the Indaleko project.

        Args:
            force: Force rediscovery even if cache is fresh

        Returns:
            Dictionary with discovery results
        """
        # Check if we need to rediscover
        now = datetime.now(UTC)
        if (
            not force
            and self._last_collector_discovery
            and (now - self._last_collector_discovery).total_seconds() < self.cache_duration
        ):
            return {
                "collectors": self._collector_cache,
                "recorders": self._recorder_cache,
                "total_collectors": (
                    sum(len(collectors) for collectors in self._collector_cache.values())
                    if isinstance(self._collector_cache, dict)
                    else len(self._collector_cache)
                ),
                "total_recorders": (
                    sum(len(recorders) for recorders in self._recorder_cache.values())
                    if isinstance(self._recorder_cache, dict)
                    else len(self._recorder_cache)
                ),
                "from_cache": True,
            }

        # Clear caches
        self._collector_cache = {}
        self._recorder_cache = {}

        # Define the module paths to search for collectors and recorders
        module_paths = [
            "activity.collectors",
            "activity.recorders",
            "semantic.collectors",
            "semantic.recorders",
            "storage.collectors",
            "storage.recorders",
        ]

        # Define base classes to look for
        collector_base_classes = [
            "CollectorBase",
            "SemanticCollectorBase",
            "StorageCollectorBase",
        ]

        recorder_base_classes = [
            "RecorderBase",
            "SemanticRecorderBase",
            "StorageRecorderBase",
        ]

        # Discover collectors and recorders
        collectors = self._discover_classes(module_paths, collector_base_classes)
        recorders = self._discover_classes(module_paths, recorder_base_classes)

        # Group by type
        collector_types = {}
        for collector in collectors:
            module_parts = collector["module"].split(".")
            if len(module_parts) >= 2:
                collector_type = module_parts[1]  # activity, semantic, storage
                if collector_type not in collector_types:
                    collector_types[collector_type] = []
                collector_types[collector_type].append(collector)

        recorder_types = {}
        for recorder in recorders:
            module_parts = recorder["module"].split(".")
            if len(module_parts) >= 2:
                recorder_type = module_parts[1]  # activity, semantic, storage
                if recorder_type not in recorder_types:
                    recorder_types[recorder_type] = []
                recorder_types[recorder_type].append(recorder)

        # Update caches
        self._collector_cache = collector_types
        self._recorder_cache = recorder_types
        self._last_collector_discovery = now

        # Create learning event
        self.kb_manager.record_learning_event(
            event_type=LearningEventType.pattern_discovery,
            source="collector_discovery",
            content={
                "pattern_type": KnowledgePatternType.collector_recorder,
                "pattern_data": {
                    "collector_count": len(collectors),
                    "recorder_count": len(recorders),
                    "collector_types": list(collector_types.keys()),
                    "recorder_types": list(recorder_types.keys()),
                },
            },
            confidence=0.95,
            metadata={
                "discovery_time": now.isoformat(),
                "module_paths_searched": module_paths,
            },
        )

        # Return results
        return {
            "collectors": collector_types,
            "recorders": recorder_types,
            "total_collectors": len(collectors),
            "total_recorders": len(recorders),
            "from_cache": False,
        }

    def analyze_collection_schemas(self, force: bool = False) -> dict[str, Any]:
        """
        Analyze all collection schemas to detect changes and patterns.

        Args:
            force: Force reanalysis even if cache is fresh

        Returns:
            Dictionary with analysis results
        """
        # Check if we need to reanalyze
        now = datetime.now(UTC)
        if (
            not force
            and self._last_schema_analysis
            and (now - self._last_schema_analysis).total_seconds() < self.cache_duration
        ):
            return {
                "status": "cached",
                "last_analysis": self._last_schema_analysis.isoformat(),
                "collections_analyzed": len(self._collection_schema_cache),
                "message": "Using cached schema analysis",
            }

        # Record that we're doing an analysis now
        self._last_schema_analysis = now

        # Reload collection schemas
        self._load_collection_schemas()

        # Track changes detected
        schema_changes = {}
        field_usage_patterns = {}
        type_distributions = {}
        field_types = {}  # Aggregate field types across collections
        required_fields = set()  # Fields that are required in at least one collection

        # Analyze each collection
        for collection_name, data in self._collection_schema_cache.items():
            schema = data.get("schema", {})

            # Skip if no schema
            if not schema:
                continue

            # Get a sample document from the collection
            try:
                sample_doc = self._get_sample_document(collection_name)

                if sample_doc:
                    # Extract fields from schema
                    fields = self._extract_fields_from_schema(schema)
                    if fields:
                        # Detect schema changes
                        changes = self._detect_schema_changes(
                            collection_name,
                            fields,
                            sample_doc,
                        )

                        if changes.get("change_detected", False):
                            schema_changes[collection_name] = changes

                        # Extract field usage patterns
                        field_usage_patterns[collection_name] = self._analyze_field_usage(collection_name, fields)

                        # Calculate type distributions
                        type_distributions[collection_name] = self._calculate_type_distributions(
                            collection_name,
                            fields,
                        )

                        # Update aggregate field types
                        for field_name, field_def in fields.items():
                            field_types[field_name] = field_def.get("type", "any")
                            if field_def.get("required", False):
                                required_fields.add(field_name)
            except Exception as e:
                self.logger.warning(
                    f"Error analyzing collection {collection_name}: {e!s}",
                )

        # Create learning event for schema analysis
        self.kb_manager.record_learning_event(
            event_type=LearningEventType.pattern_discovery,
            source="schema_analysis",
            content={
                "pattern_type": KnowledgePatternType.schema_update,
                "pattern_data": {
                    "schema_changes": schema_changes,
                    "field_usage_patterns": field_usage_patterns,
                    "type_distributions": type_distributions,
                    "field_types": field_types,
                    "required_fields": list(required_fields),
                },
            },
            confidence=0.9,
            metadata={
                "analysis_time": now.isoformat(),
                "collections_analyzed": len(self._collection_schema_cache),
            },
        )

        # Return results
        return {
            "status": "completed",
            "collections": list(self._collection_schema_cache.keys()),
            "collections_analyzed": len(self._collection_schema_cache),
            "schema_changes": schema_changes,
            "field_usage_patterns": field_usage_patterns,
            "type_distributions": type_distributions,
            "field_types": field_types,
            "required_fields": list(required_fields),
        }

    def _get_sample_document(self, collection_name: str) -> dict[str, Any] | None:
        """
        Get a sample document from a collection.

        Args:
            collection_name: The name of the collection

        Returns:
            Sample document or None if collection is empty
        """
        try:
            # Get the collection
            collection = IndalekoCollections.get_collection(
                collection_name,
            )._arangodb_collection

            # Get a sample document
            cursor = collection.all().limit(1)
            if cursor.empty():
                return None

            # Return the document
            return cursor.next()
        except Exception as e:
            self.logger.warning(
                f"Error getting sample document from {collection_name}: {e!s}",
            )
            return None

    def _extract_fields_from_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Extract field definitions from a schema.

        Args:
            schema: The schema to extract fields from

        Returns:
            Dictionary of field definitions
        """
        fields = {}

        # Check if schema has properties
        if "rule" in schema and "properties" in schema["rule"]:
            properties = schema["rule"]["properties"]

            # Extract each property
            for field_name, field_def in properties.items():
                fields[field_name] = {
                    "type": field_def.get("type", "any"),
                    "required": field_name in schema["rule"].get("required", []),
                    "definition": field_def,
                }

        return fields

    def _detect_schema_changes(
        self,
        collection_name: str,
        fields: dict[str, Any],
        sample_doc: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detect changes in a collection schema.

        Args:
            collection_name: The name of the collection
            fields: The fields defined in the schema
            sample_doc: A sample document from the collection

        Returns:
            Dictionary with change detection results
        """
        changes = {
            "collection": collection_name,
            "change_detected": False,
            "new_fields": [],
            "missing_fields": [],
            "type_mismatches": [],
        }

        # Check for fields in the document that aren't in the schema
        for field_name in sample_doc:
            if field_name not in fields and not field_name.startswith("_"):
                changes["new_fields"].append(field_name)
                changes["change_detected"] = True

        # Check for missing required fields
        for field_name, field_def in fields.items():
            if field_def.get("required", False) and field_name not in sample_doc:
                changes["missing_fields"].append(field_name)
                changes["change_detected"] = True

        # Check for type mismatches
        for field_name, field_def in fields.items():
            if field_name in sample_doc:
                field_type = field_def.get("type", "any")
                value = sample_doc[field_name]

                # Check if the value matches the expected type
                if field_type == "string" and not isinstance(value, str):
                    changes["type_mismatches"].append(
                        {
                            "field": field_name,
                            "expected": "string",
                            "actual": type(value).__name__,
                        },
                    )
                    changes["change_detected"] = True
                elif field_type == "number" and not isinstance(value, (int, float)):
                    changes["type_mismatches"].append(
                        {
                            "field": field_name,
                            "expected": "number",
                            "actual": type(value).__name__,
                        },
                    )
                    changes["change_detected"] = True
                elif field_type == "boolean" and not isinstance(value, bool):
                    changes["type_mismatches"].append(
                        {
                            "field": field_name,
                            "expected": "boolean",
                            "actual": type(value).__name__,
                        },
                    )
                    changes["change_detected"] = True
                elif field_type == "array" and not isinstance(value, list):
                    changes["type_mismatches"].append(
                        {
                            "field": field_name,
                            "expected": "array",
                            "actual": type(value).__name__,
                        },
                    )
                    changes["change_detected"] = True
                elif field_type == "object" and not isinstance(value, dict):
                    changes["type_mismatches"].append(
                        {
                            "field": field_name,
                            "expected": "object",
                            "actual": type(value).__name__,
                        },
                    )
                    changes["change_detected"] = True

        # Add a message if changes were detected
        if changes["change_detected"]:
            message_parts = []
            if changes["new_fields"]:
                fields_str = ", ".join(f'"{f}"' for f in changes["new_fields"])
                message_parts.append(f"New field(s) {fields_str} detected")
            if changes["missing_fields"]:
                fields_str = ", ".join(f'"{f}"' for f in changes["missing_fields"])
                message_parts.append(f"Required field(s) {fields_str} missing")
            if changes["type_mismatches"]:
                mismatches = []
                for mismatch in changes["type_mismatches"]:
                    mismatches.append(
                        f'"{mismatch["field"]}" (expected {mismatch["expected"]}, got {mismatch["actual"]})',
                    )
                message_parts.append(
                    f"Type mismatch in field(s): {', '.join(mismatches)}",
                )

            changes["message"] = "; ".join(message_parts)

        return changes

    def _analyze_field_usage(
        self,
        collection_name: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze field usage in a collection.

        Args:
            collection_name: The name of the collection
            fields: The fields to analyze

        Returns:
            Dictionary with field usage statistics
        """
        usage_stats = {}

        try:
            # Get the collection
            collection = IndalekoCollections.get_collection(
                collection_name,
            )._arangodb_collection

            # Count total documents
            total = collection.count()

            if total == 0:
                return {}

            # Analyze each field
            for field_name in fields:
                # Count documents with this field
                query = f"RETURN LENGTH(FOR doc IN {collection_name} FILTER HAS(doc, '{field_name}') RETURN 1)"
                cursor = collection.database.aql.execute(query)
                count = cursor.next() if not cursor.empty() else 0

                # Calculate percentage
                percentage = (count / total) * 100 if total > 0 else 0

                # Store stats
                usage_stats[field_name] = {
                    "count": count,
                    "percentage": percentage,
                    "field_type": fields[field_name].get("type", "any"),
                    "required": fields[field_name].get("required", False),
                }

                # Flag unused required fields
                if fields[field_name].get("required", False) and percentage < 100:
                    usage_stats[field_name]["warning"] = "Required field not present in all documents"

                # Flag rarely used fields
                if percentage < 10 and not fields[field_name].get("required", False):
                    usage_stats[field_name]["warning"] = "Field is rarely used (< 10%)"
        except Exception as e:
            self.logger.warning(
                f"Error analyzing field usage for {collection_name}: {e!s}",
            )

        return usage_stats

    def _calculate_type_distributions(
        self,
        collection_name: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calculate value type distributions for fields.

        Args:
            collection_name: The name of the collection
            fields: The fields to analyze

        Returns:
            Dictionary with type distribution statistics
        """
        type_stats = {}

        try:
            # Get the collection
            collection = IndalekoCollections.get_collection(
                collection_name,
            )._arangodb_collection

            # Analyze a sample of documents
            cursor = collection.all().limit(100)

            # Process documents
            docs = [doc for doc in cursor]
            total = len(docs)

            if total == 0:
                return {}

            # Analyze each field
            for field_name in fields:
                # Initialize type counts
                type_counts = {
                    "null": 0,
                    "boolean": 0,
                    "number": 0,
                    "string": 0,
                    "array": 0,
                    "object": 0,
                    "missing": 0,
                    "other": 0,
                }

                # Count each type
                for doc in docs:
                    if field_name not in doc:
                        type_counts["missing"] += 1
                    else:
                        value = doc[field_name]
                        if value is None:
                            type_counts["null"] += 1
                        elif isinstance(value, bool):
                            type_counts["boolean"] += 1
                        elif isinstance(value, (int, float)):
                            type_counts["number"] += 1
                        elif isinstance(value, str):
                            type_counts["string"] += 1
                        elif isinstance(value, list):
                            type_counts["array"] += 1
                        elif isinstance(value, dict):
                            type_counts["object"] += 1
                        else:
                            type_counts["other"] += 1

                # Calculate percentages
                type_percentages = {t: (count / total) * 100 for t, count in type_counts.items()}

                # Store stats
                type_stats[field_name] = {
                    "counts": type_counts,
                    "percentages": type_percentages,
                    "expected_type": fields[field_name].get("type", "any"),
                }

                # Flag type inconsistencies
                declared_type = fields[field_name].get("type", "any")
                if declared_type != "any":
                    # Check if the actual types match the declared type
                    consistency_issues = []

                    if declared_type == "string" and type_percentages["string"] < 90:
                        consistency_issues.append(
                            "Field is declared as string but contains other types",
                        )
                    elif declared_type == "number" and type_percentages["number"] < 90:
                        consistency_issues.append(
                            "Field is declared as number but contains other types",
                        )
                    elif declared_type == "boolean" and type_percentages["boolean"] < 90:
                        consistency_issues.append(
                            "Field is declared as boolean but contains other types",
                        )
                    elif declared_type == "array" and type_percentages["array"] < 90:
                        consistency_issues.append(
                            "Field is declared as array but contains other types",
                        )
                    elif declared_type == "object" and type_percentages["object"] < 90:
                        consistency_issues.append(
                            "Field is declared as object but contains other types",
                        )

                    if consistency_issues:
                        type_stats[field_name]["consistency_issues"] = consistency_issues
        except Exception as e:
            self.logger.warning(
                f"Error calculating type distributions for {collection_name}: {e!s}",
            )

        return type_stats

    def learn_from_query_results(
        self,
        query_text: str,
        query_results: Any,
        execution_time: float,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Learn from query results to improve future recommendations.

        Args:
            query_text: The query text
            query_results: The query results
            execution_time: The query execution time in seconds
            user_id: The ID of the user who executed the query

        Returns:
            Dictionary with learning results
        """
        # Extract metadata from results
        metadata = self._extract_result_metadata(query_results)
        result_count = metadata.get("count", 0)
        collections = metadata.get("collections", [])
        entities = metadata.get("entities", [])

        # Create the content object
        content = {
            "query": query_text,
            "result_count": result_count,
            "execution_time": execution_time,
            "collections": collections,
            "entities": entities,
            "query_intent": self._infer_query_intent(query_text, query_results),
        }

        # Add sample result for schema learning if available
        first_result = self._get_first_result(query_results)
        if first_result:
            content["first_result"] = first_result

        # Add context for contextual learning
        context = {
            "timestamp": datetime.now(UTC).isoformat(),
            "time_of_day": datetime.now(UTC).hour,
            "day_of_week": datetime.now(UTC).weekday(),
            "user_id": user_id,
        }
        content["context"] = context

        # Record learning event
        event = self.kb_manager.record_learning_event(
            event_type=LearningEventType.query_success,
            source="query_execution",
            content=content,
            confidence=0.9 if result_count > 0 else 0.6,
            metadata={"user_id": user_id, "learning_type": "continuous_query_learning"},
        )

        # Generate knowledge patterns
        patterns = self._generate_patterns_from_query(query_text, content)

        return {
            "event_id": str(event.event_id),
            "patterns": patterns,
            "patterns_generated": len(patterns),
            "learned_from_query": True,
            "result_count": result_count,
            "collections_identified": collections,
        }

    def _extract_result_metadata(self, query_results: Any) -> dict[str, Any]:
        """
        Extract metadata from query results.

        Args:
            query_results: The query results

        Returns:
            Dictionary with metadata
        """
        metadata = {"count": 0, "collections": set(), "entities": set(), "types": {}}

        # Check if results are a list
        if isinstance(query_results, list):
            metadata["count"] = len(query_results)

            # Process each result
            for result in query_results:
                self._process_result_item(result, metadata)
        elif isinstance(query_results, dict):
            # Check if it's a result wrapper
            if "result" in query_results and isinstance(query_results["result"], list):
                metadata["count"] = len(query_results["result"])

                # Process each result in the wrapper
                for result in query_results["result"]:
                    self._process_result_item(result, metadata)
            else:
                # Single result
                metadata["count"] = 1
                self._process_result_item(query_results, metadata)

        # Convert sets to lists for JSON serialization
        metadata["collections"] = list(metadata["collections"])
        metadata["entities"] = list(metadata["entities"])

        return metadata

    def _process_result_item(self, item: Any, metadata: dict[str, Any]) -> None:
        """
        Process a single result item to extract metadata.

        Args:
            item: The result item
            metadata: The metadata dictionary to update
        """
        if not isinstance(item, dict):
            return

        # Try to identify the collection
        if "_id" in item and isinstance(item["_id"], str):
            parts = item["_id"].split("/")
            if len(parts) == 2:
                metadata["collections"].add(parts[0])

        # Try to extract entities
        if "entity_type" in item and "name" in item:
            metadata["entities"].add(item["name"])
        elif "Label" in item:
            metadata["entities"].add(item["Label"])

        # Count value types
        for key, value in item.items():
            if key.startswith("_"):
                continue

            value_type = type(value).__name__
            if value_type not in metadata["types"]:
                metadata["types"][value_type] = 0
            metadata["types"][value_type] += 1

    def _get_first_result(self, query_results: Any) -> dict[str, Any] | None:
        """
        Get the first result from query results.

        Args:
            query_results: The query results

        Returns:
            The first result or None
        """
        if isinstance(query_results, list) and query_results:
            return query_results[0]
        elif isinstance(query_results, dict):
            if "result" in query_results and isinstance(query_results["result"], list) and query_results["result"]:
                return query_results["result"][0]
            elif "_id" in query_results:
                return query_results

        return None

    def _infer_query_intent(self, query_text: str, query_results: Any) -> str:
        """
        Infer the intent of a query based on text and results.

        Args:
            query_text: The query text
            query_results: The query results

        Returns:
            Inferred query intent
        """
        # Simple intent detection based on keywords
        query_lower = query_text.lower()

        if "count" in query_lower and not isinstance(query_results, list):
            return "count"
        elif any(term in query_lower for term in ["find", "search", "locate", "get"]):
            return "search"
        elif any(term in query_lower for term in ["list", "show", "display"]):
            return "list"
        elif any(term in query_lower for term in ["summarize", "summary", "aggregate"]):
            return "summarize"
        elif any(term in query_lower for term in ["related", "connected", "linked"]):
            return "relationship"
        else:
            return "general"

    def _generate_patterns_from_query(
        self,
        query_text: str,
        content: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate knowledge patterns from a query and its results.

        Args:
            query_text: The query text
            content: The content data with results metadata

        Returns:
            List of generated patterns
        """
        patterns = []

        # Generate patterns based on query intent
        intent = content.get("query_intent", "general")

        # Get basic pattern data
        pattern_data = {
            "query_text": query_text,
            "intent": intent,
            "result_count": content.get("result_count", 0),
            "execution_time": content.get("execution_time", 0.0),
            "collections": content.get("collections", []),
            "entities": content.get("entities", []),
        }

        # Only generate patterns for successful queries
        if content.get("result_count", 0) > 0:
            # Generate query pattern
            query_pattern = self.kb_manager.create_knowledge_pattern(
                pattern_type=KnowledgePatternType.query_pattern,
                name=f"Query Pattern: {intent}",
                pattern_data=pattern_data,
                source="query_pattern_generation",
                confidence=0.8,
                metadata={
                    "generation_source": "continuous_learning",
                    "query_text": query_text,
                },
            )

            patterns.append(
                {
                    "pattern_id": str(query_pattern.pattern_id),
                    "type": KnowledgePatternType.query_pattern,
                    "name": query_pattern.name,
                    "confidence": query_pattern.confidence,
                    "pattern_data": pattern_data,
                },
            )

            # If the query involves entities, generate entity patterns
            entities = content.get("entities", [])
            for entity in entities:
                entity_data = {
                    "entity_name": entity,
                    "entity_query": query_text,
                    "collections": content.get("collections", []),
                    "query_success": content.get("result_count", 0) > 0,
                }

                entity_pattern = self.kb_manager.create_knowledge_pattern(
                    pattern_type=KnowledgePatternType.entity_relationship,
                    name=f"Entity Usage: {entity}",
                    pattern_data=entity_data,
                    source="query_entity_extraction",
                    confidence=0.7,
                    metadata={
                        "generation_source": "continuous_learning",
                        "query_text": query_text,
                        "entity": entity,
                    },
                )

                patterns.append(
                    {
                        "pattern_id": str(entity_pattern.pattern_id),
                        "type": KnowledgePatternType.entity_relationship,
                        "name": entity_pattern.name,
                        "confidence": entity_pattern.confidence,
                        "pattern_data": entity_data,
                    },
                )

        return patterns

    def process_user_feedback(
        self,
        feedback_type: FeedbackType,
        feedback_data: dict[str, Any],
        query_id: str | None = None,
        pattern_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process user feedback to improve the knowledge base.

        Args:
            feedback_type: The type of feedback
            feedback_data: Detailed feedback information
            query_id: Associated query ID (optional)
            pattern_id: Pattern being evaluated (optional)
            user_id: User ID (optional)

        Returns:
            Dictionary with feedback processing results
        """
        # Record feedback
        feedback_strength = feedback_data.get("relevance", 0.8)

        feedback = self.kb_manager.record_feedback(
            feedback_type=feedback_type,
            feedback_strength=feedback_strength,
            feedback_data=feedback_data,
            query_id=query_id,
            pattern_id=pattern_id,
            user_id=user_id,
        )

        # Create learning event from feedback
        event = self.kb_manager.record_learning_event(
            event_type=LearningEventType.user_feedback,
            source="feedback_processor",
            content={
                "feedback_type": feedback_type,
                "feedback_strength": feedback_strength,
                "query_id": query_id,
                "pattern_id": pattern_id,
                "user_id": user_id,
                "feedback_data": feedback_data,
            },
            confidence=0.9,  # High confidence because direct user feedback
            metadata={
                "feedback_id": str(feedback.feedback_id),
                "feedback_source": "continuous_learning",
            },
        )

        # Check if we should update any patterns based on this feedback
        updated_patterns = []

        if pattern_id:
            try:
                # The record_feedback method already updates the pattern confidence
                # We can get the updated pattern here
                pattern = self.kb_manager.get_knowledge_pattern(UUID(pattern_id))
                if pattern:
                    updated_patterns.append(
                        {
                            "pattern_id": pattern_id,
                            "new_confidence": pattern.confidence,
                            "usage_count": pattern.usage_count,
                        },
                    )
            except Exception as e:
                self.logger.warning(f"Error updating pattern for feedback: {e!s}")

        # If there's a comment, analyze it for additional insights
        comment = feedback_data.get("comment", "")
        additional_insights = []

        if comment:
            insights = self._extract_insights_from_comment(comment, feedback_type)
            if insights:
                additional_insights.extend(insights)

                # Generate patterns based on insights
                for insight in insights:
                    pattern_data = {
                        "insight_type": insight["type"],
                        "description": insight["description"],
                        "confidence": insight["confidence"],
                        "query_id": query_id,
                        "pattern_id": pattern_id,
                        "feedback_type": feedback_type,
                        "feedback_strength": feedback_strength,
                    }

                    insight_pattern = self.kb_manager.create_knowledge_pattern(
                        pattern_type=KnowledgePatternType.user_preference,
                        name=f"User Preference: {insight['type']}",
                        pattern_data=pattern_data,
                        source="feedback_insight_extraction",
                        confidence=insight["confidence"],
                        metadata={
                            "generation_source": "continuous_learning",
                            "feedback_id": str(feedback.feedback_id),
                            "insight_type": insight["type"],
                        },
                    )

                    updated_patterns.append(
                        {
                            "pattern_id": str(insight_pattern.pattern_id),
                            "type": KnowledgePatternType.user_preference,
                            "name": insight_pattern.name,
                            "confidence": insight_pattern.confidence,
                            "pattern_data": pattern_data,
                        },
                    )

        return {
            "feedback_id": str(feedback.feedback_id),
            "event_id": str(event.event_id),
            "feedback_type": feedback_type,
            "updated_patterns": updated_patterns,
            "patterns": updated_patterns,  # For consistency with other methods
            "additional_insights": additional_insights,
            "processed": True,
        }

    def _extract_insights_from_comment(
        self,
        comment: str,
        feedback_type: FeedbackType,
    ) -> list[dict[str, Any]]:
        """
        Extract additional insights from a feedback comment.

        Args:
            comment: The feedback comment
            feedback_type: The type of feedback

        Returns:
            List of extracted insights
        """
        insights = []

        # Simple keyword-based analysis
        comment_lower = comment.lower()

        # Look for specific issues in negative feedback
        if feedback_type in [
            FeedbackType.explicit_negative,
            FeedbackType.implicit_negative,
        ]:
            if any(term in comment_lower for term in ["slow", "performance", "fast", "time"]):
                insights.append(
                    {
                        "type": "performance_issue",
                        "description": "User reported performance concerns",
                        "confidence": 0.7,
                    },
                )

            if any(term in comment_lower for term in ["wrong", "incorrect", "not right", "unrelated"]):
                insights.append(
                    {
                        "type": "relevance_issue",
                        "description": "User reported relevance issues with results",
                        "confidence": 0.8,
                    },
                )

            if any(term in comment_lower for term in ["missing", "incomplete", "not all", "partial"]):
                insights.append(
                    {
                        "type": "completeness_issue",
                        "description": "User reported incomplete results",
                        "confidence": 0.75,
                    },
                )

        # Look for specific praise in positive feedback
        if feedback_type in [
            FeedbackType.explicit_positive,
            FeedbackType.implicit_positive,
        ]:
            if any(term in comment_lower for term in ["fast", "quick", "speedy", "performance"]):
                insights.append(
                    {
                        "type": "performance_praise",
                        "description": "User praised performance",
                        "confidence": 0.7,
                    },
                )

            if any(term in comment_lower for term in ["accurate", "correct", "exactly", "right", "relevant"]):
                insights.append(
                    {
                        "type": "relevance_praise",
                        "description": "User praised relevance of results",
                        "confidence": 0.8,
                    },
                )

            if any(term in comment_lower for term in ["complete", "comprehensive", "thorough", "all"]):
                insights.append(
                    {
                        "type": "completeness_praise",
                        "description": "User praised completeness of results",
                        "confidence": 0.75,
                    },
                )

            if any(term in comment_lower for term in ["helpful", "useful", "informative"]):
                insights.append(
                    {
                        "type": "helpfulness_praise",
                        "description": "User found results helpful",
                        "confidence": 0.85,
                    },
                )

        return insights

    def detect_collector_changes(self) -> dict[str, Any]:
        """
        Detect changes in the collector/recorder landscape.

        Returns:
            Dictionary with change detection results
        """
        # Get current collectors and recorders
        discovery = self.discover_collectors_and_recorders(force=True)

        # Get patterns reflecting known collectors and recorders
        patterns = self.kb_manager.get_patterns_by_type(
            KnowledgePatternType.collector_recorder,
            min_confidence=0.7,
        )

        # Sort patterns by timestamp to get the most recent one
        if patterns:
            patterns.sort(key=lambda p: p.updated_at, reverse=True)
            latest_pattern = patterns[0]

            # Extract data from the pattern
            pattern_data = latest_pattern.pattern_data
            previous_collector_count = pattern_data.get("collector_count", 0)
            previous_recorder_count = pattern_data.get("recorder_count", 0)
            previous_collector_types = set(pattern_data.get("collector_types", []))
            previous_recorder_types = set(pattern_data.get("recorder_types", []))

            # Compare with current discovery
            current_collector_count = discovery["total_collectors"]
            current_recorder_count = discovery["total_recorders"]
            current_collector_types = set(discovery["collectors"].keys())
            current_recorder_types = set(discovery["recorders"].keys())

            # Detect changes
            new_collector_types = current_collector_types - previous_collector_types
            removed_collector_types = previous_collector_types - current_collector_types
            new_recorder_types = current_recorder_types - previous_recorder_types
            removed_recorder_types = previous_recorder_types - current_recorder_types

            # Check if counts changed
            collector_count_changed = previous_collector_count != current_collector_count
            recorder_count_changed = previous_recorder_count != current_recorder_count

            # Determine if any changes were detected
            change_detected = (
                new_collector_types
                or removed_collector_types
                or new_recorder_types
                or removed_recorder_types
                or collector_count_changed
                or recorder_count_changed
            )

            if change_detected:
                # Create a new pattern to record the changes
                self.kb_manager.create_knowledge_pattern(
                    pattern_type=KnowledgePatternType.collector_recorder,
                    name="Collector/Recorder Change",
                    pattern_data={
                        "collector_count": current_collector_count,
                        "recorder_count": current_recorder_count,
                        "collector_types": list(current_collector_types),
                        "recorder_types": list(current_recorder_types),
                        "new_collector_types": list(new_collector_types),
                        "removed_collector_types": list(removed_collector_types),
                        "new_recorder_types": list(new_recorder_types),
                        "removed_recorder_types": list(removed_recorder_types),
                    },
                    source="collector_change_detection",
                    confidence=0.95,
                    metadata={
                        "detection_time": datetime.now(UTC).isoformat(),
                        "previous_pattern_id": str(latest_pattern.pattern_id),
                    },
                )

            # Return results
            return {
                "status": "updated",
                "collectors": discovery["collectors"],
                "recorders": discovery["recorders"],
                "total_collectors": current_collector_count,
                "total_recorders": current_recorder_count,
                "previous_collector_count": previous_collector_count,
                "previous_recorder_count": previous_recorder_count,
                "previous_collector_types": list(previous_collector_types),
                "previous_recorder_types": list(previous_recorder_types),
                "new_collector_types": list(new_collector_types),
                "removed_collector_types": list(removed_collector_types),
                "new_recorder_types": list(new_recorder_types),
                "removed_recorder_types": list(removed_recorder_types),
                "change_detected": change_detected,
            }
        else:
            # If no patterns exist, this is the first run
            # Create a new pattern to record the initial state
            self.kb_manager.create_knowledge_pattern(
                pattern_type=KnowledgePatternType.collector_recorder,
                name="Collector/Recorder Initial State",
                pattern_data={
                    "collector_count": discovery["total_collectors"],
                    "recorder_count": discovery["total_recorders"],
                    "collector_types": list(discovery["collectors"].keys()),
                    "recorder_types": list(discovery["recorders"].keys()),
                },
                source="collector_discovery",
                confidence=0.95,
                metadata={
                    "discovery_time": datetime.now(UTC).isoformat(),
                    "initial_discovery": True,
                },
            )

            # Return initial results
            return {
                "status": "initial",
                "collectors": discovery["collectors"],
                "recorders": discovery["recorders"],
                "total_collectors": discovery["total_collectors"],
                "total_recorders": discovery["total_recorders"],
                "new_collector_types": list(discovery["collectors"].keys()),
                "new_recorder_types": list(discovery["recorders"].keys()),
                "removed_collector_types": [],
                "removed_recorder_types": [],
                "change_detected": False,
                "message": "Initial collector/recorder discovery",
            }


def main():
    """Test the continuous learning system."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize the system
    learning_system = ContinuousLearningSystem()

    # Discover collectors and recorders
    print("\n--- Discovering Collectors and Recorders ---")
    discovery = learning_system.discover_collectors_and_recorders()
    print(
        f"Found {discovery['total_collectors']} collectors and {discovery['total_recorders']} recorders",
    )

    # Print collector types
    print("\nCollector Types:")
    for collector_type, collectors in discovery["collectors"].items():
        print(f"- {collector_type} ({len(collectors)} collectors)")

    # Print recorder types
    print("\nRecorder Types:")
    for recorder_type, recorders in discovery["recorders"].items():
        print(f"- {recorder_type} ({len(recorders)} recorders)")

    # Analyze collection schemas
    print("\n--- Analyzing Collection Schemas ---")
    schema_analysis = learning_system.analyze_collection_schemas()
    print(f"Analyzed {schema_analysis['collections_analyzed']} collections")

    # Print schema changes if any
    if schema_analysis.get("schema_changes"):
        print("\nSchema Changes Detected:")
        for collection, changes in schema_analysis["schema_changes"].items():
            print(f"- {collection}")
            print(f"  {changes.get('message', 'Changes detected')}")
    else:
        print("No schema changes detected")

    # Simulate learning from a query
    print("\n--- Learning from Sample Query ---")
    query_text = "FOR doc IN Objects FILTER doc.Label LIKE '%test%' RETURN doc"
    query_results = [{"_id": "Objects/123", "Label": "test_file.txt"}]
    execution_time = 0.05

    learning_result = learning_system.learn_from_query_results(
        query_text=query_text,
        query_results=query_results,
        execution_time=execution_time,
    )

    print(f"Learned from query: {learning_result['learned_from_query']}")
    print(f"Generated {learning_result['patterns_generated']} patterns")

    # Simulate user feedback
    print("\n--- Processing User Feedback ---")
    feedback_data = {
        "comment": "These results were exactly what I was looking for!",
        "relevance": 0.9,
        "result_relevance": 0.95,
        "result_completeness": 0.9,
        "interaction": "used_results",
    }

    feedback_result = learning_system.process_user_feedback(
        feedback_type=FeedbackType.explicit_positive,
        feedback_data=feedback_data,
        query_id=learning_result["event_id"],
    )

    print(f"Processed feedback: {feedback_result['processed']}")
    if feedback_result["additional_insights"]:
        print("Additional insights extracted:")
        for insight in feedback_result["additional_insights"]:
            print(f"- {insight['description']} (confidence: {insight['confidence']})")

    # Detect collector changes
    print("\n--- Detecting Collector Changes ---")
    changes = learning_system.detect_collector_changes()

    if changes["status"] == "initial":
        print("Initial collector/recorder detection completed")
    else:
        print(f"Change detected: {changes['change_detected']}")
        if changes["new_collector_types"]:
            print(f"New collector types: {', '.join(changes['new_collector_types'])}")
        if changes["removed_collector_types"]:
            print(
                f"Removed collector types: {', '.join(changes['removed_collector_types'])}",
            )


if __name__ == "__main__":
    main()
