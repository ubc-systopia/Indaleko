"""
Analytics integration module for Indaleko Query CLI.

This module provides integration between the analytics packages and the query CLI,
enabling analytics commands directly within the CLI interface.

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
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple

from query.analytics.file_statistics import FileStatistics, display_report, format_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalyticsIntegration:
    """Integration between the analytics packages and the query CLI."""
    
    def __init__(self, cli_instance, db_config=None, debug=False):
        """
        Initialize the AnalyticsIntegration class.
        
        Args:
            cli_instance: The parent CLI instance
            db_config: Optional database configuration. If not provided, one will be created.
            debug: Whether to enable debug logging
        """
        self.cli = cli_instance
        self.db_config = db_config or getattr(cli_instance, 'db_config', None)
        self.debug = debug
        
        # Initialize file statistics
        self.file_statistics = FileStatistics(self.db_config)
        
        # Register commands with the CLI
        self._register_commands()
        
        logger.info("Analytics integration initialized")
        
    def _register_commands(self):
        """Register analytics commands with the CLI."""
        # Check if the CLI has the command registration methods
        if not hasattr(self.cli, 'register_command') or not callable(self.cli.register_command):
            logger.error("CLI instance doesn't have register_command method")
            return
            
        # Register the analytics command handler
        try:
            self.cli.register_command("/analytics", self.handle_analytics_command)
            logger.info("Registered /analytics command handler")
            
            # Add help text if the method exists
            if hasattr(self.cli, 'append_help_text') and callable(self.cli.append_help_text):
                self.cli.append_help_text("  /analytics           - Run analytics commands (stats, files, types, ages)")
                logger.info("Added analytics help text")
        except Exception as e:
            logger.error(f"Error registering analytics commands: {str(e)}", exc_info=self.debug)
        
    def handle_analytics_command(self, args_str: str) -> str:
        """
        Handle the /analytics command.
        
        Args:
            args_str: The arguments string passed to the command
            
        Returns:
            str: The command output
        """
        # Parse arguments
        parser = argparse.ArgumentParser(description="Indaleko Analytics Commands")
        parser.add_argument("command", nargs="?", default="help", 
                            help="The analytics command to run (stats, files, types, ages, help)")
        parser.add_argument("--output", "-o", type=str, default=".",
                            help="Output directory for reports and visualizations")
        parser.add_argument("--visualize", "-v", action="store_true",
                            help="Generate visualizations")
        parser.add_argument("--full", "-f", action="store_true",
                            help="Generate a full detailed report")
        
        try:
            args = parser.parse_args(args_str.split())
            command = args.command.lower()
            
            if command == "help" or command == "":
                return self._get_help_text()
            
            elif command == "stats" or command == "summary":
                return self._run_summary_stats()
            
            elif command == "files":
                return self._run_file_analysis()
            
            elif command == "types" or command == "extensions":
                return self._run_type_analysis()
            
            elif command == "ages":
                return self._run_age_analysis()
            
            elif command == "report":
                return self._run_full_report(args.output, args.visualize)
            
            else:
                return f"Unknown analytics command: {command}. Type '/analytics help' for available commands."
                
        except Exception as e:
            error_msg = f"Error processing analytics command: {str(e)}"
            logger.error(error_msg, exc_info=self.debug)
            return error_msg
    
    def _get_help_text(self) -> str:
        """Get the help text for analytics commands."""
        help_text = """
=== Indaleko Analytics Commands ===

Commands:
  /analytics stats       - Show basic file statistics summary
  /analytics files       - Analyze file counts and sizes
  /analytics types       - Analyze file type distribution
  /analytics ages        - Analyze file age distribution
  /analytics report      - Generate a comprehensive report with visualizations
  /analytics help        - Show this help message

Options:
  --output, -o DIR       - Specify output directory for reports
  --visualize, -v        - Generate visualizations
  --full, -f             - Generate full detailed report

Examples:
  /analytics stats
  /analytics report --output ./reports --visualize
