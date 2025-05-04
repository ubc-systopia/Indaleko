#!/usr/bin/env python3
"""
Script to apply critical path optimizations to the Prompt Management System.

This script:
1. Runs benchmarks to identify bottlenecks
2. Applies recommended optimizations from the CriticalPathOptimizer
3. Runs benchmarks again to verify improvements
4. Generates an optimization report
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Set up the environment for imports
current_path = Path(__file__).parent.resolve()
if str(current_path) not in sys.path:
    sys.path.insert(0, str(current_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import Indaleko components
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian
from query.utils.prompt_management.optimize_critical_paths import CriticalPathOptimizer
from query.utils.prompt_management.prompt_manager import (
    PromptManager,
    PromptOptimizationStrategy,
)


def create_benchmark_data(benchmark_dir):
    """
    Create benchmark data for the CriticalPathOptimizer to analyze.

    This is a simplified version that creates benchmark data directly
    rather than running the full benchmark suite.
    """
    logger.info("Creating benchmark data...")

    # Create benchmark directory if it doesn't exist
    os.makedirs(benchmark_dir, exist_ok=True)

    # Initialize components for benchmarking
    prompt_manager = PromptManager()
    prompt_guardian = PromptGuardian()
    llm_guardian = LLMGuardian(use_cache=True)

    # Test prompts
    test_prompts = {
        "simple_prompt": {"system": "You are a helpful assistant.", "user": "Tell me about Indaleko."},
        "medium_prompt": {
            "system": "You are a helpful assistant that can translate natural language to AQL.",
            "user": """
            Please translate the following natural language query to AQL:

            "Find all documents created in the last week that contain the word 'important'
            and are related to the project 'Indaleko'."

            Format your response as a JSON object with the following fields:
            - query: the original query
            - translated_query: the AQL translation
            - explanation: brief explanation of the translation
            """,
        },
        "complex_prompt": {
            "system": "You are a helpful assistant with expertise in data analysis and ArangoDB.",
            "user": """
            Please analyze the following requirements and generate appropriate AQL queries:

            The Indaleko system stores data in the following collections:
            - Objects: Contains document records with fields like Name, Path, Size, CreationTime, ModificationTime, Tags
            - Relationships: Contains edges that connect Objects with fields like RelationType, Direction
            - Activities: Contains records of user actions with fields like Action, Timestamp, User, ObjectID
            - SemanticData: Contains extracted metadata with fields like ObjectID, Type, Value

            I need to:
            1. Find all documents modified by user "John" in the last month
            2. Find all images (files with extension .jpg, .png, .gif) that were viewed in the last week
            3. Identify potential duplicate files based on size and checksum
            4. Find all documents that reference "Project X" in their content

            For each of these requirements, please:
            1. Generate an AQL query
            2. Explain the query logic
            3. Suggest any indexes that would improve performance

            Format your response as a JSON object with keys for each requirement.
            """,
        },
        "schema_prompt": {
            "system": "You are a helpful assistant that can extract structured data.",
            "user": """
            Please extract structured data from the following text according to this schema:

            {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the entity"
                                },
                                "type": {
                                    "type": "string",
                                    "enum": ["person", "organization", "location", "date", "other"],
                                    "description": "Type of entity"
                                },
                                "context": {
                                    "type": "string",
                                    "description": "Context in which the entity appears"
                                },
                                "relevance": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": "Relevance score from 0 to 1"
                                }
                            },
                            "required": ["name", "type"]
                        }
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of the text"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of keywords extracted from the text"
                    },
                    "sentiment": {
                        "type": "object",
                        "properties": {
                            "overall": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral", "mixed"],
                                "description": "Overall sentiment of the text"
                            },
                            "score": {
                                "type": "number",
                                "minimum": -1,
                                "maximum": 1,
                                "description": "Sentiment score from -1 (very negative) to 1 (very positive)"
                            }
                        }
                    }
                }
            }

            Text to analyze:

            "Indaleko Inc. announced a strategic partnership with Microsoft on January 15, 2024.
            CEO Sarah Johnson stated that this collaboration will accelerate their development of
            next-generation data management solutions. The news was well-received by investors,
            with the company's stock rising 12% in New York trading. Analyst Tom Peterson from
            Global Research described the partnership as 'transformative' for the data management sector.
            The companies plan to launch their first joint product in Q3 2024."
            """,
        },
    }

    # Build benchmark data structure
    benchmark_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "description": "Simple benchmark data for optimization analysis",
        },
        "token_optimization": {},
        "verification_performance": {},
        "caching_performance": {},
        "template_performance": {},
    }

    # 1. Token optimization benchmarks
    logger.info("Measuring token optimization performance...")
    token_optimization = {}
    strategies_to_test = [
        [],  # No optimization
        [PromptOptimizationStrategy.WHITESPACE],
        [PromptOptimizationStrategy.SCHEMA_SIMPLIFY],
        [PromptOptimizationStrategy.EXAMPLE_REDUCTION],
        [PromptOptimizationStrategy.WHITESPACE, PromptOptimizationStrategy.SCHEMA_SIMPLIFY],
    ]

    for prompt_name, prompt in test_prompts.items():
        prompt_results = {}

        for strategies in strategies_to_test:
            strategy_names = [s.name for s in strategies] if strategies else ["NONE"]
            strategy_key = "-".join(strategy_names)

            # Measure execution time and token savings
            start_time = time.time()
            result = prompt_manager.optimize_prompt(prompt, strategies=strategies)
            execution_time = time.time() - start_time

            prompt_results[strategy_key] = {
                "original_token_count": result.original_token_count,
                "avg_token_count": result.token_count,
                "avg_token_savings": result.token_savings,
                "avg_execution_time_ms": execution_time * 1000,
                "savings_percent": (
                    (result.token_savings / result.original_token_count) * 100 if result.original_token_count > 0 else 0
                ),
            }

        token_optimization[prompt_name] = prompt_results

    benchmark_data["token_optimization"] = token_optimization

    # 2. Verification performance benchmarks
    logger.info("Measuring verification performance...")
    verification_performance = {}
    verification_levels = [
        "NONE",
        "BASIC",
        "STANDARD",
        "STRICT",
        "PARANOID",
    ]

    for prompt_name, prompt in test_prompts.items():
        prompt_results = {}

        for level_name in verification_levels:
            level = getattr(PromptGuardian.VerificationLevel, level_name)

            # Measure execution time
            start_time = time.time()
            verification = prompt_guardian.verify_prompt(prompt=prompt, level=level)
            execution_time = time.time() - start_time

            prompt_results[level_name] = {
                "avg_execution_time_ms": execution_time * 1000,
                "allowed_percent": 100 if verification.allowed else 0,
                "avg_score": verification.score,
            }

        verification_performance[prompt_name] = prompt_results

    benchmark_data["verification_performance"] = verification_performance

    # 3. Caching performance (simplified)
    logger.info("Measuring caching performance...")
    caching_performance = {"openai": {}}  # We'll simulate with just one provider

    for prompt_name, prompt in test_prompts.items():
        guardian = LLMGuardian(use_cache=True)

        # First request (cache miss)
        start_time = time.time()
        guardian.prepare_prompt(prompt, optimize=True)
        miss_time = time.time() - start_time

        # Second request (cache hit)
        start_time = time.time()
        guardian.prepare_prompt(prompt, optimize=True)
        hit_time = time.time() - start_time

        caching_performance["openai"][prompt_name] = {
            "avg_miss_time_s": miss_time,
            "avg_hit_time_s": hit_time,
            "time_savings_s": miss_time - hit_time,
            "time_savings_percent": (((miss_time - hit_time) / miss_time) * 100 if miss_time > 0 else 0),
        }

    benchmark_data["caching_performance"] = caching_performance

    # 4. Template performance
    logger.info("Measuring template performance...")
    template_performance = {}

    # Register test templates
    templates = {
        "aql_translation": {
            "system_prompt": (
                "You are an expert at translating natural language queries to AQL. "
                "Your translations are precise, efficient, and optimize for performance."
            ),
            "user_prompt": (
                "Please translate the following query to AQL:\n\n"
                "Query: {query}\n\n"
                "Format your response as a JSON object with the following fields:\n"
                "- translated_query: the AQL translation\n"
                "- explanation: brief explanation of the query"
            ),
            "description": "Template for translating natural language to AQL",
            "variables": ["query"],
        },
        "entity_extraction": {
            "system_prompt": (
                "You are an expert at extracting named entities from text. "
                "Accurately identify people, organizations, locations, and dates."
            ),
            "user_prompt": (
                "Extract named entities from the following text:\n\n"
                "{text}\n\n"
                "Format your response as a JSON array of objects with 'entity', 'type', and 'context' fields."
            ),
            "description": "Template for extracting named entities from text",
            "variables": ["text"],
        },
    }

    for template_id, template in templates.items():
        prompt_manager.register_template(
            template_id=template_id,
            system_prompt=template["system_prompt"],
            user_prompt=template["user_prompt"],
            description=template["description"],
            variables=template["variables"],
        )

        # Regular template creation
        start_time = time.time()
        prompt_manager.create_prompt(
            template_id=template_id,
            variables=(
                [{"name": "query", "value": "Find documents modified in the last week"}]
                if template_id == "aql_translation"
                else [{"name": "text", "value": "Microsoft CEO Satya Nadella spoke at the conference in Seattle."}]
            ),
            optimize=False,
        )
        regular_time = time.time() - start_time

        # Optimized template creation
        start_time = time.time()
        result = prompt_manager.create_prompt(
            template_id=template_id,
            variables=(
                [{"name": "query", "value": "Find documents modified in the last week"}]
                if template_id == "aql_translation"
                else [{"name": "text", "value": "Microsoft CEO Satya Nadella spoke at the conference in Seattle."}]
            ),
            optimize=True,
        )
        optimized_time = time.time() - start_time

        template_performance[template_id] = {
            "regular": {
                "avg_creation_time_ms": regular_time * 1000,
                "avg_token_count": result.original_token_count,
                "avg_token_savings": 0,
            },
            "optimized": {
                "avg_creation_time_ms": optimized_time * 1000,
                "avg_token_count": result.token_count,
                "avg_token_savings": result.token_savings,
                "savings_percent": (
                    (result.token_savings / result.original_token_count) * 100 if result.original_token_count > 0 else 0
                ),
            },
            "optimization_overhead_ms": (optimized_time - regular_time) * 1000,
            "optimization_overhead_percent": (
                ((optimized_time - regular_time) / regular_time) * 100 if regular_time > 0 else 0
            ),
        }

    benchmark_data["template_performance"] = template_performance

    # Save benchmark data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_file = os.path.join(benchmark_dir, f"benchmark_results_{timestamp}.json")

    with open(benchmark_file, "w") as f:
        import json

        json.dump(benchmark_data, f, indent=2)

    logger.info(f"Benchmark data saved to {benchmark_file}")
    return benchmark_file


def apply_optimizations(benchmark_file, output_file="optimization_report.md", verify=True):
    """
    Apply optimizations based on the benchmark data.
    """
    logger.info(f"Applying optimizations based on benchmark data from {benchmark_file}")

    # Create optimizer
    optimizer = CriticalPathOptimizer(
        benchmark_dir=os.path.dirname(benchmark_file),
        enable_cache=True,
    )

    # Load benchmark data
    if not optimizer.load_benchmark_data():
        logger.error("Failed to load benchmark data. Exiting.")
        return False

    # Identify critical paths
    critical_paths = optimizer.identify_critical_paths()
    logger.info(f"Identified {len(critical_paths)} critical paths")

    # Apply optimizations
    optimizations = optimizer.apply_optimizations()
    total_optimizations = sum(len(opts) for opts in optimizations.values())
    logger.info(f"Applied {total_optimizations} optimizations")

    # Verify optimizations if requested
    verification_results = {}
    if verify:
        logger.info("Verifying optimizations with performance tests...")
        verification_results = optimizer.run_performance_verification()

    # Generate and save report
    report = optimizer.generate_report(verification_results)
    with open(output_file, "w") as f:
        f.write(report)
    logger.info(f"Optimization report saved to {output_file}")

    return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Apply critical path optimizations to the Prompt Management System")
    parser.add_argument(
        "--benchmark-dir",
        default="./benchmark_results",
        help="Directory for benchmark results",
    )
    parser.add_argument(
        "--output",
        default="optimization_report.md",
        help="Output file for the optimization report",
    )
    parser.add_argument(
        "--skip-benchmarks",
        action="store_true",
        help="Skip benchmarking and use existing data",
    )
    parser.add_argument(
        "--benchmark-file",
        help="Specific benchmark file to use (if skipping benchmarks)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification step",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    benchmark_file = None

    # Run benchmarks or use existing data
    if not args.skip_benchmarks:
        logger.info("Running benchmarks to identify performance bottlenecks...")
        benchmark_file = create_benchmark_data(args.benchmark_dir)
    elif args.benchmark_file:
        benchmark_file = args.benchmark_file
    else:
        # Find the most recent benchmark file
        benchmark_dir = Path(args.benchmark_dir)
        if not benchmark_dir.exists():
            logger.error(f"Benchmark directory not found: {args.benchmark_dir}")
            return 1

        benchmark_files = list(benchmark_dir.glob("benchmark_results_*.json"))
        if not benchmark_files:
            logger.error(f"No benchmark files found in {args.benchmark_dir}")
            return 1

        benchmark_file = str(max(benchmark_files, key=lambda p: p.stat().st_mtime))

    logger.info(f"Using benchmark file: {benchmark_file}")

    # Apply optimizations
    success = apply_optimizations(
        benchmark_file=benchmark_file,
        output_file=args.output,
        verify=not args.no_verify,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
