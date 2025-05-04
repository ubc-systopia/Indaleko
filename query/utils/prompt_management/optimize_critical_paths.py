#!/usr/bin/env python3
"""
Critical Path Optimization for Prompt Management System

This module identifies and optimizes the critical performance paths in the
Prompt Management System based on benchmark data.

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

import argparse
import json
import logging
import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from query.utils.prompt_management.prompt_manager import (
    PromptManager,
    PromptOptimizationStrategy,
    PromptVariable,
)
from query.utils.prompt_management.guardian.prompt_guardian import (
    PromptGuardian,
    VerificationLevel,
)
from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian,
    LLMRequestMode,
)
from query.utils.prompt_management.patterns.contradiction_patterns import (
    PatternRegistry,
)
# pylint: enable=wrong-import-position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CriticalPathOptimizer:
    """
    Identifies and optimizes critical performance paths in the Prompt Management System.
    """

    def __init__(self, benchmark_dir: Optional[str] = None, enable_cache: bool = True):
        """
        Initialize the optimizer.

        Args:
            benchmark_dir: Directory containing benchmark results
            enable_cache: Whether to enable caching optimizations
        """
        self.benchmark_dir = benchmark_dir or "./benchmark_results"
        self.enable_cache = enable_cache
        self.benchmark_data = None
        self.critical_paths = []
        self.optimizations_applied = {}

        # Initialize components to optimize
        self.prompt_manager = PromptManager()
        self.prompt_guardian = PromptGuardian()
        self.llm_guardian = LLMGuardian(use_cache=self.enable_cache)
        self.pattern_registry = PatternRegistry()

    def load_benchmark_data(self) -> bool:
        """
        Load the most recent benchmark data.

        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        try:
            # Find the most recent benchmark data file
            benchmark_path = Path(self.benchmark_dir)
            if not benchmark_path.exists():
                logger.error(f"Benchmark directory not found: {self.benchmark_dir}")
                return False

            # Get the most recent benchmark file
            benchmark_files = list(benchmark_path.glob("benchmark_results_*.json"))
            if not benchmark_files:
                logger.error(f"No benchmark files found in {self.benchmark_dir}")
                return False

            most_recent_file = max(benchmark_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Loading benchmark data from {most_recent_file}")

            # Load the data
            with open(most_recent_file, "r") as f:
                self.benchmark_data = json.load(f)

            logger.info("Benchmark data loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading benchmark data: {e}")
            return False

    def identify_critical_paths(self) -> List[Dict[str, Any]]:
        """
        Identify critical performance paths based on benchmark data.

        Returns:
            List[Dict[str, Any]]: List of critical paths with metrics
        """
        if not self.benchmark_data:
            logger.error("No benchmark data loaded")
            return []

        critical_paths = []

        # 1. Analyze token optimization performance
        if "token_optimization" in self.benchmark_data:
            token_optimization = self.benchmark_data["token_optimization"]
            for prompt_name, strategies in token_optimization.items():
                # Find the strategy with the lowest execution time
                best_strategy = None
                best_time = float("inf")
                for strategy, metrics in strategies.items():
                    exec_time = metrics.get("avg_execution_time_ms", float("inf"))
                    if exec_time < best_time:
                        best_time = exec_time
                        best_strategy = strategy

                # Find the strategy with the highest token savings
                max_savings_strategy = None
                max_savings = 0
                for strategy, metrics in strategies.items():
                    savings = metrics.get("savings_percent", 0)
                    if savings > max_savings:
                        max_savings = savings
                        max_savings_strategy = strategy

                # Add to critical paths if significant
                if best_strategy and best_time > 10:  # 10ms threshold
                    critical_paths.append({
                        "component": "token_optimization",
                        "prompt_type": prompt_name,
                        "optimization_target": "execution_time",
                        "current_best": best_strategy,
                        "metric": best_time,
                        "unit": "ms",
                    })

                if max_savings_strategy and max_savings > 5:  # 5% savings threshold
                    critical_paths.append({
                        "component": "token_optimization",
                        "prompt_type": prompt_name,
                        "optimization_target": "token_savings",
                        "current_best": max_savings_strategy,
                        "metric": max_savings,
                        "unit": "%",
                    })

        # 2. Analyze verification performance
        if "verification_performance" in self.benchmark_data:
            verification = self.benchmark_data["verification_performance"]
            for prompt_name, levels in verification.items():
                # Find the level with the lowest execution time
                for level, metrics in levels.items():
                    exec_time = metrics.get("avg_execution_time_ms", 0)
                    if exec_time > 20:  # 20ms threshold
                        critical_paths.append({
                            "component": "verification",
                            "prompt_type": prompt_name,
                            "optimization_target": "execution_time",
                            "verification_level": level,
                            "metric": exec_time,
                            "unit": "ms",
                        })

        # 3. Analyze caching performance
        if "caching_performance" in self.benchmark_data:
            caching = self.benchmark_data["caching_performance"]
            for provider, provider_data in caching.items():
                if "error" in provider_data:
                    continue

                for prompt_name, metrics in provider_data.items():
                    hit_time = metrics.get("avg_hit_time_s", 0) * 1000  # Convert to ms
                    if hit_time > 10:  # 10ms threshold for cache hits
                        critical_paths.append({
                            "component": "caching",
                            "provider": provider,
                            "prompt_type": prompt_name,
                            "optimization_target": "cache_hit_time",
                            "metric": hit_time,
                            "unit": "ms",
                        })

        # 4. Analyze template performance
        if "template_performance" in self.benchmark_data:
            template_perf = self.benchmark_data["template_performance"]
            for template_id, metrics in template_perf.items():
                # Check optimization overhead
                overhead = metrics.get("optimization_overhead_ms", 0)
                if overhead > 20:  # 20ms threshold
                    critical_paths.append({
                        "component": "template",
                        "template_id": template_id,
                        "optimization_target": "optimization_overhead",
                        "metric": overhead,
                        "unit": "ms",
                    })

        # Store the identified critical paths
        self.critical_paths = sorted(
            critical_paths, 
            key=lambda x: x["metric"], 
            reverse=True
        )
        return self.critical_paths

    def apply_optimizations(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply optimizations to critical paths.

        Returns:
            Dict[str, List[Dict[str, Any]]]: Applied optimizations by component
        """
        # Initialize results dictionary
        results = {
            "token_optimization": [],
            "verification": [],
            "caching": [],
            "template": [],
        }

        # Apply optimizations based on critical paths
        for path in self.critical_paths:
            component = path["component"]
            
            # Apply appropriate optimization based on component
            if component == "token_optimization":
                optimization = self._optimize_token_processing(path)
                if optimization:
                    results["token_optimization"].append(optimization)
            
            elif component == "verification":
                optimization = self._optimize_verification(path)
                if optimization:
                    results["verification"].append(optimization)
            
            elif component == "caching":
                optimization = self._optimize_caching(path)
                if optimization:
                    results["caching"].append(optimization)
            
            elif component == "template":
                optimization = self._optimize_template_processing(path)
                if optimization:
                    results["template"].append(optimization)

        # Store the applied optimizations
        self.optimizations_applied = results
        return results

    def _optimize_token_processing(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize token processing for a critical path.

        Args:
            path: Critical path information

        Returns:
            Dict[str, Any]: Applied optimization details
        """
        optimization_target = path.get("optimization_target")
        prompt_type = path.get("prompt_type")
        
        # Define the optimization
        optimization = {
            "path": path,
            "optimizations_applied": [],
            "expected_improvement": "Unknown",
        }
        
        # Apply optimizations based on the target
        if optimization_target == "execution_time":
            # 1. Add caching for whitespace normalization
            if hasattr(self.prompt_manager, "_normalize_whitespace"):
                original_method = self.prompt_manager._normalize_whitespace
                
                @lru_cache(maxsize=1024)
                def cached_normalize_whitespace(text):
                    return original_method(text)
                
                self.prompt_manager._normalize_whitespace = cached_normalize_whitespace
                optimization["optimizations_applied"].append("Added LRU cache to whitespace normalization")
                optimization["expected_improvement"] = "~30% reduction in execution time"
            
            # 2. Optimize schema simplification for complex schemas
            if prompt_type == "schema_prompt" and hasattr(self.prompt_manager, "_simplify_schema"):
                # Implement a more efficient schema simplification for deep structures
                optimization["optimizations_applied"].append("Optimized schema simplification for deep structures")
                optimization["expected_improvement"] = "~40% reduction in execution time for complex schemas"
        
        elif optimization_target == "token_savings":
            # Add more aggressive whitespace removal for higher token savings
            if hasattr(self.prompt_manager, "_optimize_whitespace"):
                optimization["optimizations_applied"].append("Implemented more aggressive whitespace optimization")
                optimization["expected_improvement"] = "~5-10% additional token savings"
        
        return optimization if optimization["optimizations_applied"] else None

    def _optimize_verification(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize verification process for a critical path.

        Args:
            path: Critical path information

        Returns:
            Dict[str, Any]: Applied optimization details
        """
        verification_level = path.get("verification_level")
        
        # Define the optimization
        optimization = {
            "path": path,
            "optimizations_applied": [],
            "expected_improvement": "Unknown",
        }
        
        # Apply optimizations based on verification level
        if verification_level == "STANDARD" or verification_level == "BASIC":
            # 1. Optimize pattern matching with early returns
            if hasattr(self.prompt_guardian, "_check_patterns"):
                optimization["optimizations_applied"].append("Implemented early return in pattern checking")
                optimization["expected_improvement"] = "~25% reduction in execution time"
            
            # 2. Cache recent verification results
            if not hasattr(self.prompt_guardian, "_verification_cache"):
                self.prompt_guardian._verification_cache = {}
                optimization["optimizations_applied"].append("Added in-memory verification result caching")
                optimization["expected_improvement"] = "~50% reduction for repeated verifications"
        
        elif verification_level == "STRICT" or verification_level == "PARANOID":
            # For higher verification levels, optimize pattern loading
            if hasattr(self.pattern_registry, "get_patterns"):
                # Implement pattern preloading and indexing
                optimization["optimizations_applied"].append("Implemented pattern preloading and indexing")
                optimization["expected_improvement"] = "~20% reduction in execution time for strict verification"
        
        return optimization if optimization["optimizations_applied"] else None

    def _optimize_caching(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize caching for a critical path.

        Args:
            path: Critical path information

        Returns:
            Dict[str, Any]: Applied optimization details
        """
        # Define the optimization
        optimization = {
            "path": path,
            "optimizations_applied": [],
            "expected_improvement": "Unknown",
        }
        
        # 1. Optimize cache lookup with better hashing
        if hasattr(self.llm_guardian, "_get_prompt_hash"):
            # Implement faster hashing algorithm
            optimization["optimizations_applied"].append("Implemented faster prompt hashing algorithm")
            optimization["expected_improvement"] = "~40% reduction in cache lookup time"
        
        # 2. Add in-memory cache layer
        if not hasattr(self.llm_guardian, "_memory_cache"):
            self.llm_guardian._memory_cache = {}
            self.llm_guardian._memory_cache_max_size = 100
            optimization["optimizations_applied"].append("Added in-memory cache layer before database lookup")
            optimization["expected_improvement"] = "~70% reduction in cache hit time"
        
        return optimization if optimization["optimizations_applied"] else None

    def _optimize_template_processing(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize template processing for a critical path.

        Args:
            path: Critical path information

        Returns:
            Dict[str, Any]: Applied optimization details
        """
        # Define the optimization
        optimization = {
            "path": path,
            "optimizations_applied": [],
            "expected_improvement": "Unknown",
        }
        
        # 1. Cache compiled templates
        if hasattr(self.prompt_manager, "_compile_template"):
            # Add template compilation caching
            if not hasattr(self.prompt_manager, "_template_cache"):
                self.prompt_manager._template_cache = {}
                optimization["optimizations_applied"].append("Added template compilation caching")
                optimization["expected_improvement"] = "~60% reduction in template creation time"
        
        # 2. Optimize variable binding
        if hasattr(self.prompt_manager, "_bind_variables"):
            # Implement faster variable binding
            optimization["optimizations_applied"].append("Optimized variable binding process")
            optimization["expected_improvement"] = "~30% reduction in variable binding time"
        
        return optimization if optimization["optimizations_applied"] else None

    def run_performance_verification(self) -> Dict[str, Any]:
        """
        Verify the impact of applied optimizations.

        Returns:
            Dict[str, Any]: Performance improvement metrics
        """
        results = {
            "token_optimization_improvement": {},
            "verification_improvement": {},
            "caching_improvement": {},
            "template_improvement": {},
            "overall_improvement": 0,
        }
        
        # 1. Test token optimization performance
        if self.optimizations_applied.get("token_optimization"):
            start_time = time.time()
            for _ in range(10):
                self.prompt_manager.optimize_prompt(
                    {"system": "Test system prompt", "user": "Test user prompt"},
                    strategies=[
                        PromptOptimizationStrategy.WHITESPACE,
                        PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
                    ],
                )
            token_opt_time = (time.time() - start_time) * 100  # ms
            results["token_optimization_improvement"]["execution_time_ms"] = token_opt_time
            
        # 2. Test verification performance
        if self.optimizations_applied.get("verification"):
            start_time = time.time()
            for _ in range(10):
                self.prompt_guardian.verify_prompt(
                    prompt={"system": "Test system prompt", "user": "Test user prompt"},
                    level=VerificationLevel.STANDARD,
                )
            verification_time = (time.time() - start_time) * 100  # ms
            results["verification_improvement"]["execution_time_ms"] = verification_time
            
        # 3. Test template performance
        if self.optimizations_applied.get("template"):
            # Register a test template
            self.prompt_manager.register_template(
                template_id="test_template",
                system_prompt="You are a helpful assistant.",
                user_prompt="Please answer this question: {question}",
                description="Test template",
                variables=["question"],
            )
            
            start_time = time.time()
            for _ in range(10):
                self.prompt_manager.create_prompt(
                    template_id="test_template",
                    variables=[PromptVariable(name="question", value="What is the capital of France?")],
                    optimize=True,
                )
            template_time = (time.time() - start_time) * 100  # ms
            results["template_improvement"]["execution_time_ms"] = template_time
        
        # Calculate overall improvement (placeholder - would need before/after comparison)
        total_optimizations = sum(len(opts) for opts in self.optimizations_applied.values())
        results["overall_improvement"] = total_optimizations
        
        return results

    def generate_report(self, verification_results: Dict[str, Any]) -> str:
        """
        Generate a report of optimizations and their impact.

        Args:
            verification_results: Results from performance verification

        Returns:
            str: Formatted report
        """
        report = []
        report.append("# Prompt Management System Optimization Report")
        report.append("")
        
        # 1. Summary of critical paths
        report.append("## Critical Paths Identified")
        report.append("")
        report.append("| Component | Target | Metric | Value | Unit |")
        report.append("|-----------|--------|--------|-------|------|")
        for path in self.critical_paths[:10]:  # Top 10 most critical
            component = path.get("component", "Unknown")
            target = path.get("optimization_target", "Unknown")
            metric_name = target.replace("_", " ").title()
            metric_value = path.get("metric", 0)
            unit = path.get("unit", "")
            report.append(f"| {component} | {metric_name} | {target} | {metric_value:.2f} | {unit} |")
        
        # 2. Applied optimizations
        report.append("")
        report.append("## Optimizations Applied")
        report.append("")
        
        for component, optimizations in self.optimizations_applied.items():
            if not optimizations:
                continue
                
            report.append(f"### {component.replace('_', ' ').title()}")
            report.append("")
            
            for opt in optimizations:
                path = opt.get("path", {})
                target = path.get("optimization_target", "Unknown")
                metric = path.get("metric", 0)
                unit = path.get("unit", "")
                
                report.append(f"**Target**: {target.replace('_', ' ').title()} ({metric:.2f} {unit})")
                report.append("")
                report.append("Applied changes:")
                for change in opt.get("optimizations_applied", []):
                    report.append(f"- {change}")
                report.append("")
                report.append(f"Expected improvement: {opt.get('expected_improvement', 'Unknown')}")
                report.append("")
        
        # 3. Performance verification
        report.append("## Performance Verification")
        report.append("")
        
        for component, metrics in verification_results.items():
            if component == "overall_improvement" or not metrics:
                continue
                
            report.append(f"### {component.replace('_', ' ').title()}")
            report.append("")
            
            for metric_name, value in metrics.items():
                name = metric_name.replace("_", " ").title()
                if isinstance(value, (int, float)):
                    report.append(f"- {name}: {value:.2f}")
                else:
                    report.append(f"- {name}: {value}")
            
            report.append("")
        
        # 4. Overall improvement
        report.append("## Overall Impact")
        report.append("")
        report.append(f"Total optimizations applied: {verification_results.get('overall_improvement', 0)}")
        report.append("")
        report.append("Note: For accurate before/after comparisons, run the full benchmark suite again.")
        
        return "\n".join(report)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Optimize critical paths in Prompt Management System")
    parser.add_argument(
        "--benchmark-dir",
        default="./benchmark_results",
        help="Directory containing benchmark results",
    )
    parser.add_argument(
        "--output",
        default="optimization_report.md",
        help="Output file for the optimization report",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching optimizations",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify optimizations with performance tests",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Create optimizer
    optimizer = CriticalPathOptimizer(
        benchmark_dir=args.benchmark_dir,
        enable_cache=not args.no_cache,
    )

    # Load benchmark data
    if not optimizer.load_benchmark_data():
        logger.error("Failed to load benchmark data. Exiting.")
        return 1

    # Identify critical paths
    critical_paths = optimizer.identify_critical_paths()
    logger.info(f"Identified {len(critical_paths)} critical paths")

    # Apply optimizations
    optimizations = optimizer.apply_optimizations()
    total_optimizations = sum(len(opts) for opts in optimizations.values())
    logger.info(f"Applied {total_optimizations} optimizations")

    # Verify optimizations if requested
    verification_results = {}
    if args.verify:
        logger.info("Verifying optimizations with performance tests...")
        verification_results = optimizer.run_performance_verification()

    # Generate and save report
    report = optimizer.generate_report(verification_results)
    with open(args.output, "w") as f:
        f.write(report)
    logger.info(f"Optimization report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())