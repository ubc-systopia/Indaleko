"""
CLI integration for the Archivist database optimizer.

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

from datetime import datetime, timedelta


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
import contextlib

from archivist.database_optimizer import DatabaseOptimizer
from query.memory.archivist_memory import ArchivistMemory


# pylint: enable=wrong-import-position


class DatabaseOptimizerCliIntegration:
    """CLI integration for the Archivist database optimizer."""

    def __init__(self, cli_instance, archivist_memory=None, database_optimizer=None) -> None:
        """
        Initialize the database optimizer CLI integration.

        Args:
            cli_instance: The CLI instance to integrate with
            archivist_memory: Optional ArchivistMemory instance
            database_optimizer: Optional DatabaseOptimizer instance
        """
        self.cli = cli_instance
        self.memory = archivist_memory or ArchivistMemory(self.cli.db_config)
        self.optimizer = database_optimizer or DatabaseOptimizer(
            self.cli.db_config.db,
            self.memory,
            self.cli.query_history if hasattr(self.cli, "query_history") else None,
        )

        # Add commands
        self.commands = {
            "/optimize": self.handle_optimize_command,
            "/analyze": self.analyze_queries,
            "/index": self.manage_indexes,
            "/view": self.manage_views,
            "/query": self.optimize_queries,
            "/impact": self.show_impact,
        }

    def handle_command(self, command) -> bool:
        """
        Handle a database optimization command.

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

    def handle_optimize_command(self, args) -> None:
        """
        Handle the main optimize command.

        Args:
            args: Command arguments
        """
        # If no args, show help
        if not args:
            self._show_optimize_help()
            return

        # Parse arguments
        subcommand = args.split()[0].lower()

        if subcommand == "help":
            self._show_optimize_help()
        elif subcommand == "analyze":
            self.analyze_queries("")
        elif subcommand == "apply":
            self._apply_recommendations(
                args.split()[1:] if len(args.split()) > 1 else [],
            )
        elif subcommand == "status":
            self._show_optimization_status()
        else:
            self._show_optimize_help()

    def _show_optimize_help(self) -> None:
        """Show help for database optimization commands."""

    def analyze_queries(self, args) -> None:
        """
        Analyze query patterns and suggest optimizations.

        Args:
            args: Command arguments
        """
        # Parse optional time period
        days = 7  # Default to 7 days

        if args:
            with contextlib.suppress(ValueError, IndexError):
                days = int(args.split()[0])

        analysis = self.optimizer.analyze_query_patterns(timedelta(days=days))

        # Print summary

        # Print index recommendations
        index_recs = analysis.get("index_recommendations", [])
        if index_recs:
            recs_to_show = min(5, len(index_recs))  # Show top 5 by default

            table_data = []
            for i, rec in enumerate(index_recs[:recs_to_show], 1):
                table_data.append(
                    [i, rec.short_description(), f"{rec.estimated_impact:.2f}"],
                )


            if len(index_recs) > recs_to_show:
                pass

        else:
            pass

        # Print view recommendations
        view_recs = analysis.get("view_recommendations", [])
        if view_recs:
            recs_to_show = min(3, len(view_recs))  # Show top 3 by default

            table_data = []
            for i, rec in enumerate(view_recs[:recs_to_show], 1):
                table_data.append(
                    [i, rec.short_description(), f"{rec.estimated_impact:.2f}"],
                )


            if len(view_recs) > recs_to_show:
                pass

        else:
            pass

        # Print query optimizations
        query_opts = analysis.get("query_optimizations", [])
        if query_opts:
            opts_to_show = min(3, len(query_opts))  # Show top 3 by default

            table_data = []
            for i, opt in enumerate(query_opts[:opts_to_show], 1):
                table_data.append(
                    [i, opt.optimization_type, f"{opt.estimated_speedup:.1f}x"],
                )


            if len(query_opts) > opts_to_show:
                pass

        else:
            pass

    def _apply_recommendations(self, args) -> None:
        """
        Apply recommended optimizations.

        Args:
            args: Command arguments
        """
        if not args:
            return

        opt_type = args[0].lower()
        count = int(args[1]) if len(args) > 1 else 1

        if opt_type == "index":
            # Apply top N index recommendations
            self._apply_index_recommendations(count)
        elif opt_type == "view":
            # Apply top N view recommendations
            self._apply_view_recommendations(count)
        elif opt_type == "all":
            # Apply all types of recommendations
            self._apply_index_recommendations(count)
            self._apply_view_recommendations(count)
        else:
            pass

    def _apply_index_recommendations(self, count) -> None:
        """
        Apply top N index recommendations.

        Args:
            count: Number of recommendations to apply
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        index_recs = analysis.get("index_recommendations", [])

        if not index_recs:
            return

        # Apply top N recommendations
        applied_count = 0
        for _i, rec in enumerate(index_recs[:count], 1):
            result = self.optimizer.create_index(rec)

            if result["status"] == "success" or result["status"] == "already_created":
                applied_count += 1
            else:
                pass


    def _apply_view_recommendations(self, count) -> None:
        """
        Apply top N view recommendations.

        Args:
            count: Number of recommendations to apply
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        view_recs = analysis.get("view_recommendations", [])

        if not view_recs:
            return

        # Apply top N recommendations
        applied_count = 0
        for _i, rec in enumerate(view_recs[:count], 1):
            result = self.optimizer.create_view(rec)

            if result["status"] == "success" or result["status"] == "already_created":
                applied_count += 1
            else:
                pass


    def _show_optimization_status(self) -> None:
        """Show the current status of database optimizations."""
        status = self.optimizer.get_ongoing_optimizations()


        if status["recent_optimizations"]:

            table_data = []
            for opt in status["recent_optimizations"]:
                impact = f"{opt['impact']:.2f}x" if opt["impact"] else "Pending"
                table_data.append(
                    [
                        opt["type"],
                        opt["description"],
                        opt["applied_at"].strftime("%Y-%m-%d %H:%M"),
                        impact,
                    ],
                )


    def manage_indexes(self, args) -> None:
        """
        Manage index recommendations.

        Args:
            args: Command arguments
        """
        if not args:
            return

        parts = args.split()
        subcommand = parts[0].lower()

        if subcommand == "list":
            self._list_index_recommendations()
        elif subcommand == "create" and len(parts) > 1:
            try:
                index_num = int(parts[1])
                self._create_index(index_num)
            except ValueError:
                pass
        elif subcommand == "info" and len(parts) > 1:
            try:
                index_num = int(parts[1])
                self._show_index_info(index_num)
            except ValueError:
                pass
        else:
            pass

    def _list_index_recommendations(self) -> None:
        """List all index recommendations."""
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        index_recs = analysis.get("index_recommendations", [])

        if not index_recs:
            return


        table_data = []
        for i, rec in enumerate(index_recs, 1):
            status = "Created" if rec.created else "Pending"
            table_data.append(
                [
                    i,
                    rec.collection,
                    ", ".join(rec.fields),
                    rec.index_type,
                    f"{rec.estimated_impact:.2f}",
                    status,
                ],
            )


    def _create_index(self, index_num) -> None:
        """
        Create a specific index recommendation.

        Args:
            index_num: Index number to create (1-based)
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        index_recs = analysis.get("index_recommendations", [])

        if not index_recs:
            return

        if index_num < 1 or index_num > len(index_recs):
            return

        # Get the recommendation
        rec = index_recs[index_num - 1]

        # Create the index
        result = self.optimizer.create_index(rec)

        if result["status"] == "success" or result["status"] == "already_created":
            pass
        else:
            pass

    def _show_index_info(self, index_num) -> None:
        """
        Show detailed information about an index recommendation.

        Args:
            index_num: Index number to show (1-based)
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        index_recs = analysis.get("index_recommendations", [])

        if not index_recs:
            return

        if index_num < 1 or index_num > len(index_recs):
            return

        # Get the recommendation
        rec = index_recs[index_num - 1]


        if rec.created:
            pass


        if rec.affected_queries:
            for _i, query_id in enumerate(rec.affected_queries[:3], 1):
                query = self.optimizer.query_history.get_query_by_id(query_id)
                if query and hasattr(query, "Query"):
                    pass

            if len(rec.affected_queries) > 3:
                pass

    def manage_views(self, args) -> None:
        """
        Manage view recommendations.

        Args:
            args: Command arguments
        """
        if not args:
            return

        parts = args.split()
        subcommand = parts[0].lower()

        if subcommand == "list":
            self._list_view_recommendations()
        elif subcommand == "create" and len(parts) > 1:
            try:
                view_num = int(parts[1])
                self._create_view(view_num)
            except ValueError:
                pass
        elif subcommand == "info" and len(parts) > 1:
            try:
                view_num = int(parts[1])
                self._show_view_info(view_num)
            except ValueError:
                pass
        else:
            pass

    def _list_view_recommendations(self) -> None:
        """List all view recommendations."""
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        view_recs = analysis.get("view_recommendations", [])

        if not view_recs:
            return


        table_data = []
        for i, rec in enumerate(view_recs, 1):
            status = "Created" if rec.created else "Pending"
            collections = ", ".join(rec.collections)
            field_count = sum(len(fields) for fields in rec.fields.values())

            table_data.append(
                [
                    i,
                    rec.name,
                    collections,
                    field_count,
                    f"{rec.estimated_impact:.2f}",
                    status,
                ],
            )


    def _create_view(self, view_num) -> None:
        """
        Create a specific view recommendation.

        Args:
            view_num: View number to create (1-based)
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        view_recs = analysis.get("view_recommendations", [])

        if not view_recs:
            return

        if view_num < 1 or view_num > len(view_recs):
            return

        # Get the recommendation
        rec = view_recs[view_num - 1]

        # Create the view
        result = self.optimizer.create_view(rec)

        if result["status"] == "success" or result["status"] == "already_created":
            pass
        else:
            pass

    def _show_view_info(self, view_num) -> None:
        """
        Show detailed information about a view recommendation.

        Args:
            view_num: View number to show (1-based)
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        view_recs = analysis.get("view_recommendations", [])

        if not view_recs:
            return

        if view_num < 1 or view_num > len(view_recs):
            return

        # Get the recommendation
        rec = view_recs[view_num - 1]

        for _coll, _fields in rec.fields.items():
            pass


        if rec.created:
            pass


        if rec.affected_queries:
            for _i, query_id in enumerate(rec.affected_queries[:3], 1):
                query = self.optimizer.query_history.get_query_by_id(query_id)
                if query and hasattr(query, "Query"):
                    pass

            if len(rec.affected_queries) > 3:
                pass

    def optimize_queries(self, args) -> None:
        """
        Manage query optimizations.

        Args:
            args: Command arguments
        """
        if not args:
            return

        parts = args.split()
        subcommand = parts[0].lower()

        if subcommand == "list":
            self._list_query_optimizations()
        elif subcommand == "info" and len(parts) > 1:
            try:
                query_num = int(parts[1])
                self._show_query_optimization_info(query_num)
            except ValueError:
                pass
        else:
            pass

    def _list_query_optimizations(self) -> None:
        """List all query optimization recommendations."""
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        query_opts = analysis.get("query_optimizations", [])

        if not query_opts:
            return


        table_data = []
        for i, opt in enumerate(query_opts, 1):
            status = "Verified" if opt.verified else "Pending"
            query_summary = opt.original_query[:50] + "..." if len(opt.original_query) > 50 else opt.original_query

            table_data.append(
                [
                    i,
                    opt.optimization_type,
                    query_summary,
                    f"{opt.estimated_speedup:.1f}x",
                    status,
                ],
            )


    def _show_query_optimization_info(self, query_num) -> None:
        """
        Show detailed information about a query optimization.

        Args:
            query_num: Query number to show (1-based)
        """
        # Get analysis
        analysis = self.optimizer.analyze_query_patterns()
        query_opts = analysis.get("query_optimizations", [])

        if not query_opts:
            return

        if query_num < 1 or query_num > len(query_opts):
            return

        # Get the recommendation
        opt = query_opts[query_num - 1]


        if opt.verified:
            pass



        if opt.optimized_query != opt.original_query:
            pass

    def show_impact(self, args) -> None:
        """
        Show impact of applied optimizations.

        Args:
            args: Command arguments
        """
        # Get optimization status
        status = self.optimizer.get_ongoing_optimizations()

        if status["total_optimizations"] == 0:
            return


        # Get recent queries
        recent_time = datetime.now() - timedelta(days=1)
        recent_queries = self.optimizer.query_history.get_queries_after(recent_time)

        if recent_queries:
            # Calculate average execution time
            total_time = sum(getattr(q, "ExecutionTimeMs", 0) for q in recent_queries)
            total_time / len(recent_queries)

            # Count slow queries
            slow_threshold = 500  # ms
            sum(1 for q in recent_queries if getattr(q, "ExecutionTimeMs", 0) > slow_threshold)

        else:
            pass

        # Show recent optimizations with impact
        if status["recent_optimizations"]:

            table_data = []
            for opt in status["recent_optimizations"]:
                if opt["impact"]:
                    impact_text = f"{opt['impact']:.2f}x"
                    evaluation = (
                        "Significant improvement"
                        if opt["impact"] > 1.5
                        else (
                            "Moderate improvement"
                            if opt["impact"] > 1.1
                            else (
                                "Minimal improvement"
                                if opt["impact"] > 1.0
                                else ("No improvement" if opt["impact"] >= 0.9 else "Performance regression")
                            )
                        )
                    )
                else:
                    impact_text = "Pending"
                    evaluation = "Not yet measured"

                table_data.append(
                    [opt["type"], opt["description"], impact_text, evaluation],
                )



def register_with_cli(cli_instance):
    """
    Register the database optimizer with the CLI.

    Args:
        cli_instance: The CLI instance to register with

    Returns:
        The created DatabaseOptimizerCliIntegration instance
    """
    # Create integration
    integration = DatabaseOptimizerCliIntegration(cli_instance)

    # Register commands
    for cmd in integration.commands:
        cli_instance.register_command(cmd, integration.handle_command)

    # Add help text
    cli_instance.append_help_text("\nDatabase Optimization Commands:")
    cli_instance.append_help_text(
        "  /optimize            - Show database optimization commands",
    )
    cli_instance.append_help_text(
        "  /analyze             - Analyze query patterns and suggest optimizations",
    )
    cli_instance.append_help_text(
        "  /index               - Manage index recommendations",
    )
    cli_instance.append_help_text(
        "  /view                - Manage view recommendations",
    )
    cli_instance.append_help_text("  /query               - Manage query optimizations")
    cli_instance.append_help_text(
        "  /impact              - Show impact of applied optimizations",
    )

    return integration


def main() -> None:
    """Test the database optimizer CLI integration."""
    # This would normally be called from the CLI


if __name__ == "__main__":
    main()
