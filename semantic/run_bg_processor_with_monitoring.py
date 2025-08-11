#!/usr/bin/env python3
"""
Extended wrapper for Indaleko's semantic background processor with performance monitoring.

This version adds:
1. Performance monitoring for all extraction operations
2. Detailed statistical reports
3. Database usage metrics
4. Visualization capabilities

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
import datetime
import json
import logging
import os
import sys
import threading
import time


# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Configure logging
log_dir = os.path.join(os.environ["INDALEKO_ROOT"], "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "indaleko_bg_processor_monitor.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("IndalekoBgProcessorMonitor")

# pylint: disable=wrong-import-position
from semantic.background_processor import IndalekoBackgroundProcessor
from semantic.performance_monitor import (
    SemanticExtractorPerformance,
    monitor_semantic_extraction,
)


try:
    import matplotlib.pyplot as plt

    PLOTTING_AVAILABLE = True
except ImportError:
    logger.warning("Matplotlib not available - plotting will be disabled")
    PLOTTING_AVAILABLE = False

# pylint: enable=wrong-import-position


class MonitoredBackgroundProcessor(IndalekoBackgroundProcessor):
    """
    Extended background processor with integrated performance monitoring.

    This class adds performance monitoring to all semantic extractors.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the monitored background processor."""
        super().__init__(**kwargs)

        # Initialize performance monitor
        self.performance_monitor = SemanticExtractorPerformance(
            record_to_db=kwargs.get("record_to_db", True),
            record_to_file=kwargs.get("record_to_file", True),
            perf_file_name=kwargs.get("perf_file_name"),
        )

        # Setup reporting
        self.stats_file = kwargs.get("stats_file")
        self.stats_interval = kwargs.get("stats_interval", 300)  # 5 minutes default
        self.stats_thread = None
        self.stopping = False

        # Total statistics
        self.start_time = time.time()
        self.mime_count = 0
        self.checksum_count = 0
        self.exif_count = 0

        # Apply monitoring to all extractors
        self._apply_monitoring()

        logger.info("Monitored background processor initialized")

    def _apply_monitoring(self) -> None:
        """Apply performance monitoring to all extractors."""
        # Patch MIME detector
        if hasattr(self, "_mime_detector") and self._mime_detector:
            original_mime_detect = self._mime_detector.detect_mime_type

            @monitor_semantic_extraction(extractor_name="MimeDetector")
            def monitored_mime_detect(file_path):
                return original_mime_detect(file_path)

            self._mime_detector.detect_mime_type = monitored_mime_detect
            logger.info("Applied monitoring to MIME detector")

        # Patch checksum calculator
        if hasattr(self, "_checksum_calculator") and self._checksum_calculator:
            original_checksum_calc = self._checksum_calculator.calculate_checksums

            @monitor_semantic_extraction(extractor_name="ChecksumCalculator")
            def monitored_checksum_calc(file_path):
                return original_checksum_calc(file_path)

            self._checksum_calculator.calculate_checksums = monitored_checksum_calc
            logger.info("Applied monitoring to checksum calculator")

        # Patch EXIF extractor
        if hasattr(self, "_exif_extractor") and self._exif_extractor:
            original_exif_extract = self._exif_extractor.extract_exif

            @monitor_semantic_extraction(extractor_name="ExifExtractor")
            def monitored_exif_extract(file_path):
                return original_exif_extract(file_path)

            self._exif_extractor.extract_exif = monitored_exif_extract
            logger.info("Applied monitoring to EXIF extractor")

    def _run_stats_thread(self) -> None:
        """Run the statistics reporting thread."""
        while not self.stopping:
            # Wait for the specified interval
            time.sleep(self.stats_interval)

            # Generate and save stats
            try:
                self._generate_and_save_stats()
            except Exception as e:
                logger.exception(f"Error generating stats: {e}")

    def _generate_and_save_stats(self):
        """Generate and save performance statistics."""
        stats = self.performance_monitor.get_stats()

        # Add runtime information
        now = time.time()
        elapsed = now - self.start_time

        # Create summary stats
        summary = {
            "timestamp": datetime.datetime.now().isoformat(),
            "runtime_seconds": elapsed,
            "runtime_formatted": self._format_elapsed_time(elapsed),
            "total_files_processed": stats["total_files"],
            "total_bytes_processed": stats["total_bytes"],
            "total_processing_time": stats["total_processing_time"],
            "files_per_second": stats.get("files_per_second", 0),
            "bytes_per_second": stats.get("bytes_per_second", 0),
            "extractor_stats": stats["extractor_stats"],
            "file_type_stats": stats.get("file_type_stats", {}),
        }

        # Log summary
        logger.info(f"Performance summary (runtime: {summary['runtime_formatted']}):")
        logger.info(f"  Total files: {summary['total_files_processed']}")
        logger.info(f"  Files/sec: {summary['files_per_second']:.2f}")
        logger.info(f"  MB/sec: {summary['bytes_per_second'] / (1024*1024):.2f}")

        # Save to file if specified
        if self.stats_file:
            try:
                with open(self.stats_file, "w") as f:
                    json.dump(summary, f, indent=2)
                logger.info(f"Statistics saved to {self.stats_file}")

                # Generate plots if matplotlib is available
                if PLOTTING_AVAILABLE:
                    self._generate_plots(stats, os.path.dirname(self.stats_file))

            except Exception as e:
                logger.exception(f"Error saving stats to {self.stats_file}: {e}")

        return summary

    def _generate_plots(self, stats, output_dir) -> None:
        """Generate performance visualization plots."""
        # Get extractor statistics
        extractor_stats = stats["extractor_stats"]
        extractors = list(extractor_stats.keys())

        if not extractors:
            return

        # Plot files processed by extractor
        plt.figure(figsize=(10, 6))
        files_processed = [extractor_stats[e]["files_processed"] for e in extractors]
        plt.bar(extractors, files_processed)
        plt.title("Files Processed by Extractor")
        plt.ylabel("Number of Files")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "files_by_extractor.png"))
        plt.close()

        # Plot average time per file by extractor
        plt.figure(figsize=(10, 6))
        avg_times = []
        for e in extractors:
            if extractor_stats[e]["files_processed"] > 0:
                avg_time = extractor_stats[e]["total_time"] / extractor_stats[e]["files_processed"]
            else:
                avg_time = 0
            avg_times.append(avg_time)

        plt.bar(extractors, avg_times)
        plt.title("Average Processing Time by Extractor")
        plt.ylabel("Seconds per File")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "time_by_extractor.png"))
        plt.close()

        # Plot file type distribution if available
        file_type_stats = stats.get("file_type_stats", {})
        if file_type_stats:
            plt.figure(figsize=(12, 6))

            # Get top 10 file types by count
            top_types = sorted(
                file_type_stats.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:10]

            mime_types = [t[0] for t in top_types]
            counts = [t[1]["count"] for t in top_types]

            plt.bar(mime_types, counts)
            plt.title("Top 10 File Types Processed")
            plt.ylabel("Number of Files")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "file_type_distribution.png"))
            plt.close()

    def _format_elapsed_time(self, seconds) -> str:
        """Format elapsed time in a human-readable format."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def start(self) -> None:
        """Start the monitored background processor."""
        # Start the stats thread if stats file is specified
        if self.stats_file:
            self.stats_thread = threading.Thread(target=self._run_stats_thread)
            self.stats_thread.daemon = True
            self.stats_thread.start()

        # Start the processor
        super().start()

    def stop(self) -> None:
        """Stop the monitored background processor."""
        self.stopping = True

        # Generate final statistics
        try:
            self._generate_and_save_stats()
        except Exception as e:
            logger.exception(f"Error generating final stats: {e}")

        # Stop the processor
        super().stop()


