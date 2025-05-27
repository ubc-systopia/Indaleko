"""
Example script demonstrating structured output for exemplar queries.

This shows how to run a single query and capture structured results.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, UTC

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from exemplar.q1 import ExemplarQuery1
from exemplar.query_results_model import ExemplarQueryResult
# pylint: enable=wrong-import-position


def main():
    """Run a single query with structured output."""
    # Create output file
    output_file = Path(f"test_results_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.jsonl")
    
    ic(f"Running ExemplarQuery1 with structured output to {output_file}")
    
    # Create and execute the query
    query = ExemplarQuery1()
    query.execute(output_file=output_file)
    
    # Read and display the results
    ic("Reading structured results...")
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                result = ExemplarQueryResult.from_jsonl_record(line)
                
                ic(f"Query: {result.query_name}")
                ic(f"Natural Language: {result.natural_language_query}")
                ic(f"Execution ID: {result.execution_id}")
                ic(f"Timestamp: {result.execution_timestamp}")
                
                for variant_name, variant_result in result.variant_results.items():
                    ic(f"\nVariant: {variant_name}")
                    ic(f"  Execution time: {variant_result.execution_time_seconds:.4f}s")
                    ic(f"  Result count: {variant_result.result_count}")
                    if variant_result.count_value is not None:
                        ic(f"  Count value: {variant_result.count_value}")
                    if variant_result.error:
                        ic(f"  Error: {variant_result.error}")
                    
                    # Show first few bind variables
                    if variant_result.bind_variables:
                        ic("  Bind variables:")
                        for k, v in list(variant_result.bind_variables.items())[:3]:
                            ic(f"    {k}: {v}")
                        if len(variant_result.bind_variables) > 3:
                            ic(f"    ... and {len(variant_result.bind_variables) - 3} more")


if __name__ == "__main__":
    main()