"""
Test script for the Recommendation Engine integration with Archivist.

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
import argparse
from datetime import datetime, timezone

import colorama
from colorama import Fore, Style

# Set up path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db.db_config import IndalekoDBConfig
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import ProactiveArchivist
from query.context.recommendations.engine import RecommendationEngine
from query.context.recommendations.archivist_integration import RecommendationArchivistIntegration
from query.context.data_models.recommendation import RecommendationSource


class MockCLI:
    """Mock CLI class for testing."""
    
    def __init__(self, debug=False):
        """Initialize mock CLI."""
        self.db_config = IndalekoDBConfig()
        self.query_history = None
        self.debug = debug
        self.commands = {}
        self.help_text = []
    
    def register_command(self, cmd, handler):
        """Register a command."""
        self.commands[cmd] = handler
    
    def append_help_text(self, text):
        """Append help text."""
        self.help_text.append(text)
        

def test_recommendation_integration(args):
    """Test the recommendation integration with Archivist."""
    colorama.init()
    
    print(f"{Fore.CYAN}Testing Recommendation Integration with Archivist{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
    
    # Initialize components
    print(f"{Fore.GREEN}Initializing components...{Style.RESET_ALL}")
    
    # Create mock CLI
    cli = MockCLI(debug=args.debug)
    
    # Initialize Archivist Memory
    memory = ArchivistMemory(cli.db_config)
    
    # Add some test data to memory
    memory.add_long_term_goal("File Organization", "Organize personal documents by project and year", progress=0.35)
    memory.add_long_term_goal("Knowledge Capture", "Capture knowledge from my research papers", progress=0.2)
    
    memory.add_insight("organization", "User struggles with finding documents older than 6 months", 0.8)
    memory.add_insight("temporal", "User typically searches for work documents on Monday mornings", 0.7)
    memory.add_insight("content", "PDFs are the most frequently searched document type", 0.9)
    
    # Create Proactive Archivist
    proactive = ProactiveArchivist(memory)
    
    # Add temporal pattern for testing
    from query.memory.proactive_archivist import TemporalPattern
    proactive.data.temporal_patterns.append(
        TemporalPattern(
            pattern_type="daily",
            description="Daily work document searches",
            confidence=0.8,
            timeframe={"hour_start": datetime.now(timezone.utc).hour - 1, "hour_end": datetime.now(timezone.utc).hour + 1},
            associated_actions=["Search for work documents", "Review recent documents"]
        )
    )
    
    # Create Recommendation Engine
    engine = RecommendationEngine(debug=args.debug)
    
    # Create Recommendation Integration
    integration = RecommendationArchivistIntegration(
        cli_instance=cli,
        archivist_memory=memory,
        proactive_archivist=proactive,
        recommendation_engine=engine,
        debug=args.debug
    )
    
    # Register commands with CLI
    print(f"{Fore.GREEN}Registering commands with CLI...{Style.RESET_ALL}")
    integration.register_commands()
    
    # List registered commands
    print(f"{Fore.YELLOW}Registered commands:{Style.RESET_ALL}")
    for command in integration.commands:
        print(f"  {command}")
    
    # Test context preparation
    print(f"\n{Fore.GREEN}Testing context preparation...{Style.RESET_ALL}")
    context = integration._prepare_context_data()
    print(f"{Fore.YELLOW}Context keys:{Style.RESET_ALL}")
    for key in context:
        print(f"  {key}")
    
    # Update context with queries
    print(f"\n{Fore.GREEN}Testing context updating with queries...{Style.RESET_ALL}")
    test_queries = [
        "documents from last week",
        "important work files",
        "project planning documents",
        "recent PDF files"
    ]
    
    for query in test_queries:
        print(f"{Fore.YELLOW}Adding query to context: {query}{Style.RESET_ALL}")
        integration.update_context_with_query(query)
    
    # Get recommendations
    print(f"\n{Fore.GREEN}Testing recommendation generation...{Style.RESET_ALL}")
    recommendations = integration.get_recommendations_for_context()
    
    if recommendations:
        print(f"{Fore.YELLOW}Generated {len(recommendations)} recommendations:{Style.RESET_ALL}")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec.query} ({rec.source.value}, confidence: {rec.confidence:.2f})")
            print(f"     {rec.description}")
    else:
        print(f"{Fore.RED}No recommendations generated{Style.RESET_ALL}")
    
    # Test conversion to proactive suggestions
    if recommendations:
        print(f"\n{Fore.GREEN}Testing conversion to proactive suggestions...{Style.RESET_ALL}")
        integration._convert_to_proactive_suggestions(recommendations)
        
        proactive_suggestions = proactive.data.active_suggestions
        if proactive_suggestions:
            print(f"{Fore.YELLOW}Converted to {len(proactive_suggestions)} proactive suggestions:{Style.RESET_ALL}")
            for i, suggestion in enumerate(proactive_suggestions, 1):
                print(f"  {i}. {suggestion.title}")
                print(f"     {suggestion.content}")
                print(f"     Type: {suggestion.suggestion_type}, Priority: {suggestion.priority}")
                print(f"     Confidence: {suggestion.confidence:.2f}")
                print(f"     Expires: {suggestion.expires_at}")
        else:
            print(f"{Fore.RED}No proactive suggestions created{Style.RESET_ALL}")
    
    # Test command handling
    print(f"\n{Fore.GREEN}Testing command handling...{Style.RESET_ALL}")
    
    # Test config command
    print(f"\n{Fore.YELLOW}Testing /rconfig show command:{Style.RESET_ALL}")
    integration.configure_recommendations("show")
    
    # Test recommendation stats
    print(f"\n{Fore.YELLOW}Testing /rstats command:{Style.RESET_ALL}")
    integration.show_recommendation_stats("")
    
    # Test specific source recommendations
    print(f"\n{Fore.YELLOW}Testing recommendations from specific sources:{Style.RESET_ALL}")
    
    for source in RecommendationSource:
        print(f"\n{Fore.GREEN}Testing {source.value} recommendations...{Style.RESET_ALL}")
        integration.test_recommendations(source.value)
    
    print(f"\n{Fore.CYAN}Test completed successfully{Style.RESET_ALL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Recommendation Integration with Archivist")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    test_recommendation_integration(args)