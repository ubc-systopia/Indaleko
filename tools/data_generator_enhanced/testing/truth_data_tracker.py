#!/usr/bin/env python3
"""
Truth data tracking system for the Indaleko ablation study.

This module provides a SQLite-based system for tracking test truth data
and results to support comprehensive ablation testing.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sqlite3
import logging
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional, Set, Union


class TruthDataTracker:
    """A SQLite-based system for tracking ablation test truth data and results."""

    def __init__(self, db_path: str = "ablation_results.db"):
        """Initialize the truth data tracker.

        Args:
            db_path: Path to the SQLite database file (default: ablation_results.db)
        """
        self.db_path = db_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize the database connection
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
        
        # Create the schema if it doesn't exist
        self._create_schema()
        
        self.logger.info(f"Initialized TruthDataTracker with database at {db_path}")

    def _create_schema(self) -> None:
        """Create the database schema for truth data tracking."""
        self.cursor.executescript("""
        -- Studies table to track different ablation studies
        CREATE TABLE IF NOT EXISTS studies (
            study_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            parameters TEXT,  -- JSON string of study parameters
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        -- Clusters table to track different source clusters
        CREATE TABLE IF NOT EXISTS clusters (
            cluster_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            name TEXT NOT NULL,
            experimental_sources TEXT NOT NULL,  -- JSON array of sources
            control_sources TEXT NOT NULL,      -- JSON array of sources
            created_at INTEGER NOT NULL,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        );

        -- Queries table to track test queries
        CREATE TABLE IF NOT EXISTS queries (
            query_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            text TEXT NOT NULL,
            category TEXT NOT NULL,  -- 'ablation' or 'control'
            metadata_categories TEXT,  -- JSON array of categories
            created_at INTEGER NOT NULL,
            FOREIGN KEY (study_id) REFERENCES studies(study_id)
        );

        -- Truth data table to track expected results
        CREATE TABLE IF NOT EXISTS truth_data (
            truth_id TEXT PRIMARY KEY,
            query_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            matching INTEGER NOT NULL,  -- 1 for matching, 0 for non-matching
            metadata TEXT,  -- JSON object with relevant metadata
            created_at INTEGER NOT NULL,
            FOREIGN KEY (query_id) REFERENCES queries(query_id)
        );

        -- Ablation results table to track test results
        CREATE TABLE IF NOT EXISTS ablation_results (
            result_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            query_id TEXT NOT NULL,
            ablated_sources TEXT,  -- JSON array of ablated sources
            returned_ids TEXT,     -- JSON array of returned document IDs
            precision REAL,
            recall REAL,
            f1_score REAL,
            impact REAL,
            execution_time_ms INTEGER,
            aql_query TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (study_id) REFERENCES studies(study_id),
            FOREIGN KEY (cluster_id) REFERENCES clusters(cluster_id),
            FOREIGN KEY (query_id) REFERENCES queries(query_id)
        );
        """)
        self.conn.commit()

    def create_study(self, name: str, description: str = "", parameters: Dict[str, Any] = None) -> str:
        """Create a new ablation study record.

        Args:
            name: Name of the study
            description: Description of the study
            parameters: Dictionary of study parameters

        Returns:
            The study ID
        """
        study_id = str(uuid.uuid4())
        now = int(datetime.datetime.now().timestamp())
        
        self.cursor.execute(
            """
            INSERT INTO studies (study_id, name, description, parameters, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                study_id,
                name,
                description,
                json.dumps(parameters or {}),
                now,
                now
            )
        )
        self.conn.commit()
        
        self.logger.info(f"Created study '{name}' with ID {study_id}")
        return study_id

    def add_cluster(
        self,
        study_id: str,
        name: str,
        experimental_sources: List[str],
        control_sources: List[str]
    ) -> str:
        """Add a new cluster to a study.

        Args:
            study_id: ID of the study
            name: Name of the cluster
            experimental_sources: List of experimental source names
            control_sources: List of control source names

        Returns:
            The cluster ID
        """
        cluster_id = str(uuid.uuid4())
        now = int(datetime.datetime.now().timestamp())
        
        self.cursor.execute(
            """
            INSERT INTO clusters (cluster_id, study_id, name, experimental_sources, control_sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cluster_id,
                study_id,
                name,
                json.dumps(experimental_sources),
                json.dumps(control_sources),
                now
            )
        )
        self.conn.commit()
        
        self.logger.info(f"Added cluster '{name}' to study {study_id}")
        return cluster_id

    def add_query(
        self,
        study_id: str,
        text: str,
        category: str,
        metadata_categories: List[str] = None
    ) -> str:
        """Add a new query to a study.

        Args:
            study_id: ID of the study
            text: The query text
            category: Query category ('ablation' or 'control')
            metadata_categories: List of metadata categories used in the query

        Returns:
            The query ID
        """
        query_id = str(uuid.uuid4())
        now = int(datetime.datetime.now().timestamp())
        
        self.cursor.execute(
            """
            INSERT INTO queries (query_id, study_id, text, category, metadata_categories, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                query_id,
                study_id,
                text,
                category,
                json.dumps(metadata_categories or []),
                now
            )
        )
        self.conn.commit()
        
        self.logger.info(f"Added {category} query '{text}' to study {study_id}")
        return query_id

    def add_truth_data(
        self,
        query_id: str,
        document_id: str,
        matching: bool,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add truth data for a query.

        Args:
            query_id: ID of the query
            document_id: ID of the document
            matching: Whether the document should match the query
            metadata: Additional metadata about the document

        Returns:
            The truth data ID
        """
        truth_id = str(uuid.uuid4())
        now = int(datetime.datetime.now().timestamp())
        
        self.cursor.execute(
            """
            INSERT INTO truth_data (truth_id, query_id, document_id, matching, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                truth_id,
                query_id,
                document_id,
                1 if matching else 0,
                json.dumps(metadata or {}),
                now
            )
        )
        self.conn.commit()
        
        match_status = "matching" if matching else "non-matching"
        self.logger.debug(f"Added {match_status} truth data for document {document_id} and query {query_id}")
        return truth_id

    def add_ablation_result(
        self,
        study_id: str,
        cluster_id: str,
        query_id: str,
        ablated_sources: List[str],
        returned_ids: List[str],
        precision: float,
        recall: float,
        f1_score: float,
        impact: float,
        execution_time_ms: int,
        aql_query: str
    ) -> str:
        """Add an ablation test result.

        Args:
            study_id: ID of the study
            cluster_id: ID of the cluster
            query_id: ID of the query
            ablated_sources: List of ablated source names
            returned_ids: List of document IDs returned by the query
            precision: Precision metric
            recall: Recall metric
            f1_score: F1 score
            impact: Impact score (1 - F1)
            execution_time_ms: Execution time in milliseconds
            aql_query: The AQL query executed

        Returns:
            The result ID
        """
        result_id = str(uuid.uuid4())
        now = int(datetime.datetime.now().timestamp())
        
        self.cursor.execute(
            """
            INSERT INTO ablation_results (
                result_id, study_id, cluster_id, query_id, ablated_sources,
                returned_ids, precision, recall, f1_score, impact,
                execution_time_ms, aql_query, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                study_id,
                cluster_id,
                query_id,
                json.dumps(ablated_sources),
                json.dumps(returned_ids),
                precision,
                recall,
                f1_score,
                impact,
                execution_time_ms,
                aql_query,
                now
            )
        )
        self.conn.commit()
        
        self.logger.info(
            f"Added ablation result for query {query_id} in cluster {cluster_id}: "
            f"precision={precision:.4f}, recall={recall:.4f}, f1={f1_score:.4f}, impact={impact:.4f}"
        )
        return result_id

    def get_studies(self) -> List[Dict[str, Any]]:
        """Get all studies.

        Returns:
            List of study records
        """
        self.cursor.execute("SELECT * FROM studies ORDER BY created_at DESC")
        return [dict(row) for row in self.cursor.fetchall()]

    def get_clusters(self, study_id: str) -> List[Dict[str, Any]]:
        """Get all clusters for a study.

        Args:
            study_id: ID of the study

        Returns:
            List of cluster records
        """
        self.cursor.execute(
            "SELECT * FROM clusters WHERE study_id = ? ORDER BY created_at",
            (study_id,)
        )
        
        clusters = []
        for row in self.cursor.fetchall():
            cluster = dict(row)
            # Parse JSON fields
            cluster["experimental_sources"] = json.loads(cluster["experimental_sources"])
            cluster["control_sources"] = json.loads(cluster["control_sources"])
            clusters.append(cluster)
            
        return clusters

    def get_queries(self, study_id: str, category: str = None) -> List[Dict[str, Any]]:
        """Get queries for a study, optionally filtered by category.

        Args:
            study_id: ID of the study
            category: Optional filter for query category ('ablation' or 'control')

        Returns:
            List of query records
        """
        if category:
            self.cursor.execute(
                "SELECT * FROM queries WHERE study_id = ? AND category = ? ORDER BY created_at",
                (study_id, category)
            )
        else:
            self.cursor.execute(
                "SELECT * FROM queries WHERE study_id = ? ORDER BY created_at",
                (study_id,)
            )
            
        queries = []
        for row in self.cursor.fetchall():
            query = dict(row)
            # Parse JSON fields
            query["metadata_categories"] = json.loads(query["metadata_categories"])
            queries.append(query)
            
        return queries

    def get_truth_data(self, query_id: str, matching_only: bool = False) -> List[Dict[str, Any]]:
        """Get truth data for a query.

        Args:
            query_id: ID of the query
            matching_only: If True, only return matching documents

        Returns:
            List of truth data records
        """
        if matching_only:
            self.cursor.execute(
                "SELECT * FROM truth_data WHERE query_id = ? AND matching = 1 ORDER BY created_at",
                (query_id,)
            )
        else:
            self.cursor.execute(
                "SELECT * FROM truth_data WHERE query_id = ? ORDER BY created_at",
                (query_id,)
            )
            
        truth_data = []
        for row in self.cursor.fetchall():
            data = dict(row)
            # Parse JSON fields
            data["metadata"] = json.loads(data["metadata"])
            # Convert matching to boolean
            data["matching"] = bool(data["matching"])
            truth_data.append(data)
            
        return truth_data

    def get_ablation_results(
        self,
        study_id: str,
        cluster_id: str = None,
        query_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get ablation results, optionally filtered by cluster and/or query.

        Args:
            study_id: ID of the study
            cluster_id: Optional cluster ID filter
            query_id: Optional query ID filter

        Returns:
            List of ablation result records
        """
        params = [study_id]
        query = "SELECT * FROM ablation_results WHERE study_id = ?"
        
        if cluster_id:
            query += " AND cluster_id = ?"
            params.append(cluster_id)
            
        if query_id:
            query += " AND query_id = ?"
            params.append(query_id)
            
        query += " ORDER BY created_at"
            
        self.cursor.execute(query, params)
        
        results = []
        for row in self.cursor.fetchall():
            result = dict(row)
            # Parse JSON fields
            result["ablated_sources"] = json.loads(result["ablated_sources"])
            result["returned_ids"] = json.loads(result["returned_ids"])
            results.append(result)
            
        return results

    def get_study_summary(self, study_id: str) -> Dict[str, Any]:
        """Get a summary of study results.

        Args:
            study_id: ID of the study

        Returns:
            Dictionary with study summary information
        """
        # Get study information
        self.cursor.execute("SELECT * FROM studies WHERE study_id = ?", (study_id,))
        study = dict(self.cursor.fetchone())
        study["parameters"] = json.loads(study["parameters"])
        
        # Get cluster information
        clusters = self.get_clusters(study_id)
        
        # Get query information
        queries = self.get_queries(study_id)
        
        # Get result metrics by cluster and source
        cluster_metrics = {}
        source_metrics = {}
        all_sources = set()
        
        for cluster in clusters:
            cluster_id = cluster["cluster_id"]
            cluster_name = cluster["name"]
            
            # Get all sources in this cluster
            cluster_sources = cluster["experimental_sources"] + cluster["control_sources"]
            all_sources.update(cluster_sources)
            
            # Get result metrics for this cluster
            results = self.get_ablation_results(study_id, cluster_id)
            
            # Calculate average metrics for the cluster
            precision_values = [r["precision"] for r in results]
            recall_values = [r["recall"] for r in results]
            f1_values = [r["f1_score"] for r in results]
            impact_values = [r["impact"] for r in results]
            
            if precision_values:
                avg_precision = sum(precision_values) / len(precision_values)
                avg_recall = sum(recall_values) / len(recall_values)
                avg_f1 = sum(f1_values) / len(f1_values)
                avg_impact = sum(impact_values) / len(impact_values)
                
                cluster_metrics[cluster_name] = {
                    "precision": avg_precision,
                    "recall": avg_recall,
                    "f1": avg_f1,
                    "impact": avg_impact,
                    "result_count": len(results)
                }
                
        # Calculate metrics by source
        for source in all_sources:
            # Find all results where this source was ablated
            source_results = []
            
            for cluster in clusters:
                cluster_id = cluster["cluster_id"]
                results = self.get_ablation_results(study_id, cluster_id)
                
                for result in results:
                    if source in result["ablated_sources"]:
                        source_results.append(result)
            
            # Calculate average metrics for the source
            if source_results:
                precision_values = [r["precision"] for r in source_results]
                recall_values = [r["recall"] for r in source_results]
                f1_values = [r["f1_score"] for r in source_results]
                impact_values = [r["impact"] for r in source_results]
                
                avg_precision = sum(precision_values) / len(precision_values)
                avg_recall = sum(recall_values) / len(recall_values)
                avg_f1 = sum(f1_values) / len(f1_values)
                avg_impact = sum(impact_values) / len(impact_values)
                
                source_metrics[source] = {
                    "precision": avg_precision,
                    "recall": avg_recall,
                    "f1": avg_f1,
                    "impact": avg_impact,
                    "result_count": len(source_results)
                }
                
        return {
            "study": study,
            "clusters": clusters,
            "queries": queries,
            "metrics": {
                "clusters": cluster_metrics,
                "sources": source_metrics
            }
        }

    def generate_report(self, study_id: str, output_path: str) -> bool:
        """Generate a comprehensive report for a study.

        Args:
            study_id: ID of the study
            output_path: File path for the report

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get study summary
            summary = self.get_study_summary(study_id)
            
            # Open output file
            with open(output_path, "w") as f:
                # Write header
                f.write("# Indaleko Ablation Study Report\n\n")
                f.write(f"## Study: {summary['study']['name']}\n\n")
                f.write(f"Date: {datetime.datetime.fromtimestamp(summary['study']['created_at'])}\n\n")
                if summary['study']['description']:
                    f.write(f"{summary['study']['description']}\n\n")
                
                # Write parameters
                f.write("### Parameters\n\n")
                for key, value in summary['study']['parameters'].items():
                    f.write(f"- **{key}**: {value}\n")
                f.write("\n")
                
                # Write source impact metrics
                f.write("### Source Impact Metrics\n\n")
                f.write("| Source | Impact | F1 Score | Precision | Recall | Tests |\n")
                f.write("|--------|--------|----------|-----------|--------|-------|\n")
                
                for source, metrics in sorted(summary['metrics']['sources'].items(), key=lambda x: x[1]['impact'], reverse=True):
                    f.write(f"| {source} | {metrics['impact']:.4f} | {metrics['f1']:.4f} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['result_count']} |\n")
                f.write("\n")
                
                # Write cluster metrics
                f.write("### Cluster Metrics\n\n")
                f.write("| Cluster | Impact | F1 Score | Precision | Recall | Tests |\n")
                f.write("|---------|--------|----------|-----------|--------|-------|\n")
                
                for cluster, metrics in sorted(summary['metrics']['clusters'].items(), key=lambda x: x[1]['impact'], reverse=True):
                    f.write(f"| {cluster} | {metrics['impact']:.4f} | {metrics['f1']:.4f} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['result_count']} |\n")
                f.write("\n")
                
                # Write cluster details
                f.write("### Cluster Configurations\n\n")
                for cluster in summary['clusters']:
                    f.write(f"#### {cluster['name']}\n\n")
                    f.write("**Experimental Sources:**\n\n")
                    for source in cluster['experimental_sources']:
                        f.write(f"- {source}\n")
                    f.write("\n**Control Sources:**\n\n")
                    for source in cluster['control_sources']:
                        f.write(f"- {source}\n")
                    f.write("\n")
                
                # Write query details
                f.write("### Test Queries\n\n")
                f.write("| Category | Query | Metadata Categories |\n")
                f.write("|----------|-------|--------------------|\n")
                
                for query in summary['queries']:
                    categories = ", ".join(query['metadata_categories'])
                    f.write(f"| {query['category']} | {query['text']} | {categories} |\n")
                
            self.logger.info(f"Generated report saved to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return False

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Closed database connection")


def main():
    """Simple test of the TruthDataTracker."""
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
    
    # Create a tracker with an in-memory database
    tracker = TruthDataTracker(":memory:")
    
    # Create a test study
    study_id = tracker.create_study(
        "Test Ablation Study",
        "A test of the TruthDataTracker",
        {"seed": 42, "clusters": 3}
    )
    
    # Create a test cluster
    cluster_id = tracker.add_cluster(
        study_id,
        "Cluster 1",
        ["ActivityContext", "MusicActivityContext", "GeoActivityContext", "CalendarActivityContext"],
        ["ThermostatActivityContext", "SocialMediaActivityContext"]
    )
    
    # Create test queries
    query1_id = tracker.add_query(
        study_id,
        "Find all documents I worked on yesterday",
        "ablation",
        ["temporal", "activity"]
    )
    
    query2_id = tracker.add_query(
        study_id,
        "Find music I listened to in Seattle",
        "control",
        ["activity", "spatial"]
    )
    
    # Add truth data
    for i in range(5):
        tracker.add_truth_data(
            query1_id,
            f"doc_{i}",
            True,
            {"type": "document", "created_at": "2025-05-01T12:00:00Z"}
        )
        
    for i in range(5, 50):
        tracker.add_truth_data(
            query1_id,
            f"doc_{i}",
            False,
            {"type": "document", "created_at": "2025-04-01T12:00:00Z"}
        )
    
    # Add some sample ablation results
    tracker.add_ablation_result(
        study_id,
        cluster_id,
        query1_id,
        ["ActivityContext"],
        ["doc_0", "doc_1", "doc_2"],
        0.6,
        0.6,
        0.6,
        0.4,
        42,
        "FOR doc IN Objects RETURN doc"
    )
    
    # Print a summary
    print("\nStudy Summary:")
    summary = tracker.get_study_summary(study_id)
    import pprint
    pprint.pprint(summary)
    
    # Generate a report
    tracker.generate_report(study_id, "test_ablation_report.md")
    print("\nReport generated: test_ablation_report.md")
    
    # Close the tracker
    tracker.close()


if __name__ == "__main__":
    main()