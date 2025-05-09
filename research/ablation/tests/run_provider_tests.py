#!/usr/bin/env python3
"""Run all ablation provider tests.

This script runs tests to verify that all activity provider components
(collectors and recorders) are working correctly in isolation. This helps
prevent regressions where one component breaks but isn't caught until
integration testing.
"""

import argparse
import importlib
import inspect
import logging
import os
import sys
import unittest
from pathlib import Path

# Add the project root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# Import test modules
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.music_recorder import MusicActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder


# Define provider configurations for testing
PROVIDERS = [
    {
        "name": "Location",
        "collector": LocationActivityCollector,
        "recorder": LocationActivityRecorder,
        "collector_test": "test_location_activity.py",
        "recorder_test": None,  # Will be auto-discovered
    },
    {
        "name": "Music",
        "collector": MusicActivityCollector,
        "recorder": MusicActivityRecorder,
        "collector_test": "test_music_collector.py",
        "recorder_test": None,  # Will be auto-discovered
    },
    {
        "name": "Task",
        "collector": TaskActivityCollector,
        "recorder": TaskActivityRecorder,
        "collector_test": "test_task_activity.py",
        "recorder_test": None,  # Will be auto-discovered
    },
]


def setup_logging():
    """Set up logging for the test runner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def verify_implementation(provider_class, expected_methods):
    """Verify that a provider class implements all required methods.
    
    Args:
        provider_class: The class to verify
        expected_methods: List of method names that should be implemented
        
    Returns:
        Tuple of (bool, list): Success flag and list of missing methods
    """
    missing_methods = []
    for method_name in expected_methods:
        if not hasattr(provider_class, method_name):
            missing_methods.append(method_name)
            continue
            
        method = getattr(provider_class, method_name)
        if not callable(method):
            missing_methods.append(method_name)
            continue
            
        # Check if the method is abstract (not implemented)
        if getattr(method, "__isabstractmethod__", False):
            missing_methods.append(method_name)
    
    return len(missing_methods) == 0, missing_methods


def verify_provider_implementations():
    """Verify that all providers implement the required methods.
    
    Returns:
        bool: True if all providers implement all required methods
    """
    logger = logging.getLogger("provider_verification")
    all_valid = True
    
    # Define required methods for each provider type
    collector_methods = [
        "collect", 
        "generate_batch", 
        "generate_truth_data", 
        "generate_matching_data", 
        "generate_non_matching_data", 
        "seed"
    ]
    
    recorder_methods = [
        "record", 
        "record_batch", 
        "record_truth_data", 
        "delete_all", 
        "get_collection_name", 
        "count_records"
    ]
    
    # Verify each provider
    for provider in PROVIDERS:
        logger.info(f"Verifying {provider['name']} provider implementation")
        
        # Verify collector
        collector_valid, collector_missing = verify_implementation(
            provider["collector"], collector_methods
        )
        if not collector_valid:
            all_valid = False
            logger.error(
                f"{provider['name']}ActivityCollector missing required methods: {', '.join(collector_missing)}"
            )
        else:
            logger.info(f"{provider['name']}ActivityCollector implements all required methods")
        
        # Verify recorder
        recorder_valid, recorder_missing = verify_implementation(
            provider["recorder"], recorder_methods
        )
        if not recorder_valid:
            all_valid = False
            logger.error(
                f"{provider['name']}ActivityRecorder missing required methods: {', '.join(recorder_missing)}"
            )
        else:
            logger.info(f"{provider['name']}ActivityRecorder implements all required methods")
    
    return all_valid


def discover_tests():
    """Discover all test modules for providers.
    
    Returns:
        dict: Dictionary mapping provider names to test module paths
    """
    logger = logging.getLogger("test_discovery")
    test_modules = {}
    
    # Get the unit test directory
    unit_test_dir = Path(__file__).parent / "unit"
    
    # Discover test modules for each provider
    for provider in PROVIDERS:
        provider_name = provider["name"].lower()
        test_modules[provider_name] = []
        
        # Check for collector tests
        collector_test = provider.get("collector_test")
        if collector_test:
            collector_test_path = unit_test_dir / collector_test
            if collector_test_path.exists():
                test_modules[provider_name].append(str(collector_test_path))
                logger.info(f"Found collector test for {provider['name']}: {collector_test}")
            else:
                logger.warning(f"Collector test for {provider['name']} not found: {collector_test}")
        
        # Check for recorder tests
        recorder_test = provider.get("recorder_test")
        if recorder_test:
            recorder_test_path = unit_test_dir / recorder_test
            if recorder_test_path.exists():
                test_modules[provider_name].append(str(recorder_test_path))
                logger.info(f"Found recorder test for {provider['name']}: {recorder_test}")
            else:
                logger.warning(f"Recorder test for {provider['name']} not found: {recorder_test}")
        
        # Auto-discover tests if needed
        if not collector_test or not recorder_test:
            for test_file in unit_test_dir.glob(f"test_{provider_name}*.py"):
                if str(test_file) not in test_modules[provider_name]:
                    test_modules[provider_name].append(str(test_file))
                    logger.info(f"Auto-discovered test for {provider['name']}: {test_file.name}")
    
    return test_modules


def run_tests(test_modules, provider_filter=None):
    """Run tests for all providers.
    
    Args:
        test_modules: Dictionary mapping provider names to test module paths
        provider_filter: Optional list of provider names to filter on
        
    Returns:
        bool: True if all tests pass
    """
    logger = logging.getLogger("test_runner")
    all_passed = True
    
    # Filter providers if needed
    if provider_filter:
        filtered_modules = {}
        for provider in provider_filter:
            provider_lower = provider.lower()
            if provider_lower in test_modules:
                filtered_modules[provider_lower] = test_modules[provider_lower]
            else:
                logger.warning(f"Provider not found: {provider}")
        test_modules = filtered_modules
    
    # Run tests for each provider
    for provider_name, module_paths in test_modules.items():
        if not module_paths:
            logger.warning(f"No tests found for {provider_name}")
            continue
        
        logger.info(f"Running tests for {provider_name}")
        
        for module_path in module_paths:
            # Load the test module
            module_name = Path(module_path).stem
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Discover test cases
            test_cases = []
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, unittest.TestCase) and obj != unittest.TestCase:
                    test_cases.append(obj)
            
            if not test_cases:
                logger.warning(f"No test cases found in {module_path}")
                continue
            
            # Run tests for each test case
            for test_case in test_cases:
                logger.info(f"Running test case: {test_case.__name__}")
                
                # Create a test suite with all test methods
                suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case)
                
                # Run the tests
                result = unittest.TextTestRunner(verbosity=2).run(suite)
                
                # Check results
                if not result.wasSuccessful():
                    all_passed = False
                    logger.error(f"Tests failed for {test_case.__name__}")
                else:
                    logger.info(f"All tests passed for {test_case.__name__}")
    
    return all_passed


def generate_compatibility_report():
    """Generate a compatibility report for all providers.
    
    Returns:
        str: The compatibility report as a string
    """
    report = []
    report.append("# Ablation Provider Compatibility Report\n")
    
    # Define required methods for each provider type
    collector_methods = [
        "collect", 
        "generate_batch", 
        "generate_truth_data", 
        "generate_matching_data", 
        "generate_non_matching_data", 
        "seed"
    ]
    
    recorder_methods = [
        "record", 
        "record_batch", 
        "record_truth_data", 
        "delete_all", 
        "get_collection_name", 
        "count_records"
    ]
    
    # Generate the collector methods table
    report.append("## Collector Compatibility\n")
    
    # Table header
    header = "| Provider |"
    separator = "|----------|"
    for method in collector_methods:
        header += f" {method} |"
        separator += "----------|"
    
    report.append(header)
    report.append(separator)
    
    # Table rows
    for provider in PROVIDERS:
        row = f"| {provider['name']} |"
        
        for method in collector_methods:
            has_method = hasattr(provider["collector"], method)
            if has_method:
                method_obj = getattr(provider["collector"], method)
                is_abstract = getattr(method_obj, "__isabstractmethod__", False)
                if is_abstract:
                    row += " ❌ |"
                else:
                    row += " ✅ |"
            else:
                row += " ❌ |"
        
        report.append(row)
    
    report.append("\n")
    
    # Generate the recorder methods table
    report.append("## Recorder Compatibility\n")
    
    # Table header
    header = "| Provider |"
    separator = "|----------|"
    for method in recorder_methods:
        header += f" {method} |"
        separator += "----------|"
    
    report.append(header)
    report.append(separator)
    
    # Table rows
    for provider in PROVIDERS:
        row = f"| {provider['name']} |"
        
        for method in recorder_methods:
            has_method = hasattr(provider["recorder"], method)
            if has_method:
                method_obj = getattr(provider["recorder"], method)
                is_abstract = getattr(method_obj, "__isabstractmethod__", False)
                if is_abstract:
                    row += " ❌ |"
                else:
                    row += " ✅ |"
            else:
                row += " ❌ |"
        
        report.append(row)
    
    report.append("\n")
    
    # Generate test coverage report
    test_modules = discover_tests()
    report.append("## Test Coverage\n")
    
    # Table header
    report.append("| Provider | Collector Tests | Recorder Tests |")
    report.append("|----------|----------------|----------------|")
    
    # Table rows
    for provider in PROVIDERS:
        provider_name = provider["name"].lower()
        
        collector_tests = sum(
            1 for path in test_modules.get(provider_name, []) 
            if Path(path).stem.startswith(f"test_{provider_name}_collector") or
               Path(path).stem == f"test_{provider_name}_activity"
        )
        
        recorder_tests = sum(
            1 for path in test_modules.get(provider_name, []) 
            if Path(path).stem.startswith(f"test_{provider_name}_recorder")
        )
        
        report.append(f"| {provider['name']} | {collector_tests} | {recorder_tests} |")
    
    return "\n".join(report)


def main():
    """Run the provider tests."""
    parser = argparse.ArgumentParser(description="Run ablation provider tests")
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Only verify provider implementations, don't run tests"
    )
    parser.add_argument(
        "--provider", action="append",
        help="Only run tests for specific providers (can be used multiple times)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate a compatibility report"
    )
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    logger = logging.getLogger("main")
    
    logger.info("Starting ablation provider tests")
    
    # Verify provider implementations
    implementation_valid = verify_provider_implementations()
    
    if args.verify_only:
        logger.info("Verification complete")
        sys.exit(0 if implementation_valid else 1)
    
    # Discover tests
    test_modules = discover_tests()
    
    # Generate report if requested
    if args.report:
        report = generate_compatibility_report()
        report_path = Path(os.environ.get("INDALEKO_ROOT", ".")) / "ablation_provider_report.md"
        with open(report_path, "w") as f:
            f.write(report)
        logger.info(f"Compatibility report saved to {report_path}")
    
    # Run tests
    tests_passed = run_tests(test_modules, args.provider)
    
    # Return status code
    success = implementation_valid and tests_passed
    logger.info(f"All tests {'passed' if success else 'failed'}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()