def main() -> None:
    """Main function for the monitored background processor."""
    parser = argparse.ArgumentParser(
        description="Indaleko Background Processor with Performance Monitoring",
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "bg_processor_config.json"),
        help="Path to background processor configuration file",
    )

    # Performance monitoring options
    parser.add_argument(
        "--no-db-record",
        action="store_false",
        dest="record_to_db",
        help="Disable recording performance data to database",
    )
    parser.add_argument(
        "--no-file-record",
        action="store_false",
        dest="record_to_file",
        help="Disable recording performance data to file",
    )
    parser.add_argument(
        "--perf-file",
        type=str,
        default=os.path.join(log_dir, "semantic_extractor_perf.jsonl"),
        help="Path to performance data file",
    )
    parser.add_argument(
        "--stats-file",
        type=str,
        default=os.path.join(log_dir, "bg_processor_stats.json"),
        help="Path to statistics summary file",
    )
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=300,
        help="Statistics reporting interval in seconds (default: 300)",
    )

    # Runtime options
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all statistics and start fresh",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate performance report without running the processor",
    )

    args = parser.parse_args()

    # Report-only mode
    if args.report_only:
        generate_performance_report(args.stats_file, args.perf_file)
        return

    # Create and start the processor
    processor = MonitoredBackgroundProcessor(
        config_path=args.config,
        record_to_db=args.record_to_db,
        record_to_file=args.record_to_file,
        perf_file_name=args.perf_file,
        stats_file=args.stats_file,
        stats_interval=args.stats_interval,
    )

    # Reset statistics if requested
    if args.reset:
        processor.performance_monitor.reset_stats()
        logger.info("Statistics reset")

    try:
        logger.info("Starting monitored background processor")
        processor.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping...")
    finally:
        processor.stop()
        logger.info("Monitored background processor stopped")


