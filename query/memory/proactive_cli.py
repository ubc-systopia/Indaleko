"""
CLI integration for the Proactive Archivist system.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import ProactiveArchivist, ProactiveSuggestion, SuggestionType
# pylint: enable=wrong-import-position


class ProactiveCliIntegration:
    """
    Integrates the Proactive Archivist capabilities with the Indaleko CLI.
    """
    
    def __init__(self, cli_instance, archivist_memory=None, proactive_archivist=None):
        """
        Initialize the CLI integration for Proactive Archivist.
        
        Args:
            cli_instance: The CLI instance to integrate with
            archivist_memory: An existing ArchivistMemory instance, or None to create a new one
            proactive_archivist: An existing ProactiveArchivist instance, or None to create a new one
        """
        self.cli = cli_instance
        self.memory = archivist_memory or ArchivistMemory(self.cli.db_config)
        self.proactive = proactive_archivist or ProactiveArchivist(self.memory)
        
        # Suggestion display settings
        self.show_suggestions = True
        self.suggestion_limit = 3
        self.last_suggestions_time = None
        self.suggestion_cooldown_minutes = 30
        
        # Record context information
        self.context = {
            "session_start": datetime.now(timezone.utc),
            "last_queries": [],
            "current_goal": None,
            "current_topics": []
        }
        
        # Add commands to CLI
        self.commands = {
            "/proactive": self.show_proactive_help,
            "/suggest": self.show_suggestions_cmd,
            "/feedback": self.provide_feedback,
            "/patterns": self.view_patterns,
            "/insights": self.view_insights,
            "/priorities": self.manage_priorities,
            "/disable": self.disable_suggestions,
            "/enable": self.enable_suggestions,
            "/cross-source": self.show_cross_source_status,
            "/cross-enable": self.enable_cross_source,
            "/cross-disable": self.disable_cross_source,
            "/cross-analyze": self.force_cross_source_analysis
        }
    
    def handle_command(self, command):
        """
        Handle a proactive-related command.
        
        Args:
            command: The command to handle
            
        Returns:
            bool: True if the command was handled, False otherwise
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in self.commands:
            self.commands[cmd](args)
            return True
        
        return False
    
    def show_proactive_help(self, args):
        """Show help for proactive commands."""
        print("\nProactive Archivist Commands:")
        print("---------------------------")
        print("/proactive       - Show this help message")
        print("/suggest         - Show current suggestions")
        print("/feedback        - Provide feedback on a suggestion (positive/negative)")
        print("/patterns        - View detected temporal patterns")
        print("/insights        - View insights from proactive analysis")
        print("/priorities      - Manage suggestion priorities")
        print("/disable         - Disable proactive suggestions")
        print("/enable          - Enable proactive suggestions")
        print("/cross-source    - View cross-source pattern status")
        print("/cross-enable    - Enable cross-source pattern detection")
        print("/cross-disable   - Disable cross-source pattern detection")
        print("/cross-analyze   - Force a cross-source pattern analysis")
    
    def check_suggestions(self, context_update=None):
        """
        Check if it's time to show suggestions and display them if appropriate.
        
        Args:
            context_update: Optional updated context information
        """
        if not self.show_suggestions:
            return
            
        # Update context if provided
        if context_update:
            self.context.update(context_update)
            
        # Only show suggestions once per cooldown period
        now = datetime.now(timezone.utc)
        if (self.last_suggestions_time and 
            (now - self.last_suggestions_time).total_seconds() < self.suggestion_cooldown_minutes * 60):
            return
            
        # Generate new suggestions
        suggestions = self.proactive.generate_suggestions(self.context)
        
        # Show top suggestions
        if suggestions:
            self._display_suggestions(suggestions[:self.suggestion_limit])
            self.last_suggestions_time = now
    
    def _display_suggestions(self, suggestions: List[ProactiveSuggestion]):
        """
        Display suggestions to the user.
        
        Args:
            suggestions: List of suggestions to display
        """
        if not suggestions:
            return
            
        print("\n🔮 Proactive suggestions:")
        print("------------------------")
        
        for i, suggestion in enumerate(suggestions, 1):
            priority_icon = {
                "low": "📌",
                "medium": "⭐",
                "high": "🔥",
                "critical": "⚠️"
            }.get(suggestion.priority, "📌")
            
            print(f"{i}. {priority_icon} {suggestion.title}")
            print(f"   {suggestion.content}")
            
            # Add a tip about the feedback command
            if i == len(suggestions):
                print("\nTip: Use /feedback <number> positive|negative to provide feedback")
    
    def show_suggestions_cmd(self, args):
        """Force display of suggestions."""
        suggestions = self.proactive.generate_suggestions(self.context)
        
        if not suggestions:
            print("No suggestions available at this time.")
            return
            
        self._display_suggestions(suggestions[:5])  # Show more when explicitly requested
        self.last_suggestions_time = datetime.now(timezone.utc)
    
    def provide_feedback(self, args):
        """
        Process feedback on a suggestion.
        
        Args:
            args: Format should be "<suggestion_number> <positive|negative>"
        """
        if not args:
            print("Usage: /feedback <suggestion_number> positive|negative")
            return
            
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            print("Usage: /feedback <suggestion_number> positive|negative")
            return
            
        try:
            num = int(parts[0]) - 1  # Convert to 0-based index
            feedback_type = parts[1].lower()
            
            if feedback_type not in ["positive", "negative"]:
                print("Feedback must be either 'positive' or 'negative'")
                return
                
            if not self.proactive.data.active_suggestions or num >= len(self.proactive.data.active_suggestions):
                print("Invalid suggestion number")
                return
                
            suggestion = self.proactive.data.active_suggestions[num]
            
            # Apply feedback
            feedback_value = 1.0 if feedback_type == "positive" else -1.0
            self.proactive.record_user_feedback(suggestion.suggestion_id, feedback_value)
            
            # Confirm to user
            if feedback_type == "positive":
                print(f"Thanks for the positive feedback! I'll show more suggestions like this.")
                
                # If it's a query suggestion, offer to run it
                if suggestion.suggestion_type == SuggestionType.QUERY and suggestion.related_queries:
                    query = suggestion.related_queries[0]
                    print(f"\nWould you like to run the suggested query? Type: {query}")
            else:
                print(f"Thanks for the feedback. I'll show fewer suggestions like this.")
                
        except ValueError:
            print("Invalid suggestion number")
    
    def view_patterns(self, args):
        """View detected temporal patterns."""
        patterns = self.proactive.data.temporal_patterns
        
        if not patterns:
            print("No temporal patterns detected yet.")
            return
            
        print("\nDetected Temporal Patterns:")
        print("--------------------------")
        
        for i, pattern in enumerate(sorted(patterns, key=lambda p: p.confidence, reverse=True), 1):
            print(f"{i}. {pattern.description}")
            print(f"   Type: {pattern.pattern_type}, Confidence: {pattern.confidence:.2f}")
            
            # Print timeframe details
            if pattern.pattern_type == "daily":
                print(f"   Active hours: {pattern.timeframe.get('hour_start')}:00-{pattern.timeframe.get('hour_end')}:00")
            elif pattern.pattern_type == "weekly":
                day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][pattern.timeframe.get("day_of_week", 0)]
                print(f"   Active day: {day}")
            elif pattern.pattern_type == "monthly":
                print(f"   Active day: {pattern.timeframe.get('day_of_month')}")
                
            if pattern.associated_actions:
                print(f"   Associated actions: {', '.join(pattern.associated_actions[:3])}")
                
            print()
    
    def view_insights(self, args):
        """View insights derived from proactive analysis."""
        # Get insights from archivist memory
        insights = self.memory.get_most_relevant_insights("", 10)  # Get up to 10 insights
        
        if not insights:
            print("No insights available yet.")
            return
            
        # Filter for insights from proactive analysis
        proactive_insights = [i for i in insights if i.category in ["temporal", "sequential", "pattern"]]
        
        if not proactive_insights:
            print("No proactive insights available yet.")
            return
            
        print("\nProactive Insights:")
        print("------------------")
        
        for i, insight in enumerate(proactive_insights, 1):
            print(f"{i}. {insight.insight}")
            print(f"   Category: {insight.category}, Confidence: {insight.confidence:.2f}")
            print()
    
    def manage_priorities(self, args):
        """Manage suggestion type priorities."""
        if args:
            # Handle sub-commands
            parts = args.split(maxsplit=2)
            if len(parts) >= 2:
                suggestion_type = parts[0].upper()
                threshold_str = parts[1]
                
                # Validate suggestion type
                try:
                    suggestion_type = SuggestionType(suggestion_type.lower())
                except ValueError:
                    print(f"Invalid suggestion type. Valid types: {', '.join(t.value for t in SuggestionType)}")
                    return
                
                # Update threshold
                try:
                    threshold = float(threshold_str)
                    if 0.0 <= threshold <= 1.0:
                        self.proactive.data.suggestion_thresholds[suggestion_type] = threshold
                        print(f"Updated threshold for {suggestion_type} to {threshold:.2f}")
                    else:
                        print("Threshold must be between 0.0 and 1.0")
                except ValueError:
                    print("Threshold must be a number between 0.0 and 1.0")
                
                return
        
        # Display current thresholds
        print("\nSuggestion Type Thresholds:")
        print("-------------------------")
        print("(Higher thresholds mean fewer but more confident suggestions)")
        print()
        
        for suggestion_type, threshold in sorted(self.proactive.data.suggestion_thresholds.items()):
            print(f"{suggestion_type.value}: {threshold:.2f}")
            
        print("\nUsage: /priorities <type> <threshold>")
        print("Example: /priorities query 0.7")
    
    def disable_suggestions(self, args):
        """Disable proactive suggestions."""
        self.show_suggestions = False
        print("Proactive suggestions have been disabled.")
        print("Use /enable to turn them back on.")
    
    def enable_suggestions(self, args):
        """Enable proactive suggestions."""
        self.show_suggestions = True
        self.last_suggestions_time = None  # Reset cooldown
        print("Proactive suggestions have been enabled.")
        
        # Show suggestions immediately
        self.show_suggestions_cmd("")
    
    def show_cross_source_status(self, args):
        """Show the status of cross-source pattern detection."""
        enabled = self.proactive.data.cross_source_enabled
        status = "enabled" if enabled else "disabled"
        
        print(f"\nCross-Source Pattern Detection: {status}")
        
        # Show last analysis time if available
        if self.proactive.data.last_cross_source_analysis:
            last_time = self.proactive.data.last_cross_source_analysis
            now = datetime.now(timezone.utc)
            time_diff = now - last_time
            hours_ago = time_diff.total_seconds() / 3600
            
            if hours_ago < 1:
                time_str = f"{int(time_diff.total_seconds() / 60)} minutes ago"
            elif hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                days_ago = int(hours_ago / 24)
                time_str = f"{days_ago} days ago"
                
            print(f"Last analysis: {last_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_str})")
        else:
            print("No analysis has been run yet.")
        
        # Show patterns and correlations if available
        if hasattr(self.proactive, 'cross_source_detector'):
            patterns = len(self.proactive.cross_source_detector.data.patterns)
            correlations = len(self.proactive.cross_source_detector.data.correlations)
            print(f"Detected patterns: {patterns}")
            print(f"Detected correlations: {correlations}")
            
            # Show data sources with events
            sources = self.proactive.cross_source_detector.data.source_statistics
            if sources:
                print("\nData sources with events:")
                for source_type, stats in sources.items():
                    if stats["event_count"] > 0:
                        print(f"- {source_type}: {stats['event_count']} events")
    
    def enable_cross_source(self, args):
        """Enable cross-source pattern detection."""
        self.proactive.data.cross_source_enabled = True
        print("Cross-source pattern detection has been enabled.")
        print("Run /cross-analyze to perform an immediate analysis.")
    
    def disable_cross_source(self, args):
        """Disable cross-source pattern detection."""
        self.proactive.data.cross_source_enabled = False
        print("Cross-source pattern detection has been disabled.")
    
    def force_cross_source_analysis(self, args):
        """Force a cross-source pattern analysis."""
        print("Running cross-source pattern analysis. This may take a moment...")
        
        try:
            # Run the analysis
            self.proactive.analyze_cross_source_patterns()
            
            # Show results
            print("Analysis complete.")
            self.show_cross_source_status("")
            
            # Show new suggestions if any
            cross_source_suggestions = [
                s for s in self.proactive.data.active_suggestions 
                if "correlation_id" in s.context or "pattern_id" in s.context
            ]
            
            if cross_source_suggestions:
                print("\nNew cross-source suggestions:")
                self._display_suggestions(cross_source_suggestions[:3])
            else:
                print("No new cross-source suggestions generated.")
                
        except Exception as e:
            print(f"Error running cross-source analysis: {e}")
    
    def update_context_with_query(self, query_text, results=None):
        """
        Update context with a new query.
        
        Args:
            query_text: The query text
            results: Optional results information
        """
        # Update recent queries list
        self.context["last_queries"] = [query_text] + self.context.get("last_queries", [])[:4]
        
        # Extract topics from query
        topics = self._extract_topics_from_query(query_text)
        if topics:
            self.context["current_topics"] = topics
            
        # Update context with results info if provided
        if results:
            self.context["last_results_count"] = len(results) if hasattr(results, "__len__") else 0
            
        # Check if we should show suggestions after this query
        # Don't show after every query to avoid being annoying
        if random.random() < 0.3:  # 30% chance to show suggestions after a query
            self.check_suggestions(self.context)
    
    def _extract_topics_from_query(self, query_text):
        """
        Extract potential topics from a query.
        
        Args:
            query_text: The query text
            
        Returns:
            List of potential topics
        """
        # Simple keyword extraction (this could be more sophisticated)
        topics = []
        
        # Check against known topics
        for topic in self.memory.memory.semantic_topics.keys():
            if topic.lower() in query_text.lower():
                topics.append(topic)
                
        return topics
    
    def analyze_session(self, query_history=None):
        """
        Analyze the current session and update patterns.
        
        Args:
            query_history: Optional query history to analyze
        """
        if query_history:
            self.proactive.analyze_session(query_history, self.context)
        
        # Reset context for next session
        self.context = {
            "session_start": datetime.now(timezone.utc),
            "last_queries": [],
            "current_goal": self.context.get("current_goal"),
            "current_topics": self.context.get("current_topics", [])
        }
    
    def get_initial_suggestions(self):
        """
        Get initial suggestions to show at the start of a session.
        
        Returns:
            List of suggestions
        """
        # Generate suggestions based on current context
        suggestions = self.proactive.generate_suggestions(self.context)
        
        # Filter to only show high-priority or goal-related suggestions
        important_suggestions = [
            s for s in suggestions 
            if s.priority in ["high", "critical"] or s.suggestion_type == SuggestionType.GOAL_PROGRESS
        ]
        
        # Only show a limited number to avoid overwhelming the user
        return important_suggestions[:2]


