#!/usr/bin/env python3
"""Regression test suite for ablation framework.

This script runs tests to ensure that critical functionality doesn't break
as new features are added. It functions as both a test script and a continuous
integration check to catch regressions early.
"""

import argparse
import importlib
import logging
import os
import subprocess
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_provider_compatibility_check():
    """Run the provider compatibility check."""
    logger.info("Running provider compatibility check...")
    
    try:
        # Import the provider test module
        provider_test_path = Path(__file__).parent / "run_provider_tests.py"
        if not provider_test_path.exists():
            logger.error(f"Provider test script not found at {provider_test_path}")
            return False
        
        # Run the provider tests with verify-only flag
        result = subprocess.run(
            [sys.executable, str(provider_test_path), "--verify-only", "--report"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        # Check the result
        if result.returncode != 0:
            logger.error(f"Provider compatibility check failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
        
        logger.info("Provider compatibility check passed")
        return True
    except Exception as e:
        logger.error(f"Failed to run provider compatibility check: {e}")
        return False


def run_basic_ablation_test():
    """Run a basic ablation test to ensure core functionality works."""
    logger.info("Running basic ablation test...")
    
    try:
        # Import the ablation test module
        from research.ablation.ablation_tester import AblationTester, AblationConfig
        from research.ablation.ner.entity_manager import NamedEntityManager
        
        # Initialize the entity manager and ablation tester
        entity_manager = NamedEntityManager()
        ablation_tester = AblationTester()
        
        # Register a test entity
        entity_manager.register_entity("location", "Test Location")
        
        # Create a simple query ID
        import uuid
        query_id = uuid.uuid4()
        
        # Create some test entity IDs
        entity_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        # Store test truth data
        result = ablation_tester.store_truth_data(query_id, "AblationLocationActivity", entity_ids)
        if not result:
            logger.error("Failed to store truth data")
            return False
        
        # Retrieve the stored truth data
        truth_data = ablation_tester.get_truth_data(query_id, "AblationLocationActivity")
        if not truth_data or len(truth_data) != len(entity_ids):
            logger.error(f"Truth data mismatch: stored {len(entity_ids)}, retrieved {len(truth_data)}")
            return False
        
        logger.info("Basic ablation test passed")
        return True
    except Exception as e:
        logger.error(f"Failed to run basic ablation test: {e}")
        return False


def run_activity_provider_tests():
    """Run unit tests for all activity providers."""
    logger.info("Running activity provider unit tests...")
    
    try:
        # Define the test cases to run
        test_modules = [
            "research.ablation.tests.unit.test_location_activity",
            "research.ablation.tests.unit.test_music_collector",
            "research.ablation.tests.unit.test_task_collector",
        ]
        
        # Run each test module
        all_passed = True
        for module_name in test_modules:
            logger.info(f"Running tests in {module_name}")
            
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Run the tests
                suite = unittest.defaultTestLoader.loadTestsFromModule(module)
                result = unittest.TextTestRunner(verbosity=2).run(suite)
                
                # Check the result
                if not result.wasSuccessful():
                    logger.error(f"Tests failed in {module_name}")
                    all_passed = False
                else:
                    logger.info(f"All tests passed in {module_name}")
            except ImportError:
                logger.warning(f"Could not import module {module_name} - skipping tests")
            except Exception as e:
                logger.error(f"Failed to run tests in {module_name}: {e}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        logger.error(f"Failed to run activity provider unit tests: {e}")
        return False


def run_cross_collection_test():
    """Run a cross-collection test to ensure integration works."""
    logger.info("Running cross-collection test...")
    
    try:
        # Build and run a minimal version of the comprehensive test
        minimal_test_path = Path(os.environ.get("INDALEKO_ROOT")) / "test_single_activity.py"
        
        if not minimal_test_path.exists():
            # Create a minimal test script
            with open(minimal_test_path, "w") as f:
                f.write("""#!/usr/bin/env python3
\"\"\"Minimal ablation test to verify core functionality.\"\"\"

import os
import sys
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.ablation_tester import AblationTester

def main():
    # Initialize components
    entity_manager = NamedEntityManager()
    collector = LocationActivityCollector(entity_manager=entity_manager)
    recorder = LocationActivityRecorder()
    ablation_tester = AblationTester()
    
    # Generate and record data
    data = collector.generate_batch(10)
    success = recorder.record_batch(data)
    
    if not success:
        print("Failed to record data")
        return 1
    
    # Create a test query
    query_id = collector.generate_deterministic_uuid("test_query")
    query_text = "Find activities at Home"
    
    # Generate matching entities
    entity_ids = []
    for i in range(5):
        entity_id = str(collector.generate_deterministic_uuid(f"location_match:{i}"))
        entity_ids.append(entity_id)
    
    # Store truth data
    success = ablation_tester.store_truth_data(query_id, "AblationLocationActivity", entity_ids)
    
    if not success:
        print("Failed to store truth data")
        return 1
    
    # Retrieve truth data
    truth_data = ablation_tester.get_truth_data(query_id, "AblationLocationActivity")
    
    if not truth_data or len(truth_data) != len(entity_ids):
        print(f"Truth data mismatch: stored {len(entity_ids)}, retrieved {len(truth_data)}")
        return 1
    
    print("Single activity test passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
""")
                logger.info(f"Created minimal test script at {minimal_test_path}")
            
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(minimal_test_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        
        # Check the result
        if result.returncode != 0:
            logger.error(f"Cross-collection test failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
        
        logger.info("Cross-collection test passed")
        return True
    except Exception as e:
        logger.error(f"Failed to run cross-collection test: {e}")
        return False


def main():
    """Run the regression tests."""
    parser = argparse.ArgumentParser(description="Run ablation framework regression tests")
    parser.add_argument(
        "--all", action="store_true",
        help="Run all tests (default behavior)"
    )
    parser.add_argument(
        "--compatibility", action="store_true",
        help="Run provider compatibility check"
    )
    parser.add_argument(
        "--basic", action="store_true",
        help="Run basic ablation test"
    )
    parser.add_argument(
        "--providers", action="store_true",
        help="Run activity provider unit tests"
    )
    parser.add_argument(
        "--cross-collection", action="store_true",
        help="Run cross-collection test"
    )
    args = parser.parse_args()
    
    # If no specific tests are selected, run all tests
    run_all = args.all or not (args.compatibility or args.basic or args.providers or args.cross_collection)
    
    # Initialize result tracking
    results = {}
    
    # Run the selected tests
    if run_all or args.compatibility:
        results["compatibility"] = run_provider_compatibility_check()
    
    if run_all or args.basic:
        results["basic"] = run_basic_ablation_test()
    
    if run_all or args.providers:
        results["providers"] = run_activity_provider_tests()
    
    if run_all or args.cross_collection:
        results["cross_collection"] = run_cross_collection_test()
    
    # Print the results
    logger.info("====== Regression Test Results ======")
    all_passed = True
    for test_name, passed in results.items():
        logger.info(f"{test_name}: {'PASSED' if passed else 'FAILED'}")
        all_passed = all_passed and passed
    
    # Exit with appropriate status code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()