"""
Test script for Fire Circle implementation.

This script tests the Fire Circle implementation with its specialized entity roles
and integration with the Indaleko Archivist.

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

import argparse
import logging
import os
import sys
import time
import uuid

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
try:
    from src.firecircle.core import (
        FireCircleEntity,
        create_analyst,
        create_critic,
        create_storyteller,
        create_synthesizer,
    )
    from src.firecircle.orchestrator import FireCircleOrchestrator
    from src.firecircle.protocol import EntityRole

    HAS_FIRE_CIRCLE = True
except ImportError:
    HAS_FIRE_CIRCLE = False

try:
    from archivist.fire_circle_integration import FireCircleArchivistIntegration

    HAS_INTEGRATION = True
except ImportError:
    HAS_INTEGRATION = False

try:
    from archivist.knowledge_base.data_models.knowledge_pattern import KnowledgePattern
    from archivist.knowledge_base.knowledge_manager import KnowledgeBaseManager

    HAS_KB = True
except ImportError:
    HAS_KB = False
# pylint: enable=wrong-import-position


class TestInterface:
    """Simple interface for displaying test results."""

    def __init__(self, debug: bool = False):
        """
        Initialize a new test interface.

        Args:
            debug: Whether to enable debug output
        """
        self.debug = debug

    def display_info(self, message: str) -> None:
        """Display an informational message."""
        print(f"\033[94m[INFO]\033[0m {message}")

    def display_success(self, message: str) -> None:
        """Display a success message."""
        print(f"\033[92m[SUCCESS]\033[0m {message}")

    def display_warning(self, message: str) -> None:
        """Display a warning message."""
        print(f"\033[93m[WARNING]\033[0m {message}")

    def display_error(self, message: str) -> None:
        """Display an error message."""
        print(f"\033[91m[ERROR]\033[0m {message}")

    def display_debug(self, message: str) -> None:
        """Display a debug message if debug is enabled."""
        if self.debug:
            print(f"\033[90m[DEBUG]\033[0m {message}")


def test_create_entity(ui: TestInterface) -> None:
    """
    Test creating Fire Circle entities.

    Args:
        ui: The test interface
    """
    if not HAS_FIRE_CIRCLE:
        ui.display_error("Fire Circle is not available")
        return

    ui.display_info("Testing creation of Fire Circle entities...")

    try:
        # Create one entity of each role
        storyteller = create_storyteller()
        analyst = create_analyst()
        critic = create_critic()
        synthesizer = create_synthesizer()

        # Verify roles
        assert storyteller.role == EntityRole.STORYTELLER
        assert analyst.role == EntityRole.ANALYST
        assert critic.role == EntityRole.CRITIC
        assert synthesizer.role == EntityRole.SYNTHESIZER

        ui.display_success("Successfully created entities with all roles")
    except Exception as e:
        ui.display_error(f"Failed to create entities: {e!s}")


def test_process_message(ui: TestInterface) -> None:
    """
    Test processing a message with a Fire Circle entity.

    Args:
        ui: The test interface
    """
    if not HAS_FIRE_CIRCLE:
        ui.display_error("Fire Circle is not available")
        return

    ui.display_info("Testing message processing with Fire Circle entities...")

    try:
        # Create entities
        storyteller = create_storyteller()
        analyst = create_analyst()

        # Test message
        test_message = "What insights can be gleaned from a user who frequently searches for PDF documents related to project management?"

        # Process with storyteller
        ui.display_info("Processing with Storyteller role...")
        storyteller_response = storyteller.process_message(test_message)
        ui.display_info(f"Storyteller response: {storyteller_response[:150]}...")

        # Process with analyst
        ui.display_info("Processing with Analyst role...")
        analyst_response = analyst.process_message(test_message)
        ui.display_info(f"Analyst response: {analyst_response[:150]}...")

        # Verify responses are different
        assert storyteller_response != analyst_response

        ui.display_success(
            "Successfully processed messages with different perspectives",
        )
    except Exception as e:
        ui.display_error(f"Failed to process messages: {e!s}")


def test_orchestrator(ui: TestInterface) -> None:
    """
    Test the Fire Circle orchestrator.

    Args:
        ui: The test interface
    """
    if not HAS_FIRE_CIRCLE:
        ui.display_error("Fire Circle is not available")
        return

    ui.display_info("Testing Fire Circle orchestrator...")

    try:
        # Create orchestrator
        orchestrator = FireCircleOrchestrator()

        # Create session
        session = orchestrator.create_session()

        # Verify session was created
        assert session.session_id is not None
        assert len(session.entities) == 4  # All four specialized roles

        # Process a message
        ui.display_info("Processing message with all perspectives...")
        test_message = "What patterns might emerge from a user who frequently searches for documents related to machine learning alongside music files from the same time periods?"

        result = orchestrator.process_message(
            session_id=session.session_id,
            message=test_message,
            gather_all_perspectives=True,
        )

        # Verify result
        assert "perspectives" in result
        assert "synthesis" in result
        assert len(result["perspectives"]) > 0

        # Display summary
        for role, perspective in result["perspectives"].items():
            ui.display_info(
                f"{role.capitalize()} ({len(perspective)} chars): {perspective[:100]}...",
            )

        if result.get("synthesis"):
            ui.display_info(
                f"Synthesis ({len(result['synthesis'])} chars): {result['synthesis'][:100]}...",
            )

        ui.display_success("Successfully orchestrated multi-perspective analysis")
    except Exception as e:
        ui.display_error(f"Failed to test orchestrator: {e!s}")


def test_archivist_integration(ui: TestInterface) -> None:
    """
    Test the integration with the Archivist.

    Args:
        ui: The test interface
    """
    if not HAS_FIRE_CIRCLE or not HAS_INTEGRATION or not HAS_KB:
        ui.display_error("Fire Circle integration with Archivist is not available")
        return

    ui.display_info("Testing Fire Circle integration with Archivist...")

    try:
        # Create integration
        fc_integration = FireCircleArchivistIntegration()

        # Create a mock knowledge pattern
        pattern = KnowledgePattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type="query_pattern",
            description="Users frequently search for PDF files containing financial data",
            confidence=0.85,
            source_events=[
                {
                    "query": "find PDF files with budget data",
                    "timestamp": time.time() - 3600,
                    "result_count": 5,
                },
                {
                    "query": "financial reports PDF",
                    "timestamp": time.time() - 1800,
                    "result_count": 7,
                },
                {
                    "query": "quarterly PDF statements",
                    "timestamp": time.time() - 900,
                    "result_count": 3,
                },
            ],
            application_context={
                "suggested_optimizations": [
                    "index PDF content",
                    "prioritize financial terms in search",
                ],
            },
        )

        # Analyze pattern
        ui.display_info("Analyzing knowledge pattern with multiple perspectives...")
        result = fc_integration.analyze_pattern(pattern)

        # Verify result
        assert "pattern_id" in result
        assert "perspectives" in result
        assert "synthesis" in result
        assert "learning_event_id" in result

        # Display summary
        for role, perspective in result["perspectives"].items():
            ui.display_info(f"{role.capitalize()} analysis: {perspective[:100]}...")

        if result.get("synthesis"):
            ui.display_info(f"Synthesis: {result['synthesis'][:100]}...")

        ui.display_info(f"Learning event ID: {result['learning_event_id']}")

        ui.display_success("Successfully tested Archivist integration")
    except Exception as e:
        ui.display_error(f"Failed to test Archivist integration: {e!s}")


def test_pattern_suggestions(ui: TestInterface) -> None:
    """
    Test pattern suggestions from query history.

    Args:
        ui: The test interface
    """
    if not HAS_FIRE_CIRCLE or not HAS_INTEGRATION:
        ui.display_error("Fire Circle integration is not available")
        return

    ui.display_info("Testing pattern suggestions from query history...")

    try:
        # Create integration
        fc_integration = FireCircleArchivistIntegration()

        # Create mock query history
        query_history = [
            {
                "query": "find documents about machine learning",
                "timestamp": time.time() - 86400 * 5,
                "result_count": 15,
                "selected_result": "machine_learning_intro.pdf",
            },
            {
                "query": "python neural networks tutorial",
                "timestamp": time.time() - 86400 * 4,
                "result_count": 8,
                "selected_result": "neural_net_tutorial.py",
            },
            {
                "query": "tensorflow examples",
                "timestamp": time.time() - 86400 * 3,
                "result_count": 12,
                "selected_result": "tensorflow_examples.py",
            },
            {
                "query": "deep learning papers 2024",
                "timestamp": time.time() - 86400 * 2,
                "result_count": 25,
                "selected_result": "transformer_architecture.pdf",
            },
            {
                "query": "how to implement LSTM python",
                "timestamp": time.time() - 86400,
                "result_count": 6,
                "selected_result": "lstm_implementation.ipynb",
            },
        ]

        # Get suggestions
        ui.display_info("Generating pattern suggestions from query history...")
        result = fc_integration.suggest_knowledge_patterns(query_history)

        # Verify result
        assert "perspectives" in result
        assert "synthesis" in result

        # Display summary
        for role, perspective in result["perspectives"].items():
            ui.display_info(f"{role.capitalize()} suggestions: {perspective[:100]}...")

        if result.get("synthesis"):
            ui.display_info(f"Synthesized suggestions: {result['synthesis'][:100]}...")

        ui.display_success("Successfully generated pattern suggestions")
    except Exception as e:
        ui.display_error(f"Failed to test pattern suggestions: {e!s}")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Fire Circle implementation")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug output",
    )

    # Test selection arguments
    parser.add_argument("--entities", action="store_true", help="Test entity creation")
    parser.add_argument(
        "--messages",
        action="store_true",
        help="Test message processing",
    )
    parser.add_argument("--orchestrator", action="store_true", help="Test orchestrator")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Test Archivist integration",
    )
    parser.add_argument(
        "--suggestions",
        action="store_true",
        help="Test pattern suggestions",
    )
    parser.add_argument("--all", "-a", action="store_true", help="Run all tests")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    # Create test interface
    ui = TestInterface(debug=args.debug)

    # Check if Fire Circle is available
    if not HAS_FIRE_CIRCLE:
        ui.display_error(
            "Fire Circle is not available. Please check your installation.",
        )
        return

    ui.display_info("Starting Fire Circle tests...")

    # Determine which tests to run
    run_all = args.all or not any(
        [
            args.entities,
            args.messages,
            args.orchestrator,
            args.integration,
            args.suggestions,
        ],
    )

    # Run tests
    if run_all or args.entities:
        test_create_entity(ui)

    if run_all or args.messages:
        test_process_message(ui)

    if run_all or args.orchestrator:
        test_orchestrator(ui)

    if run_all or args.integration:
        test_archivist_integration(ui)

    if run_all or args.suggestions:
        test_pattern_suggestions(ui)

    ui.display_info("Fire Circle tests completed.")


if __name__ == "__main__":
    main()
