#!/usr/bin/env python3
"""Run comprehensive provider implementation checks.

This script verifies that all activity providers implement the required methods
from their respective interfaces and reports any issues found.

Usage:
    python -m research.ablation.tests.run_provider_checks [--fix] [--check-only]

Options:
    --fix           Attempt to generate stub implementations for missing methods
    --check-only    Only check for issues, don't run any tests
"""

import argparse
import inspect
import logging
import os
import sys

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("provider_checks")


def get_abstract_methods(cls) -> set[str]:
    """Get all abstract methods defined in a class.

    Args:
        cls: The class to inspect.

    Returns:
        Set of method names that are abstract.
    """
    abstract_methods = set()

    # Get all methods with the abstractmethod decorator
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if getattr(method, "__isabstractmethod__", False):
            abstract_methods.add(name)

    return abstract_methods


def check_implementation(impl_cls, interface_cls) -> dict[str, bool]:
    """Check if a class implements all required methods from an interface.

    Args:
        impl_cls: The implementation class to check.
        interface_cls: The interface class to check against.

    Returns:
        Dictionary of method names mapped to implementation status.
    """
    # Get all abstract methods from the interface
    required_methods = get_abstract_methods(interface_cls)

    # Check if each method is implemented
    implementation_status = {}
    for method_name in required_methods:
        # Check if the method exists in the implementation
        if hasattr(impl_cls, method_name):
            method = getattr(impl_cls, method_name)
            # Check if the method is still abstract
            if getattr(method, "__isabstractmethod__", False):
                implementation_status[method_name] = False
            else:
                implementation_status[method_name] = True
        else:
            implementation_status[method_name] = False

    return implementation_status


def generate_implementation_stub(method_name: str, interface_cls) -> str:
    """Generate a stub implementation for a method.

    Args:
        method_name: The name of the method to generate a stub for.
        interface_cls: The interface class containing the method.

    Returns:
        A string containing the stub implementation.
    """
    # Get the method from the interface
    method = getattr(interface_cls, method_name)

    # Get the method signature
    sig = inspect.signature(method)

    # Generate the method signature
    params = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue

        if param.annotation is not inspect.Parameter.empty:
            params.append(f"{name}: {param.annotation.__name__}")
        else:
            params.append(name)

    method_sig = f"def {method_name}(self, {', '.join(params)})"

    # Generate docstring
    docstring = f'"""TODO: Implement {method_name} method."""'

    # Generate return value
    return_type = sig.return_annotation
    if return_type is bool:
        return_value = "False  # TODO: Implement and return True for success"
    elif return_type is int:
        return_value = "0  # TODO: Implement and return actual count"
    elif return_type is str:
        return_value = '""  # TODO: Implement and return actual value'
    elif "List" in str(return_type) or "list" in str(return_type):
        return_value = "[]  # TODO: Implement and return actual list"
    elif "Dict" in str(return_type) or "dict" in str(return_type):
        return_value = "{}  # TODO: Implement and return actual dict"
    elif "Set" in str(return_type) or "set" in str(return_type):
        return_value = "set()  # TODO: Implement and return actual set"
    else:
        return_value = "None  # TODO: Implement and return appropriate value"

    # Generate the implementation
    implementation = f"""
    {method_sig}:
        {docstring}
        logging.warning(f"{method_name} is not fully implemented")
        return {return_value}
    """

    return implementation


def run_provider_checks(fix: bool = False) -> bool:
    """Run checks on all activity providers.

    Args:
        fix: Whether to attempt to fix issues by generating stub implementations.

    Returns:
        True if all providers pass all checks, False otherwise.
    """
    # Import the base interfaces
    from research.ablation.base import ISyntheticCollector, ISyntheticRecorder

    # Import all collectors and recorders
    from research.ablation.collectors.music_collector import MusicActivityCollector
    from research.ablation.recorders.music_recorder import MusicActivityRecorder

    try:
        from research.ablation.collectors.task_collector import TaskActivityCollector
        from research.ablation.recorders.task_recorder import TaskActivityRecorder

        task_available = True
    except ImportError:
        logger.warning("Task activity providers not available")
        task_available = False

    try:
        from research.ablation.collectors.location_collector import (
            LocationActivityCollector,
        )
        from research.ablation.recorders.location_recorder import (
            LocationActivityRecorder,
        )

        location_available = True
    except ImportError:
        logger.warning("Location activity providers not available")
        location_available = False

    # Define provider pairs to check
    providers = [
        ("Music", MusicActivityCollector, MusicActivityRecorder, ISyntheticCollector, ISyntheticRecorder),
    ]

    if task_available:
        providers.append(("Task", TaskActivityCollector, TaskActivityRecorder, ISyntheticCollector, ISyntheticRecorder))

    if location_available:
        providers.append(
            ("Location", LocationActivityCollector, LocationActivityRecorder, ISyntheticCollector, ISyntheticRecorder),
        )

    # Check each provider
    all_providers_pass = True

    for provider_name, collector_cls, recorder_cls, collector_interface, recorder_interface in providers:
        logger.info(f"Checking {provider_name} activity providers...")

        # Check collector
        collector_status = check_implementation(collector_cls, collector_interface)
        missing_collector_methods = [name for name, implemented in collector_status.items() if not implemented]

        # Check recorder
        recorder_status = check_implementation(recorder_cls, recorder_interface)
        missing_recorder_methods = [name for name, implemented in recorder_status.items() if not implemented]

        # Report results
        if not missing_collector_methods and not missing_recorder_methods:
            logger.info(f"✅ {provider_name} activity providers implement all required methods")
        else:
            all_providers_pass = False
            if missing_collector_methods:
                logger.error(
                    f"❌ {provider_name}ActivityCollector is missing implementations for: {', '.join(missing_collector_methods)}",
                )

                if fix:
                    logger.info(f"Generating stub implementations for {provider_name}ActivityCollector...")
                    for method_name in missing_collector_methods:
                        stub = generate_implementation_stub(method_name, collector_interface)
                        logger.info(f"Generated stub for {method_name}:\n{stub}")

            if missing_recorder_methods:
                logger.error(
                    f"❌ {provider_name}ActivityRecorder is missing implementations for: {', '.join(missing_recorder_methods)}",
                )

                if fix:
                    logger.info(f"Generating stub implementations for {provider_name}ActivityRecorder...")
                    for method_name in missing_recorder_methods:
                        stub = generate_implementation_stub(method_name, recorder_interface)
                        logger.info(f"Generated stub for {method_name}:\n{stub}")

    return all_providers_pass


