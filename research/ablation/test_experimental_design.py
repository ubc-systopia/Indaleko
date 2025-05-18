#!/usr/bin/env python3
"""
Test script for the experimental ablation design.

This script validates the experimental design without running the full study:
1. Ensures group generation creates proper control/test splits
2. Validates all ablation combinations are generated correctly
3. Tests query generation for different activity types
4. Verifies crossover design implementation
"""

import logging
import random
import sys

from research.ablation.run_experimental_ablation import ExperimentalAblationRunner
from utils.i_logging import configure_logging


def test_group_generation():
    """Test the experimental group generation."""
    # Initialize runner with small values for quick testing
    runner = ExperimentalAblationRunner(iterations=2, queries_per_combination=1)

    # Generate experimental groups
    groups = runner.generate_experimental_groups()

    # We should have 2 iterations * 2 (with crossover) = 4 group configurations
    assert len(groups) == 4, f"Expected 4 group configurations, got {len(groups)}"

    # Each configuration should have control (4) and test (2) groups
    for i, (control, test) in enumerate(groups):
        print(f"Group configuration {i+1}:")
        print(f"  Control: {control}")
        print(f"  Test: {test}")

        # Verify group sizes
        assert len(control) == 4 if i % 2 == 0 else 2, f"Control group has incorrect size: {len(control)}"
        assert len(test) == 2 if i % 2 == 0 else 4, f"Test group has incorrect size: {len(test)}"

        # Verify no overlap between control and test groups
        assert set(control).isdisjoint(set(test)), "Control and test groups overlap"

        # Verify all activity types are covered
        assert set(control).union(set(test)) == set(
            [p.name for p in runner.activity_providers],
        ), "Not all activity types are covered"

    # Crossover design: verify flipped groups
    for i in range(0, len(groups), 2):
        control1, test1 = groups[i]
        control2, test2 = groups[i + 1]

        # In crossover, control1 becomes test2 and test1 becomes control2
        assert set(control1) == set(test2), "Crossover design incorrect for control groups"
        assert set(test1) == set(control2), "Crossover design incorrect for test groups"

    print("Group generation test: PASSED")
    return True


def test_ablation_combinations():
    """Test the generation of ablation combinations."""
    runner = ExperimentalAblationRunner()

    # Test with 4 items
    group4 = ["A", "B", "C", "D"]
    combinations4 = runner.generate_ablation_combinations(group4)

    # Should have: 4C1 + 4C2 + 4C3 = 4 + 6 + 4 = 14 combinations
    assert len(combinations4) == 14, f"Expected 14 combinations for group of 4, got {len(combinations4)}"

    # Test with 2 items
    group2 = ["X", "Y"]
    combinations2 = runner.generate_ablation_combinations(group2)

    # Should have: 2C1 = 2 combinations
    assert len(combinations2) == 1, f"Expected 1 combination for group of 2, got {len(combinations2)}"

    # Print some sample combinations
    print("Sample ablation combinations:")
    for i, combo in enumerate(combinations4[:5]):  # Show first 5 for brevity
        print(f"  Combination {i+1}: {combo}")

    print("Ablation combinations test: PASSED")
    return True


def test_query_generation():
    """Test query generation for different activity types."""
    runner = ExperimentalAblationRunner(queries_per_combination=2)

    # Test query generation for each activity type
    for provider in runner.activity_providers:
        print(f"Generating queries for {provider.name} activity:")

        for i in range(2):  # Generate 2 sample queries for each
            query = runner.query_generator.generate_query(activity_type=provider.name, query_index=i, seed=42 + i)
            print(f"  Query {i+1}: {query}")

            # Verify non-empty query
            assert query and isinstance(query, str), f"Invalid query generated: {query}"

            # Verify query is relevant to the activity type (basic check)
            # This is a simple check and might not always work for all query types
            assert len(query) > 10, f"Query too short: {query}"

    print("Query generation test: PASSED")
    return True


def main():
    """Main entry point for the test script."""
    configure_logging()
    logging.getLogger().setLevel(logging.INFO)

    print("\n=== Testing Experimental Ablation Design ===\n")

    # Set seed for reproducibility
    random.seed(42)

    # Run tests
    try:
        if not test_group_generation():
            logging.error("Group generation test failed")
            return 1

        print("\n")

        if not test_ablation_combinations():
            logging.error("Ablation combinations test failed")
            return 1

        print("\n")

        if not test_query_generation():
            logging.error("Query generation test failed")
            return 1

    except Exception as e:
        logging.exception(f"Test failed with error: {e}")
        return 1

    print("\n=== All tests passed successfully ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
