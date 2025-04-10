"""
Test script for AQL query explain functionality.

This script demonstrates how to use the EXPLAIN functionality
with ArangoDB queries in Indaleko.

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
import json
import argparse
import datetime
import uuid

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.search_execution.data_models.query_execution_plan import QueryExecutionPlan

# pylint: enable=wrong-import-position


def print_section(title, content=None):
    """Helper function to print a formatted section."""
    print(f"\n{'-' * 5} {title} {'-' * 5}")
    if content is not None:
        print(content)


def print_color(text, color=None):
    """Print text in color if supported by terminal."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    
    if color and color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)


def test_explain(query=None, all_plans=False, max_plans=5, json_output=False, output_file=None, bind_vars=None):
    """Test the EXPLAIN functionality using a sample query."""
    # Connect to the database
    db_config = IndalekoDBConfig()
    
    # Default query if none provided
    if query is None:
        from db.db_collections import IndalekoDBCollections
        
        query = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Object_Collection}
                FILTER doc.Record.Attributes.Path LIKE "%pdf"
                SORT doc.Record.Attributes.Timestamp DESC
                LIMIT 10
                RETURN doc
        """
    
    # Generate a unique query ID
    query_id = str(uuid.uuid4())
    
    # Initialize bind variables if not provided
    if bind_vars is None:
        bind_vars = {}
    
    # Execute the query with EXPLAIN
    executor = AQLExecutor()
    explain_result = executor.explain_query(
        query, 
        db_config, 
        bind_vars=bind_vars,
        all_plans=all_plans,
        max_plans=max_plans
    )
    
    # Process into a structured model
    execution_plan = QueryExecutionPlan.from_explain_result(
        query_id=query_id,
        query=query,
        explain_result=explain_result
    )
    
    # Output as JSON if requested
    if json_output:
        output = execution_plan.model_dump_json(indent=2)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"Execution plan saved to {output_file}")
        else:
            print(output)
        return
    
    # Format and display the execution plan
    print_color("AQL Query Execution Plan Analysis", "blue")
    print_section("Query", query.strip())
    
    # Analysis summary
    summary = execution_plan.analysis.summary
    if summary:
        print_section("Summary")
        print(f"Estimated Cost: {execution_plan.plan.estimatedCost:.2f}")
        print(f"Collections Used: {len(execution_plan.plan.collections)}")
        for coll in execution_plan.plan.collections:
            print(f"  - {coll}")
        print(f"Operations: {len(execution_plan.plan.nodes)}")
        print(f"Cacheable: {execution_plan.cacheable}")
        
        # Show indexes used
        if execution_plan.analysis.indexes_used:
            print("\nIndexes Used:")
            for idx in execution_plan.analysis.indexes_used:
                print_color(f"  - {idx}", "green")
    
    # Warnings
    if execution_plan.analysis.warnings:
        print_section("Warnings")
        for warning in execution_plan.analysis.warnings:
            print_color(f"- {warning}", "yellow")
    
    # Recommendations
    if execution_plan.analysis.recommendations:
        print_section("Recommendations")
        for rec in execution_plan.analysis.recommendations:
            print_color(f"- {rec}", "cyan")
    
    # Alternative plans
    if execution_plan.alternative_plans:
        print_section("Alternative Plans")
        print(f"Found {len(execution_plan.alternative_plans)} alternative execution plans")
        for i, plan in enumerate(execution_plan.alternative_plans[:3], 1):  # Show top 3
            print(f"\nPlan {i} - Cost: {plan.estimatedCost:.2f}")
            if hasattr(plan, "rules") and plan.rules:
                print(f"Rules: {', '.join(plan.rules[:3])}...")
    
    # Execution stats
    if execution_plan.stats:
        print_section("Optimization Stats")
        for key, value in execution_plan.stats.items():
            print(f"- {key.replace('rules', 'Rules ').title()}: {value}")


def print_help():
    """Print extended help text with examples."""
    help_text = """
EXPLAIN Query Analyzer for Indaleko
===================================

This tool helps analyze and optimize AQL queries by showing execution plans,
cost estimates, and optimization recommendations.

EXAMPLES:

1. Basic usage with default query:
   python -m query.test_explain

2. Analyze a specific query:
   python -m query.test_explain --query "FOR doc IN Objects FILTER doc.Record.Attributes.Path LIKE '%pdf' RETURN doc"

3. Using bind variables:
   python -m query.test_explain --query "FOR doc IN Objects FILTER doc.Record.Attributes.Size > @size RETURN doc" --bind-vars '{"size": 1000000}'

4. Compare two queries:
   python -m query.test_explain --query "FOR doc IN Objects RETURN doc" --compare "FOR doc IN Objects LIMIT 100 RETURN doc"

5. Generate JSON output:
   python -m query.test_explain --query "FOR doc IN Objects RETURN doc" --json

6. Show all possible execution plans:
   python -m query.test_explain --query "FOR doc IN Objects RETURN doc" --all-plans

7. Save results to a file:
   python -m query.test_explain --query "FOR doc IN Objects RETURN doc" --json --output plans.json

RECOMMENDATIONS:

- Use --all-plans to see alternative execution strategies
- Compare queries with --compare to identify more efficient patterns
- Export plans with --json for sharing or documentation
- Use specific collection names from IndalekoDBCollections class
"""
    print(help_text)


def main():
    """Main function to run the test."""
    # Disable icecream debug output by default
    from icecream import ic
    ic.disable()
    
    parser = argparse.ArgumentParser(
        description="Test AQL query EXPLAIN functionality",
        epilog="Use --help-examples for more detailed usage examples"
    )
    
    parser.add_argument("--query", type=str, help="AQL query to explain")
    parser.add_argument("--all-plans", action="store_true", help="Show all possible execution plans")
    parser.add_argument("--max-plans", type=int, default=5, help="Maximum number of plans to return")
    parser.add_argument("--bind-vars", type=str, help="JSON-formatted bind variables (e.g. '{\"size\": 1000000}')")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--output", type=str, help="Output file for JSON results")
    parser.add_argument("--compare", type=str, help="Compare with another query for performance analysis")
    parser.add_argument("--debug", action="store_true", help="Show debug output")
    parser.add_argument("--help-examples", action="store_true", help="Show extended help with examples")
    
    args = parser.parse_args()
    
    # Show extended help if requested
    if args.help_examples:
        print_help()
        sys.exit(0)
        
    # Enable debug output if requested
    if args.debug:
        from icecream import ic
        ic.enable()
        
    # Parse bind variables if provided
    bind_vars = {}
    if args.bind_vars:
        try:
            bind_vars = json.loads(args.bind_vars)
        except json.JSONDecodeError as e:
            print(f"Error parsing bind variables: {e}")
            print("Please provide bind variables as valid JSON, e.g. '{\"size\": 1000000}'")
            sys.exit(1)
    
    # Run the test
    test_explain(
        query=args.query,
        all_plans=args.all_plans,
        max_plans=args.max_plans,
        json_output=args.json,
        output_file=args.output,
        bind_vars=bind_vars
    )
    
    # Compare with another query if requested
    if args.compare:
        print("\n\n" + "="*50)
        print("COMPARING WITH ALTERNATIVE QUERY")
        print("="*50 + "\n")
        test_explain(
            query=args.compare,
            all_plans=args.all_plans,
            max_plans=args.max_plans,
            json_output=args.json,
            output_file=None,
            bind_vars=bind_vars
        )


if __name__ == "__main__":
    main()