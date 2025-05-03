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
        self.tool_registry.register_tool(FileMetadataGeneratorTool())
        
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
                criteria["storage_objects"] = storage_objects[:count]
            else:
                criteria["storage_objects"] = storage_objects
        
        self.logger.info(f"Generating {count} semantic objects with criteria: {criteria}")
        semantic_objects = agent.generate(count, criteria)
        
        self.logger.info(f"Generated {len(semantic_objects)} semantic objects")
        return semantic_objects
    
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
            # Use a subset of storage objects
            sample_size = min(count, len(storage_objects))
            import random
            criteria["storage_objects"] = random.sample(storage_objects, sample_size)
        
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
        if scenario_config.get("activity_sequences", False):
            criteria["create_sequences"] = True
            criteria["sequence_count"] = scenario_config.get("activity_sequence_count", max(1, count // 10))
        
        self.logger.info(f"Generating {count} activity objects with criteria: {criteria}")
        activity_objects = agent.generate(count, criteria)
        
        self.logger.info(f"Generated {len(activity_objects)} activity objects")
        return activity_objects
    
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
        criteria["storage_objects"] = storage_objects
        criteria["semantic_objects"] = semantic_objects
        criteria["activity_objects"] = activity_objects
        
        self.logger.info(f"Generating {count} relationships with criteria: {criteria}")
        relationships = agent.generate(count, criteria)
        
        self.logger.info(f"Generated {len(relationships)} relationships")
        return relationships
    
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