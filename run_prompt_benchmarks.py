#!/usr/bin/env python3
"""
Wrapper script to run the prompt management system benchmarks.
"""

import os
import sys
import argparse
import logging
import subprocess
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_OUTPUT_DIR = "./benchmark_results"
DEFAULT_REPEATS = 5
DEFAULT_PROVIDERS = ["openai"]

def run_benchmarks(args):
    """Run the prompt management benchmarks with specified arguments."""
    benchmark_script = os.path.join("tests", "prompt_management", "benchmark_performance.py")
    
    # Ensure the output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Build command
    cmd = [sys.executable, benchmark_script]
    
    # Add arguments
    cmd.extend(["--output-dir", args.output_dir])
    cmd.extend(["--repeats", str(args.repeats)])
    
    if args.providers:
        cmd.append("--providers")
        cmd.extend(args.providers)
    
    if args.use_db:
        cmd.append("--use-db")
    
    if args.skip_token_optimization:
        cmd.append("--skip-token-optimization")
    
    if args.skip_verification:
        cmd.append("--skip-verification")
    
    if args.skip_caching:
        cmd.append("--skip-caching")
    
    if args.skip_response_time:
        cmd.append("--skip-response-time")
    
    if args.skip_memory:
        cmd.append("--skip-memory")
    
    if args.skip_templates:
        cmd.append("--skip-templates")
    
    # Run the benchmark script
    logger.info(f"Running benchmark command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        
        logger.info(f"Benchmarks completed successfully. Results saved to {args.output_dir}")
        return 0
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Benchmark execution failed: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return 1
    
    except Exception as e:
        logger.error(f"An error occurred while running benchmarks: {e}")
        return 1

def main():
    """Parse arguments and run benchmarks."""
    parser = argparse.ArgumentParser(description="Run Prompt Management Benchmarks")
    
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                      help=f"Directory to save benchmark results (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                      help=f"Number of repetitions for each test (default: {DEFAULT_REPEATS})")
    parser.add_argument("--providers", nargs="+", default=DEFAULT_PROVIDERS,
                      choices=["openai", "anthropic", "gemma", "google"],
                      help=f"LLM providers to test (default: {DEFAULT_PROVIDERS})")
    parser.add_argument("--use-db", action="store_true",
                      help="Use database for templates and caching")
    
    # Allow skipping specific benchmark types
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
    
    # Run benchmarks
    return run_benchmarks(args)

if __name__ == "__main__":
    sys.exit(main())