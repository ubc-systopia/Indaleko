#!/usr/bin/env python3
"""
Ablation study implementation for Indaleko.

This script implements a comprehensive ablation study to measure the impact
of different activity data types on query precision and recall. The study
divides activity data collections into control and study groups, then
measures how the absence of specific collections affects search results.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import json
import logging
import datetime
import time
import random
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"ablation_study_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query

# Define seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

class AblationStudy:
    """Main class for running the ablation study."""

    def __init__(self):
        """Initialize the ablation study."""
        # Set up directory for results
        self.results_dir = Path("./ablation_results")
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize the SQLite results database
        self.init_results_db()

        # Test queries organized by category focus
        self.test_queries = self._define_test_queries()

        # Control and study groups will be defined when running the study
        self.control_group = []
        self.study_group = []

        # Reset the Arango database before starting
        if not self.reset_database():
            logging.error("Failed to reset database. Aborting study.")
            raise RuntimeError("Database reset failed")

        # Try to connect to ArangoDB
        try:
            IndalekoDBCollections() # trigger creation after reset.
            self.db_config = IndalekoDBConfig()
            logging.info("Created IndalekoDBConfig")
            self.db = self.db_config.get_arangodb()
            logging.info("Connected to ArangoDB")
            self.collections_metadata = IndalekoDBCollectionsMetadata(self.db_config)
            logging.info("Created collections metadata")

            # Define all activity data collections
            self.activity_collections = self._get_activity_collections()
            logging.info(f"Found {len(self.activity_collections)} activity collections")
        except Exception as e:
            logging.error(f"Failed to connect to ArangoDB: {e}")
            import traceback
            traceback.print_exc()
            self.db_config = None
            self.db = None
            self.collections_metadata = None
            self.activity_collections = []
            logging.warning("The ablation study will run with empty collections")

    def _get_activity_collections(self) -> List[str]:
        """
        Get all activity data collections from the database.

        This function uses the DBCollections class and discovery to find
        all activity data-related collections.

        Returns:
            List of activity collection names
        """
        # Start with known collections from IndalekoDBCollections
        collections = [
            # Various activity data collections
            IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            IndalekoDBCollections.Indaleko_GeoActivityData_Collection,

            # Additional activity collections we might find
            "CollaborationActivity",
            "LocationActivity",
            "NetworkActivity",
            "StorageActivity",
            "TaskActivity"
        ]

        # Filter out collections that don't exist in the database
        existing_collections = []
        for collection in collections:
            try:
                if self.db.has_collection(collection):
                    existing_collections.append(collection)
                    logging.info(f"Found activity collection: {collection}")
            except Exception as e:
                logging.warning(f"Error checking collection {collection}: {e}")

        # Add any dynamically registered collections that look like activity data
        all_collections = self.db.collections()
        for collection in all_collections:
            collection_name = collection["name"]
            if (collection_name not in existing_collections and
                ("Activity" in collection_name or
                 collection_name.endswith("Context"))):
                if not collection_name.startswith("_"):  # Skip system collections
                    existing_collections.append(collection_name)
                    logging.info(f"Found additional activity collection: {collection_name}")

        if not existing_collections:
            logging.warning("No activity collections found in database. Study results will be limited.")

        return existing_collections

    def _define_test_queries(self) -> Dict[str, List[str]]:
        """
        Define test queries organized by their focus area.

        Returns:
            Dictionary mapping categories to lists of queries
        """
        return {
            "ambient": [
                "Find all music I listened to last week",
                "Show me songs by Taylor Swift I played recently",
                "What was the temperature in my house yesterday?",
                "Find videos I watched on YouTube about Python programming",
                "What music was I listening to while working on the presentation?",
            ],
            "collaboration": [
                "Find all files shared with me by email last month",
                "Show me documents I collaborated on with Sarah",
                "Find meeting notes from yesterday's team call",
                "What files did I share during the budget meeting?",
                "Show calendar events from last week",
            ],
            "location": [
                "Find documents I worked on while at the coffee shop",
                "What files did I access while traveling to Seattle?",
                "Show me photos taken at home last weekend",
                "Find notes I wrote during my visit to the library",
                "What documents did I edit while at the office?",
            ],
            "storage": [
                "Find all PDF files I modified last week",
                "Show me recently deleted spreadsheets",
                "Find Word documents created yesterday",
                "What image files did I open last month?",
                "Show me files I uploaded to Google Drive recently",
            ],
            "task": [
                "Find documents I edited while using Microsoft Word",
                "Show me files I viewed during my video call with the marketing team",
                "What documents did I work on while running the database application?",
                "Find files I edited while multitasking between browser and Excel",
                "Show me notes I took during the Zoom meeting",
            ],
        }

    def init_results_db(self):
        """Initialize SQLite database for storing ablation results."""
        self.results_db_path = Path("ablation_results.db")

        try:
            conn = sqlite3.connect(str(self.results_db_path))
            cursor = conn.cursor()

            # Drop existing tables first to ensure schema is correct
            cursor.execute("DROP TABLE IF EXISTS ablation_results")
            cursor.execute("DROP TABLE IF EXISTS test_queries")
            cursor.execute("DROP TABLE IF EXISTS ablation_runs")

            # Create tables with the correct schema
            cursor.execute("""
            CREATE TABLE ablation_runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT,
                description TEXT,
                random_seed INTEGER,
                config TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE test_queries (
                query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                query_text TEXT,
                category TEXT,
                group_type TEXT,
                FOREIGN KEY (run_id) REFERENCES ablation_runs (run_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE ablation_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                query_id INTEGER,
                ablated_collections TEXT,
                baseline_count INTEGER,
                ablated_count INTEGER,
                true_positives INTEGER,
                false_positives INTEGER,
                false_negatives INTEGER,
                precision REAL,
                recall REAL,
                f1 REAL,
                impact REAL,
                execution_time REAL,
                aql TEXT,
                FOREIGN KEY (run_id) REFERENCES ablation_runs (run_id),
                FOREIGN KEY (query_id) REFERENCES test_queries (query_id)
            )
            """)

            conn.commit()
            conn.close()
            logging.info(f"Initialized results database at {self.results_db_path}")

        except Exception as e:
            logging.error(f"Error initializing results database: {e}")
            raise

    def reset_database(self):
        """Reset the ArangoDB database."""
        try:
            logging.info("Resetting ArangoDB database...")
            # Call the db_config reset command
            result = subprocess.run(
                [sys.executable, "-m", "db.db_config", "reset"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logging.info("Database reset successful")
                return True
            else:
                logging.error(f"Database reset failed: {result.stderr}")
                return False


        except Exception as e:
            logging.error(f"Error resetting database: {e}")
            return False

    def divide_collections(self):
        """
        Divide activity collections into control and study groups.

        This function randomly assigns activity collections to either
        the control group or the study group, ensuring a balanced distribution.
        """
        if not self.activity_collections:
            logging.warning("No activity collections to divide")
            return

        # Shuffle collections to randomize assignments
        collections = self.activity_collections.copy()
        random.shuffle(collections)

        # Split collections evenly between control and study groups
        midpoint = len(collections) // 2
        self.control_group = collections[:midpoint]
        self.study_group = collections[midpoint:]

        # If odd number, add the extra to study group
        if len(collections) % 2 != 0 and len(self.control_group) == len(self.study_group):
            self.study_group.append(collections[-1])

        logging.info(f"Control group collections: {self.control_group}")
        logging.info(f"Study group collections: {self.study_group}")

    def select_queries(self, num_queries_per_group: int = 10) -> Dict[str, List[str]]:
        """
        Select queries for the study.

        Args:
            num_queries_per_group: Number of queries to select for each group

        Returns:
            Dictionary with control and study queries
        """
        # Flatten all queries
        all_queries = []
        for category, queries in self.test_queries.items():
            all_queries.extend([(query, category) for query in queries])

        # Shuffle queries
        random.shuffle(all_queries)

        # Select queries
        total_queries = min(len(all_queries), num_queries_per_group * 2)
        selected_queries = all_queries[:total_queries]

        # Divide queries between control and study groups
        midpoint = len(selected_queries) // 2
        control_queries = selected_queries[:midpoint]
        study_queries = selected_queries[midpoint:]

        return {
            "control": control_queries,
            "study": study_queries
        }

    def extract_ids(self, results: List[Dict[str, Any]]) -> Set[str]:
        """Extract unique IDs from query results."""
        id_fields = ["_id", "_key", "ID", "ObjectIdentifier", "Handle", "URI"]
        ids = set()

        for result in results:
            if not isinstance(result, dict):
                continue

            for field in id_fields:
                if field in result:
                    ids.add(str(result[field]))
                    break

        return ids

    def calculate_metrics(self, baseline_ids: Set[str], ablated_ids: Set[str]) -> Dict[str, float]:
        """Calculate precision, recall, and F1 metrics."""
        # Calculate true positives, false positives, false negatives
        true_positives = len(ablated_ids.intersection(baseline_ids))
        false_positives = len(ablated_ids - baseline_ids)
        false_negatives = len(baseline_ids - ablated_ids)

        # Calculate precision, recall, F1 score
        if true_positives + false_positives > 0:
            precision = true_positives / (true_positives + false_positives)
        else:
            precision = 1.0

        if true_positives + false_negatives > 0:
            recall = true_positives / (true_positives + false_negatives)
        else:
            recall = 1.0

        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0

        # Impact is defined as the change in F1 score
        impact = 1.0 - f1

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "impact": impact,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }

    def run_ablation_test(self, query: str, collection_group: List[str]) -> Dict[str, Any]:
        """
        Run an ablation test for a specific query and collection group.

        Args:
            query: Natural language query to test
            collection_group: List of collections to ablate

        Returns:
            Dictionary with test results
        """
        logging.info(f"Testing query: '{query}' with ablated collections: {collection_group}")

        # If database is not available, return empty results
        if self.db is None or self.collections_metadata is None:
            logging.warning("Database not available, returning empty results")
            metrics = {
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "impact": 0.0,
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0
            }
            return {
                "query": query,
                "ablated_collections": collection_group,
                "baseline_count": 0,
                "ablated_count": 0,
                "metrics": metrics,
                "baseline_time": 0.0,
                "ablated_time": 0.0,
                "baseline_aql": "",
                "ablated_aql": "",
                "timestamp": datetime.datetime.now().isoformat()
            }

        # Run baseline query (no ablation)
        baseline_results = []
        baseline_aql = ""
        baseline_time = 0.0

        try:
            start_time = time.time()
            baseline_results = fixed_execute_query(query, capture_aql=True)
            baseline_time = time.time() - start_time
            baseline_count = len(baseline_results)
            logging.info(f"Baseline returned {baseline_count} results in {baseline_time:.3f}s")

            # Extract baseline AQL if available
            if baseline_results and isinstance(baseline_results[0], dict) and "_debug" in baseline_results[0]:
                baseline_aql = baseline_results[0]["_debug"].get("aql", "")
        except Exception as e:
            logging.error(f"Error running baseline query: {e}")
            baseline_results = []

        # Extract IDs for baseline results
        baseline_ids = self.extract_ids(baseline_results)
        logging.info(f"Extracted {len(baseline_ids)} unique IDs from baseline results")

        # Ablate the collections
        try:
            for collection in collection_group:
                if self.collections_metadata:
                    self.collections_metadata.ablate_collection(collection)
                    logging.info(f"Ablated collection: {collection}")
        except Exception as e:
            logging.error(f"Error ablating collections: {e}")

        # Run the ablated query
        ablated_results = []
        ablated_aql = ""
        ablated_time = 0.0

        try:
            start_time = time.time()
            ablated_results = fixed_execute_query(query, capture_aql=True)
            ablated_time = time.time() - start_time
            ablated_count = len(ablated_results)
            logging.info(f"Ablated query returned {ablated_count} results in {ablated_time:.3f}s")

            # Extract ablated AQL if available
            if ablated_results and isinstance(ablated_results[0], dict) and "_debug" in ablated_results[0]:
                ablated_aql = ablated_results[0]["_debug"].get("aql", "")
        except Exception as e:
            logging.error(f"Error running ablated query: {e}")
            ablated_results = []

        # Extract IDs for ablated results
        ablated_ids = self.extract_ids(ablated_results)
        logging.info(f"Extracted {len(ablated_ids)} unique IDs from ablated results")

        # Calculate metrics
        metrics = self.calculate_metrics(baseline_ids, ablated_ids)

        # Restore the collections
        try:
            for collection in collection_group:
                if self.collections_metadata:
                    self.collections_metadata.restore_collection(collection)
                    logging.info(f"Restored collection: {collection}")
        except Exception as e:
            logging.error(f"Error restoring collections: {e}")

        # Prepare results
        result = {
            "query": query,
            "ablated_collections": collection_group,
            "baseline_count": len(baseline_results),
            "ablated_count": len(ablated_results),
            "metrics": metrics,
            "baseline_time": baseline_time,
            "ablated_time": ablated_time,
            "baseline_aql": baseline_aql,
            "ablated_aql": ablated_aql,
            "timestamp": datetime.datetime.now().isoformat()
        }

        return result

    def save_result_to_db(self, run_id: str, query_id: int, result: Dict[str, Any]):
        """
        Save an individual test result to the SQLite database.

        Args:
            run_id: Identifier for the current ablation run
            query_id: Identifier for the test query
            result: The ablation test result
        """
        try:
            conn = sqlite3.connect(str(self.results_db_path))
            cursor = conn.cursor()

            metrics = result["metrics"]

            cursor.execute("""
            INSERT INTO ablation_results (
                run_id, query_id, ablated_collections, baseline_count, ablated_count,
                true_positives, false_positives, false_negatives,
                precision, recall, f1, impact, execution_time, aql
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                query_id,
                json.dumps(result["ablated_collections"]),
                result["baseline_count"],
                result["ablated_count"],
                metrics["true_positives"],
                metrics["false_positives"],
                metrics["false_negatives"],
                metrics["precision"],
                metrics["recall"],
                metrics["f1"],
                metrics["impact"],
                result["ablated_time"],
                result["ablated_aql"]
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logging.error(f"Error saving result to database: {e}")

    def run_study(self, num_queries_per_group: int = 10):
        """
        Run the complete ablation study.

        Args:
            num_queries_per_group: Number of queries to run for each group
        """
        try:

            # Generate a unique run ID
            run_id = f"ablation_{self.timestamp}"

            # Initialize the run in the database
            conn = sqlite3.connect(str(self.results_db_path))
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO ablation_runs (run_id, timestamp, description, random_seed, config)
            VALUES (?, ?, ?, ?, ?)
            """, (
                run_id,
                datetime.datetime.now().isoformat(),
                "Full ablation study with control and study groups",
                RANDOM_SEED,
                json.dumps({
                    "num_queries_per_group": num_queries_per_group,
                })
            ))

            conn.commit()

            # Divide collections into control and study groups
            self.divide_collections()

            # Select test queries
            selected_queries = self.select_queries(num_queries_per_group)

            # Save queries to database
            query_ids = {}

            for group_type, queries in selected_queries.items():
                for query, category in queries:
                    cursor.execute("""
                    INSERT INTO test_queries (run_id, query_text, category, group_type)
                    VALUES (?, ?, ?, ?)
                    """, (run_id, query, category, group_type))

                    query_id = cursor.lastrowid
                    query_ids[(query, category)] = query_id

            conn.commit()
            conn.close()

            # Phase 1: Test study queries with ablated study collections
            logging.info("=== Phase 1: Ablating study collections for study queries ===")

            phase1_results = {}

            for query, category in selected_queries["study"]:
                query_id = query_ids.get((query, category))
                result = self.run_ablation_test(query, self.study_group)
                phase1_results[query] = result
                self.save_result_to_db(run_id, query_id, result)

            # Phase 2: Test control queries with ablated study collections
            logging.info("=== Phase 2: Ablating study collections for control queries ===")

            phase2_results = {}

            for query, category in selected_queries["control"]:
                query_id = query_ids.get((query, category))
                result = self.run_ablation_test(query, self.study_group)
                phase2_results[query] = result
                self.save_result_to_db(run_id, query_id, result)

            # Phase 3: Reverse roles - ablate control collections and test study queries
            logging.info("=== Phase 3: Ablating control collections for study queries ===")

            phase3_results = {}

            for query, category in selected_queries["study"]:
                query_id = query_ids.get((query, category))
                result = self.run_ablation_test(query, self.control_group)
                phase3_results[query] = result
                self.save_result_to_db(run_id, query_id, result)

            # Phase 4: Reverse roles - ablate control collections and test control queries
            logging.info("=== Phase 4: Ablating control collections for control queries ===")

            phase4_results = {}

            for query, category in selected_queries["control"]:
                query_id = query_ids.get((query, category))
                result = self.run_ablation_test(query, self.control_group)
                phase4_results[query] = result
                self.save_result_to_db(run_id, query_id, result)

            # Generate summary report
            self.generate_summary_report(run_id, {
                "phase1": phase1_results,
                "phase2": phase2_results,
                "phase3": phase3_results,
                "phase4": phase4_results
            })

            logging.info(f"Ablation study {run_id} completed successfully")

        except Exception as e:
            logging.error(f"Error running ablation study: {e}")
            import traceback
            traceback.print_exc()

    def generate_summary_report(self, run_id: str, results: Dict[str, Dict[str, Any]]):
        """
        Generate a summary report for the ablation study.

        Args:
            run_id: Identifier for the current ablation run
            results: Dictionary with results from all phases
        """
        output_file = self.results_dir / f"ablation_summary_{self.timestamp}.txt"

        conn = sqlite3.connect(str(self.results_db_path))
        cursor = conn.cursor()

        # Get run details
        cursor.execute("SELECT * FROM ablation_runs WHERE run_id = ?", (run_id,))
        run_details = cursor.fetchone()

        # Calculate aggregate metrics by phase
        phase_metrics = {}

        for phase, phase_results in results.items():
            phase_metrics[phase] = {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "impact": 0.0,
                "count": 0
            }

            for query, result in phase_results.items():
                metrics = result["metrics"]
                phase_metrics[phase]["precision"] += metrics["precision"]
                phase_metrics[phase]["recall"] += metrics["recall"]
                phase_metrics[phase]["f1"] += metrics["f1"]
                phase_metrics[phase]["impact"] += metrics["impact"]
                phase_metrics[phase]["count"] += 1

            # Calculate averages
            count = phase_metrics[phase]["count"]
            if count > 0:
                phase_metrics[phase]["precision"] /= count
                phase_metrics[phase]["recall"] /= count
                phase_metrics[phase]["f1"] /= count
                phase_metrics[phase]["impact"] /= count

        with open(output_file, "w") as f:
            f.write(f"Indaleko Ablation Study Summary - {self.timestamp}\n")
            f.write("="* 50 + "\n\n")

            f.write("Study Configuration\n")
            f.write("-" * 20 + "\n")
            f.write(f"Run ID: {run_id}\n")
            f.write(f"Random Seed: {RANDOM_SEED}\n")
            f.write(f"Activity Collections: {len(self.activity_collections)}\n")
            f.write(f"Control Group: {len(self.control_group)} collections\n")
            f.write(f"Study Group: {len(self.study_group)} collections\n\n")

            f.write("Summary Metrics by Phase\n")
            f.write("-" * 20 + "\n")

            for phase, metrics in phase_metrics.items():
                if phase == "phase1":
                    description = "Study queries with ablated study collections"
                elif phase == "phase2":
                    description = "Control queries with ablated study collections"
                elif phase == "phase3":
                    description = "Study queries with ablated control collections"
                elif phase == "phase4":
                    description = "Control queries with ablated control collections"

                f.write(f"Phase: {phase} - {description}\n")
                f.write(f"  Precision: {metrics['precision']:.4f}\n")
                f.write(f"  Recall: {metrics['recall']:.4f}\n")
                f.write(f"  F1 Score: {metrics['f1']:.4f}\n")
                f.write(f"  Impact: {metrics['impact']:.4f}\n")
                f.write(f"  Query Count: {metrics['count']}\n\n")

            # Write collection details
            f.write("Collection Groups\n")
            f.write("-" * 20 + "\n")
            f.write("Control Group Collections:\n")
            for collection in self.control_group:
                f.write(f"  - {collection}\n")

            f.write("\nStudy Group Collections:\n")
            for collection in self.study_group:
                f.write(f"  - {collection}\n")

            f.write("\n\nDetailed Results\n")
            f.write("-" * 20 + "\n")

            for phase, phase_results in results.items():
                if phase == "phase1":
                    description = "Study queries with ablated study collections"
                elif phase == "phase2":
                    description = "Control queries with ablated study collections"
                elif phase == "phase3":
                    description = "Study queries with ablated control collections"
                elif phase == "phase4":
                    description = "Control queries with ablated control collections"

                f.write(f"\nPhase: {phase} - {description}\n")

                for query, result in phase_results.items():
                    metrics = result["metrics"]
                    f.write(f"  Query: {query}\n")
                    f.write(f"    Baseline Results: {result['baseline_count']}\n")
                    f.write(f"    Ablated Results: {result['ablated_count']}\n")
                    f.write(f"    Precision: {metrics['precision']:.4f}\n")
                    f.write(f"    Recall: {metrics['recall']:.4f}\n")
                    f.write(f"    F1 Score: {metrics['f1']:.4f}\n")
                    f.write(f"    Impact: {metrics['impact']:.4f}\n")
                    f.write(f"    True Positives: {metrics['true_positives']}\n")
                    f.write(f"    False Positives: {metrics['false_positives']}\n")
                    f.write(f"    False Negatives: {metrics['false_negatives']}\n\n")

        logging.info(f"Summary report saved to {output_file}")

def main():
    """Main entry point."""
    logging.info("Starting ablation study")

    parser = argparse.ArgumentParser(description="Run ablation study for Indaleko")
    parser.add_argument("--queries", type=int, default=10, help="Number of queries per group (default: 10)")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility")
    args = parser.parse_args()

    # Override default seed if specified
    if args.seed != RANDOM_SEED:
        random.seed(args.seed)
        logging.info(f"Using custom random seed: {args.seed}")

    study = AblationStudy()
    study.run_study(num_queries_per_group=args.queries)

    logging.info("Ablation study completed")

if __name__ == "__main__":
    import argparse
    main()