def main():
    """Test the Proactive CLI integration."""
    # This would normally be integrated with the main CLI
    from query.memory.archivist_memory import ArchivistMemory
    
    # Create a simple mock CLI class
    class MockCLI:
        def __init__(self):
            from db import IndalekoDBConfig
            self.db_config = IndalekoDBConfig()
            self.query_history = None
    
    # Initialize components
    cli = MockCLI()
    memory = ArchivistMemory(cli.db_config)
    proactive = ProactiveArchivist(memory)
    cli_integration = ProactiveCliIntegration(cli, memory, proactive)
    
    # Add some test data
    memory.add_long_term_goal("Document Organization", "Organize and tag work documents")
    memory.add_insight("temporal", "User typically searches for work documents on Monday mornings", 0.8)
    
    # Test commands
    print("Testing Proactive CLI Integration")
    cli_integration.show_proactive_help("")
    
    # Show initial suggestions
    initial_suggestions = cli_integration.get_initial_suggestions()
    if initial_suggestions:
        cli_integration._display_suggestions(initial_suggestions)
    else:
        print("\nNo initial suggestions available.")
    
    # Simulate a query
    print("\nSimulating a query about work documents...")
    cli_integration.update_context_with_query("Find recent work documents about budgets")
    
    # Show suggestions
    cli_integration.show_suggestions_cmd("")


if __name__ == "__main__":
    main()