def generate_performance_report(stats_file, perf_file) -> None:
    """Generate a comprehensive performance report from existing data."""
    logger.info("Generating performance report...")

    # Check if files exist
    if not os.path.exists(stats_file):
        logger.error(f"Stats file not found: {stats_file}")
        return

    if not os.path.exists(perf_file):
        logger.warning(f"Performance data file not found: {perf_file}")

    # Load stats
    try:
        with open(stats_file) as f:
            stats = json.load(f)

        # Create report
        report_dir = os.path.join(os.path.dirname(stats_file), "reports")
        os.makedirs(report_dir, exist_ok=True)

        report_file = os.path.join(
            report_dir,
            f"performance_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        )

        # Create HTML report
        with open(report_file, "w") as f:
            f.write(
                f"""<!DOCTYPE html>
<html>
<head>
    <title>Indaleko Semantic Extractor Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .section {{ margin-bottom: 30px; }}
        .image-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .image-container img {{ max-width: 45%; margin: 0 10px; }}
    </style>
</head>
<body>
    <h1>Indaleko Semantic Extractor Performance Report</h1>
    <p><strong>Generated:</strong> {datetime.datetime.now().isoformat()}</p>
    <p><strong>Runtime:</strong> {stats.get('runtime_formatted', 'N/A')}</p>

    <div class="section">
        <h2>Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Files Processed</td>
                <td>{stats.get('total_files_processed', 0):,}</td>
            </tr>
            <tr>
                <td>Total Bytes Processed</td>
                <td>{stats.get('total_bytes_processed', 0):,} ({stats.get('total_bytes_processed', 0) / (1024*1024*1024):.2f} GB)</td>
            </tr>
            <tr>
                <td>Total Processing Time</td>
                <td>{stats.get('total_processing_time', 0):.2f} seconds</td>
            </tr>
            <tr>
                <td>Files Per Second</td>
                <td>{stats.get('files_per_second', 0):.2f}</td>
            </tr>
            <tr>
                <td>MB Per Second</td>
                <td>{stats.get('bytes_per_second', 0) / (1024*1024):.2f}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>Extractor Performance</h2>
        <table>
            <tr>
                <th>Extractor</th>
                <th>Files Processed</th>
                <th>Bytes Processed</th>
                <th>Total Time (s)</th>
                <th>Avg Time/File (s)</th>
                <th>MB/Second</th>
                <th>Success Rate</th>
            </tr>
""",
            )

            # Add extractor stats
            for extractor, extractor_stats in stats.get("extractor_stats", {}).items():
                files = extractor_stats.get("files_processed", 0)
                bytes_processed = extractor_stats.get("bytes_processed", 0)
                total_time = extractor_stats.get("total_time", 0)

                avg_time = total_time / files if files > 0 else 0
                mb_per_second = (bytes_processed / (1024 * 1024)) / total_time if total_time > 0 else 0

                success = extractor_stats.get("success_count", 0)
                errors = extractor_stats.get("error_count", 0)
                success_rate = (success / (success + errors)) * 100 if (success + errors) > 0 else 0

                f.write(
                    f"""
            <tr>
                <td>{extractor}</td>
                <td>{files:,}</td>
                <td>{bytes_processed:,} ({bytes_processed / (1024*1024):.2f} MB)</td>
                <td>{total_time:.2f}</td>
                <td>{avg_time:.4f}</td>
                <td>{mb_per_second:.2f}</td>
                <td>{success_rate:.2f}% ({success:,}/{success+errors:,})</td>
            </tr>""",
                )

            f.write(
                """
        </table>
    </div>

    <div class="section">
        <h2>MIME Type Distribution</h2>
        <table>
            <tr>
                <th>MIME Type</th>
                <th>Count</th>
                <th>Total Size</th>
                <th>Avg Size</th>
                <th>Avg Processing Time</th>
            </tr>
""",
            )

            # Add MIME type stats
            for mime_type, mime_stats in sorted(
                stats.get("file_type_stats", {}).items(),
                key=lambda x: x[1].get("count", 0),
                reverse=True,
            ):
                count = mime_stats.get("count", 0)
                total_bytes = mime_stats.get("total_bytes", 0)
                total_time = mime_stats.get("total_time", 0)

                avg_size = total_bytes / count if count > 0 else 0
                avg_time = total_time / count if count > 0 else 0

                f.write(
                    f"""
            <tr>
                <td>{mime_type}</td>
                <td>{count:,}</td>
                <td>{total_bytes:,} ({total_bytes / (1024*1024):.2f} MB)</td>
                <td>{avg_size / 1024:.2f} KB</td>
                <td>{avg_time:.4f} seconds</td>
            </tr>""",
                )

            f.write(
                """
        </table>
    </div>

    <div class="section">
        <h2>Visualizations</h2>
        <div class="image-container">
            <img src="../files_by_extractor.png" alt="Files by Extractor">
            <img src="../time_by_extractor.png" alt="Processing Time by Extractor">
        </div>
        <div class="image-container">
            <img src="../file_type_distribution.png" alt="File Type Distribution">
        </div>
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            <li>The MIME type detector is the fastest extractor and should be prioritized for initial processing.</li>
            <li>Checksums are more CPU-intensive and should be scheduled during system idle time.</li>
            <li>EXIF extraction should target only image files to maximize efficiency.</li>
            <li>Consider increasing the number of extraction threads to improve throughput.</li>
            <li>Large files (>100MB) should be processed with lower priority to avoid blocking other extractions.</li>
        </ul>
    </div>
</body>
</html>
""",
            )

        logger.info(f"Report generated: {report_file}")

    except Exception as e:
        logger.exception(f"Error generating report: {e}")


if __name__ == "__main__":
    main()
