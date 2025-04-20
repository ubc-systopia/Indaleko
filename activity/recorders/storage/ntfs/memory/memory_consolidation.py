#!/usr/bin/env python
"""
Memory Consolidation Process for NTFS Cognitive Memory System.

This module implements the memory consolidation process that transfers information
between the different memory tiers of the NTFS cognitive memory system:

- Sensory Memory → Short-Term Memory → Long-Term Memory → Archival Memory

The consolidation process applies importance scoring, entity resolution, and other
cognitive processes to mimic the way human memory consolidates information from
immediate sensory perception to longer-term storage.

Usage:
    python memory_consolidation.py --consolidate-sensory  # Consolidate from sensory to short-term
    python memory_consolidation.py --consolidate-short    # Consolidate from short-term to long-term
    python memory_consolidation.py --consolidate-long     # Consolidate from long-term to archival
    python memory_consolidation.py --consolidate-all      # Run all consolidation processes

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
import uuid
import json
import time
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from utils.i_logging import get_logger
# pylint: enable=wrong-import-position


class MemoryConsolidationManager:
    """
    Manages the cognitive memory consolidation process.
    
    This class coordinates the consolidation of data between different memory tiers
    in the cognitive memory system, applying importance scoring, entity resolution,
    and other cognitive processes to mimic human memory consolidation.
    
    The consolidation follows this pattern:
    Sensory Memory → Short-Term Memory → Long-Term Memory → Archival Memory
    """
    
    def __init__(
        self,
        db_config_path: Optional[str] = None,
        sensory_memory_recorder = None,
        short_term_memory_recorder = None,
        long_term_memory_recorder = None,
        archival_memory_recorder = None,
        sensory_days: int = 2,
        short_term_min_importance: float = 0.3,
        long_term_min_importance: float = 0.7,
        archival_min_importance: float = 0.8,
        entity_batch_size: int = 100,
        debug: bool = False
    ):
        """
        Initialize the memory consolidation manager.
        
        Args:
            db_config_path: Path to database configuration file
            sensory_memory_recorder: Sensory memory recorder instance (optional)
            short_term_memory_recorder: Short-term memory recorder instance (optional)
            long_term_memory_recorder: Long-term memory recorder instance (optional)
            archival_memory_recorder: Archival memory recorder instance (optional)
            sensory_days: Number of days of sensory data to consolidate
            short_term_min_importance: Minimum importance for short-term memory
            long_term_min_importance: Minimum importance for long-term memory
            archival_min_importance: Minimum importance for archival memory
            entity_batch_size: Number of entities to process in each batch
            debug: Whether to enable debug logging
        """
        # Configure logging
        self._logger = get_logger(__name__)
        if debug:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)
            
        # Store parameters
        self._db_config_path = db_config_path
        self._sensory_days = sensory_days
        self._short_term_min_importance = short_term_min_importance
        self._long_term_min_importance = long_term_min_importance
        self._archival_min_importance = archival_min_importance
        self._entity_batch_size = entity_batch_size
        
        # Initialize recorders
        self._sensory_memory_recorder = sensory_memory_recorder
        self._short_term_memory_recorder = short_term_memory_recorder
        self._long_term_memory_recorder = long_term_memory_recorder
        self._archival_memory_recorder = archival_memory_recorder
        
        # Initialize statistics
        self._stats = {}
        
    def _initialize_recorders(self):
        """Initialize memory recorders if not provided."""
        # Initialize sensory memory recorder if needed
        if self._sensory_memory_recorder is None:
            try:
                from activity.recorders.storage.ntfs.memory.sensory.recorder import NtfsSensoryMemoryRecorder
                self._sensory_memory_recorder = NtfsSensoryMemoryRecorder(
                    db_config_path=self._db_config_path,
                    consolidation_enabled=True
                )
                self._logger.info("Created sensory memory recorder")
            except Exception as e:
                self._logger.error(f"Failed to create sensory memory recorder: {e}")
                
        # Initialize short-term memory recorder if needed
        if self._short_term_memory_recorder is None:
            try:
                from activity.recorders.storage.ntfs.memory.short_term.recorder import NtfsShortTermMemoryRecorder
                self._short_term_memory_recorder = NtfsShortTermMemoryRecorder(
                    db_config_path=self._db_config_path,
                    consolidation_enabled=True
                )
                self._logger.info("Created short-term memory recorder")
            except Exception as e:
                self._logger.error(f"Failed to create short-term memory recorder: {e}")
                
        # Initialize long-term memory recorder if needed
        if self._long_term_memory_recorder is None:
            try:
                from activity.recorders.storage.ntfs.memory.long_term.recorder import NtfsLongTermMemoryRecorder
                self._long_term_memory_recorder = NtfsLongTermMemoryRecorder(
                    db_config_path=self._db_config_path,
                    consolidation_enabled=True
                )
                self._logger.info("Created long-term memory recorder")
            except Exception as e:
                self._logger.error(f"Failed to create long-term memory recorder: {e}")
                
        # Initialize archival memory recorder if needed
        if self._archival_memory_recorder is None:
            try:
                from activity.recorders.storage.ntfs.memory.archival.recorder import NtfsArchivalMemoryRecorder
                self._archival_memory_recorder = NtfsArchivalMemoryRecorder(
                    db_config_path=self._db_config_path
                )
                self._logger.info("Created archival memory recorder")
            except Exception as e:
                self._logger.error(f"Failed to create archival memory recorder: {e}")
    
    def consolidate_sensory_to_short_term(self) -> Dict[str, Any]:
        """
        Consolidate data from sensory memory to short-term memory.
        
        Returns:
            Dictionary with consolidation statistics
        """
        self._logger.info("Starting sensory to short-term memory consolidation")
        
        # Initialize recorders if needed
        self._initialize_recorders()
        
        # Check if required recorders are available
        if self._sensory_memory_recorder is None:
            error_msg = "Sensory memory recorder not available"
            self._logger.error(error_msg)
            return {"error": error_msg}
            
        if self._short_term_memory_recorder is None:
            error_msg = "Short-term memory recorder not available"
            self._logger.error(error_msg)
            return {"error": error_msg}
            
        try:
            # Perform consolidation
            start_time = time.time()
            
            stats = self._short_term_memory_recorder.consolidate_from_sensory_memory(
                days=self._sensory_days,
                min_importance=self._short_term_min_importance,
                entity_limit=self._entity_batch_size
            )
            
            end_time = time.time()
            
            # Add timing information
            stats["execution_time"] = end_time - start_time
            stats["timestamp"] = datetime.now(timezone.utc).isoformat()
            stats["consolidation_type"] = "sensory_to_short_term"
            
            # Log results
            self._logger.info(f"Consolidated {stats.get('entities_consolidated', 0)} entities to short-term memory")
            self._logger.info(f"Execution time: {stats['execution_time']:.2f} seconds")
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Error during sensory to short-term consolidation: {e}")
            return {"error": str(e), "consolidation_type": "sensory_to_short_term"}
    
    def consolidate_short_term_to_long_term(self) -> Dict[str, Any]:
        """
        Consolidate data from short-term memory to long-term memory.
        
        Returns:
            Dictionary with consolidation statistics
        """
        self._logger.info("Starting short-term to long-term memory consolidation")
        
        # Initialize recorders if needed
        self._initialize_recorders()
        
        # Check if required recorders are available
        if self._short_term_memory_recorder is None:
            error_msg = "Short-term memory recorder not available"
            self._logger.error(error_msg)
            return {"error": error_msg}
            
        if self._long_term_memory_recorder is None:
            error_msg = "Long-term memory recorder not available"
            self._logger.error(error_msg)
            return {"error": error_msg, "status": "not_implemented"}
            
        try:
            # Get entities eligible for long-term memory
            start_time = time.time()
            
            # Perform consolidation through the long-term memory recorder
            stats = self._long_term_memory_recorder.consolidate_from_short_term_memory(
                min_age_days=7,  # Use a default of 7 days minimum age
                min_importance=self._long_term_min_importance,
                entity_limit=self._entity_batch_size
            )
            
            end_time = time.time()
            
            # Add timing information
            stats["execution_time"] = end_time - start_time
            stats["timestamp"] = datetime.now(timezone.utc).isoformat()
            stats["consolidation_type"] = "short_term_to_long_term"
            
            # Log results
            self._logger.info(f"Consolidated {stats.get('entities_consolidated', 0)} entities to long-term memory")
            self._logger.info(f"Execution time: {stats['execution_time']:.2f} seconds")
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Error during short-term to long-term consolidation: {e}")
            return {"error": str(e), "consolidation_type": "short_term_to_long_term"}
    
    def consolidate_long_term_to_archival(self) -> Dict[str, Any]:
        """
        Consolidate data from long-term memory to archival memory.
        
        Returns:
            Dictionary with consolidation statistics
        """
        self._logger.info("Starting long-term to archival memory consolidation")
        
        # Initialize recorders if needed
        self._initialize_recorders()
        
        # Check if required recorders are available
        if self._long_term_memory_recorder is None:
            error_msg = "Long-term memory recorder not available"
            self._logger.error(error_msg)
            return {"error": error_msg}
            
        if self._archival_memory_recorder is None:
            error_msg = "Archival memory recorder not available"
            self._logger.error(error_msg)
            return {"error": error_msg, "status": "not_implemented"}
            
        try:
            # Perform consolidation through the archival memory recorder
            start_time = time.time()
            
            stats = self._archival_memory_recorder.consolidate_from_long_term_memory(
                min_age_days=90,  # Use a default of 90 days minimum age
                min_importance=self._archival_min_importance,
                entity_limit=self._entity_batch_size
            )
            
            end_time = time.time()
            
            # Add timing information
            stats["execution_time"] = end_time - start_time
            stats["timestamp"] = datetime.now(timezone.utc).isoformat()
            stats["consolidation_type"] = "long_term_to_archival"
            
            # Log results
            self._logger.info(f"Consolidated {stats.get('entities_consolidated', 0)} entities to archival memory")
            self._logger.info(f"Execution time: {stats['execution_time']:.2f} seconds")
            
        except Exception as e:
            self._logger.error(f"Error during long-term to archival consolidation: {e}")
            stats = {
                "error": str(e),
                "entities_processed": 0,
                "entities_consolidated": 0,
                "execution_time": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "consolidation_type": "long_term_to_archival"
            }
        
        return stats
    
    def consolidate_all(self) -> Dict[str, Any]:
        """
        Run all consolidation processes in sequence.
        
        Returns:
            Dictionary with combined consolidation statistics
        """
        self._logger.info("Starting full memory consolidation process")
        
        # Initialize recorders if needed
        self._initialize_recorders()
        
        start_time = time.time()
        
        # Run all consolidation processes
        results = {}
        
        # Sensory → Short-Term
        sensory_results = self.consolidate_sensory_to_short_term()
        results["sensory_to_short_term"] = sensory_results
        
        # Short-Term → Long-Term
        short_term_results = self.consolidate_short_term_to_long_term()
        results["short_term_to_long_term"] = short_term_results
        
        # Long-Term → Archival
        long_term_results = self.consolidate_long_term_to_archival()
        results["long_term_to_archival"] = long_term_results
        
        end_time = time.time()
        
        # Add overall statistics
        results["total_execution_time"] = end_time - start_time
        results["timestamp"] = datetime.now(timezone.utc).isoformat()
        results["consolidation_type"] = "all"
        
        # Calculate totals
        total_entities_processed = (
            sensory_results.get("entities_processed", 0) +
            short_term_results.get("entities_processed", 0) +
            long_term_results.get("entities_processed", 0)
        )
        
        total_entities_consolidated = (
            sensory_results.get("entities_consolidated", 0) +
            short_term_results.get("entities_consolidated", 0) +
            long_term_results.get("entities_consolidated", 0)
        )
        
        total_errors = (
            sensory_results.get("errors", 0) +
            short_term_results.get("errors", 0) +
            long_term_results.get("errors", 0)
        )
        
        results["total_entities_processed"] = total_entities_processed
        results["total_entities_consolidated"] = total_entities_consolidated
        results["total_errors"] = total_errors
        
        # Log results
        self._logger.info(f"Completed full memory consolidation process")
        self._logger.info(f"Total consolidated entities: {total_entities_consolidated}")
        self._logger.info(f"Total execution time: {results['total_execution_time']:.2f} seconds")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.
        
        Returns:
            Dictionary with memory statistics
        """
        self._logger.info("Gathering memory system statistics")
        
        # Initialize recorders if needed
        self._initialize_recorders()
        
        stats = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_tiers": {}
        }
        
        # Get sensory memory statistics
        if self._sensory_memory_recorder is not None:
            try:
                sensory_stats = self._sensory_memory_recorder.get_sensory_memory_statistics()
                stats["memory_tiers"]["sensory"] = sensory_stats
            except Exception as e:
                self._logger.error(f"Error getting sensory memory statistics: {e}")
                stats["memory_tiers"]["sensory"] = {"error": str(e)}
        else:
            stats["memory_tiers"]["sensory"] = {"status": "recorder_not_available"}
            
        # Get short-term memory statistics
        if self._short_term_memory_recorder is not None:
            try:
                short_term_stats = self._short_term_memory_recorder.get_short_term_memory_statistics()
                stats["memory_tiers"]["short_term"] = short_term_stats
            except Exception as e:
                self._logger.error(f"Error getting short-term memory statistics: {e}")
                stats["memory_tiers"]["short_term"] = {"error": str(e)}
        else:
            stats["memory_tiers"]["short_term"] = {"status": "recorder_not_available"}
            
        # Get long-term memory statistics
        if self._long_term_memory_recorder is not None:
            try:
                long_term_stats = self._long_term_memory_recorder.get_long_term_memory_statistics()
                stats["memory_tiers"]["long_term"] = long_term_stats
            except Exception as e:
                self._logger.error(f"Error getting long-term memory statistics: {e}")
                stats["memory_tiers"]["long_term"] = {"error": str(e)}
        else:
            stats["memory_tiers"]["long_term"] = {"status": "recorder_not_available"}
            
        # Get archival memory statistics
        if self._archival_memory_recorder is not None:
            try:
                archival_stats = self._archival_memory_recorder.get_archival_memory_statistics()
                stats["memory_tiers"]["archival"] = archival_stats
            except Exception as e:
                self._logger.error(f"Error getting archival memory statistics: {e}")
                stats["memory_tiers"]["archival"] = {"error": str(e)}
        else:
            stats["memory_tiers"]["archival"] = {"status": "recorder_not_available"}
            
        return stats


