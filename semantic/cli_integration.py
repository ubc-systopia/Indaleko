#!/usr/bin/env python3
"""
Indaleko Project - CLI Integration for Semantic Performance Monitoring.

This module integrates the semantic performance monitoring framework with
the Indaleko command-line interface, allowing users to run and analyze
performance experiments directly from the CLI.

Note: Semantic extractors should only run on machines where data is physically
stored. Storage recorders should add device-file relationships (UUID:
f3dde8a2-cff5-41b9-bd00-0f41330895e1) between files and the machines
where they're stored.
"""

import json

from datetime import UTC, datetime

from semantic.experiments.experiment_driver import SemanticExtractorExperiment
from semantic.performance_monitor import SemanticExtractorPerformance
from utils.cli.base import IndalekoBaseCLI


class SemanticPerformanceCliIntegration:
    """
    Integration for semantic performance monitoring with the Indaleko CLI.
    Provides commands for running performance experiments and viewing results.
    """

    def __init__(self, cli_instance: IndalekoBaseCLI) -> None:
        """
        Initialize the CLI integration.

        Args:
            cli_instance: The CLI instance to integrate with
        """
        self.cli = cli_instance
        self.experiment_driver = SemanticExtractorExperiment()
        self.performance_monitor = SemanticExtractorPerformance()

        # Register commands
        self.cli.register_command("/perf", self.handle_perf_command)
        self.cli.register_command("/experiments", self.handle_experiments_command)
        self.cli.register_command("/report", self.handle_report_command)

        # Add help text
        self.cli.append_help_text(
            "  /perf              - Show performance monitoring commands",
        )
        self.cli.append_help_text(
            "  /experiments       - List and run performance experiments",
        )
        self.cli.append_help_text("  /report            - Generate performance reports")

    def handle_perf_command(self, args: list[str]) -> None:
        """
        Handle the /perf command.

        Args:
            args: Command arguments
        """
        if not args or args[0] == "help":
            self.cli.output("Performance Monitoring Commands:")
            self.cli.output(
                "  /perf status              - Show current monitoring status",
            )
            self.cli.output(
                "  /perf enable              - Enable performance monitoring",
            )
            self.cli.output(
                "  /perf disable             - Disable performance monitoring",
            )
            self.cli.output(
                "  /perf stats               - Show current performance statistics",
            )
            self.cli.output(
                "  /perf reset               - Reset performance statistics",
            )
            self.cli.output(
                "  /perf analyze <file>      - Analyze performance data file",
            )
            return

        if args[0] == "status":
            status = "enabled" if self.performance_monitor.is_enabled() else "disabled"
            self.cli.output(f"Performance monitoring is {status}")
            return

        if args[0] == "enable":
            self.performance_monitor.enable()
            self.cli.output("Performance monitoring enabled")
            return

        if args[0] == "disable":
            self.performance_monitor.disable()
            self.cli.output("Performance monitoring disabled")
            return

        if args[0] == "stats":
            stats = self.performance_monitor.get_statistics()
            self.cli.output(json.dumps(stats, indent=2))
            return

        if args[0] == "reset":
            self.performance_monitor.reset_statistics()
            self.cli.output("Performance statistics reset")
            return

        if args[0] == "analyze" and len(args) > 1:
            try:
                results = self.experiment_driver.analyze_performance_data(args[1])
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error analyzing performance data: {e}")
            return

        self.cli.output(f"Unknown perf command: {args[0]}")

    def handle_experiments_command(self, args: list[str]) -> None:
        """
        Handle the /experiments command.

        Args:
            args: Command arguments
        """
        if not args or args[0] == "help":
            self.cli.output("Experiment Commands:")
            self.cli.output(
                "  /experiments list                      - List available experiments",
            )
            self.cli.output(
                "  /experiments throughput <type> <count> - Run throughput experiment",
            )
            self.cli.output(
                "  /experiments filetypes <type>          - Run file type comparison",
            )
            self.cli.output(
                "  /experiments scaling <type>            - Run size scaling analysis",
            )
            self.cli.output(
                "  /experiments coverage <type>           - Run coverage experiment",
            )
            return

        if args[0] == "list":
            self.cli.output("Available experiments:")
            self.cli.output(
                "  throughput - Measures extraction throughput (files/sec, MB/sec)",
            )
            self.cli.output(
                "  filetypes  - Compares performance across different file types",
            )
            self.cli.output(
                "  scaling    - Analyzes how performance scales with file size",
            )
            self.cli.output(
                "  coverage   - Projects metadata growth for different extractors",
            )
            return

        if args[0] == "throughput" and len(args) >= 3:
            try:
                extractor_type = args[1]
                sample_size = int(args[2])
                self.cli.output(
                    f"Running throughput experiment for {extractor_type} with {sample_size} files...",
                )
                results = self.experiment_driver.run_throughput_experiment(
                    extractor_type=extractor_type,
                    sample_size=sample_size,
                )
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error running throughput experiment: {e}")
            return

        if args[0] == "filetypes" and len(args) >= 2:
            try:
                extractor_type = args[1]
                self.cli.output(f"Running file type comparison for {extractor_type}...")
                results = self.experiment_driver.run_file_type_comparison(
                    extractor_type=extractor_type,
                )
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error running file type comparison: {e}")
            return

        if args[0] == "scaling" and len(args) >= 2:
            try:
                extractor_type = args[1]
                self.cli.output(
                    f"Running size scaling analysis for {extractor_type}...",
                )
                results = self.experiment_driver.run_size_scaling_analysis(
                    extractor_type=extractor_type,
                )
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error running size scaling analysis: {e}")
            return

        if args[0] == "coverage" and len(args) >= 2:
            try:
                extractor_type = args[1]
                self.cli.output(f"Running coverage experiment for {extractor_type}...")
                results = self.experiment_driver.run_coverage_experiment(
                    extractor_type=extractor_type,
                )
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error running coverage experiment: {e}")
            return

        self.cli.output(f"Unknown experiments command: {args[0]}")

    def handle_report_command(self, args: list[str]) -> None:
        """
        Handle the /report command.

        Args:
            args: Command arguments
        """
        if not args or args[0] == "help":
            self.cli.output("Report Commands:")
            self.cli.output(
                "  /report generate <type> <output>      - Generate performance report",
            )
            self.cli.output(
                "  /report compare <file1> <file2>       - Compare performance data files",
            )
            self.cli.output(
                "  /report summary <days>                - Summarize recent performance data",
            )
            return

        if args[0] == "generate" and len(args) >= 3:
            try:
                report_type = args[1]
                output_file = args[2]
                self.cli.output(f"Generating {report_type} report to {output_file}...")

                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                report_title = f"Indaleko Semantic Extractor Performance Report - {timestamp}"

                self.experiment_driver.generate_html_report(
                    report_title=report_title,
                    output_file=output_file,
                    report_type=report_type,
                )
                self.cli.output(f"Report generated: {output_file}")
            except Exception as e:
                self.cli.output(f"Error generating report: {e}")
            return

        if args[0] == "compare" and len(args) >= 3:
            try:
                file1 = args[1]
                file2 = args[2]
                self.cli.output(f"Comparing performance data: {file1} vs {file2}...")
                results = self.experiment_driver.compare_performance_data(file1, file2)
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error comparing performance data: {e}")
            return

        if args[0] == "summary" and len(args) >= 2:
            try:
                days = int(args[1])
                self.cli.output(f"Generating summary for the last {days} days...")
                results = self.experiment_driver.summarize_recent_performance(days)
                self.cli.output(json.dumps(results, indent=2))
            except Exception as e:
                self.cli.output(f"Error generating summary: {e}")
            return

        self.cli.output(f"Unknown report command: {args[0]}")


def register_semantic_performance_cli(
    cli_instance: IndalekoBaseCLI,
) -> SemanticPerformanceCliIntegration:
    """
    Register semantic performance monitoring with an Indaleko CLI instance.

    Args:
        cli_instance: The CLI instance to register with

    Returns:
        The CLI integration instance
    """
    return SemanticPerformanceCliIntegration(cli_instance)


if __name__ == "__main__":
    # Quick test for the CLI integration
    pass