"""
        return help_text
    
    def _run_summary_stats(self) -> str:
        """Run summary statistics analysis."""
        try:
            total_objects = self.file_statistics.count_total_objects()
            file_count = self.file_statistics.count_files()
            directory_count = self.file_statistics.count_directories()
            
            # Get size statistics
            size_stats = self.file_statistics.get_file_size_statistics()
            
            # Format the results
            result = "\n=== Indaleko File Statistics Summary ===\n\n"
            result += f"Total Objects: {total_objects:,}\n"
            result += f"Files: {file_count:,} ({file_count/max(1, total_objects)*100:.1f}%)\n"
            result += f"Directories: {directory_count:,} ({directory_count/max(1, total_objects)*100:.1f}%)\n"
            
            if size_stats:
                result += f"\nTotal Storage: {format_size(size_stats['total_size'])}\n"
                result += f"Average File Size: {format_size(size_stats['average_size'])}\n"
                result += f"Median File Size: {format_size(size_stats['median_size'])}\n"
            
            return result
            
        except Exception as e:
            error_msg = f"Error running summary statistics: {str(e)}"
            logger.error(error_msg, exc_info=self.debug)
            return error_msg
    
    def _run_file_analysis(self) -> str:
        """Run file analysis."""
        try:
            # Get size statistics
            size_stats = self.file_statistics.get_file_size_statistics()
            
            # Format the results
            result = "\n=== Indaleko File Size Analysis ===\n\n"
            result += f"File Count: {size_stats['count']:,}\n"
            result += f"Total Size: {format_size(size_stats['total_size'])}\n"
            result += f"Average Size: {format_size(size_stats['average_size'])}\n"
            result += f"Median Size: {format_size(size_stats['median_size'])}\n"
            result += f"Smallest File: {format_size(size_stats['min_size'])}\n"
            result += f"Largest File: {format_size(size_stats['max_size'])}\n"
            
            # Calculate size distribution
            if size_stats['count'] > 0:
                result += "\nSize Distribution Analysis:\n"
                
                # Calculate rough storage distribution
                total_size = size_stats['total_size']
                large_file_threshold = 100 * 1024 * 1024  # 100 MB
                medium_file_threshold = 1 * 1024 * 1024   # 1 MB
                small_file_threshold = 100 * 1024         # 100 KB
                
                # Use a separate AQL query to get size distribution
                # (simplified estimation for CLI display)
                result += "\nEstimated File Size Distribution:\n"
                result += f"- Very Large Files (>100 MB): ~{size_stats['max_size'] > large_file_threshold and '✓' or '✗'}\n"
                result += f"- Large Files (1-100 MB): ~{size_stats['max_size'] > medium_file_threshold and '✓' or '✗'}\n"
                result += f"- Medium Files (100 KB-1 MB): ~{size_stats['max_size'] > small_file_threshold and '✓' or '✗'}\n"
                result += f"- Small Files (<100 KB): ~{size_stats['min_size'] < small_file_threshold and '✓' or '✗'}\n"
                
                # Add recommendation for visualization
                result += "\nNote: Run '/analytics report --visualize' for detailed visualization of size distribution."
            
            return result
            
        except Exception as e:
            error_msg = f"Error running file analysis: {str(e)}"
            logger.error(error_msg, exc_info=self.debug)
            return error_msg
    
    def _run_type_analysis(self) -> str:
        """Run file type analysis."""
        try:
            # Get file type distribution
            file_types = self.file_statistics.get_file_type_distribution()
            
            # Format the results
            result = "\n=== Indaleko File Type Analysis ===\n\n"
            
            if not file_types:
                return result + "No file type information available."
            
            # Get total count for percentage calculation
            total_count = sum(file_types.values())
            
            # Sort by count and show top types
            sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)
            
            # Show top 10 types with percentages
            result += "Top 10 File Types:\n"
            for ext, count in sorted_types[:10]:
                percentage = count / total_count * 100 if total_count > 0 else 0
                result += f"- .{ext}: {count:,} files ({percentage:.1f}%)\n"
            
            # Show statistics
            result += f"\nTotal Unique File Types: {len(file_types)}\n"
            
            # Calculate diversity metrics
            if len(file_types) > 0 and total_count > 0:
                top_3_percentage = sum(count for _, count in sorted_types[:3]) / total_count * 100
                result += f"Top 3 Types Percentage: {top_3_percentage:.1f}%\n"
                
                # Indicate type diversity
                if len(file_types) > 20:
                    result += "File Type Diversity: High\n"
                elif len(file_types) > 10:
                    result += "File Type Diversity: Medium\n"
                else:
                    result += "File Type Diversity: Low\n"
            
            return result
            
        except Exception as e:
            error_msg = f"Error running file type analysis: {str(e)}"
            logger.error(error_msg, exc_info=self.debug)
            return error_msg
    
    def _run_age_analysis(self) -> str:
        """Run file age analysis."""
        try:
            # Get file age distribution
            age_distribution = self.file_statistics.get_file_age_distribution()
            
            # Format the results
            result = "\n=== Indaleko File Age Analysis ===\n\n"
            
            if not age_distribution:
                return result + "No file age information available."
            
            # Calculate total files and size for percentages
            total_files = sum(item["count"] for item in age_distribution)
            total_size = sum(item["total_size"] for item in age_distribution)
            
            # Show distribution with counts, sizes, and percentages
            result += "File Age Distribution:\n"
            for item in age_distribution:
                file_percentage = item["count"] / total_files * 100 if total_files > 0 else 0
                size_percentage = item["total_size"] / total_size * 100 if total_size > 0 else 0
                
                result += f"- {item['age_range']}: {item['count']:,} files ({file_percentage:.1f}%), "
                result += f"{format_size(item['total_size'])} ({size_percentage:.1f}%)\n"
            
            # Add age pattern analysis
            result += "\nFile Age Pattern Analysis:\n"
            
            # Check for recent activity
            recent_files = next((item for item in age_distribution if item["age_range"] == "Last week"), None)
            if recent_files and recent_files["count"] > 0:
                result += "- Recent Activity: Yes (files created/modified in the last week)\n"
            else:
                result += "- Recent Activity: No (no files created/modified in the last week)\n"
            
            # Check age pattern
            recent_count = sum(item["count"] for item in age_distribution 
                               if item["age_range"] in ["Last week", "Last month"])
            old_count = sum(item["count"] for item in age_distribution 
                            if "years" in item["age_range"])
            
            if total_files > 0:
                recent_percentage = recent_count / total_files * 100
                old_percentage = old_count / total_files * 100
                
                if recent_percentage > 50:
                    result += "- Primary Usage Pattern: Active (mostly recent files)\n"
                elif old_percentage > 50:
                    result += "- Primary Usage Pattern: Archive (mostly older files)\n"
                else:
                    result += "- Primary Usage Pattern: Mixed (balanced between recent and older files)\n"
            
            return result
            
        except Exception as e:
            error_msg = f"Error running file age analysis: {str(e)}"
            logger.error(error_msg, exc_info=self.debug)
            return error_msg
    
    def _run_full_report(self, output_dir: str = ".", visualize: bool = False) -> str:
        """
        Run a full comprehensive report.
        
        Args:
            output_dir: Directory to save report and visualizations
            visualize: Whether to generate visualizations
            
        Returns:
            str: Status message
        """
        try:
            # Generate the report
            logger.info(f"Generating full report at {output_dir}")
            report = self.file_statistics.generate_report(output_dir, visualize)
            
            # Create a message about the report
            result = f"\nFull analytics report generated at: {os.path.abspath(output_dir)}\n"
            result += f"- Report file: {os.path.join(output_dir, 'file_statistics_report.json')}\n"
            
            if visualize:
                result += "- Visualizations:\n"
                result += f"  - {os.path.join(output_dir, 'files_vs_directories.png')}\n"
                result += f"  - {os.path.join(output_dir, 'file_types.png')}\n"
                result += f"  - {os.path.join(output_dir, 'file_age_distribution.png')}\n"
                result += f"  - {os.path.join(output_dir, 'file_size_by_age.png')}\n"
            
            # Display the report in a formatted way
            result += "\n=== Report Summary ===\n"
            display_buffer = []
            display_report(report, display_buffer=display_buffer)
            result += "\n".join(display_buffer)
            
            return result
            
        except Exception as e:
            error_msg = f"Error generating full report: {str(e)}"
            logger.error(error_msg, exc_info=self.debug)
            return error_msg

# Update display_report function in file_statistics.py to support output buffer
def register_analytics_commands(cli_instance, db_config=None, debug=False):
    """
    Register analytics commands with the CLI.
    
    Args:
        cli_instance: The CLI instance
        db_config: Optional database configuration
        debug: Whether to enable debug mode
        
    Returns:
        AnalyticsIntegration: The analytics integration instance
    """
    return AnalyticsIntegration(cli_instance, db_config, debug)

def add_analytics_arguments(parser):
    """
    Add analytics-related arguments to the argument parser.
    
    Args:
        parser: The argument parser
    """
    parser.add_argument(
        "--analytics", 
        action="store_true",
        help="Enable analytics capabilities"
    )