def main():
    """Main function for the memory consolidation process."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Memory Consolidation Process for NTFS Cognitive Memory System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # General options
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true",
                      help="Simulate consolidation without making changes")
    parser.add_argument("--db-config", type=str, default=None,
                      help="Path to database configuration file")
    
    # Consolidation options
    parser.add_argument("--sensory-days", type=int, default=2,
                      help="Number of days of sensory data to consolidate")
    parser.add_argument("--short-term-min-importance", type=float, default=0.3,
                      help="Minimum importance for short-term memory")
    parser.add_argument("--long-term-min-importance", type=float, default=0.7,
                      help="Minimum importance for long-term memory")
    parser.add_argument("--archival-min-importance", type=float, default=0.8,
                      help="Minimum importance for archival memory")
    parser.add_argument("--batch-size", type=int, default=100,
                      help="Number of entities to process in each batch")
    
    # Consolidation modes
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--consolidate-sensory", action="store_true",
                          help="Consolidate from sensory to short-term memory")
    mode_group.add_argument("--consolidate-short", action="store_true",
                          help="Consolidate from short-term to long-term memory")
    mode_group.add_argument("--consolidate-long", action="store_true",
                          help="Consolidate from long-term to archival memory")
    mode_group.add_argument("--consolidate-all", action="store_true",
                          help="Run all consolidation processes")
    mode_group.add_argument("--stats", action="store_true",
                          help="Get memory system statistics")
    
    # Output options
    parser.add_argument("--json", action="store_true",
                      help="Output results as JSON")
    parser.add_argument("--output-file", type=str,
                      help="Write results to a file instead of stdout")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = get_logger("memory_consolidation")
    
    # Create manager
    manager = MemoryConsolidationManager(
        db_config_path=args.db_config,
        sensory_days=args.sensory_days,
        short_term_min_importance=args.short_term_min_importance,
        long_term_min_importance=args.long_term_min_importance,
        archival_min_importance=args.archival_min_importance,
        entity_batch_size=args.batch_size,
        debug=args.debug
    )
    
    # Execute requested operation
    results = None
    
    try:
        if args.consolidate_sensory:
            if args.dry_run:
                logger.info("DRY RUN: Simulating sensory to short-term memory consolidation")
                results = {"status": "dry_run", "consolidation_type": "sensory_to_short_term"}
            else:
                results = manager.consolidate_sensory_to_short_term()
                
        elif args.consolidate_short:
            if args.dry_run:
                logger.info("DRY RUN: Simulating short-term to long-term memory consolidation")
                results = {"status": "dry_run", "consolidation_type": "short_term_to_long_term"}
            else:
                results = manager.consolidate_short_term_to_long_term()
                
        elif args.consolidate_long:
            if args.dry_run:
                logger.info("DRY RUN: Simulating long-term to archival memory consolidation")
                results = {"status": "dry_run", "consolidation_type": "long_term_to_archival"}
            else:
                results = manager.consolidate_long_term_to_archival()
                
        elif args.consolidate_all:
            if args.dry_run:
                logger.info("DRY RUN: Simulating all memory consolidation processes")
                results = {"status": "dry_run", "consolidation_type": "all"}
            else:
                results = manager.consolidate_all()
                
        elif args.stats:
            results = manager.get_statistics()
            
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        import traceback
        traceback.print_exc()
        results = {"error": str(e), "status": "error"}
        
    # Output results
    if results:
        if args.json:
            output = json.dumps(results, indent=2)
        else:
            # Generate text report
            if isinstance(results, dict):
                output = "=== Memory Consolidation Results ===\n\n"
                
                if "error" in results:
                    output += f"ERROR: {results['error']}\n"
                    
                if "consolidation_type" in results:
                    consolidation_type = results["consolidation_type"]
                    output += f"Consolidation Type: {consolidation_type}\n"
                    
                    if consolidation_type == "sensory_to_short_term":
                        output += f"Entities Processed: {results.get('entities_processed', 0)}\n"
                        output += f"Entities Consolidated: {results.get('entities_consolidated', 0)}\n"
                        output += f"Already in Short-Term: {results.get('already_in_short_term', 0)}\n"
                        output += f"Below Threshold: {results.get('below_threshold', 0)}\n"
                        output += f"Errors: {results.get('errors', 0)}\n"
                        
                    elif consolidation_type == "short_term_to_long_term":
                        output += f"Entities Processed: {results.get('entities_processed', 0)}\n"
                        output += f"Entities Consolidated: {results.get('entities_consolidated', 0)}\n"
                        output += f"Errors: {results.get('errors', 0)}\n"
                        
                    elif consolidation_type == "long_term_to_archival":
                        output += f"Entities Processed: {results.get('entities_processed', 0)}\n"
                        output += f"Entities Consolidated: {results.get('entities_consolidated', 0)}\n"
                        output += f"Errors: {results.get('errors', 0)}\n"
                        
                    elif consolidation_type == "all":
                        output += f"Total Entities Processed: {results.get('total_entities_processed', 0)}\n"
                        output += f"Total Entities Consolidated: {results.get('total_entities_consolidated', 0)}\n"
                        output += f"Total Errors: {results.get('total_errors', 0)}\n"
                        
                if "execution_time" in results:
                    output += f"Execution Time: {results['execution_time']:.2f} seconds\n"
                    
                if "timestamp" in results:
                    output += f"Timestamp: {results['timestamp']}\n"
                    
                # If it's stats, format memory tier statistics
                if "memory_tiers" in results:
                    output += "\n=== Memory System Statistics ===\n\n"
                    
                    for tier, tier_stats in results["memory_tiers"].items():
                        output += f"--- {tier.upper()} MEMORY ---\n"
                        
                        if "error" in tier_stats:
                            output += f"Error: {tier_stats['error']}\n"
                            continue
                            
                        if "status" in tier_stats:
                            output += f"Status: {tier_stats['status']}\n"
                            continue
                            
                        if "total_count" in tier_stats:
                            output += f"Total Count: {tier_stats['total_count']}\n"
                            
                        if tier == "short_term" and "eligible_for_long_term" in tier_stats:
                            output += f"Eligible for Long-Term: {tier_stats['eligible_for_long_term']}\n"
                            
                        if "by_importance" in tier_stats:
                            output += "Importance Distribution:\n"
                            for importance, count in tier_stats["by_importance"].items():
                                output += f"  {importance}: {count}\n"
                                
                        output += "\n"
            else:
                output = str(results)
                
        # Write output
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info(f"Results written to {args.output_file}")
        else:
            print(output)
            
    return 0


if __name__ == "__main__":
    main()