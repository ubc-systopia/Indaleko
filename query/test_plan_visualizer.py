"""
Test script for query execution plan visualization.

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


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.search_execution.query_visualizer import PlanVisualizer


def load_sample_explain_result():
    """
    Create a sample explain result for testing.
    This is similar to what ArangoDB would return.
    """
    return {
        "plan": {
            "nodes": [
                {
                    "type": "SingletonNode",
                    "dependencies": [],
                    "id": 1,
                    "estimatedCost": 1,
                    "estimatedNrItems": 1,
                },
                {
                    "type": "EnumerateCollectionNode",
                    "dependencies": [1],
                    "id": 2,
                    "estimatedCost": 12,
                    "estimatedNrItems": 10,
                    "collection": "Objects",
                    "outVariable": {"id": 0, "name": "obj"},
                    "random": False,
                    "satellite": False,
                },
                {
                    "type": "FilterNode",
                    "dependencies": [2],
                    "id": 3,
                    "estimatedCost": 22,
                    "estimatedNrItems": 5,
                    "expression": {
                        "type": "n-ary or",
                        "subNodes": [
                            {
                                "type": "n-ary and",
                                "subNodes": [
                                    {
                                        "type": "compare >",
                                        "subNodes": [
                                            {
                                                "type": "attribute access",
                                                "name": "size",
                                                "subNodes": [
                                                    {
                                                        "type": "reference",
                                                        "name": "obj",
                                                        "id": 0,
                                                    },
                                                ],
                                            },
                                            {"type": "value", "value": 1000000},
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                },
                {
                    "type": "LimitNode",
                    "dependencies": [3],
                    "id": 4,
                    "estimatedCost": 27,
                    "estimatedNrItems": 5,
                    "offset": 0,
                    "limit": 10,
                    "fullCount": False,
                },
                {
                    "type": "ReturnNode",
                    "dependencies": [4],
                    "id": 5,
                    "estimatedCost": 32,
                    "estimatedNrItems": 5,
                    "inVariable": {"id": 0, "name": "obj"},
                },
            ],
            "rules": [
                "move-calculations-up",
                "move-filters-up",
                "remove-redundant-calculations",
                "remove-unnecessary-calculations",
                "move-calculations-up-2",
                "move-filters-up-2",
                "use-indexes",
                "remove-filter-covered-by-index",
                "use-index-for-sort",
                "remove-unnecessary-filters-2",
                "use-indexes-for-sort",
            ],
            "collections": ["Objects"],
            "variables": [{"id": 0, "name": "obj"}],
            "estimatedCost": 32,
            "estimatedNrItems": 5,
            "isModificationQuery": False,
        },
        "cacheable": True,
        "warnings": [],
        "stats": {"rulesExecuted": 11, "rulesSkipped": 0, "plansCreated": 1},
        "query": "FOR obj IN Objects FILTER obj.size > 1000000 LIMIT 10 RETURN obj",
    }


def load_optimized_explain_result():
    """
    Create a sample optimized explain result that uses indexes.
    """
    return {
        "plan": {
            "nodes": [
                {
                    "type": "SingletonNode",
                    "dependencies": [],
                    "id": 1,
                    "estimatedCost": 1,
                    "estimatedNrItems": 1,
                },
                {
                    "type": "IndexNode",
                    "dependencies": [1],
                    "id": 2,
                    "estimatedCost": 5,
                    "estimatedNrItems": 5,
                    "collection": "Objects",
                    "outVariable": {"id": 0, "name": "obj"},
                    "indexes": [
                        {
                            "id": "12345",
                            "type": "persistent",
                            "name": "size_index",
                            "fields": ["size"],
                            "selectivityEstimate": 0.1,
                            "unique": False,
                            "sparse": False,
                        },
                    ],
                    "condition": {
                        "type": "n-ary and",
                        "subNodes": [
                            {
                                "type": "compare >",
                                "subNodes": [
                                    {
                                        "type": "attribute access",
                                        "name": "size",
                                        "subNodes": [
                                            {
                                                "type": "reference",
                                                "name": "obj",
                                                "id": 0,
                                            },
                                        ],
                                    },
                                    {"type": "value", "value": 1000000},
                                ],
                            },
                        ],
                    },
                    "reverse": False,
                    "satellite": False,
                },
                {
                    "type": "LimitNode",
                    "dependencies": [2],
                    "id": 3,
                    "estimatedCost": 10,
                    "estimatedNrItems": 5,
                    "offset": 0,
                    "limit": 10,
                    "fullCount": False,
                },
                {
                    "type": "ReturnNode",
                    "dependencies": [3],
                    "id": 4,
                    "estimatedCost": 15,
                    "estimatedNrItems": 5,
                    "inVariable": {"id": 0, "name": "obj"},
                },
            ],
            "rules": [
                "move-calculations-up",
                "move-filters-up",
                "remove-redundant-calculations",
                "remove-unnecessary-calculations",
                "move-calculations-up-2",
                "move-filters-up-2",
                "use-indexes",
                "remove-filter-covered-by-index",
                "use-index-for-sort",
                "remove-unnecessary-filters-2",
                "use-indexes-for-sort",
            ],
            "collections": ["Objects"],
            "variables": [{"id": 0, "name": "obj"}],
            "estimatedCost": 15,
            "estimatedNrItems": 5,
            "isModificationQuery": False,
        },
        "cacheable": True,
        "warnings": [],
        "stats": {"rulesExecuted": 11, "rulesSkipped": 0, "plansCreated": 1},
        "query": "FOR obj IN Objects FILTER obj.size > 1000000 LIMIT 10 RETURN obj",
    }


def load_complex_explain_result():
    """
    Create a more complex sample explain result with a join.
    """
    return {
        "plan": {
            "nodes": [
                {
                    "type": "SingletonNode",
                    "dependencies": [],
                    "id": 1,
                    "estimatedCost": 1,
                    "estimatedNrItems": 1,
                },
                {
                    "type": "EnumerateCollectionNode",
                    "dependencies": [1],
                    "id": 2,
                    "estimatedCost": 1002,
                    "estimatedNrItems": 1000,
                    "collection": "Users",
                    "outVariable": {"id": 0, "name": "u"},
                    "random": False,
                    "satellite": False,
                },
                {
                    "type": "EnumerateCollectionNode",
                    "dependencies": [2],
                    "id": 3,
                    "estimatedCost": 12002,
                    "estimatedNrItems": 10000,
                    "collection": "Objects",
                    "outVariable": {"id": 1, "name": "obj"},
                    "random": False,
                    "satellite": False,
                },
                {
                    "type": "FilterNode",
                    "dependencies": [3],
                    "id": 4,
                    "estimatedCost": 22002,
                    "estimatedNrItems": 5000,
                    "expression": {
                        "type": "n-ary and",
                        "subNodes": [
                            {
                                "type": "compare ==",
                                "subNodes": [
                                    {
                                        "type": "attribute access",
                                        "name": "owner",
                                        "subNodes": [
                                            {
                                                "type": "reference",
                                                "name": "obj",
                                                "id": 1,
                                            },
                                        ],
                                    },
                                    {
                                        "type": "attribute access",
                                        "name": "_id",
                                        "subNodes": [
                                            {"type": "reference", "name": "u", "id": 0},
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                },
                {
                    "type": "CalculationNode",
                    "dependencies": [4],
                    "id": 5,
                    "estimatedCost": 27002,
                    "estimatedNrItems": 5000,
                    "expression": {
                        "type": "object",
                        "subNodes": [
                            {
                                "type": "object element",
                                "name": "user",
                                "subNodes": [
                                    {"type": "reference", "name": "u", "id": 0},
                                ],
                            },
                            {
                                "type": "object element",
                                "name": "object",
                                "subNodes": [
                                    {"type": "reference", "name": "obj", "id": 1},
                                ],
                            },
                        ],
                    },
                    "outVariable": {"id": 2, "name": "result"},
                    "canThrow": False,
                },
                {
                    "type": "SortNode",
                    "dependencies": [5],
                    "id": 6,
                    "estimatedCost": 47002,
                    "estimatedNrItems": 5000,
                    "elements": [
                        {
                            "inVariable": {"id": 1, "name": "obj"},
                            "ascending": False,
                            "attributePath": ["size"],
                        },
                    ],
                },
                {
                    "type": "LimitNode",
                    "dependencies": [6],
                    "id": 7,
                    "estimatedCost": 47027,
                    "estimatedNrItems": 25,
                    "offset": 0,
                    "limit": 25,
                    "fullCount": False,
                },
                {
                    "type": "ReturnNode",
                    "dependencies": [7],
                    "id": 8,
                    "estimatedCost": 47052,
                    "estimatedNrItems": 25,
                    "inVariable": {"id": 2, "name": "result"},
                },
            ],
            "rules": [
                "move-calculations-up",
                "move-filters-up",
                "remove-redundant-calculations",
                "remove-unnecessary-calculations",
                "move-calculations-up-2",
                "move-filters-up-2",
                "use-indexes",
                "remove-filter-covered-by-index",
                "use-index-for-sort",
                "remove-unnecessary-filters-2",
                "use-indexes-for-sort",
            ],
            "collections": ["Users", "Objects"],
            "variables": [
                {"id": 0, "name": "u"},
                {"id": 1, "name": "obj"},
                {"id": 2, "name": "result"},
            ],
            "estimatedCost": 47052,
            "estimatedNrItems": 25,
            "isModificationQuery": False,
        },
        "cacheable": True,
        "warnings": [
            "Large collection scan on 'Objects'",
            "Expensive join operation detected",
        ],
        "stats": {"rulesExecuted": 11, "rulesSkipped": 0, "plansCreated": 1},
        "query": "FOR u IN Users FOR obj IN Objects FILTER obj.owner == u._id SORT obj.size DESC LIMIT 25 RETURN { user: u, object: obj }",
    }


def main():
    """Test the query plan visualization."""

    # Create the plan visualizer
    visualizer = PlanVisualizer(colorize=True, max_depth=10)

    # Test cases
    test_cases = [
        {
            "name": "Basic query with full collection scan",
            "explain_result": load_sample_explain_result(),
            "verbose": False,
        },
        {
            "name": "Optimized query using index",
            "explain_result": load_optimized_explain_result(),
            "verbose": False,
        },
        {
            "name": "Complex query with join",
            "explain_result": load_complex_explain_result(),
            "verbose": True,
        },
    ]

    # Process each test case
    for _i, test_case in enumerate(test_cases, 1):

        # Parse and visualize the execution plan
        explain_result = test_case["explain_result"]
        plan = visualizer.parse_plan(explain_result)

        # Display the execution plan
        visualizer.visualize_text(plan, verbose=test_case["verbose"])

        # Print plan statistics



if __name__ == "__main__":
    main()
