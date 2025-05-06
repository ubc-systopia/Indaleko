"""
Data generation controller.

This module provides the main controller for coordinating
the data generation process across different domain agents.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections

from .llm import LLMProvider, OpenAIProvider, AnthropicProvider
from .tools import ToolRegistry
from ..tools.db import DatabaseQueryTool, DatabaseInsertTool, DatabaseBulkInsertTool
from ..tools.stats import StatisticalDistributionTool, FileMetadataGeneratorTool
from ..agents.storage import StorageGeneratorAgent
from ..agents.semantic import SemanticGeneratorAgent
from ..agents.activity import ActivityGeneratorAgent
from ..agents.relationship import RelationshipGeneratorAgent
from ..agents.machine_config import MachineConfigGeneratorAgent


class GenerationController:
    """Main controller for the data generation process."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the data generation controller.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize database configuration
        self.logger.info("Initializing database connection")
        self.db_config = IndalekoDBConfig()

        # Initialize LLM provider
        self.logger.info("Initializing LLM provider")
        self.llm = self._initialize_llm_provider()

        # Initialize tool registry
        self.logger.info("Initializing tool registry")
        self.tool_registry = ToolRegistry()
        self._register_tools()

        # Initialize agents
        self.logger.info("Initializing domain agents")
        self.agents = {}
        self._initialize_agents()

        # Statistics and reporting
        self.stats = {}
        self.truth_records = {}

        self.logger.info("Generation controller initialized")

    def _initialize_llm_provider(self) -> LLMProvider:
        """Initialize the appropriate LLM provider based on configuration.

        Returns:
            Initialized LLM provider
        """
        provider_name = self.config.get("llm_provider", "openai")
        self.logger.info(f"Using LLM provider: {provider_name}")

        if provider_name.lower() == "anthropic":
            anthropic_config = self.config.get("anthropic_config", {})
            return AnthropicProvider(anthropic_config)
        else:  # Default to OpenAI
            openai_config = self.config.get("openai_config", {})
            return OpenAIProvider(openai_config)

    def _register_tools(self) -> None:
        """Register all tools with the registry."""
        # Database tools
        self.tool_registry.register_tool(DatabaseQueryTool(self.db_config))
        self.tool_registry.register_tool(DatabaseInsertTool(self.db_config))
        self.tool_registry.register_tool(DatabaseBulkInsertTool(self.db_config))

        # Statistical tools
        self.tool_registry.register_tool(StatisticalDistributionTool())

        # Import all our model-based generator tools
        from ..tools.stats import (
            FileMetadataGeneratorTool,
            ActivityGeneratorTool,
            RelationshipGeneratorTool,
            SemanticMetadataGeneratorTool,
            MachineConfigGeneratorTool
        )

        # Register model-based generator tools
        self.tool_registry.register_tool(FileMetadataGeneratorTool())
        self.tool_registry.register_tool(ActivityGeneratorTool())
        self.tool_registry.register_tool(RelationshipGeneratorTool())
        self.tool_registry.register_tool(SemanticMetadataGeneratorTool())
        self.tool_registry.register_tool(MachineConfigGeneratorTool())

        self.logger.info(f"Registered {len(self.tool_registry.get_all_tools())} tools")

    def _initialize_agents(self) -> None:
        """Initialize all domain agents."""
        # Storage agent
        self.agents["storage"] = StorageGeneratorAgent(
            self.llm,
            self.tool_registry,
            self.config.get("storage_config", {})
        )

        # Semantic agent
        self.agents["semantic"] = SemanticGeneratorAgent(
            self.llm,
            self.tool_registry,
            self.config.get("semantic_config", {})
        )

        # Activity agent
        self.agents["activity"] = ActivityGeneratorAgent(
            self.llm,
            self.tool_registry,
            self.config.get("activity_config", {})
        )

        # Relationship agent
        self.agents["relationship"] = RelationshipGeneratorAgent(
            self.llm,
            self.tool_registry,
            self.config.get("relationship_config", {})
        )

        # Machine configuration agent
        self.agents["machine_config"] = MachineConfigGeneratorAgent(
            self.llm,
            self.tool_registry,
            self.config.get("machine_config_config", {})
        )

        # Initialize each agent
        for name, agent in self.agents.items():
            agent.initialize()

        self.logger.info(f"Initialized {len(self.agents)} domain agents")

    def generate_dataset(self, scenario: Optional[str] = None) -> Dict[str, Any]:
        """Generate a complete dataset according to the scenario.

        Args:
            scenario: Optional scenario name from configuration

        Returns:
            Generation statistics
        """
        # Get scenario configuration
        scenario_config = self._get_scenario_config(scenario)
        if not scenario_config:
            self.logger.warning(f"Scenario '{scenario}' not found, using default")
            scenario_config = {}

        self.logger.info(f"Starting dataset generation for scenario: {scenario or 'default'}")
        start_time = time.time()

        # Get generation counts
        storage_count = scenario_config.get("storage_count", 100)
        semantic_count = scenario_config.get("semantic_count", int(storage_count * 0.8))
        activity_count = scenario_config.get("activity_count", int(storage_count * 0.5))
        relationship_count = scenario_config.get("relationship_count", int(storage_count * 1.5))
        machine_config_count = scenario_config.get("machine_config_count", 5)

        # Phase 1: Generate machine configurations
        self.logger.info("Phase 1: Generating machine configurations")
        machine_configs = self._generate_machine_configs(machine_config_count, scenario_config)

        # Phase 2: Generate storage objects
        self.logger.info("Phase 2: Generating storage objects")
        storage_objects = self._generate_storage_objects(storage_count, scenario_config, machine_configs)

        # Phase 3: Generate semantic metadata
        self.logger.info("Phase 3: Generating semantic metadata")
        semantic_objects = self._generate_semantic_objects(semantic_count, scenario_config, storage_objects)

        # Phase 4: Generate activity metadata
        self.logger.info("Phase 4: Generating activity metadata")
        activity_objects = self._generate_activity_objects(activity_count, scenario_config, storage_objects, machine_configs)

        # Phase 5: Generate relationships
        self.logger.info("Phase 5: Generating relationships")
        relationships = self._generate_relationships(relationship_count, scenario_config,
                                                   storage_objects, semantic_objects, activity_objects)

        # Calculate statistics
        end_time = time.time()
        elapsed_time = end_time - start_time

        self.stats = {
            "scenario": scenario or "default",
            "timestamp": datetime.now().isoformat(),
            "elapsed_time": elapsed_time,
            "counts": {
                "storage": len(storage_objects),
                "semantic": len(semantic_objects),
                "activity": len(activity_objects),
                "relationship": len(relationships),
                "machine_config": len(machine_configs),
                "total": (len(storage_objects) + len(semantic_objects) +
                         len(activity_objects) + len(relationships) +
                         len(machine_configs))
            }
        }

        self.logger.info(f"Dataset generation complete in {elapsed_time:.2f}s")
        self.logger.info(f"Generated {self.stats['counts']['total']} total records")

        return self.stats

    def generate_truth_dataset(self, scenario: Optional[str] = None) -> Dict[str, Any]:
        """Generate truth data for testing specific queries.

        Args:
            scenario: Optional scenario name from configuration

        Returns:
            Truth generation statistics
        """
        # Get scenario configuration
        scenario_config = self._get_scenario_config(scenario)
        if not scenario_config:
            self.logger.warning(f"Scenario '{scenario}' not found, using default")
            scenario_config = {}

        truth_criteria = scenario_config.get("truth_criteria", {})
        if not truth_criteria:
            self.logger.warning("No truth criteria found in scenario, using defaults")
            truth_criteria = {
                "storage": {"extension": ".pdf", "name_pattern": "Report%"},
                "semantic": {"mime_type": "application/pdf", "content_category": "document"},
                "activity": {"activity_type": "FileAccess", "days_ago": 5},
                "machine_config": {"device_type": "laptop", "os_name": "Windows"}
            }

        self.logger.info(f"Starting truth dataset generation for scenario: {scenario or 'default'}")
        start_time = time.time()

        # Get truth counts
        storage_truth_count = scenario_config.get("storage_truth_count", 10)
        semantic_truth_count = scenario_config.get("semantic_truth_count", storage_truth_count)
        activity_truth_count = scenario_config.get("activity_truth_count", storage_truth_count)
        machine_config_truth_count = scenario_config.get("machine_config_truth_count", 3)

        # Step 1: Generate machine configuration truth records
        self.logger.info("Step 1: Generating machine configuration truth records")
        machine_config_truth = self._generate_machine_config_truth(
            machine_config_truth_count,
            truth_criteria.get("machine_config", {})
        )

        # Step 2: Generate storage truth records
        self.logger.info("Step 2: Generating storage truth records")
        storage_truth = self._generate_storage_truth(
            storage_truth_count,
            truth_criteria.get("storage", {}),
            machine_config_truth
        )

        # Step 3: Generate semantic truth records
        self.logger.info("Step 3: Generating semantic truth records")
        semantic_truth = self._generate_semantic_truth(
            semantic_truth_count,
            truth_criteria.get("semantic", {}),
            storage_truth
        )

        # Step 4: Generate activity truth records
        self.logger.info("Step 4: Generating activity truth records")
        activity_truth = self._generate_activity_truth(
            activity_truth_count,
            truth_criteria.get("activity", {}),
            storage_truth,
            machine_config_truth
        )

        # Step 5: Generate relationship truth records
        self.logger.info("Step 5: Generating relationship truth records")
        relationship_truth = self._generate_relationship_truth(
            truth_criteria.get("relationship", {}),
            storage_truth,
            semantic_truth,
            activity_truth
        )

        # Store truth records
        self.truth_records = {
            "storage": storage_truth,
            "semantic": semantic_truth,
            "activity": activity_truth,
            "relationship": relationship_truth,
            "machine_config": machine_config_truth
        }

        # Calculate statistics
        end_time = time.time()
        elapsed_time = end_time - start_time

        truth_stats = {
            "scenario": scenario or "default",
            "timestamp": datetime.now().isoformat(),
            "elapsed_time": elapsed_time,
            "counts": {
                "storage": len(storage_truth),
                "semantic": len(semantic_truth),
                "activity": len(activity_truth),
                "relationship": len(relationship_truth),
                "machine_config": len(machine_config_truth),
                "total": (len(storage_truth) + len(semantic_truth) +
                         len(activity_truth) + len(relationship_truth) +
                         len(machine_config_truth))
            }
        }

        self.logger.info(f"Truth dataset generation complete in {elapsed_time:.2f}s")
        self.logger.info(f"Generated {truth_stats['counts']['total']} total truth records")

        return truth_stats

    def _get_scenario_config(self, scenario: Optional[str]) -> Dict[str, Any]:
        """Get the configuration for a given scenario.

        Args:
            scenario: Scenario name

        Returns:
            Scenario configuration
        """
        if not scenario:
            return self.config.get("default_scenario", {})

        scenarios = self.config.get("scenarios", {})
        return scenarios.get(scenario, {})

    def _generate_machine_configs(self, count: int, scenario_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate machine configuration records.

        Args:
            count: Number of records to generate
            scenario_config: Scenario configuration

        Returns:
            Generated machine configuration records
        """
        if count <= 0:
            self.logger.info("Skipping machine configuration generation (count is 0)")
            return []

        agent = self.agents["machine_config"]
        criteria = scenario_config.get("machine_config_criteria", {})

        self.logger.info(f"Generating {count} machine configurations with criteria: {criteria}")
        machine_configs = agent.generate(count, criteria)

        self.logger.info(f"Generated {len(machine_configs)} machine configurations")
        return machine_configs

    def _generate_storage_objects(self, count: int, scenario_config: Dict[str, Any],
                               machine_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate storage objects.

        Args:
            count: Number of records to generate
            scenario_config: Scenario configuration
            machine_configs: Generated machine configurations

        Returns:
            Generated storage objects
        """
        if count <= 0:
            self.logger.info("Skipping storage object generation (count is 0)")
            return []

        agent = self.agents["storage"]
        criteria = scenario_config.get("storage_criteria", {})

        # Add machine configs to criteria if available
        if machine_configs:
            # Get machine IDs for attribution
            machine_ids = [config.get("MachineID") for config in machine_configs if "MachineID" in config]
            if machine_ids:
                criteria["machine_ids"] = machine_ids

        self.logger.info(f"Generating {count} storage objects with criteria: {criteria}")
        storage_objects = agent.generate(count, criteria)

        self.logger.info(f"Generated {len(storage_objects)} storage objects")
        return storage_objects

    def _generate_semantic_objects(self, count: int, scenario_config: Dict[str, Any],
                               storage_objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic metadata objects.

        Args:
            count: Number of records to generate
            scenario_config: Scenario configuration
            storage_objects: Generated storage objects

        Returns:
            Generated semantic objects
        """
        if count <= 0:
            self.logger.info("Skipping semantic metadata generation (count is 0)")
            return []

        # If count exceeds storage objects, adjust it
        if count > len(storage_objects):
            self.logger.warning(f"Semantic count ({count}) exceeds storage count ({len(storage_objects)}), adjusting")
            count = len(storage_objects)

        agent = self.agents["semantic"]
        criteria = scenario_config.get("semantic_criteria", {})

        # Add storage objects to criteria
        if storage_objects:
            # Use a subset of storage objects if count is less
            if count < len(storage_objects):
                # Select diverse storage objects for semantic analysis
                selected_objects = self._select_diverse_storage_objects(storage_objects, count)
                criteria["storage_objects"] = selected_objects
            else:
                criteria["storage_objects"] = storage_objects

        # Add additional semantic-specific criteria
        if "mime_type_distribution" not in criteria:
            # Default MIME type distribution
            criteria["mime_type_distribution"] = {
                "text/plain": 0.1,
                "application/pdf": 0.15,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 0.15,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": 0.1,
                "image/jpeg": 0.15,
                "image/png": 0.1,
                "video/mp4": 0.05,
                "audio/mpeg": 0.05,
                "application/zip": 0.05,
                "application/json": 0.05,
                "text/html": 0.05
            }

        # Add content extraction options if not specified
        if "content_extraction" not in criteria:
            criteria["content_extraction"] = {
                "extract_percentage": 0.7,  # Extract content for 70% of objects
                "extract_length": {
                    "min": 50,
                    "max": 500
                }
            }

        self.logger.info(f"Generating {count} semantic objects with criteria: {criteria}")

        try:
            semantic_objects = agent.generate(count, criteria)
            self.logger.info(f"Generated {len(semantic_objects)} semantic objects")
        except Exception as e:
            self.logger.error(f"Error generating semantic objects: {str(e)}")
            semantic_objects = []

        return semantic_objects

    def _select_diverse_storage_objects(self, storage_objects: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """Select a diverse subset of storage objects for semantic analysis.

        This ensures we have a good mix of file types and sizes for semantic metadata generation.

        Args:
            storage_objects: Complete list of storage objects
            count: Number of objects to select

        Returns:
            Selected diverse storage objects
        """
        if count >= len(storage_objects):
            return storage_objects

        # Group storage objects by their extension
        extension_groups = {}

        for obj in storage_objects:
            # Extract extension from filename or attributes
            extension = ""
            if "Label" in obj:
                filename = obj["Label"]
                if "." in filename:
                    extension = filename.split(".")[-1].lower()
            elif "Record" in obj and "Attributes" in obj["Record"]:
                extension = obj["Record"]["Attributes"].get("Extension", "").lower()
                if extension.startswith("."):
                    extension = extension[1:]

            # Group by extension
            if extension:
                if extension not in extension_groups:
                    extension_groups[extension] = []
                extension_groups[extension].append(obj)

        # Calculate how many objects to select from each group
        total_extensions = len(extension_groups)
        if total_extensions == 0:
            # No extensions found, return random selection
            import random
            return random.sample(storage_objects, count)

        # Distribute selection across extensions
        selected = []

        # First, ensure we have at least one from each extension group
        for ext, objects in extension_groups.items():
            if objects and len(selected) < count:
                selected.append(objects[0])

        # Fill the remaining slots proportionally
        remaining = count - len(selected)
        if remaining > 0:
            # Calculate proportions
            extension_counts = {ext: len(objects) for ext, objects in extension_groups.items()}
            total_objects = sum(extension_counts.values())

            # Allocate remaining slots proportionally
            allocated = 0
            for ext, objects in extension_groups.items():
                # Skip extensions we've already taken from
                if not objects[1:]:
                    continue

                # Calculate allocation (proportional to group size)
                allocation = int((extension_counts[ext] / total_objects) * remaining)
                # Ensure we don't exceed available objects or remaining slots
                allocation = min(allocation, len(objects) - 1, remaining - allocated)

                # Add allocated objects
                if allocation > 0:
                    selected.extend(objects[1:allocation+1])
                    allocated += allocation

            # If we still have slots, fill them randomly
            if allocated < remaining:
                # Create a pool of unused objects
                unused = [obj for obj in storage_objects if obj not in selected]
                # Select randomly from unused
                import random
                if unused:
                    additional = random.sample(unused, min(remaining - allocated, len(unused)))
                    selected.extend(additional)

        return selected

    def _generate_activity_objects(self, count: int, scenario_config: Dict[str, Any],
                              storage_objects: List[Dict[str, Any]],
                              machine_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate activity metadata objects.

        Args:
            count: Number of records to generate
            scenario_config: Scenario configuration
            storage_objects: Generated storage objects
            machine_configs: Generated machine configurations

        Returns:
            Generated activity objects
        """
        if count <= 0:
            self.logger.info("Skipping activity metadata generation (count is 0)")
            return []

        agent = self.agents["activity"]
        criteria = scenario_config.get("activity_criteria", {})

        # Add storage objects and machine configs to criteria
        if storage_objects:
            # Use a subset of storage objects based on activity_focus distribution
            activity_focus = scenario_config.get("activity_focus", "balanced")
            selected_objects = self._select_activity_focus_objects(storage_objects, count, activity_focus)
            criteria["storage_objects"] = selected_objects
            self.logger.info(f"Selected {len(selected_objects)} storage objects for activity generation with {activity_focus} focus")

        if machine_configs:
            # Get usernames and device info
            usernames = [config.get("Username") for config in machine_configs if "Username" in config]
            devices = [
                {
                    "type": config.get("DeviceType", "unknown"),
                    "os": config.get("Software", {}).get("OS", "unknown"),
                    "model": config.get("Hardware", {}).get("Model", "unknown")
                }
                for config in machine_configs
            ]

            if usernames:
                criteria["user_ids"] = usernames
            if devices:
                criteria["devices"] = devices

        # Set up sequence generation if specified
        sequence_config = scenario_config.get("activity_sequence_config", {})
        if sequence_config or scenario_config.get("activity_sequences", False):
            criteria["create_sequences"] = True

            # If explicit sequence config is provided, use it
            if sequence_config:
                criteria.update(sequence_config)
            else:
                # Otherwise use defaults
                criteria["sequence_count"] = scenario_config.get(
                    "activity_sequence_count", max(1, count // 10)
                )

                # Default sequence types if not specified
                if "sequence_types" not in criteria:
                    criteria["sequence_types"] = {
                        "file_workflow": 0.4,      # 40% file workflows
                        "meeting_sequence": 0.2,   # 20% meeting sequences
                        "application_session": 0.2, # 20% application sessions
                        "multi_device": 0.1,       # 10% multi-device interactions
                        "location_movement": 0.05,  # 5% location movements
                        "media_consumption": 0.05   # 5% media consumption patterns
                    }

        # Configure activity time distribution
        if "time_distribution" not in criteria:
            criteria["time_distribution"] = {
                "workday_hours": {
                    # Hour of day -> probability weight
                    "8": 0.05,   # 8 AM - start of day
                    "9": 0.08,
                    "10": 0.1,
                    "11": 0.15,  # Morning productivity peak
                    "12": 0.05,  # Lunch dip
                    "13": 0.07,
                    "14": 0.15,  # Early afternoon peak
                    "15": 0.15,  # Mid-afternoon peak
                    "16": 0.1,   # Late afternoon
                    "17": 0.05,  # End of day
                    "18": 0.02,
                    "19": 0.02,
                    "20": 0.01   # Evening
                },
                "weekday_weights": {
                    # 0=Monday -> 6=Sunday
                    "0": 0.2,    # Monday
                    "1": 0.25,   # Tuesday - peak productivity
                    "2": 0.25,   # Wednesday - peak productivity
                    "3": 0.2,    # Thursday
                    "4": 0.08,   # Friday
                    "5": 0.01,   # Saturday
                    "6": 0.01    # Sunday
                }
            }

        # Add activity type distribution if not specified
        if "activity_type_distribution" not in criteria:
            criteria["activity_type_distribution"] = {
                "FileAccess": 0.25,
                "FileEdit": 0.2,
                "FileCreation": 0.1,
                "FileShare": 0.05,
                "ApplicationUse": 0.2,
                "WebBrowsing": 0.1,
                "EmailSend": 0.05,
                "EmailReceive": 0.05
            }

        self.logger.info(f"Generating {count} activity objects with criteria: {criteria}")

        try:
            activity_objects = agent.generate(count, criteria)
            self.logger.info(f"Generated {len(activity_objects)} activity objects")
        except Exception as e:
            self.logger.error(f"Error generating activity objects: {str(e)}")
            activity_objects = []

        return activity_objects

    def _select_activity_focus_objects(self, storage_objects: List[Dict[str, Any]], count: int,
                                    focus: str) -> List[Dict[str, Any]]:
        """Select storage objects based on activity focus.

        Different focus strategies:
        - recent: Focus on recently modified objects
        - popular: Focus on objects that would be frequently accessed
        - diverse: Even distribution across different file types
        - balanced: Mixed approach (default)

        Args:
            storage_objects: Storage objects to select from
            count: Maximum number of objects to select
            focus: Activity focus strategy

        Returns:
            Selected storage objects for activity generation
        """
        if count >= len(storage_objects):
            return storage_objects

        import random
        sample_size = min(count, len(storage_objects))

        if focus == "recent":
            # Sort by modification time (most recent first)
            sorted_objects = sorted(
                storage_objects,
                key=lambda obj: self._extract_timestamp(obj, "Modified"),
                reverse=True
            )
            # Take the most recent objects
            return sorted_objects[:sample_size]

        elif focus == "popular":
            # Select objects based on weighted probabilities favoring:
            # - Documents and spreadsheets (work files)
            # - Moderate sizes (not too large or small)
            # - Files with descriptive names (longer names)
            weighted_objects = []

            for obj in storage_objects:
                weight = 1.0  # Base weight

                # Check extension/file type
                extension = ""
                if "Record" in obj and "Attributes" in obj["Record"]:
                    extension = obj["Record"]["Attributes"].get("Extension", "").lower()

                # Favor work document types
                if extension in [".docx", ".xlsx", ".pptx", ".pdf", ".txt"]:
                    weight *= 2.0

                # Check file size
                size = 0
                if "Record" in obj and "Attributes" in obj["Record"]:
                    size = obj["Record"]["Attributes"].get("Size", 0)

                # Favor moderate file sizes
                if 100_000 <= size <= 5_000_000:  # Between 100KB and 5MB
                    weight *= 1.5

                # Check name length (more descriptive names)
                name = obj.get("Label", "")
                if len(name) > 10:
                    weight *= 1.2

                weighted_objects.append((obj, weight))

            # Select based on weights
            total_weight = sum(w for _, w in weighted_objects)
            probabilities = [w / total_weight for _, w in weighted_objects]
            selected_indices = random.choices(
                range(len(weighted_objects)),
                weights=probabilities,
                k=sample_size
            )

            return [weighted_objects[i][0] for i in selected_indices]

        elif focus == "diverse":
            # Group by file types/extensions and select evenly
            extension_groups = {}

            for obj in storage_objects:
                # Extract extension
                extension = ""
                if "Record" in obj and "Attributes" in obj["Record"]:
                    extension = obj["Record"]["Attributes"].get("Extension", "").lower()

                if not extension:
                    extension = "unknown"

                if extension not in extension_groups:
                    extension_groups[extension] = []
                extension_groups[extension].append(obj)

            # Distribute selection evenly across extensions
            selected = []
            extensions = list(extension_groups.keys())

            # Round-robin selection from each extension group
            while len(selected) < sample_size and extensions:
                for ext in extensions[:]:
                    if extension_groups[ext]:
                        selected.append(extension_groups[ext].pop(0))
                        if len(selected) >= sample_size:
                            break
                    else:
                        extensions.remove(ext)

            return selected

        else:  # "balanced" or anything else
            # Use random selection
            return random.sample(storage_objects, sample_size)

    def _extract_timestamp(self, obj: Dict[str, Any], label: str) -> datetime:
        """Extract a timestamp from an object.

        Args:
            obj: Object to extract timestamp from
            label: Timestamp label to extract

        Returns:
            Extracted timestamp or current time if not found
        """
        from datetime import datetime, timezone

        # Check if there are timestamps in the object
        if "Timestamps" in obj:
            for ts in obj["Timestamps"]:
                if ts.get("Label") == label and "Value" in ts:
                    try:
                        return datetime.fromisoformat(ts["Value"])
                    except (ValueError, TypeError):
                        pass

        # Default to current time
        return datetime.now(timezone.utc)

    def _generate_relationships(self, count: int, scenario_config: Dict[str, Any],
                            storage_objects: List[Dict[str, Any]],
                            semantic_objects: List[Dict[str, Any]],
                            activity_objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate relationship objects.

        Args:
            count: Number of records to generate
            scenario_config: Scenario configuration
            storage_objects: Generated storage objects
            semantic_objects: Generated semantic objects
            activity_objects: Generated activity objects

        Returns:
            Generated relationship objects
        """
        if count <= 0:
            self.logger.info("Skipping relationship generation (count is 0)")
            return []

        agent = self.agents["relationship"]
        criteria = scenario_config.get("relationship_criteria", {})

        # Add objects to criteria
        if storage_objects:
            criteria["storage_objects"] = storage_objects

        if semantic_objects:
            criteria["semantic_objects"] = semantic_objects

        if activity_objects:
            criteria["activity_objects"] = activity_objects

        # Generate strategic relationships if specified in config
        relationship_strategy = scenario_config.get("relationship_strategy", "balanced")

        # Apply different relationship patterns based on strategy
        if relationship_strategy == "storage_semantic_focused":
            # Prioritize storage-semantic relationships
            if storage_objects and semantic_objects:
                self.logger.info("Applying storage-semantic relationship strategy")
                # Create object ID to semantic ID mappings for more accurate relationships
                storage_semantic_map = self._map_storage_to_semantic(storage_objects, semantic_objects)
                criteria["storage_semantic_mapping"] = storage_semantic_map
                criteria["relationship_distribution"] = {
                    "STORAGE_SEMANTIC": 0.6,  # 60% storage-semantic
                    "STORAGE_ACTIVITY": 0.2,  # 20% storage-activity
                    "ACTIVITY_SEMANTIC": 0.1,  # 10% activity-semantic
                    "GENERAL": 0.1  # 10% other relationships
                }

        elif relationship_strategy == "activity_focused":
            # Prioritize activity-related relationships
            if activity_objects:
                self.logger.info("Applying activity-focused relationship strategy")
                criteria["relationship_distribution"] = {
                    "STORAGE_ACTIVITY": 0.5,  # 50% storage-activity
                    "ACTIVITY_SEMANTIC": 0.3,  # 30% activity-semantic
                    "STORAGE_SEMANTIC": 0.1,  # 10% storage-semantic
                    "GENERAL": 0.1  # 10% other relationships
                }

        elif relationship_strategy == "balanced":
            # Distribute relationships evenly
            self.logger.info("Applying balanced relationship strategy")
            criteria["relationship_distribution"] = {
                "STORAGE_SEMANTIC": 0.33,  # ~33% storage-semantic
                "STORAGE_ACTIVITY": 0.33,  # ~33% storage-activity
                "ACTIVITY_SEMANTIC": 0.24,  # ~24% activity-semantic
                "GENERAL": 0.1  # 10% other relationships
            }

        # Add relationship types with probabilities if not specified
        if "relationship_types" not in criteria:
            criteria["relationship_types"] = {
                "CONTAINS": 0.2,
                "DERIVED_FROM": 0.15,
                "RELATED_TO": 0.2,
                "MODIFIED_BY": 0.15,
                "ACCESSED_BY": 0.1,
                "CREATED_BY": 0.1,
                "OWNED_BY": 0.05,
                "HAS_SEMANTIC_DATA": 0.05
            }

        self.logger.info(f"Generating {count} relationships with criteria: {criteria}")

        try:
            relationships = agent.generate(count, criteria)
            self.logger.info(f"Generated {len(relationships)} relationships")
        except Exception as e:
            self.logger.error(f"Error generating relationships: {str(e)}")
            relationships = []

        return relationships

    def _map_storage_to_semantic(self, storage_objects: List[Dict[str, Any]],
                               semantic_objects: List[Dict[str, Any]]) -> Dict[str, str]:
        """Create a mapping from storage object IDs to semantic object IDs.

        This helps create more accurate and meaningful relationships between
        storage and semantic objects.

        Args:
            storage_objects: List of storage objects
            semantic_objects: List of semantic objects

        Returns:
            Dictionary mapping storage IDs to semantic IDs
        """
        mapping = {}

        # Create a dictionary of semantic objects by their ObjectIdentifier
        semantic_dict = {}
        for semantic in semantic_objects:
            obj_id = semantic.get("ObjectIdentifier")
            if obj_id:
                semantic_dict[obj_id] = semantic

        # For each storage object, find matching semantic objects
        for storage in storage_objects:
            storage_id = storage.get("ObjectIdentifier")
            if not storage_id:
                continue

            # Check if there's a direct match in semantic objects
            if storage_id in semantic_dict:
                mapping[storage_id] = storage_id  # Same ID used in both domains
            else:
                # Look for semantic objects that might be related
                for semantic_id, semantic in semantic_dict.items():
                    # Check if the semantic object has content that matches this storage object
                    if self._objects_might_be_related(storage, semantic):
                        mapping[storage_id] = semantic_id
                        break

        self.logger.info(f"Created {len(mapping)} storage-to-semantic mappings")
        return mapping

    def _objects_might_be_related(self, storage: Dict[str, Any], semantic: Dict[str, Any]) -> bool:
        """Check if a storage object and semantic object might be related.

        Args:
            storage: Storage object
            semantic: Semantic object

        Returns:
            True if objects might be related, False otherwise
        """
        # If ObjectIdentifier matches, they're definitely related
        if storage.get("ObjectIdentifier") == semantic.get("ObjectIdentifier"):
            return True

        # Check filenames/paths
        storage_name = storage.get("Label", "")
        storage_path = ""
        if "Record" in storage and "Attributes" in storage["Record"]:
            storage_path = storage["Record"]["Attributes"].get("Path", "")

        # Look for name in semantic content
        if "Content" in semantic:
            content = semantic["Content"]
            if isinstance(content, dict) and "Extract" in content:
                extract = content["Extract"]
                # Check if storage name appears in the extract
                if storage_name and storage_name in extract:
                    return True

        # Default: return False if no connection found
        return False

    def _generate_machine_config_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate machine configuration truth records.

        Args:
            count: Number of records to generate
            criteria: Truth criteria

        Returns:
            Generated machine configuration truth records
        """
        if count <= 0:
            self.logger.info("Skipping machine configuration truth generation (count is 0)")
            return []

        agent = self.agents["machine_config"]

        self.logger.info(f"Generating {count} machine configuration truth records with criteria: {criteria}")
        machine_configs = agent.generate_truth(count, criteria)

        self.logger.info(f"Generated {len(machine_configs)} machine configuration truth records")
        return machine_configs

    def _generate_storage_truth(self, count: int, criteria: Dict[str, Any],
                             machine_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate storage truth records.

        Args:
            count: Number of records to generate
            criteria: Truth criteria
            machine_configs: Generated machine configuration truth records

        Returns:
            Generated storage truth records
        """
        if count <= 0:
            self.logger.info("Skipping storage truth generation (count is 0)")
            return []

        agent = self.agents["storage"]

        # Add machine configs to criteria if available
        if machine_configs:
            # Get machine IDs for attribution
            machine_ids = [config.get("MachineID") for config in machine_configs if "MachineID" in config]
            if machine_ids:
                criteria["machine_ids"] = machine_ids

        self.logger.info(f"Generating {count} storage truth records with criteria: {criteria}")
        storage_truth = agent.generate_truth(count, criteria)

        self.logger.info(f"Generated {len(storage_truth)} storage truth records")
        return storage_truth

    def _generate_semantic_truth(self, count: int, criteria: Dict[str, Any],
                             storage_truth: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic truth records.

        Args:
            count: Number of records to generate
            criteria: Truth criteria
            storage_truth: Generated storage truth records

        Returns:
            Generated semantic truth records
        """
        if count <= 0:
            self.logger.info("Skipping semantic truth generation (count is 0)")
            return []

        # If count exceeds storage objects, adjust it
        if count > len(storage_truth):
            self.logger.warning(f"Semantic truth count ({count}) exceeds storage count ({len(storage_truth)}), adjusting")
            count = len(storage_truth)

        agent = self.agents["semantic"]

        # Add storage objects to criteria
        criteria["storage_objects"] = storage_truth

        self.logger.info(f"Generating {count} semantic truth records with criteria: {criteria}")
        semantic_truth = agent.generate_truth(count, criteria)

        self.logger.info(f"Generated {len(semantic_truth)} semantic truth records")
        return semantic_truth

    def _generate_activity_truth(self, count: int, criteria: Dict[str, Any],
                             storage_truth: List[Dict[str, Any]],
                             machine_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate activity truth records.

        Args:
            count: Number of records to generate
            criteria: Truth criteria
            storage_truth: Generated storage truth records
            machine_configs: Generated machine configuration truth records

        Returns:
            Generated activity truth records
        """
        if count <= 0:
            self.logger.info("Skipping activity truth generation (count is 0)")
            return []

        agent = self.agents["activity"]

        # Add storage objects to criteria
        if storage_truth:
            criteria["storage_objects"] = storage_truth

        # Add machine configs to criteria if available
        if machine_configs:
            # Get usernames and device info for the first machine config
            if len(machine_configs) > 0:
                config = machine_configs[0]
                criteria["user_id"] = config.get("Username")
                criteria["device"] = {
                    "type": config.get("DeviceType", "unknown"),
                    "os": config.get("Software", {}).get("OS", "unknown"),
                    "model": config.get("Hardware", {}).get("Model", "unknown")
                }

        self.logger.info(f"Generating {count} activity truth records with criteria: {criteria}")
        activity_truth = agent.generate_truth(count, criteria)

        self.logger.info(f"Generated {len(activity_truth)} activity truth records")
        return activity_truth

    def _generate_relationship_truth(self, criteria: Dict[str, Any],
                                storage_truth: List[Dict[str, Any]],
                                semantic_truth: List[Dict[str, Any]],
                                activity_truth: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate relationship truth records.

        Args:
            criteria: Truth criteria
            storage_truth: Generated storage truth records
            semantic_truth: Generated semantic truth records
            activity_truth: Generated activity truth records

        Returns:
            Generated relationship truth records
        """
        agent = self.agents["relationship"]

        # Get counts
        count = criteria.get("count", 5)

        # Add objects to criteria
        if storage_truth:
            criteria["storage_objects"] = storage_truth
        if semantic_truth:
            criteria["semantic_objects"] = semantic_truth
        if activity_truth:
            criteria["activity_objects"] = activity_truth

        # Set relationship type if not specified
        if "relationship_type" not in criteria:
            criteria["relationship_type"] = "RELATED_TO"

        self.logger.info(f"Generating {count} relationship truth records with criteria: {criteria}")
        relationship_truth = agent.generate_truth(count, criteria)

        self.logger.info(f"Generated {len(relationship_truth)} relationship truth records")
        return relationship_truth

    def verify_truth_dataset(self, query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify query results against the truth dataset.

        Args:
            query_results: Results from a query

        Returns:
            Verification metrics (precision, recall, etc.)
        """
        if not self.truth_records:
            self.logger.warning("No truth records available for verification")
            return {
                "error": "No truth records available"
            }

        # Collect all truth IDs
        all_truth_ids = []
        for category, records in self.truth_records.items():
            for record in records:
                if category == "storage":
                    all_truth_ids.append(record.get("ObjectIdentifier", ""))
                elif category == "semantic":
                    all_truth_ids.append(record.get("ObjectIdentifier", ""))
                elif category == "activity":
                    all_truth_ids.append(record.get("Handle", ""))
                elif category == "relationship":
                    all_truth_ids.append(record.get("_key", ""))
                elif category == "machine_config":
                    all_truth_ids.append(record.get("MachineID", ""))

        # Remove any empty strings
        all_truth_ids = [id for id in all_truth_ids if id]

        # Get all result IDs
        result_ids = []
        for result in query_results:
            # Check for various ID fields
            for id_field in ["ObjectIdentifier", "Handle", "_key", "MachineID"]:
                if id_field in result:
                    result_ids.append(result[id_field])
                    break

        # Calculate metrics
        true_positives = [id for id in result_ids if id in all_truth_ids]
        false_positives = [id for id in result_ids if id not in all_truth_ids]
        false_negatives = [id for id in all_truth_ids if id not in result_ids]

        tp_count = len(true_positives)
        fp_count = len(false_positives)
        fn_count = len(false_negatives)

        # Calculate precision, recall, and F1 score
        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0
        recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        metrics = {
            "true_positives": tp_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "total_truth": len(all_truth_ids),
            "total_results": len(result_ids)
        }

        self.logger.info(f"Verification metrics: precision={precision:.2f}, recall={recall:.2f}, F1={f1_score:.2f}")

        return metrics

    def get_truth_examples(self, count: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get a sample of truth records for testing.

        Args:
            count: Number of examples to return from each category

        Returns:
            Dictionary of truth records by category
        """
        examples = {}

        for category, records in self.truth_records.items():
            sample_size = min(count, len(records))
            if sample_size > 0:
                import random
                examples[category] = random.sample(records, sample_size)
            else:
                examples[category] = []

        return examples

    def export_statistics(self, output_path: str) -> None:
        """Export generation statistics to a file.

        Args:
            output_path: Path to output file
        """
        with open(output_path, 'w') as f:
            json.dump({
                "generation_stats": self.stats,
                "truth_records_count": {
                    category: len(records) for category, records in self.truth_records.items()
                }
            }, f, indent=2)

        self.logger.info(f"Statistics exported to {output_path}")

    def export_truth_dataset(self, output_path: str) -> None:
        """Export truth dataset to a file for reference.

        Args:
            output_path: Path to output file
        """
        with open(output_path, 'w') as f:
            json.dump(self.truth_records, f, indent=2)

        self.logger.info(f"Truth dataset exported to {output_path}")
