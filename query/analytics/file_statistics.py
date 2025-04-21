"""
Analytics module for Indaleko file statistics.

This module provides analytical queries for file statistics in the Indaleko system,
leveraging ArangoDB for efficient querying against the Objects collection.

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
import json
import logging
import argparse
import time
from typing import Dict, Any, List, Tuple, Optional
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Set up environment variables
current_path = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_path))
os.environ["INDALEKO_ROOT"] = root_dir
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import Indaleko components
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileStatistics:
    """Class for retrieving and analyzing file statistics from Indaleko."""
    
    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """
        Initialize the FileStatistics class.
        
        Args:
            db_config: Optional database configuration. If not provided, a new one will be created.
        """
        try:
            self.db_config = db_config or IndalekoDBConfig()
            self.db = self.db_config.db
            logger.info("FileStatistics initialized with database connection")
            
            # Check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            self.has_objects_collection = 'Objects' in collection_names
            
            if not self.has_objects_collection:
                logger.warning("Objects collection not found in database. Analytics will return empty results.")
                logger.info("Available collections: " + ", ".join(collection_names))
            else:
                logger.info("Objects collection found in database.")
        except Exception as e:
            logger.error(f"Error initializing FileStatistics: {e}")
            self.db = None
            self.has_objects_collection = False
    
    def count_total_objects(self) -> int:
        """
        Count the total number of objects (files and directories) in the system.
        
        Returns:
            int: The total count of objects
        """
        try:
            # First check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            
            if 'Objects' not in collection_names:
                logger.warning("Objects collection not found in database")
                return 0
                
            query = """
            RETURN COUNT(FOR obj IN Objects RETURN 1)
            """
            
            logger.info("Counting total objects in the system")
            cursor = self.db.aql.execute(query)
            result = list(cursor)[0]
            
            # Ensure the result is an integer
            if result is None:
                result = 0
                
            logger.info(f"Total objects found: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error counting objects: {e}")
            return 0
    
    def count_files(self) -> int:
        """
        Count only files (not directories) in the system.
        This query uses SemanticAttributes to identify file objects.
        
        Returns:
            int: The total count of files
        """
        try:
            # First check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            
            if 'Objects' not in collection_names:
                logger.warning("Objects collection not found in database")
                return 0
                
            # Query to count objects that have a "Type" semantic attribute with value "file"
            query = """
            RETURN COUNT(
                FOR obj IN Objects
                FILTER obj.Record != null 
                AND obj.Record.Attributes != null
                AND obj.Record.Attributes.Type != null
                AND obj.Record.Attributes.Type == "file"
                RETURN 1
            )
            """
            
            logger.info("Counting files in the system")
            cursor = self.db.aql.execute(query)
            result = list(cursor)[0]
            
            # Ensure the result is an integer
            if result is None:
                result = 0
                
            logger.info(f"Total files found: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error counting files: {e}")
            return 0
    
    def count_directories(self) -> int:
        """
        Count only directories in the system.
        
        Returns:
            int: The total count of directories
        """
        try:
            # First check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            
            if 'Objects' not in collection_names:
                logger.warning("Objects collection not found in database")
                return 0
                
            # Query to count objects that have a "Type" semantic attribute with value "directory"
            query = """
            RETURN COUNT(
                FOR obj IN Objects
                FILTER obj.Record != null 
                AND obj.Record.Attributes != null
                AND obj.Record.Attributes.Type != null
                AND obj.Record.Attributes.Type == "directory"
                RETURN 1
            )
            """
            
            logger.info("Counting directories in the system")
            cursor = self.db.aql.execute(query)
            result = list(cursor)[0]
            
            # Ensure the result is an integer
            if result is None:
                result = 0
                
            logger.info(f"Total directories found: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error counting directories: {e}")
            return 0
    
    def get_file_type_distribution(self) -> Dict[str, int]:
        """
        Get the distribution of file types based on extensions.
        
        Returns:
            Dict[str, int]: A dictionary mapping file extensions to counts
        """
        try:
            # First check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            
            if 'Objects' not in collection_names:
                logger.warning("Objects collection not found in database")
                return {}
                
            # Query to group files by extension and count
            query = """
            LET extensions = (
                FOR obj IN Objects
                FILTER obj.Record != null 
                AND obj.Record.Attributes != null
                AND obj.Record.Attributes.Type != null
                AND obj.Record.Attributes.Type == "file"
                AND obj.Label != null
                
                LET extension = REGEX_EXTRACT(obj.Label, '\\.([^.]+)$', 1)
                FILTER extension != null AND LENGTH(extension) > 0
                
                RETURN LOWER(extension)
            )
            
            FOR ext IN extensions
            COLLECT extension = ext INTO counts
            SORT COUNT(counts) DESC
            LIMIT 20
            RETURN {
                "extension": extension,
                "count": COUNT(counts)
            }
            """
            
            logger.info("Getting file type distribution")
            cursor = self.db.aql.execute(query)
            results = list(cursor)
            
            # Convert to dictionary
            distribution = {item["extension"]: item["count"] for item in results}
            
            logger.info(f"Found {len(distribution)} different file types")
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting file type distribution: {e}")
            return {}
    
    def get_file_size_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about file sizes in the system.
        
        Returns:
            Dict[str, Any]: Statistics about file sizes
        """
        try:
            # First check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            
            if 'Objects' not in collection_names:
                logger.warning("Objects collection not found in database")
                return {
                    "count": 0,
                    "total_size": 0,
                    "average_size": 0,
                    "median_size": 0,
                    "min_size": 0,
                    "max_size": 0
                }
                
            # Query to calculate file size statistics
            query = """
            LET files = (
                FOR obj IN Objects
                FILTER obj.Record != null 
                AND obj.Record.Attributes != null
                AND obj.Record.Attributes.Type != null
                AND obj.Record.Attributes.Type == "file"
                AND obj.Size != null
                RETURN obj.Size
            )
            
            LET count = LENGTH(files)
            
            RETURN {
                "count": count,
                "total_size": count > 0 ? SUM(files) : 0,
                "average_size": count > 0 ? AVERAGE(files) : 0,
                "median_size": count > 0 ? (
                    count % 2 == 1 ? 
                        NTH(SORTED(files), FLOOR(count / 2)) : 
                        (NTH(SORTED(files), (count / 2) - 1) + NTH(SORTED(files), count / 2)) / 2
                ) : 0,
                "min_size": count > 0 ? MIN(files) : 0,
                "max_size": count > 0 ? MAX(files) : 0
            }
            """
            
            logger.info("Getting file size statistics")
            cursor = self.db.aql.execute(query)
            result = list(cursor)[0]
            
            # Ensure all values are valid numbers
            default_stats = {
                "count": 0,
                "total_size": 0,
                "average_size": 0,
                "median_size": 0,
                "min_size": 0,
                "max_size": 0
            }
            
            # Replace any None values with 0
            for key in default_stats:
                if key not in result or result[key] is None:
                    result[key] = default_stats[key]
            
            logger.info("File size statistics calculated")
            return result
            
        except Exception as e:
            logger.error(f"Error getting file size statistics: {e}")
            return {
                "count": 0,
                "total_size": 0,
                "average_size": 0,
                "median_size": 0,
                "min_size": 0,
                "max_size": 0
            }
    
    def get_file_age_distribution(self) -> List[Dict[str, Any]]:
        """
        Get the distribution of files by age.
        
        Returns:
            List[Dict[str, Any]]: The distribution of files by age
        """
        try:
            # First check if the Objects collection exists
            collections = self.db.collections()
            collection_names = [c['name'] for c in collections]
            
            if 'Objects' not in collection_names:
                logger.warning("Objects collection not found in database")
                return []
                
            # Query to group files by age range
            query = """
            LET now = DATE_NOW() / 1000
            LET files = (
                FOR obj IN Objects
                FILTER obj.Record != null 
                AND obj.Record.Attributes != null
                AND obj.Record.Attributes.Type != null
                AND obj.Record.Attributes.Type == "file"
                AND obj.Record.Attributes.st_mtime != null
                
                LET age_days = FLOOR((now - TO_NUMBER(obj.Record.Attributes.st_mtime)) / (60 * 60 * 24))
                
                RETURN {
                    "age_days": age_days,
                    "size": obj.Size || 0
                }
            )
            
            LET age_ranges = [
                {min: 0, max: 7, label: "Last week"},
                {min: 8, max: 30, label: "Last month"},
                {min: 31, max: 90, label: "Last quarter"},
                {min: 91, max: 365, label: "Last year"},
                {min: 366, max: 730, label: "1-2 years"},
                {min: 731, max: 1095, label: "2-3 years"},
                {min: 1096, max: 1825, label: "3-5 years"},
                {min: 1826, max: 3650, label: "5-10 years"},
                {min: 3651, max: 99999, label: "10+ years"}
            ]
            
            FOR range IN age_ranges
            LET files_in_range = (
                FOR file IN files
                FILTER file.age_days >= range.min AND file.age_days <= range.max
                RETURN file
            )
            
            LET count = LENGTH(files_in_range)
            LET total_size = SUM(files_in_range[*].size)
            
            FILTER count > 0
            
            RETURN {
                "age_range": range.label,
                "count": count,
                "total_size": total_size,
                "avg_size": count > 0 ? total_size / count : 0
            }
            """
            
            logger.info("Getting file age distribution")
            cursor = self.db.aql.execute(query)
            results = list(cursor)
            
            logger.info(f"File age distribution calculated with {len(results)} ranges")
            return results
            
        except Exception as e:
            logger.error(f"Error getting file age distribution: {e}")
            return []
    
    def generate_report(self, output_dir: str = ".", visualize: bool = True) -> Dict[str, Any]:
        """
        Generate a comprehensive report of file statistics.
        
        Args:
            output_dir: Directory to save report and visualizations
            visualize: Whether to generate visualizations
            
        Returns:
            Dict[str, Any]: Complete statistics report
        """
        start_time = time.time()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Collect all statistics
        logger.info("Generating comprehensive file statistics report")
        
        total_objects = self.count_total_objects()
        file_count = self.count_files()
        directory_count = self.count_directories()
        file_types = self.get_file_type_distribution()
        size_stats = self.get_file_size_statistics()
        age_distribution = self.get_file_age_distribution()
        
        # Compile report
        report = {
            "total_objects": total_objects,
            "file_count": file_count,
            "directory_count": directory_count,
            "file_types": file_types,
            "size_statistics": size_stats,
            "age_distribution": age_distribution,
            "generated_at": time.time()
        }
        
        # Save report to file
        report_file = os.path.join(output_dir, "file_statistics_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate visualizations if requested
        if visualize:
            self._generate_visualizations(report, output_dir)
        
        end_time = time.time()
        logger.info(f"Report generated in {end_time - start_time:.2f} seconds")
        
        return report
    
    def _generate_visualizations(self, report: Dict[str, Any], output_dir: str) -> None:
        """
        Generate visualizations for the statistics report.
        
        Args:
            report: The statistics report
            output_dir: Directory to save visualizations
        """
        logger.info("Generating visualizations")
        
        # 1. Files vs Directories pie chart
        plt.figure(figsize=(10, 6))
        plt.pie(
            [report["file_count"], report["directory_count"]],
            labels=["Files", "Directories"],
            autopct='%1.1f%%',
            startangle=90
        )
        plt.axis('equal')
        plt.title('Files vs Directories')
        plt.savefig(os.path.join(output_dir, 'files_vs_directories.png'))
        plt.close()
        
        # 2. File types bar chart
        if report["file_types"]:
            # Sort by count and get top 10
            file_types = dict(sorted(report["file_types"].items(), key=lambda x: x[1], reverse=True)[:10])
            
            plt.figure(figsize=(12, 6))
            plt.bar(file_types.keys(), file_types.values())
            plt.title('Top 10 File Types by Count')
            plt.xlabel('File Extension')
            plt.ylabel('Count')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'file_types.png'))
            plt.close()
        
        # 3. File age distribution
        if report["age_distribution"]:
            # Extract data
            age_labels = [item["age_range"] for item in report["age_distribution"]]
            age_counts = [item["count"] for item in report["age_distribution"]]
            
            plt.figure(figsize=(12, 6))
            plt.bar(age_labels, age_counts)
            plt.title('File Age Distribution')
            plt.xlabel('Age Range')
            plt.ylabel('Count')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'file_age_distribution.png'))
            plt.close()
            
            # 4. File size by age
            age_sizes = [item["avg_size"] / (1024 * 1024) for item in report["age_distribution"]]  # Convert to MB
            
            plt.figure(figsize=(12, 6))
            plt.bar(age_labels, age_sizes)
            plt.title('Average File Size by Age')
            plt.xlabel('Age Range')
            plt.ylabel('Average Size (MB)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'file_size_by_age.png'))
            plt.close()
        
        logger.info("Visualizations generated successfully")

def format_size(size_bytes: int) -> str:
    """
    Format file size from bytes to human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Human-readable size
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def display_report(report: Dict[str, Any], display_buffer: List[str] = None) -> None:
    """
    Display the statistics report in a human-readable format.
    
    Args:
        report: The statistics report
        display_buffer: Optional buffer to collect output instead of printing directly
                        If not provided, output is printed to stdout
    """
    # Helper function to handle output
    def output(line: str):
        if display_buffer is not None:
            display_buffer.append(line)
        else:
            print(line)
    
    output("\n=== Indaleko File Statistics Report ===\n")
    
    # Object counts
    output(f"Total Objects: {report['total_objects']:,}")
    output(f"Files: {report['file_count']:,} ({report['file_count']/max(1, report['total_objects'])*100:.1f}%)")
    output(f"Directories: {report['directory_count']:,} ({report['directory_count']/max(1, report['total_objects'])*100:.1f}%)")
    
    # Size statistics
    size_stats = report["size_statistics"]
    output("\n=== File Size Statistics ===")
    output(f"Total Size: {format_size(size_stats['total_size'])}")
    output(f"Average Size: {format_size(size_stats['average_size'])}")
    output(f"Median Size: {format_size(size_stats['median_size'])}")
    output(f"Smallest File: {format_size(size_stats['min_size'])}")
    output(f"Largest File: {format_size(size_stats['max_size'])}")
    
    # File types
    output("\n=== Top 5 File Types ===")
    file_types = dict(sorted(report["file_types"].items(), key=lambda x: x[1], reverse=True)[:5])
    for ext, count in file_types.items():
        output(f".{ext}: {count:,} files ({count/max(1, report['file_count'])*100:.1f}%)")
    
    # Age distribution
    output("\n=== File Age Distribution ===")
    for age_range in report["age_distribution"]:
        output(f"{age_range['age_range']}: {age_range['count']:,} files, "
              f"{format_size(age_range['total_size'])}")

def main():
    """Main entry point for the file statistics tool."""
    parser = argparse.ArgumentParser(description="Indaleko File Statistics Tool")
    parser.add_argument("--report", "-r", action="store_true", help="Generate comprehensive report")
    parser.add_argument("--visualize", "-v", action="store_true", help="Generate visualizations")
    parser.add_argument("--output", "-o", type=str, default=".", help="Output directory for report and visualizations")
    parser.add_argument("--db-config", type=str, help="Path to database configuration file")
    
    args = parser.parse_args()
    
    # Initialize database connection
    if args.db_config:
        db_config = IndalekoDBConfig(config_file=args.db_config)
    else:
        db_config = IndalekoDBConfig()
    
    # Create statistics object
    stats = FileStatistics(db_config)
    
    if args.report:
        # Generate comprehensive report
        report = stats.generate_report(args.output, args.visualize)
        display_report(report)
    else:
        # Display basic statistics
        total_objects = stats.count_total_objects()
        file_count = stats.count_files()
        directory_count = stats.count_directories()
        
        print("\n=== Indaleko File Statistics ===\n")
        print(f"Total Objects: {total_objects:,}")
        print(f"Files: {file_count:,} ({file_count/max(1, total_objects)*100:.1f}%)")
        print(f"Directories: {directory_count:,} ({directory_count/max(1, total_objects)*100:.1f}%)")

if __name__ == "__main__":
    main()