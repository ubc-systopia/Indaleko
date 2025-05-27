"""Run the exemplar queries, taking measurements and logging results."""

import argparse
import json
import os
import sys

from datetime import datetime, UTC
from typing import Self
from pathlib import Path

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from exemplar.qbase import ExemplarQueryBase, exemplar_main
from exemplar.q1 import ExemplarQuery1
from exemplar.q2 import ExemplarQuery2
from exemplar.q3 import ExemplarQuery3
from exemplar.q4 import ExemplarQuery4
from exemplar.q5 import ExemplarQuery5
from exemplar.q6 import ExemplarQuery6
from exemplar.thesis_results_model import ThesisQueryResult
# pylint: enable=wrong-import-position


default_runs = 10

# Configure icecream to only output to screen
ic.configureOutput(includeContext=True)


def main() -> None:
    """Main function for running exemplar queries."""
    parser = argparse.ArgumentParser(description="Run exemplar queries.")
    parser.add_argument(
        "--runs",
        type=int,
        default=default_runs,
        help=f"Number of times to run each query (default: {default_runs})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("query_results"),
        help="Directory to store query results (default: query_results)",
    )
    args = parser.parse_args()
    runs = args.runs
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    ic(f"Running {runs} iterations per query")
    ic(f"Output directory: {output_dir}")

    query_tests = {
        "Q1": ExemplarQuery1,
        "Q2": ExemplarQuery2,
        "Q3": ExemplarQuery3,
        "Q4": ExemplarQuery4,
        "Q5": ExemplarQuery5,
        "Q6": ExemplarQuery6,
    }
    
    # Create timestamp for this run
    run_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    
    # Create JSONL file for results
    jsonl_file = output_dir / f"query_results_{run_timestamp}.jsonl"
    ic(f"Results will be written to: {jsonl_file}")

    # Validate all query classes first
    for test, query_class in query_tests.items():
        if not isinstance(test, str):
            raise TypeError(f"Test name {test} must be a string")
        if not issubclass(query_class, ExemplarQueryBase):
            raise TypeError(
                f"{query_class} with type {type(query_class)} is not a subclass of ExemplarQueryBase"
            )
    
    # Run queries in round-robin fashion (warm cache pattern)
    for run in range(runs):
        ic(f"=== Starting Round {run + 1}/{runs} ===")
        for test, query_class in query_tests.items():
            ic(f"Running {test} - Round {run + 1}/{runs}")
            exemplar_main(
                query_class, 
                output_file=jsonl_file,
                run_id=run_timestamp,
                sequence_number=run + 1
            )
    
    # Create summary report
    if jsonl_file.exists():
        summary_file = output_dir / f"query_summary_{run_timestamp}.json"
        create_summary_report(jsonl_file, summary_file)


def create_summary_report(jsonl_file: Path, summary_file: Path) -> None:
    """Create a summary report from the JSONL results."""
    results: list[ThesisQueryResult] = []
    
    # Read all results
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(ThesisQueryResult.from_jsonl_record(line))
    
    # Group by query_id and variant
    query_groups = {}
    for result in results:
        key = f"{result.query_id}_{result.variant}"
        if key not in query_groups:
            query_groups[key] = []
        query_groups[key].append(result)
    
    # Create summary
    summary = {
        "run_id": results[0].run_id if results else "unknown",
        "total_executions": len(results),
        "queries": {}
    }
    
    # Process each query
    for query_id in sorted(set(r.query_id for r in results)):
        query_results = [r for r in results if r.query_id == query_id]
        
        # Get the query text (same for all variants)
        query_text = query_results[0].query_text if query_results else ""
        
        # Calculate stats for each variant
        variant_stats = {}
        for variant in ["with_limits", "no_limit", "count"]:
            variant_results = [r for r in query_results if r.variant == variant and r.error is None]
            
            if variant_results:
                times = [r.execution_time for r in variant_results]
                counts = [r.result_count for r in variant_results]
                
                variant_stats[variant] = {
                    "avg_execution_time": sum(times) / len(times),
                    "min_execution_time": min(times),
                    "max_execution_time": max(times),
                    "avg_result_count": sum(counts) / len(counts),
                    "successful_runs": len(variant_results),
                    "failed_runs": len([r for r in query_results if r.variant == variant]) - len(variant_results),
                    # Cache state distribution
                    "cache_states": {
                        state: len([r for r in variant_results if r.cache_state == state])
                        for state in ["cold", "warm", "hot"]
                    }
                }
        
        summary["queries"][query_id] = {
            "query_text": query_text,
            "total_runs": len(set(r.sequence_number for r in query_results)),
            "variants": variant_stats
        }
    
    # Write summary
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    ic(f"Summary report written to: {summary_file}")


if __name__ == "__main__":
    main()
