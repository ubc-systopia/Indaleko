#!/usr/bin/env python3
"""
Run the model-based data generator benchmark suite.

This script provides a command-line interface for running comprehensive
benchmarks of the model-based data generator across different scenarios
and generator configurations.
"""

import argparse
import configparser
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the Python path
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.testing.benchmark import BenchmarkSuite


def setup_logging(verbose: bool = False):
    """Set up logging with appropriate level.

    Args:
        verbose: Whether to enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("benchmark.log")
        ]
    )


def parse_args():
    """Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run model-based data generation benchmarks")

    parser.add_argument(
        "--config",
        type=str,
        help="Path to benchmark configuration file",
        default=None
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to save benchmark results",
        default="./benchmark_results"
    )

    parser.add_argument(
        "--repeat",
        type=int,
        help="Number of times to repeat each benchmark",
        default=1
    )

    parser.add_argument(
        "--scenarios",
        type=str,
        nargs="+",
        help="Specific scenarios to run (default: all)",
        default=None
    )

    parser.add_argument(
        "--generators",
        type=str,
        nargs="+",
        help="Specific generators to use (default: all)",
        default=None
    )

    parser.add_argument(
        "--small-only",
        action="store_true",
        help="Only run small dataset scenarios"
    )

    parser.add_argument(
        "--skip-large",
        action="store_true",
        help="Skip large dataset scenarios"
    )

    parser.add_argument(
        "--report-formats",
        type=str,
        nargs="+",
        choices=["md", "json", "csv", "html", "pdf"],
        help="Report formats to generate",
        default=["md", "json"]
    )

    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip chart generation"
    )

    parser.add_argument(
        "--domain-specific",
        action="store_true",
        help="Run only domain-specific scenarios (storage, semantic, activity, relationship, cross-domain)"
    )

    parser.add_argument(
        "--compare-legacy",
        action="store_true",
        help="Run only the legacy generator and model-based generators for comparison"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def load_custom_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load a custom configuration file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    if not config_path:
        return {}

    path = Path(config_path)
    if not path.exists():
        logging.warning(f"Configuration file {config_path} not found, using defaults")
        return {}

    with open(path, "r") as f:
        config = json.load(f)

    logging.info(f"Loaded configuration from {config_path}")
    return config


def main():
    """Main function."""
    # Parse arguments
    args = parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Load configuration
    config = load_custom_config(args.config)

    # Set output directory
    output_dir = Path(args.output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_dir / f"benchmark_{timestamp}"

    # Override config with command-line arguments
    config["output_dir"] = str(output_dir)
    config["repeat"] = args.repeat

    # Load OpenAI API key
    project_root = Path(__file__).parent.parent.parent.parent
    openai_config_path = project_root / "config" / "openai-key.ini"

    if openai_config_path.exists():
        logging.info(f"Loading OpenAI key from {openai_config_path}")
        openai_config = configparser.ConfigParser()
        openai_config.read(openai_config_path)

        if "openai" in openai_config and "api_key" in openai_config["openai"]:
            os.environ["OPENAI_API_KEY"] = openai_config["openai"]["api_key"].strip('"')
            logging.info("OpenAI API key set successfully")
        else:
            logging.warning("Invalid OpenAI config format, missing api_key")
    else:
        logging.warning(f"OpenAI config not found at {openai_config_path}")

    # Filter scenarios if specified
    if args.scenarios:
        if "scenarios" in config:
            config["scenarios"] = [s for s in config["scenarios"] if s["name"] in args.scenarios]
        else:
            # Need to filter the default scenarios later
            config["scenario_filter"] = args.scenarios

    # Filter generators if specified
    if args.generators:
        if "generators" in config:
            config["generators"] = [g for g in config["generators"] if g["name"] in args.generators]
        else:
            # Need to filter the default generators later
            config["generator_filter"] = args.generators

    # Handle special scenario filters
    if args.small_only:
        config["scenario_filter"] = ["small_dataset"]

    if args.skip_large:
        if "scenario_filter" in config:
            if "large_dataset" in config["scenario_filter"]:
                config["scenario_filter"].remove("large_dataset")
        else:
            config["scenario_filter"] = ["small_dataset", "medium_dataset",
                                        "storage_focused", "semantic_focused",
                                        "activity_sequence", "relationship_network",
                                        "cross_domain"]

    if args.domain_specific:
        config["scenario_filter"] = ["storage_focused", "semantic_focused",
                                    "activity_sequence", "relationship_network",
                                    "cross_domain"]

    if args.compare_legacy:
        config["generator_filter"] = ["legacy", "model_based", "model_based_templates"]

    # Setup chart generation
    if args.no_charts:
        config["skip_charts"] = True

    # Create benchmark suite
    benchmark = BenchmarkSuite(config_path=None)

    # Apply configuration
    benchmark.config = config

    # Apply scenario filter if specified
    if "scenario_filter" in config:
        benchmark.config["scenarios"] = [s for s in benchmark.DEFAULT_SCENARIOS
                                        if s["name"] in config["scenario_filter"]]

    # Apply generator filter if specified
    if "generator_filter" in config:
        benchmark.config["generators"] = [g for g in benchmark.DEFAULT_GENERATORS
                                         if g["name"] in config["generator_filter"]]

    # Run benchmarks
    logging.info(f"Starting benchmark suite, results will be saved to {output_dir}")
    results = benchmark.run_benchmarks()

    # Generate additional report formats if requested
    if "md" in args.report_formats:
        # Already generated by default
        logging.info(f"Markdown report saved to {output_dir}/benchmark_report.md")

    if "html" in args.report_formats:
        try:
            import markdown

            md_path = output_dir / "benchmark_report.md"
            html_path = output_dir / "benchmark_report.html"

            with open(md_path, "r") as f:
                md_content = f.read()

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Model-Based Data Generator Benchmark Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; }}
                    h1 {{ color: #333; }}
                    h2 {{ color: #444; margin-top: 30px; }}
                    h3 {{ color: #555; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    img {{ max-width: 800px; margin: 20px 0; }}
                    code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; }}
                    pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                </style>
            </head>
            <body>
                {markdown.markdown(md_content, extensions=['tables'])}
            </body>
            </html>
            """

            with open(html_path, "w") as f:
                f.write(html)

            logging.info(f"HTML report saved to {html_path}")
        except ImportError:
            logging.warning("markdown package not available, skipping HTML report generation")

    if "pdf" in args.report_formats:
        try:
            import weasyprint

            html_path = output_dir / "benchmark_report.html"
            pdf_path = output_dir / "benchmark_report.pdf"

            # Check if HTML report exists, if not, generate it
            if not html_path.exists() and "html" not in args.report_formats:
                try:
                    import markdown

                    md_path = output_dir / "benchmark_report.md"

                    with open(md_path, "r") as f:
                        md_content = f.read()

                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>Model-Based Data Generator Benchmark Report</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; }}
                            h1 {{ color: #333; }}
                            h2 {{ color: #444; margin-top: 30px; }}
                            h3 {{ color: #555; }}
                            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                            th {{ background-color: #f2f2f2; }}
                            tr:hover {{ background-color: #f5f5f5; }}
                            img {{ max-width: 800px; margin: 20px 0; }}
                            code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; }}
                            pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                        </style>
                    </head>
                    <body>
                        {markdown.markdown(md_content, extensions=['tables'])}
                    </body>
                    </html>
                    """

                    with open(html_path, "w") as f:
                        f.write(html)
                except ImportError:
                    logging.warning("markdown package not available, skipping PDF report generation")
                    html_path = None

            # Generate PDF from HTML
            if html_path.exists():
                weasyprint.HTML(str(html_path)).write_pdf(str(pdf_path))
                logging.info(f"PDF report saved to {pdf_path}")
            else:
                logging.warning("HTML report not available, skipping PDF report generation")
        except ImportError:
            logging.warning("weasyprint package not available, skipping PDF report generation")

    logging.info(f"Benchmark suite completed with {len(results)} test cases")
    logging.info(f"Reports are available in the {output_dir} directory")


if __name__ == "__main__":
    main()
