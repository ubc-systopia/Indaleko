"""
CLI integration for the Archivist memory system.

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
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.archivist_memory import ArchivistMemory
# pylint: enable=wrong-import-position


class ArchivistCliIntegration:
    """
    Integrates Archivist memory capabilities with the Indaleko Query CLI.
    """
    
    def __init__(self, cli_instance, archivist_memory=None):
        """
        Initialize the CLI integration for Archivist memory.
        
        Args:
            cli_instance: The CLI instance to integrate with
            archivist_memory: An existing ArchivistMemory instance, or None to create a new one
        """
        self.cli = cli_instance
        self.memory = archivist_memory or ArchivistMemory(self.cli.db_config)
        
        # Add the memory commands to the CLI
        self.commands = {
            "/memory": self.show_memory_help,
            "/forward": self.generate_forward_prompt,
            "/load": self.load_forward_prompt,
            "/goals": self.manage_goals,
            "/insights": self.view_insights,
            "/topics": self.view_topics,
            "/strategies": self.view_strategies,
            "/save": self.save_memory
        }
    
    def handle_command(self, command):
        """
        Handle a memory-related command.
        
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
    
    def show_memory_help(self, args):
        """Show help for memory commands."""
        print("\nArchivist Memory Commands:")
        print("-------------------------")
        print("/memory     - Show this help message")
        print("/forward    - Generate a forward prompt for the next session")
        print("/load       - Load a forward prompt from a previous session")
        print("/goals      - Manage long-term goals")
        print("/insights   - View insights about search patterns")
        print("/topics     - View topics of interest")
        print("/strategies - View effective search strategies")
        print("/save       - Save the current memory state")
    
    def generate_forward_prompt(self, args):
        """Generate and display a forward prompt."""
        # Update memory with recent query history first
        if hasattr(self.cli, "query_history"):
            self.memory.distill_knowledge(self.cli.query_history, self.cli.query_history)
            
        # Generate and display prompt
        prompt = self.memory.generate_forward_prompt()
        print("\nGenerated Forward Prompt:")
        print("=========================")
        print(prompt)
        
        # Save to file if requested
        if args and args.lower().startswith("save"):
            filename = args.split(maxsplit=1)[1] if len(args.split()) > 1 else "archivist_prompt.txt"
            with open(filename, "w") as f:
                f.write(prompt)
            print(f"\nPrompt saved to {filename}")
    
    def load_forward_prompt(self, args):
        """Load a forward prompt."""
        if args:
            # Load from file
            try:
                with open(args, "r") as f:
                    prompt = f.read()
                self.memory.update_from_forward_prompt(prompt)
                print(f"Forward prompt loaded from {args}")
                self.memory.save_memory()
            except Exception as e:
                print(f"Error loading prompt: {e}")
        else:
            # Interactive load
            print("Enter or paste the forward prompt, end with a line containing only '---':")
            lines = []
            while True:
                line = input()
                if line == "---":
                    break
                lines.append(line)
            
            if lines:
                prompt = "\n".join(lines)
                self.memory.update_from_forward_prompt(prompt)
                print("Forward prompt loaded")
                self.memory.save_memory()
    
    def manage_goals(self, args):
        """Interface for managing long-term goals."""
        if args:
            # Handle sub-commands
            parts = args.split(maxsplit=1)
            subcmd = parts[0].lower()
            
            if subcmd == "add" and len(parts) > 1:
                # Add a new goal
                goal_parts = parts[1].split(" - ", 1)
                if len(goal_parts) == 2:
                    name, description = goal_parts
                    self.memory.add_long_term_goal(name, description)
                    print(f"Goal '{name}' added")
                    self.memory.save_memory()
                else:
                    print("Usage: /goals add NAME - DESCRIPTION")
                    
            elif subcmd == "progress" and len(parts) > 1:
                # Update goal progress
                goal_parts = parts[1].split(maxsplit=1)
                if len(goal_parts) == 2:
                    name, progress_str = goal_parts
                    try:
                        progress = float(progress_str) / 100.0
                        self.memory.update_goal_progress(name, progress)
                        print(f"Goal '{name}' progress updated to {progress_str}%")
                        self.memory.save_memory()
                    except ValueError:
                        print("Progress must be a number between 0 and 100")
                else:
                    print("Usage: /goals progress NAME PERCENTAGE")
            else:
                print("Unknown goals command. Use /goals without arguments to view goals.")
        else:
            # Display goals
            goals = self.memory.memory.long_term_goals
            if not goals:
                print("No long-term goals defined")
                print("Use '/goals add NAME - DESCRIPTION' to add a goal")
                return
                
            print("\nLong-Term Goals:")
            print("---------------")
            for i, goal in enumerate(goals, 1):
                print(f"{i}. {goal.name} - {goal.progress*100:.0f}% complete")
                print(f"   {goal.description}")
                print(f"   Last updated: {goal.last_updated.strftime('%Y-%m-%d %H:%M')}")
                print()
                
            print("\nCommands:")
            print("  /goals add NAME - DESCRIPTION  # Add a new goal")
            print("  /goals progress NAME PERCENTAGE # Update goal progress")
    
    def view_insights(self, args):
        """View insights about search patterns."""
        insights = self.memory.memory.insights
        if not insights:
            print("No insights recorded yet")
            return
            
        insights = sorted(insights, key=lambda x: x.confidence, reverse=True)
        
        print("\nSearch Insights:")
        print("--------------")
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight.insight}")
            print(f"   Category: {insight.category}, Confidence: {insight.confidence:.2f}, Impact: {insight.impact}")
            if insight.supporting_evidence:
                print(f"   Evidence: {', '.join(insight.supporting_evidence[:3])}")
            print()
    
    def view_topics(self, args):
        """View topics of interest."""
        topics = self.memory.memory.semantic_topics
        if not topics:
            print("No topics of interest recorded yet")
            return
            
        print("\nTopics of Interest:")
        print("-----------------")
        for topic, importance in sorted(topics.items(), key=lambda x: x[1], reverse=True):
            print(f"- {topic}: {importance:.2f}")
    
    def view_strategies(self, args):
        """View effective search strategies."""
        strategies = self.memory.memory.effective_strategies
        if not strategies:
            print("No effective strategies recorded yet")
            return
            
        print("\nEffective Search Strategies:")
        print("---------------------------")
        for strategy in sorted(strategies, key=lambda x: x.success_rate, reverse=True):
            print(f"- {strategy.strategy_name}: {strategy.description}")
            print(f"  Success rate: {strategy.success_rate:.2f}")
            if strategy.applicable_contexts:
                print(f"  Applicable for: {', '.join(strategy.applicable_contexts)}")
            print()
    
    def save_memory(self, args):
        """Save the current memory state."""
        self.memory.save_memory()
        print("Memory state saved to database")
        
    def update_from_session(self, query_history):
        """
        Update the memory with information from the current session.
        
        Args:
            query_history: The query history from the current session
        """
        self.memory.distill_knowledge(query_history, query_history)
        self.memory.save_memory()