def run_compatibility_report():
    """Generate a compatibility report for all providers."""
    # Import the base interfaces
    from research.ablation.base import ISyntheticCollector, ISyntheticRecorder

    logger.info("Generating provider compatibility report...")

    # Get all abstract methods from the interfaces
    collector_methods = get_abstract_methods(ISyntheticCollector)
    recorder_methods = get_abstract_methods(ISyntheticRecorder)

    # Find all provider modules
    provider_modules = []

    import research.ablation.collectors
    import research.ablation.recorders

    # Identify collector and recorder classes
    collectors = {}
    recorders = {}

    # Find all collector classes
    for item_name in dir(research.ablation.collectors):
        if item_name.endswith("Collector") and item_name != "ISyntheticCollector":
            try:
                collector_cls = getattr(research.ablation.collectors, item_name)
                if inspect.isclass(collector_cls) and issubclass(collector_cls, ISyntheticCollector):
                    collectors[item_name] = collector_cls
            except (ImportError, AttributeError):
                continue

    # Find all recorder classes
    for item_name in dir(research.ablation.recorders):
        if item_name.endswith("Recorder") and item_name != "ISyntheticRecorder":
            try:
                recorder_cls = getattr(research.ablation.recorders, item_name)
                if inspect.isclass(recorder_cls) and issubclass(recorder_cls, ISyntheticRecorder):
                    recorders[item_name] = recorder_cls
            except (ImportError, AttributeError):
                continue

    # Print collector compatibility report
    logger.info("\nCollector Compatibility Report:")
    logger.info("=" * 80)
    logger.info(f"{'Method':<20} | {'Required':<10} | " + " | ".join(f"{name:<20}" for name in collectors))
    logger.info("-" * 80)

    for method_name in sorted(collector_methods):
        required = "Yes" if method_name in collector_methods else "No"
        row = f"{method_name:<20} | {required:<10} | "

        for collector_name, collector_cls in collectors.items():
            implemented = hasattr(collector_cls, method_name) and not getattr(
                getattr(collector_cls, method_name), "__isabstractmethod__", False,
            )
            status = "✅" if implemented else "❌"
            row += f"{status:<20} | "

        logger.info(row)

    # Print recorder compatibility report
    logger.info("\nRecorder Compatibility Report:")
    logger.info("=" * 80)
    logger.info(f"{'Method':<20} | {'Required':<10} | " + " | ".join(f"{name:<20}" for name in recorders))
    logger.info("-" * 80)

    for method_name in sorted(recorder_methods):
        required = "Yes" if method_name in recorder_methods else "No"
        row = f"{method_name:<20} | {required:<10} | "

        for recorder_name, recorder_cls in recorders.items():
            implemented = hasattr(recorder_cls, method_name) and not getattr(
                getattr(recorder_cls, method_name), "__isabstractmethod__", False,
            )
            status = "✅" if implemented else "❌"
            row += f"{status:<20} | "

        logger.info(row)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run provider implementation checks.")
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to generate stub implementations for missing methods",
    )
    parser.add_argument("--check-only", action="store_true", help="Only check for issues, don't run any tests")
    parser.add_argument("--report", action="store_true", help="Generate a compatibility report for all providers")
    args = parser.parse_args()

    if args.report:
        run_compatibility_report()
        return

    all_providers_pass = run_provider_checks(fix=args.fix)

    if not all_providers_pass:
        logger.error("Some providers are missing method implementations. See above for details.")
        sys.exit(1)

    if args.check_only:
        logger.info("All providers implement all required methods")
        return

    # Run the tests
    logger.info("Running provider tests...")
    import unittest

    from research.ablation.tests.unit.test_music_collector import (
        TestMusicActivityCollector,
        TestMusicActivityRecorder,
    )

    # Create a test suite
    suite = unittest.TestSuite()

    # Add music activity tests
    suite.addTest(unittest.makeSuite(TestMusicActivityCollector))
    suite.addTest(unittest.makeSuite(TestMusicActivityRecorder))

    # Add other activity tests as needed

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        logger.error("Some tests failed. See above for details.")
        sys.exit(1)

    logger.info("All tests passed!")


if __name__ == "__main__":
    main()
