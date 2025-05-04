#!/usr/bin/env python3
"""
Performance benchmarking script for the Prompt Management System.

This script runs a series of benchmarks to measure:
1. Token optimization effectiveness
2. Verification speed
3. Caching performance
4. Response time with/without guardian
5. Memory usage
"""

import os
import time
import json
import gc
import statistics
import tracemalloc
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import argparse
import logging
import matplotlib.pyplot as plt
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import Indaleko components
from query.utils.llm_connector.factory_updated import LLMFactory
from query.utils.prompt_management.prompt_manager import (
    PromptManager, 
    PromptOptimizationStrategy,
    PromptVariable
)
from query.utils.prompt_management.guardian.prompt_guardian import (
    PromptGuardian,
    VerificationLevel
)
from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian,
    LLMRequestMode
)

# Define benchmark config
DEFAULT_REPEATS = 5
DEFAULT_OUTPUT_DIR = "./benchmark_results"
DEFAULT_PROVIDERS = ["openai"]
AVAILABLE_PROVIDERS = ["openai", "anthropic", "gemma", "google"]

# Test prompts
TEST_PROMPTS = {
    "simple_prompt": {
        "system": "You are a helpful assistant.",
        "user": "Tell me about Indaleko."
    },
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
        """
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
        """
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
        """
    }
}

# Template definitions for testing
TEST_TEMPLATES = {
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
        "examples": [
            {"query": "Find all documents created last week"},
            {"query": "Show me documents tagged as 'important'"}
        ]
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
        "examples": [
            {"text": "Apple CEO Tim Cook announced new products at their Cupertino headquarters on Tuesday."}
        ]
    }
}

# Test cases for template-based benchmarks
TEST_TEMPLATE_VARIABLES = {
    "aql_translation": [
        {"query": "Find documents modified in the last week"},
        {"query": "Show me files larger than 1MB created by John"},
        {"query": "Find all PDF documents that contain the word 'project' and were modified in the last month"}
    ],
    "entity_extraction": [
        {"text": "Microsoft CEO Satya Nadella spoke at the conference in Seattle on Monday."},
        {"text": "The University of California opened a new research center in Los Angeles."},
        {"text": "Tesla announced record profits for Q4 2023, exceeding Wall Street expectations."}
    ]
}


class PromptManagementBenchmark:
    """Benchmark class for measuring prompt management system performance."""
    
    def __init__(
        self, 
        output_dir: str = DEFAULT_OUTPUT_DIR,
        repeats: int = DEFAULT_REPEATS,
        providers: List[str] = None,
        use_db: bool = False,
    ):
        """Initialize the benchmark runner.
        
        Args:
            output_dir: Directory to save benchmark results
            repeats: Number of repetitions for each test
            providers: List of LLM providers to test
            use_db: Whether to use database for templates and caching
        """
        self.output_dir = output_dir
        self.repeats = repeats
        self.providers = providers or DEFAULT_PROVIDERS
        self.use_db = use_db
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Results storage
        self.results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "repeats": repeats,
                "providers": self.providers,
                "use_db": self.use_db,
            },
            "token_optimization": {},
            "verification_performance": {},
            "caching_performance": {},
            "response_time": {},
            "memory_usage": {},
            "template_performance": {},
        }
        
        # Initialize components
        self.factory = LLMFactory()
        self.prompt_manager = PromptManager()
        self.prompt_guardian = PromptGuardian()
        self.llm_guardian = LLMGuardian(use_cache=True)
        
        # Register test templates
        for template_id, template in TEST_TEMPLATES.items():
            self.prompt_manager.register_template(
                template_id=template_id,
                system_prompt=template["system_prompt"],
                user_prompt=template["user_prompt"],
                description=template["description"],
                variables=template["variables"],
                examples=template.get("examples", [])
            )
        
        logger.info(f"Benchmark initialized with {len(self.providers)} providers")
    
    def run_all_benchmarks(self):
        """Run all benchmarks and save results."""
        logger.info("Starting comprehensive benchmarks")
        
        # Run individual benchmarks
        self.benchmark_token_optimization()
        self.benchmark_verification_performance()
        self.benchmark_caching_performance()
        self.benchmark_response_time()
        self.benchmark_memory_usage()
        self.benchmark_template_performance()
        
        # Save results
        self.save_results()
        
        # Generate visualizations
        self.generate_visualizations()
        
        logger.info("All benchmarks completed")
    
    def benchmark_token_optimization(self):
        """Benchmark token optimization strategies."""
        logger.info("Benchmarking token optimization strategies")
        
        results = {}
        
        # Define strategies to test
        strategies_to_test = [
            [],  # No optimization
            [PromptOptimizationStrategy.WHITESPACE],
            [PromptOptimizationStrategy.SCHEMA_SIMPLIFY],
            [PromptOptimizationStrategy.EXAMPLE_REDUCTION],
            [PromptOptimizationStrategy.WHITESPACE, PromptOptimizationStrategy.SCHEMA_SIMPLIFY],
            [PromptOptimizationStrategy.WHITESPACE, PromptOptimizationStrategy.SCHEMA_SIMPLIFY, 
             PromptOptimizationStrategy.EXAMPLE_REDUCTION],
        ]
        
        for prompt_name, prompt in TEST_PROMPTS.items():
            prompt_results = {}
            
            for strategies in strategies_to_test:
                strategy_names = [s.name for s in strategies] if strategies else ["NONE"]
                strategy_key = "-".join(strategy_names)
                
                # Run multiple times for consistency
                token_counts = []
                token_savings = []
                execution_times = []
                
                for _ in range(self.repeats):
                    start_time = time.time()
                    result = self.prompt_manager.optimize_prompt(prompt, strategies=strategies)
                    execution_time = time.time() - start_time
                    
                    token_counts.append(result.token_count)
                    token_savings.append(result.token_savings)
                    execution_times.append(execution_time)
                
                # Calculate statistics
                prompt_results[strategy_key] = {
                    "original_token_count": result.original_token_count,
                    "avg_token_count": statistics.mean(token_counts),
                    "avg_token_savings": statistics.mean(token_savings),
                    "avg_execution_time_ms": statistics.mean(execution_times) * 1000,
                    "savings_percent": (statistics.mean(token_savings) / result.original_token_count) * 100 
                        if result.original_token_count > 0 else 0,
                }
            
            results[prompt_name] = prompt_results
        
        self.results["token_optimization"] = results
        logger.info("Token optimization benchmark completed")
    
    def benchmark_verification_performance(self):
        """Benchmark verification performance across levels."""
        logger.info("Benchmarking verification performance")
        
        results = {}
        
        # Test different verification levels
        levels_to_test = [
            VerificationLevel.NONE,
            VerificationLevel.BASIC,
            VerificationLevel.STANDARD,
            VerificationLevel.STRICT,
            VerificationLevel.PARANOID
        ]
        
        for prompt_name, prompt in TEST_PROMPTS.items():
            prompt_results = {}
            
            for level in levels_to_test:
                # Run multiple times for consistency
                execution_times = []
                allowed_results = []
                scores = []
                
                for _ in range(self.repeats):
                    start_time = time.time()
                    verification = self.prompt_guardian.verify_prompt(prompt=prompt, level=level)
                    execution_time = time.time() - start_time
                    
                    execution_times.append(execution_time)
                    allowed_results.append(1 if verification.allowed else 0)
                    scores.append(verification.score)
                
                # Calculate statistics
                prompt_results[level.name] = {
                    "avg_execution_time_ms": statistics.mean(execution_times) * 1000,
                    "allowed_percent": (sum(allowed_results) / len(allowed_results)) * 100,
                    "avg_score": statistics.mean(scores),
                    "warnings": verification.warnings,
                    "reasons": verification.reasons if hasattr(verification, "reasons") else []
                }
            
            results[prompt_name] = prompt_results
        
        self.results["verification_performance"] = results
        logger.info("Verification performance benchmark completed")
    
    def benchmark_caching_performance(self):
        """Benchmark caching performance."""
        logger.info("Benchmarking caching performance")
        
        results = {}
        
        for provider in self.providers:
            try:
                provider_results = {}
                
                # Create guardian with caching
                guardian = LLMGuardian(
                    use_cache=True,
                    cache_ttl=3600,
                    archive_ttl=86400
                )
                
                # Get connector with guardian
                connector = self.factory.create_connector(
                    connector_type=provider,
                    use_guardian=True,
                    guardian_instance=guardian
                )
                
                for prompt_name, prompt in TEST_PROMPTS.items():
                    # First request (cache miss)
                    miss_times = []
                    for _ in range(self.repeats):
                        start_time = time.time()
                        _, metadata = connector.get_query_completion(prompt)
                        execution_time = time.time() - start_time
                        miss_times.append(execution_time)
                    
                    # Second request (cache hit)
                    hit_times = []
                    for _ in range(self.repeats):
                        start_time = time.time()
                        _, metadata = connector.get_query_completion(prompt)
                        execution_time = time.time() - start_time
                        hit_times.append(execution_time)
                    
                    # Calculate statistics
                    provider_results[prompt_name] = {
                        "avg_miss_time_s": statistics.mean(miss_times),
                        "avg_hit_time_s": statistics.mean(hit_times),
                        "time_savings_s": statistics.mean(miss_times) - statistics.mean(hit_times),
                        "time_savings_percent": ((statistics.mean(miss_times) - statistics.mean(hit_times)) / statistics.mean(miss_times)) * 100 
                            if statistics.mean(miss_times) > 0 else 0,
                    }
                
                results[provider] = provider_results
                
            except Exception as e:
                logger.error(f"Error benchmarking caching for provider {provider}: {e}")
                results[provider] = {"error": str(e)}
        
        self.results["caching_performance"] = results
        logger.info("Caching performance benchmark completed")
    
    def benchmark_response_time(self):
        """Benchmark response time with and without guardian."""
        logger.info("Benchmarking response time")
        
        results = {}
        
        for provider in self.providers:
            try:
                provider_results = {}
                
                # Create connectors with and without guardian
                connector_with_guardian = self.factory.create_connector(
                    connector_type=provider,
                    use_guardian=True
                )
                
                connector_without_guardian = self.factory.create_connector(
                    connector_type=provider,
                    use_guardian=False
                )
                
                for prompt_name, prompt in TEST_PROMPTS.items():
                    # With guardian
                    with_guardian_times = []
                    for _ in range(self.repeats):
                        start_time = time.time()
                        _, metadata = connector_with_guardian.get_query_completion(prompt)
                        execution_time = time.time() - start_time
                        with_guardian_times.append(execution_time)
                    
                    # Without guardian
                    without_guardian_times = []
                    for _ in range(self.repeats):
                        start_time = time.time()
                        _, metadata = connector_without_guardian.get_query_completion(prompt)
                        execution_time = time.time() - start_time
                        without_guardian_times.append(execution_time)
                    
                    # Calculate statistics
                    provider_results[prompt_name] = {
                        "avg_with_guardian_s": statistics.mean(with_guardian_times),
                        "avg_without_guardian_s": statistics.mean(without_guardian_times),
                        "overhead_s": statistics.mean(with_guardian_times) - statistics.mean(without_guardian_times),
                        "overhead_percent": ((statistics.mean(with_guardian_times) - statistics.mean(without_guardian_times)) / 
                                            statistics.mean(without_guardian_times)) * 100 
                            if statistics.mean(without_guardian_times) > 0 else 0,
                    }
                
                results[provider] = provider_results
                
            except Exception as e:
                logger.error(f"Error benchmarking response time for provider {provider}: {e}")
                results[provider] = {"error": str(e)}
        
        self.results["response_time"] = results
        logger.info("Response time benchmark completed")
    
    def benchmark_memory_usage(self):
        """Benchmark memory usage."""
        logger.info("Benchmarking memory usage")
        
        results = {}
        
        # Define component creation functions
        components = {
            "prompt_manager": lambda: PromptManager(),
            "prompt_guardian": lambda: PromptGuardian(),
            "llm_guardian": lambda: LLMGuardian(use_cache=True),
            "llm_factory": lambda: LLMFactory()
        }
        
        for component_name, create_component in components.items():
            # Force garbage collection
            gc.collect()
            
            # Start memory tracking
            tracemalloc.start()
            
            # Create component
            component = create_component()
            
            # Get current memory snapshot
            current, peak = tracemalloc.get_traced_memory()
            
            # Execute some operations
            if component_name == "prompt_manager":
                for template_id, template in TEST_TEMPLATES.items():
                    component.register_template(
                        template_id=template_id,
                        system_prompt=template["system_prompt"],
                        user_prompt=template["user_prompt"],
                        description=template["description"],
                        variables=template["variables"],
                        examples=template.get("examples", [])
                    )
                
                for prompt_name, prompt in TEST_PROMPTS.items():
                    component.optimize_prompt(prompt)
            
            elif component_name == "prompt_guardian":
                for prompt_name, prompt in TEST_PROMPTS.items():
                    component.verify_prompt(prompt, level=VerificationLevel.STANDARD)
            
            elif component_name == "llm_guardian":
                # Only test operations, not actual API calls
                for prompt_name, prompt in TEST_PROMPTS.items():
                    component.prepare_prompt(prompt, optimize=True)
            
            # Get updated memory snapshot
            current_after_ops, peak_after_ops = tracemalloc.get_traced_memory()
            
            # Stop memory tracking
            tracemalloc.stop()
            
            # Record results
            results[component_name] = {
                "initial_memory_kb": current / 1024,
                "peak_memory_kb": peak / 1024,
                "after_operations_memory_kb": current_after_ops / 1024,
                "growth_kb": (current_after_ops - current) / 1024,
                "growth_percent": ((current_after_ops - current) / current) * 100 if current > 0 else 0
            }
        
        self.results["memory_usage"] = results
        logger.info("Memory usage benchmark completed")
    
    def benchmark_template_performance(self):
        """Benchmark template-based prompt creation performance."""
        logger.info("Benchmarking template performance")
        
        results = {}
        
        for template_id, variable_sets in TEST_TEMPLATE_VARIABLES.items():
            template_results = {}
            
            # Test regular template usage
            regular_creation_times = []
            regular_token_counts = []
            regular_token_savings = []
            
            for variable_set in variable_sets:
                for _ in range(self.repeats):
                    start_time = time.time()
                    result = self.prompt_manager.create_prompt(
                        template_id=template_id,
                        variables=[PromptVariable(name=k, value=v) for k, v in variable_set.items()],
                        optimize=False
                    )
                    execution_time = time.time() - start_time
                    
                    regular_creation_times.append(execution_time)
                    regular_token_counts.append(result.token_count)
                    regular_token_savings.append(0)
            
            # Test optimized template usage
            optimized_creation_times = []
            optimized_token_counts = []
            optimized_token_savings = []
            
            for variable_set in variable_sets:
                for _ in range(self.repeats):
                    start_time = time.time()
                    result = self.prompt_manager.create_prompt(
                        template_id=template_id,
                        variables=[PromptVariable(name=k, value=v) for k, v in variable_set.items()],
                        optimize=True
                    )
                    execution_time = time.time() - start_time
                    
                    optimized_creation_times.append(execution_time)
                    optimized_token_counts.append(result.token_count)
                    optimized_token_savings.append(result.token_savings)
            
            # Calculate statistics
            template_results["regular"] = {
                "avg_creation_time_ms": statistics.mean(regular_creation_times) * 1000,
                "avg_token_count": statistics.mean(regular_token_counts),
                "avg_token_savings": statistics.mean(regular_token_savings),
            }
            
            template_results["optimized"] = {
                "avg_creation_time_ms": statistics.mean(optimized_creation_times) * 1000,
                "avg_token_count": statistics.mean(optimized_token_counts),
                "avg_token_savings": statistics.mean(optimized_token_savings),
                "savings_percent": (statistics.mean(optimized_token_savings) / 
                                   statistics.mean(regular_token_counts)) * 100 
                    if statistics.mean(regular_token_counts) > 0 else 0,
            }
            
            # Calculate overhead
            template_results["optimization_overhead_ms"] = (
                template_results["optimized"]["avg_creation_time_ms"] - 
                template_results["regular"]["avg_creation_time_ms"]
            )
            
            template_results["optimization_overhead_percent"] = (
                (template_results["optimized"]["avg_creation_time_ms"] - 
                 template_results["regular"]["avg_creation_time_ms"]) / 
                template_results["regular"]["avg_creation_time_ms"]
            ) * 100 if template_results["regular"]["avg_creation_time_ms"] > 0 else 0
            
            results[template_id] = template_results
        
        self.results["template_performance"] = results
        logger.info("Template performance benchmark completed")
    
    def save_results(self):
        """Save benchmark results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"benchmark_results_{timestamp}.json")
        
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
    
    def generate_visualizations(self):
        """Generate visualizations from benchmark results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Token Optimization Comparison
        if self.results["token_optimization"]:
            self._create_token_optimization_chart(
                os.path.join(self.output_dir, f"token_optimization_{timestamp}.png")
            )
        
        # 2. Verification Performance Comparison
        if self.results["verification_performance"]:
            self._create_verification_performance_chart(
                os.path.join(self.output_dir, f"verification_performance_{timestamp}.png")
            )
        
        # 3. Caching Performance Chart
        if self.results["caching_performance"]:
            self._create_caching_performance_chart(
                os.path.join(self.output_dir, f"caching_performance_{timestamp}.png")
            )
        
        # 4. Response Time Comparison
        if self.results["response_time"]:
            self._create_response_time_chart(
                os.path.join(self.output_dir, f"response_time_{timestamp}.png")
            )
        
        # 5. Memory Usage Chart
        if self.results["memory_usage"]:
            self._create_memory_usage_chart(
                os.path.join(self.output_dir, f"memory_usage_{timestamp}.png")
            )
        
        # 6. Template Performance Chart
        if self.results["template_performance"]:
            self._create_template_performance_chart(
                os.path.join(self.output_dir, f"template_performance_{timestamp}.png")
            )
        
        # 7. Summary Chart
        self._create_summary_chart(
            os.path.join(self.output_dir, f"summary_{timestamp}.png")
        )
        
        logger.info("Visualizations generated")
    
    def _create_token_optimization_chart(self, filename):
        """Create token optimization comparison chart."""
        plt.figure(figsize=(12, 8))
        
        prompt_data = self.results["token_optimization"]
        strategies = set()
        for prompt_results in prompt_data.values():
            strategies.update(prompt_results.keys())
        
        strategies = sorted(strategies)
        prompt_names = list(prompt_data.keys())
        
        # Create grouped bar chart
        x = np.arange(len(prompt_names))
        width = 0.8 / len(strategies)
        
        for i, strategy in enumerate(strategies):
            savings_pcts = []
            for prompt_name in prompt_names:
                if strategy in prompt_data[prompt_name]:
                    savings_pcts.append(prompt_data[prompt_name][strategy]["savings_percent"])
                else:
                    savings_pcts.append(0)
            
            plt.bar(x + (i - len(strategies)/2 + 0.5) * width, savings_pcts, width, label=strategy)
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Token Savings (%)")
        plt.title("Token Optimization Effectiveness by Strategy")
        plt.xticks(x, prompt_names)
        plt.legend(title="Optimization Strategy")
        plt.tight_layout()
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.savefig(filename)
        plt.close()
    
    def _create_verification_performance_chart(self, filename):
        """Create verification performance comparison chart."""
        plt.figure(figsize=(12, 8))
        
        prompt_data = self.results["verification_performance"]
        levels = set()
        for prompt_results in prompt_data.values():
            levels.update(prompt_results.keys())
        
        levels = sorted(levels)
        prompt_names = list(prompt_data.keys())
        
        # Create grouped bar chart for execution time
        plt.subplot(2, 1, 1)
        x = np.arange(len(prompt_names))
        width = 0.8 / len(levels)
        
        for i, level in enumerate(levels):
            times = []
            for prompt_name in prompt_names:
                if level in prompt_data[prompt_name]:
                    times.append(prompt_data[prompt_name][level]["avg_execution_time_ms"])
                else:
                    times.append(0)
            
            plt.bar(x + (i - len(levels)/2 + 0.5) * width, times, width, label=level)
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Avg. Execution Time (ms)")
        plt.title("Verification Execution Time by Level")
        plt.xticks(x, prompt_names)
        plt.legend(title="Verification Level")
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        # Create heatmap for allowed percentage
        plt.subplot(2, 1, 2)
        allowed_data = np.zeros((len(levels), len(prompt_names)))
        
        for i, level in enumerate(levels):
            for j, prompt_name in enumerate(prompt_names):
                if level in prompt_data[prompt_name]:
                    allowed_data[i, j] = prompt_data[prompt_name][level]["allowed_percent"]
        
        im = plt.imshow(allowed_data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
        plt.colorbar(im, label="Allowed Percentage (%)")
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Verification Level")
        plt.title("Prompt Acceptance Rate by Verification Level")
        plt.xticks(range(len(prompt_names)), prompt_names)
        plt.yticks(range(len(levels)), levels)
        
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
    
    def _create_caching_performance_chart(self, filename):
        """Create caching performance chart."""
        plt.figure(figsize=(12, 8))
        
        if not any("error" not in provider_data for provider_data in self.results["caching_performance"].values()):
            plt.text(0.5, 0.5, "No valid caching performance data available", 
                    horizontalalignment="center", verticalalignment="center")
            plt.savefig(filename)
            plt.close()
            return
        
        providers = [p for p in self.results["caching_performance"].keys() 
                   if "error" not in self.results["caching_performance"][p]]
        
        if not providers:
            plt.text(0.5, 0.5, "No valid caching performance data available", 
                    horizontalalignment="center", verticalalignment="center")
            plt.savefig(filename)
            plt.close()
            return
            
        prompt_names = set()
        for provider in providers:
            prompt_names.update(self.results["caching_performance"][provider].keys())
        
        prompt_names = sorted(prompt_names)
        
        # Create grouped bar chart for time savings
        plt.subplot(2, 1, 1)
        x = np.arange(len(prompt_names))
        width = 0.8 / len(providers)
        
        for i, provider in enumerate(providers):
            savings = []
            for prompt_name in prompt_names:
                if prompt_name in self.results["caching_performance"][provider]:
                    savings.append(self.results["caching_performance"][provider][prompt_name]["time_savings_s"])
                else:
                    savings.append(0)
            
            plt.bar(x + (i - len(providers)/2 + 0.5) * width, savings, width, label=provider)
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Time Savings (s)")
        plt.title("Cache Performance - Time Savings by Provider")
        plt.xticks(x, prompt_names)
        plt.legend(title="Provider")
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        # Create comparison of hit vs miss times
        plt.subplot(2, 1, 2)
        
        # Average across providers for simplicity
        miss_times = []
        hit_times = []
        
        for prompt_name in prompt_names:
            miss_avg = []
            hit_avg = []
            
            for provider in providers:
                if prompt_name in self.results["caching_performance"][provider]:
                    miss_avg.append(self.results["caching_performance"][provider][prompt_name]["avg_miss_time_s"])
                    hit_avg.append(self.results["caching_performance"][provider][prompt_name]["avg_hit_time_s"])
            
            miss_times.append(statistics.mean(miss_avg) if miss_avg else 0)
            hit_times.append(statistics.mean(hit_avg) if hit_avg else 0)
        
        plt.bar(x - width/2, miss_times, width, label="Cache Miss")
        plt.bar(x + width/2, hit_times, width, label="Cache Hit")
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Response Time (s)")
        plt.title("Cache Performance - Miss vs. Hit Response Time")
        plt.xticks(x, prompt_names)
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
    
    def _create_response_time_chart(self, filename):
        """Create response time comparison chart."""
        plt.figure(figsize=(12, 8))
        
        if not any("error" not in provider_data for provider_data in self.results["response_time"].values()):
            plt.text(0.5, 0.5, "No valid response time data available", 
                    horizontalalignment="center", verticalalignment="center")
            plt.savefig(filename)
            plt.close()
            return
        
        providers = [p for p in self.results["response_time"].keys() 
                   if "error" not in self.results["response_time"][p]]
        
        if not providers:
            plt.text(0.5, 0.5, "No valid response time data available", 
                    horizontalalignment="center", verticalalignment="center")
            plt.savefig(filename)
            plt.close()
            return
            
        prompt_names = set()
        for provider in providers:
            prompt_names.update(self.results["response_time"][provider].keys())
        
        prompt_names = sorted(prompt_names)
        
        # Create grouped bar chart for overhead percentage
        plt.subplot(2, 1, 1)
        x = np.arange(len(prompt_names))
        width = 0.8 / len(providers)
        
        for i, provider in enumerate(providers):
            overhead_pcts = []
            for prompt_name in prompt_names:
                if prompt_name in self.results["response_time"][provider]:
                    overhead_pcts.append(self.results["response_time"][provider][prompt_name]["overhead_percent"])
                else:
                    overhead_pcts.append(0)
            
            plt.bar(x + (i - len(providers)/2 + 0.5) * width, overhead_pcts, width, label=provider)
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Guardian Overhead (%)")
        plt.title("Response Time - Guardian Overhead Percentage by Provider")
        plt.xticks(x, prompt_names)
        plt.legend(title="Provider")
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        # Create comparison of with vs without guardian
        plt.subplot(2, 1, 2)
        
        # Use first provider for simplicity
        provider = providers[0]
        
        with_guardian = []
        without_guardian = []
        
        for prompt_name in prompt_names:
            if prompt_name in self.results["response_time"][provider]:
                with_guardian.append(self.results["response_time"][provider][prompt_name]["avg_with_guardian_s"])
                without_guardian.append(self.results["response_time"][provider][prompt_name]["avg_without_guardian_s"])
            else:
                with_guardian.append(0)
                without_guardian.append(0)
        
        plt.bar(x - width/2, without_guardian, width, label="Without Guardian")
        plt.bar(x + width/2, with_guardian, width, label="With Guardian")
        
        plt.xlabel("Prompt Type")
        plt.ylabel("Response Time (s)")
        plt.title(f"Response Time - With vs Without Guardian ({provider})")
        plt.xticks(x, prompt_names)
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
    
    def _create_memory_usage_chart(self, filename):
        """Create memory usage chart."""
        plt.figure(figsize=(12, 8))
        
        components = list(self.results["memory_usage"].keys())
        
        # Create bar chart for initial and peak memory
        plt.subplot(2, 1, 1)
        x = np.arange(len(components))
        width = 0.35
        
        initial_memory = [self.results["memory_usage"][component]["initial_memory_kb"] for component in components]
        after_ops = [self.results["memory_usage"][component]["after_operations_memory_kb"] for component in components]
        peak_memory = [self.results["memory_usage"][component]["peak_memory_kb"] for component in components]
        
        plt.bar(x - width/2, initial_memory, width, label="Initial Memory")
        plt.bar(x + width/2, peak_memory, width, label="Peak Memory")
        
        plt.xlabel("Component")
        plt.ylabel("Memory Usage (KB)")
        plt.title("Memory Usage - Initial vs Peak")
        plt.xticks(x, components)
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        # Create bar chart for memory growth
        plt.subplot(2, 1, 2)
        
        growth = [self.results["memory_usage"][component]["growth_kb"] for component in components]
        growth_pct = [self.results["memory_usage"][component]["growth_percent"] for component in components]
        
        plt.bar(x, growth_pct, 0.7)
        
        plt.xlabel("Component")
        plt.ylabel("Memory Growth (%)")
        plt.title("Memory Growth During Operations")
        plt.xticks(x, components)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
    
    def _create_template_performance_chart(self, filename):
        """Create template performance chart."""
        plt.figure(figsize=(12, 8))
        
        templates = list(self.results["template_performance"].keys())
        
        # Create bar chart for creation time comparison
        plt.subplot(2, 1, 1)
        x = np.arange(len(templates))
        width = 0.35
        
        regular_times = [self.results["template_performance"][template]["regular"]["avg_creation_time_ms"] 
                       for template in templates]
        optimized_times = [self.results["template_performance"][template]["optimized"]["avg_creation_time_ms"] 
                         for template in templates]
        
        plt.bar(x - width/2, regular_times, width, label="Regular")
        plt.bar(x + width/2, optimized_times, width, label="Optimized")
        
        plt.xlabel("Template")
        plt.ylabel("Creation Time (ms)")
        plt.title("Template Performance - Creation Time")
        plt.xticks(x, templates)
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        # Create bar chart for token savings
        plt.subplot(2, 1, 2)
        
        savings_pct = [self.results["template_performance"][template]["optimized"]["savings_percent"] 
                     for template in templates]
        
        plt.bar(x, savings_pct, 0.7)
        
        plt.xlabel("Template")
        plt.ylabel("Token Savings (%)")
        plt.title("Template Performance - Token Savings")
        plt.xticks(x, templates)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
    
    def _create_summary_chart(self, filename):
        """Create summary chart with key metrics."""
        plt.figure(figsize=(14, 10))
        
        # 1. Token Optimization Summary
        plt.subplot(2, 2, 1)
        
        if self.results["token_optimization"]:
            # Average token savings percentage across all prompt types and strategies
            avg_savings = []
            
            for prompt_name, prompt_results in self.results["token_optimization"].items():
                for strategy, stats in prompt_results.items():
                    if strategy != "NONE":  # Skip no optimization
                        avg_savings.append(stats["savings_percent"])
            
            best_strategy = None
            best_savings = 0
            
            for prompt_name, prompt_results in self.results["token_optimization"].items():
                for strategy, stats in prompt_results.items():
                    if stats["savings_percent"] > best_savings:
                        best_savings = stats["savings_percent"]
                        best_strategy = strategy
            
            plt.text(0.5, 0.5, 
                    f"Avg Token Savings: {statistics.mean(avg_savings):.2f}%\n" +
                    f"Max Token Savings: {max(avg_savings):.2f}%\n" +
                    f"Best Strategy: {best_strategy}\n" +
                    f"Savings Range: {min(avg_savings):.2f}% - {max(avg_savings):.2f}%",
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes, fontsize=11)
        else:
            plt.text(0.5, 0.5, "No token optimization data available", 
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes)
        
        plt.title("Token Optimization Summary")
        plt.axis("off")
        
        # 2. Verification Performance Summary
        plt.subplot(2, 2, 2)
        
        if self.results["verification_performance"]:
            # Average execution times by level
            level_times = {}
            
            for prompt_name, prompt_results in self.results["verification_performance"].items():
                for level, stats in prompt_results.items():
                    if level not in level_times:
                        level_times[level] = []
                    level_times[level].append(stats["avg_execution_time_ms"])
            
            avg_level_times = {level: statistics.mean(times) for level, times in level_times.items()}
            
            # Allowed percentages by level
            level_allowed = {}
            
            for prompt_name, prompt_results in self.results["verification_performance"].items():
                for level, stats in prompt_results.items():
                    if level not in level_allowed:
                        level_allowed[level] = []
                    level_allowed[level].append(stats["allowed_percent"])
            
            avg_level_allowed = {level: statistics.mean(pcts) for level, pcts in level_allowed.items()}
            
            # Format summary text
            summary_text = "Verification Times (ms):\n"
            for level, avg_time in sorted(avg_level_times.items()):
                summary_text += f"{level}: {avg_time:.2f}ms\n"
            
            summary_text += "\nAllowed Percentages:\n"
            for level, avg_pct in sorted(avg_level_allowed.items()):
                summary_text += f"{level}: {avg_pct:.1f}%\n"
            
            plt.text(0.5, 0.5, summary_text,
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes, fontsize=10)
        else:
            plt.text(0.5, 0.5, "No verification performance data available", 
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes)
        
        plt.title("Verification Performance Summary")
        plt.axis("off")
        
        # 3. Caching Performance Summary
        plt.subplot(2, 2, 3)
        
        valid_cache_data = {p: d for p, d in self.results["caching_performance"].items() if "error" not in d}
        
        if valid_cache_data:
            # Average time savings across all providers and prompts
            time_savings = []
            time_savings_pct = []
            
            for provider, provider_results in valid_cache_data.items():
                for prompt_name, stats in provider_results.items():
                    time_savings.append(stats["time_savings_s"])
                    time_savings_pct.append(stats["time_savings_percent"])
            
            summary_text = f"Avg Cache Time Savings: {statistics.mean(time_savings):.2f}s\n"
            summary_text += f"Avg Cache Savings %: {statistics.mean(time_savings_pct):.2f}%\n"
            summary_text += f"Max Cache Time Savings: {max(time_savings):.2f}s\n"
            summary_text += f"Max Cache Savings %: {max(time_savings_pct):.2f}%\n"
            
            plt.text(0.5, 0.5, summary_text,
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes, fontsize=11)
        else:
            plt.text(0.5, 0.5, "No valid caching performance data available", 
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes)
        
        plt.title("Caching Performance Summary")
        plt.axis("off")
        
        # 4. Guardian Overhead Summary
        plt.subplot(2, 2, 4)
        
        valid_response_data = {p: d for p, d in self.results["response_time"].items() if "error" not in d}
        
        if valid_response_data:
            # Average overhead across all providers and prompts
            overhead_times = []
            overhead_pcts = []
            
            for provider, provider_results in valid_response_data.items():
                for prompt_name, stats in provider_results.items():
                    overhead_times.append(stats["overhead_s"])
                    overhead_pcts.append(stats["overhead_percent"])
            
            summary_text = f"Avg Guardian Overhead: {statistics.mean(overhead_times):.2f}s\n"
            summary_text += f"Avg Overhead %: {statistics.mean(overhead_pcts):.2f}%\n"
            summary_text += f"Max Overhead: {max(overhead_times):.2f}s\n"
            summary_text += f"Max Overhead %: {max(overhead_pcts):.2f}%\n"
            
            plt.text(0.5, 0.5, summary_text,
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes, fontsize=11)
        else:
            plt.text(0.5, 0.5, "No valid response time data available", 
                    horizontalalignment="center", verticalalignment="center",
                    transform=plt.gca().transAxes)
        
        plt.title("Guardian Overhead Summary")
        plt.axis("off")
        
        # Add overall title
        plt.suptitle("Prompt Management System Performance Summary", fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(filename)
        plt.close()


def main():
    """Main function to run the benchmark."""
    parser = argparse.ArgumentParser(description="Prompt Management Benchmarking Tool")
    
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                      help=f"Directory to save benchmark results (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                      help=f"Number of repetitions for each test (default: {DEFAULT_REPEATS})")
    parser.add_argument("--providers", nargs="+", default=DEFAULT_PROVIDERS,
                      choices=AVAILABLE_PROVIDERS,
                      help=f"LLM providers to test (default: {DEFAULT_PROVIDERS})")
    parser.add_argument("--use-db", action="store_true",
                      help="Use database for templates and caching")
    parser.add_argument("--skip-token-optimization", action="store_true",
                      help="Skip token optimization benchmarks")
    parser.add_argument("--skip-verification", action="store_true",
                      help="Skip verification benchmarks")
    parser.add_argument("--skip-caching", action="store_true",
                      help="Skip caching benchmarks")
    parser.add_argument("--skip-response-time", action="store_true",
                      help="Skip response time benchmarks")
    parser.add_argument("--skip-memory", action="store_true",
                      help="Skip memory benchmarks")
    parser.add_argument("--skip-templates", action="store_true",
                      help="Skip template benchmarks")
    
    args = parser.parse_args()
    
    # Create benchmark runner
    benchmark = PromptManagementBenchmark(
        output_dir=args.output_dir,
        repeats=args.repeats,
        providers=args.providers,
        use_db=args.use_db
    )
    
    # Run selected benchmarks or all if none specified
    if (args.skip_token_optimization and args.skip_verification and 
        args.skip_caching and args.skip_response_time and 
        args.skip_memory and args.skip_templates):
        logger.info("No benchmarks selected, running all benchmarks")
        benchmark.run_all_benchmarks()
    else:
        if not args.skip_token_optimization:
            benchmark.benchmark_token_optimization()
        if not args.skip_verification:
            benchmark.benchmark_verification_performance()
        if not args.skip_caching:
            benchmark.benchmark_caching_performance()
        if not args.skip_response_time:
            benchmark.benchmark_response_time()
        if not args.skip_memory:
            benchmark.benchmark_memory_usage()
        if not args.skip_templates:
            benchmark.benchmark_template_performance()
        
        benchmark.save_results()
        benchmark.generate_visualizations()
    
    logger.info("Benchmarking completed")


if __name__ == "__main__":
    main()