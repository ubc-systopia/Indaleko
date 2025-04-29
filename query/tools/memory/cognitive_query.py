"""
Cognitive Memory Query Tool for Indaleko.

This tool provides a unified interface for querying the cognitive memory system,
which includes sensory memory, short-term memory, long-term memory, and archival memory.

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

import os
import sys
import time
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from query.tools.base import (
    BaseTool,
    ToolDefinition,
    ToolInput,
    ToolOutput,
    ToolParameter,
)

# Try to import utilities
try:
    from icecream import ic
except ImportError:
    # Create a simple ic function for logging if icecream isn't available
    def ic(*args):
        for arg in args:
            print(arg)


# Make sure utils.i_logging is available
try:
    from utils.i_logging import get_logger
except ImportError:
    # Create a simple logger if the utility isn't available
    import logging

    def get_logger(name):
        return logging.getLogger(name)


class CognitiveMemoryQueryTool(BaseTool):
    """
    Tool for querying the cognitive memory system.

    This tool provides a unified interface for querying all memory tiers:
    - Sensory Memory: Recent, high-detail, raw activity data
    - Short-Term Memory: Processed activity data with entity resolution
    - Long-Term Memory: Consolidated entities with semantic enrichment
    - Archival Memory: Permanent knowledge store with rich semantic relationships
    """

    def __init__(self):
        """Initialize the cognitive memory query tool."""
        super().__init__()
        self._db_config = None
        self._recorders = {}

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name="cognitive_memory_query",
            description="Queries the cognitive memory system across all memory tiers (sensory, short-term, long-term, archival).",
            parameters=[
                ToolParameter(
                    name="query",
                    description="The search query to execute",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="memory_tiers",
                    description="Memory tiers to include in the search (comma-separated list)",
                    type="string",
                    required=False,
                    default="all",  # Valid options: sensory, short_term, long_term, archival, all
                ),
                ToolParameter(
                    name="importance_min",
                    description="Minimum importance score for results",
                    type="number",
                    required=False,
                    default=0.0,
                ),
                ToolParameter(
                    name="w5h_filter",
                    description="W5H filter to apply (who, what, when, where, why, how dimensions)",
                    type="object",
                    required=False,
                    default={},
                ),
                ToolParameter(
                    name="concept_filter",
                    description="List of concepts to filter by",
                    type="array",
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="include_relationships",
                    description="Whether to include entity relationships in results",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="limit",
                    description="Maximum number of results to return per tier",
                    type="integer",
                    required=False,
                    default=10,
                ),
                ToolParameter(
                    name="db_config_path",
                    description="Path to the database configuration file",
                    type="string",
                    required=False,
                ),
            ],
            returns={
                "results": "The combined query results from all tiers",
                "tier_stats": "Statistics about the results from each tier",
                "performance": "Performance metrics for the query",
            },
            examples=[
                {
                    "parameters": {
                        "query": "project report",
                        "memory_tiers": "long_term,archival",
                        "w5h_filter": {
                            "what": ["document", "report"],
                            "why": ["project_work"],
                        },
                        "include_relationships": True,
                    },
                    "returns": {
                        "results": [
                            {
                                "memory_tier": "long_term",
                                "file_path": "Documents/ProjectReport.pdf",
                                "importance": 0.85,
                            },
                            {
                                "memory_tier": "archival",
                                "file_path": "Archive/2023/Q2Report.pdf",
                                "importance": 0.92,
                            },
                        ],
                        "tier_stats": {
                            "long_term": {"count": 1, "avg_importance": 0.85},
                            "archival": {"count": 1, "avg_importance": 0.92},
                        },
                    },
                },
            ],
        )

    def _initialize_db_config(self, db_config_path: str | None = None) -> None:
        """
        Initialize the database configuration.

        Args:
            db_config_path (Optional[str]): Path to the database configuration file.
        """
        if db_config_path is None:
            config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
            db_config_path = os.path.join(config_dir, "indaleko-db-config.ini")

        self._db_config = IndalekoDBConfig(config_file=db_config_path)

    def _initialize_memory_recorders(self) -> None:
        """Initialize the memory recorders for each tier."""
        # Report initial progress
        self.report_progress(
            stage="initialization",
            message="Initializing memory recorders",
            progress=0.1,
        )

        # We'll track any errors but not raise them to avoid stopping execution
        errors = []

        # Initialize sensory memory recorder
        self.report_progress(
            stage="initialization",
            message="Initializing sensory memory recorder",
            progress=0.2,
        )

        try:
            # Importing here to avoid dependency issues
            import importlib

            sensory_module = importlib.import_module(
                "activity.recorders.storage.ntfs.memory.sensory.recorder",
            )
            NtfsSensoryMemoryRecorder = sensory_module.NtfsSensoryMemoryRecorder

            # Create with no_db option in case service manager has issues
            self._recorders["sensory"] = NtfsSensoryMemoryRecorder(
                db_config_path=self._db_config.config_file,
                no_db=True,  # Start with no_db to avoid dependency issues
            )

            # Now try to connect to the database if we can
            try:
                # If we have a recorder with a connect method, try to use it
                if hasattr(self._recorders["sensory"], "connect"):
                    self._recorders["sensory"].connect()
                ic("Sensory memory recorder initialized")
            except Exception as e:
                ic(f"Failed to connect sensory memory recorder to database: {e}")
                errors.append(f"Sensory connection error: {e}")

        except Exception as e:
            ic(f"Failed to initialize sensory memory recorder: {e}")
            errors.append(f"Sensory initialization error: {e}")

        # Initialize short-term memory recorder
        self.report_progress(
            stage="initialization",
            message="Initializing short-term memory recorder",
            progress=0.3,
        )

        try:
            # Importing here to avoid dependency issues
            import importlib

            short_term_module = importlib.import_module(
                "activity.recorders.storage.ntfs.memory.short_term.recorder",
            )
            NtfsShortTermMemoryRecorder = short_term_module.NtfsShortTermMemoryRecorder

            # Create with no_db option in case service manager has issues
            self._recorders["short_term"] = NtfsShortTermMemoryRecorder(
                db_config_path=self._db_config.config_file,
                no_db=True,  # Start with no_db to avoid dependency issues
            )

            # Now try to connect to the database if we can
            try:
                # If we have a recorder with a connect method, try to use it
                if hasattr(self._recorders["short_term"], "connect"):
                    self._recorders["short_term"].connect()
                ic("Short-term memory recorder initialized")
            except Exception as e:
                ic(f"Failed to connect short-term memory recorder to database: {e}")
                errors.append(f"Short-term connection error: {e}")

        except Exception as e:
            ic(f"Failed to initialize short-term memory recorder: {e}")
            errors.append(f"Short-term initialization error: {e}")

        # Initialize long-term memory recorder
        self.report_progress(
            stage="initialization",
            message="Initializing long-term memory recorder",
            progress=0.4,
        )

        try:
            # Importing here to avoid dependency issues
            import importlib

            long_term_module = importlib.import_module(
                "activity.recorders.storage.ntfs.memory.long_term.recorder",
            )
            NtfsLongTermMemoryRecorder = long_term_module.NtfsLongTermMemoryRecorder

            # Create with no_db option in case service manager has issues
            self._recorders["long_term"] = NtfsLongTermMemoryRecorder(
                db_config_path=self._db_config.config_file,
                no_db=True,  # Start with no_db to avoid dependency issues
            )

            # Now try to connect to the database if we can
            try:
                # If we have a recorder with a connect method, try to use it
                if hasattr(self._recorders["long_term"], "connect"):
                    self._recorders["long_term"].connect()
                ic("Long-term memory recorder initialized")
            except Exception as e:
                ic(f"Failed to connect long-term memory recorder to database: {e}")
                errors.append(f"Long-term connection error: {e}")

        except Exception as e:
            ic(f"Failed to initialize long-term memory recorder: {e}")
            errors.append(f"Long-term initialization error: {e}")

        # Initialize archival memory recorder
        self.report_progress(
            stage="initialization",
            message="Initializing archival memory recorder",
            progress=0.5,
        )

        try:
            # Importing here to avoid dependency issues
            import importlib

            archival_module = importlib.import_module(
                "activity.recorders.storage.ntfs.memory.archival.recorder",
            )
            NtfsArchivalMemoryRecorder = archival_module.NtfsArchivalMemoryRecorder

            # Create with no_db option in case service manager has issues
            self._recorders["archival"] = NtfsArchivalMemoryRecorder(
                db_config_path=self._db_config.config_file,
                no_db=True,  # Start with no_db to avoid dependency issues
            )

            # Now try to connect to the database if we can
            try:
                # If we have a recorder with a connect method, try to use it
                if hasattr(self._recorders["archival"], "connect"):
                    self._recorders["archival"].connect()
                ic("Archival memory recorder initialized")
            except Exception as e:
                ic(f"Failed to connect archival memory recorder to database: {e}")
                errors.append(f"Archival connection error: {e}")

        except Exception as e:
            ic(f"Failed to initialize archival memory recorder: {e}")
            errors.append(f"Archival initialization error: {e}")

        # Log summary of initialization
        if errors:
            error_summary = "\n".join(errors)
            ic(
                f"Memory recorder initialization completed with some errors:\n{error_summary}",
            )
        else:
            ic("All memory recorders initialized successfully")

    def _query_sensory_memory(
        self,
        query: str,
        importance_min: float = 0.0,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Query the sensory memory tier.

        Args:
            query: The search query
            importance_min: Minimum importance score
            limit: Maximum number of results

        Returns:
            List of results from sensory memory
        """
        if "sensory" not in self._recorders:
            return []

        # Get the sensory memory recorder
        recorder = self._recorders["sensory"]

        try:
            # Execute the query
            results = recorder.search_sensory_memory(
                query=query,
                importance_min=importance_min,
                limit=limit,
            )

            # Process results to add the memory tier
            processed_results = []
            for item in results:
                # Add memory tier to result
                item_copy = dict(item)
                item_copy["memory_tier"] = "sensory"
                processed_results.append(item_copy)

            return processed_results

        except Exception as e:
            ic(f"Error querying sensory memory: {e}")
            return []

    def _query_short_term_memory(
        self,
        query: str,
        importance_min: float = 0.0,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Query the short-term memory tier.

        Args:
            query: The search query
            importance_min: Minimum importance score
            limit: Maximum number of results

        Returns:
            List of results from short-term memory
        """
        if "short_term" not in self._recorders:
            return []

        # Get the short-term memory recorder
        recorder = self._recorders["short_term"]

        try:
            # Execute the query
            results = recorder.search_short_term_memory(
                query=query,
                importance_min=importance_min,
                limit=limit,
            )

            # Process results to add the memory tier
            processed_results = []
            for item in results:
                # Add memory tier to result
                item_copy = dict(item)
                item_copy["memory_tier"] = "short_term"
                processed_results.append(item_copy)

            return processed_results

        except Exception as e:
            ic(f"Error querying short-term memory: {e}")
            return []

    def _query_long_term_memory(
        self,
        query: str,
        importance_min: float = 0.0,
        w5h_filter: dict[str, list[str]] | None = None,
        concept_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Query the long-term memory tier.

        Args:
            query: The search query
            importance_min: Minimum importance score
            w5h_filter: Optional W5H filter dictionary
            concept_filter: Optional list of concepts to filter by
            limit: Maximum number of results

        Returns:
            List of results from long-term memory
        """
        if "long_term" not in self._recorders:
            return []

        # Get the long-term memory recorder
        recorder = self._recorders["long_term"]

        try:
            # Execute the query
            results = recorder.search_long_term_memory(
                query=query,
                w5h_filter=w5h_filter,
                concept_filter=concept_filter,
                importance_min=importance_min,
                limit=limit,
            )

            # Process results to add the memory tier
            processed_results = []
            for item in results:
                # Add memory tier to result
                item_copy = dict(item)
                item_copy["memory_tier"] = "long_term"
                processed_results.append(item_copy)

            return processed_results

        except Exception as e:
            ic(f"Error querying long-term memory: {e}")
            return []

    def _query_archival_memory(
        self,
        query: str,
        importance_min: float = 0.0,
        w5h_filter: dict[str, list[str]] | None = None,
        concept_filter: list[str] | None = None,
        include_relationships: bool = False,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Query the archival memory tier.

        Args:
            query: The search query
            importance_min: Minimum importance score
            w5h_filter: Optional W5H filter dictionary
            concept_filter: Optional list of concepts to filter by
            include_relationships: Whether to include relationships
            limit: Maximum number of results

        Returns:
            List of results from archival memory
        """
        if "archival" not in self._recorders:
            return []

        # Get the archival memory recorder
        recorder = self._recorders["archival"]

        try:
            # Execute the query
            results = recorder.search_archival_memory(
                query=query,
                w5h_filter=w5h_filter,
                concept_filter=concept_filter,
                importance_min=importance_min,
                include_knowledge_graph=include_relationships,
                limit=limit,
            )

            # Process results to add the memory tier
            processed_results = []
            for item in results:
                # Add memory tier to result
                item_copy = dict(item)
                item_copy["memory_tier"] = "archival"
                processed_results.append(item_copy)

            return processed_results

        except Exception as e:
            ic(f"Error querying archival memory: {e}")
            return []

    def _calculate_tier_statistics(
        self,
        results_by_tier: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate statistics for each memory tier.

        Args:
            results_by_tier: Dictionary mapping tier names to result lists

        Returns:
            Dictionary of statistics for each tier
        """
        tier_stats = {}

        # Ensure all four tiers are included in statistics, even if empty
        for tier in ["sensory", "short_term", "long_term", "archival"]:
            if tier not in tier_stats:
                tier_stats[tier] = {
                    "count": 0,
                    "avg_importance": 0.0,
                    "min_importance": 0.0,
                    "max_importance": 0.0,
                }

        # Process actual results
        for tier, results in results_by_tier.items():
            if not results:
                tier_stats[tier] = {
                    "count": 0,
                    "avg_importance": 0.0,
                    "min_importance": 0.0,
                    "max_importance": 0.0,
                }
                continue

            # Calculate statistics
            count = len(results)

            # Extract importance scores with flexible detection
            importance_scores = []
            for result in results:
                score = self._extract_importance_score(result)
                if score is not None:
                    importance_scores.append(score)

            # Calculate average importance if we have scores
            avg_importance = 0.0
            min_importance = 0.0
            max_importance = 0.0

            if importance_scores:
                avg_importance = sum(importance_scores) / len(importance_scores)
                min_importance = min(importance_scores)
                max_importance = max(importance_scores)

            # Store enhanced statistics
            tier_stats[tier] = {
                "count": count,
                "avg_importance": avg_importance,
                "min_importance": min_importance,
                "max_importance": max_importance,
                "scores_found": len(importance_scores),
            }

        return tier_stats

    def _extract_importance_score(self, result: dict[str, Any]) -> float | None:
        """
        Extract importance score from a result with flexible detection.

        Args:
            result: Result dictionary from any memory tier

        Returns:
            Importance score if found, None otherwise
        """
        if not isinstance(result, dict):
            return None

        # Try Record.Data.importance_score (most common)
        data = result.get("Record", {}).get("Data", {})
        if data and "importance_score" in data:
            return data["importance_score"]

        # Try direct importance_score
        if "importance_score" in result:
            return result["importance_score"]

        # Try Record.importance_score
        record = result.get("Record", {})
        if "importance_score" in record:
            return record["importance_score"]

        # Try Data.importance_score
        data = result.get("Data", {})
        if data and "importance_score" in data:
            return data["importance_score"]

        return None

    def _rank_results(
        self,
        results: list[dict[str, Any]],
        tier_weights: dict[str, float],
    ) -> list[dict[str, Any]]:
        """
        Rank results based on tier weights and importance scores.

        Args:
            results: Combined results from all tiers
            tier_weights: Weights for each memory tier

        Returns:
            Ranked list of results
        """
        # Create a scored list for ranking
        scored_results = []
        for result in results:
            # Skip results without necessary information
            if not isinstance(result, dict) or "memory_tier" not in result:
                continue

            # Get tier and importance
            tier = result.get("memory_tier", "unknown")
            tier_weight = tier_weights.get(tier, 1.0)

            # Extract importance score
            importance_score = 0.0
            if isinstance(result, dict):
                data = result.get("Record", {}).get("Data", {})
                if data and "importance_score" in data:
                    importance_score = data["importance_score"]

                # Handle different memory tier implementations that might store importance in different locations
                elif "importance_score" in result:
                    importance_score = result["importance_score"]

            # Calculate combined score
            combined_score = importance_score * tier_weight

            # Add to scored results
            scored_results.append((result, combined_score))

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Return just the results, not the scores
        return [result for result, _ in scored_results]

    def execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Execute the cognitive memory query tool.

        Args:
            input_data (ToolInput): The input data for the tool.

        Returns:
            ToolOutput: The result of the tool execution.
        """
        # Track execution time
        start_time = time.time()

        # Extract parameters
        query = input_data.parameters["query"]
        memory_tiers_str = input_data.parameters.get("memory_tiers", "all")
        importance_min = float(input_data.parameters.get("importance_min", 0.0))
        w5h_filter = input_data.parameters.get("w5h_filter", {})
        concept_filter = input_data.parameters.get("concept_filter", [])
        include_relationships = input_data.parameters.get(
            "include_relationships",
            False,
        )
        limit = int(input_data.parameters.get("limit", 10))
        db_config_path = input_data.parameters.get("db_config_path")

        # Parse memory tiers
        if memory_tiers_str.lower() == "all":
            memory_tiers = ["sensory", "short_term", "long_term", "archival"]
        else:
            # Parse tier names
            parsed_tiers = [tier.strip() for tier in memory_tiers_str.split(",")]

            # Validate tier names
            valid_tiers = {"sensory", "short_term", "long_term", "archival"}
            invalid_tiers = [tier for tier in parsed_tiers if tier not in valid_tiers]

            if invalid_tiers:
                # Log a warning but continue with valid tiers
                print(
                    f"Warning: Invalid memory tier names ignored: {', '.join(invalid_tiers)}. "
                    f"Valid values are: sensory, short_term, long_term, archival",
                )
                ic(f"Invalid tier names ignored: {invalid_tiers}")

                # Filter out invalid tiers
                memory_tiers = [tier for tier in parsed_tiers if tier in valid_tiers]

                # If no valid tiers left, use all
                if not memory_tiers:
                    self._logger.warning("No valid tiers specified, using all tiers")
                    memory_tiers = ["sensory", "short_term", "long_term", "archival"]
            else:
                memory_tiers = parsed_tiers

        # Report initial progress
        self.report_progress(
            stage="initialization",
            message=f"Initializing cognitive memory query for: {query}",
            progress=0.05,
            data={"tiers": memory_tiers},
        )

        # Initialize database configuration
        if self._db_config is None:
            self._initialize_db_config(db_config_path)

        # Initialize memory recorders if needed
        if not self._recorders:
            self._initialize_memory_recorders()

        try:
            # Query each requested memory tier
            results_by_tier = {}

            # Sensory Memory
            if "sensory" in memory_tiers:
                self.report_progress(
                    stage="query",
                    message="Querying sensory memory",
                    progress=0.5,
                    data={"tier": "sensory"},
                )

                results_by_tier["sensory"] = self._query_sensory_memory(
                    query=query,
                    importance_min=importance_min,
                    limit=limit,
                )

            # Short-Term Memory
            if "short_term" in memory_tiers:
                self.report_progress(
                    stage="query",
                    message="Querying short-term memory",
                    progress=0.6,
                    data={"tier": "short_term"},
                )

                results_by_tier["short_term"] = self._query_short_term_memory(
                    query=query,
                    importance_min=importance_min,
                    limit=limit,
                )

            # Long-Term Memory
            if "long_term" in memory_tiers:
                self.report_progress(
                    stage="query",
                    message="Querying long-term memory",
                    progress=0.7,
                    data={"tier": "long_term"},
                )

                results_by_tier["long_term"] = self._query_long_term_memory(
                    query=query,
                    importance_min=importance_min,
                    w5h_filter=w5h_filter,
                    concept_filter=concept_filter,
                    limit=limit,
                )

            # Archival Memory
            if "archival" in memory_tiers:
                self.report_progress(
                    stage="query",
                    message="Querying archival memory",
                    progress=0.8,
                    data={"tier": "archival"},
                )

                results_by_tier["archival"] = self._query_archival_memory(
                    query=query,
                    importance_min=importance_min,
                    w5h_filter=w5h_filter,
                    concept_filter=concept_filter,
                    include_relationships=include_relationships,
                    limit=limit,
                )

            # Calculate tier statistics
            tier_stats = self._calculate_tier_statistics(results_by_tier)

            # Combine all results
            all_results = []
            for tier, results in results_by_tier.items():
                all_results.extend(results)

            # Rank results with tier-specific weighting
            tier_weights = {
                "sensory": 0.7,  # Recent but less processed
                "short_term": 0.8,  # Recent and partially processed
                "long_term": 0.9,  # Older but with semantic enrichment
                "archival": 1.0,  # Most important historical data
            }

            ranked_results = self._rank_results(all_results, tier_weights)

            # Calculate performance metrics
            elapsed_time = time.time() - start_time
            performance = {
                "execution_time_seconds": elapsed_time,
                "total_results": len(ranked_results),
                "results_by_tier": {tier: len(results) for tier, results in results_by_tier.items()},
            }

            # Report completion
            self.report_progress(
                stage="completion",
                message="Cognitive memory query complete",
                progress=1.0,
                data={
                    "total_results": len(ranked_results),
                    "execution_time": elapsed_time,
                },
            )

            # Return the result
            return ToolOutput(
                tool_name=self.definition.name,
                success=True,
                result={
                    "results": ranked_results,
                    "tier_stats": tier_stats,
                    "performance": performance,
                },
                elapsed_time=elapsed_time,
            )

        except Exception as e:
            ic(f"Error executing cognitive memory query: {e}")
            import traceback

            trace = traceback.format_exc()

            # Report error
            self.report_progress(
                stage="error",
                message=f"Error executing cognitive memory query: {e}",
                progress=1.0,
                data={"error": str(e)},
            )

            elapsed_time = time.time() - start_time

            return ToolOutput(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                trace=trace,
                elapsed_time=elapsed_time,
            )
