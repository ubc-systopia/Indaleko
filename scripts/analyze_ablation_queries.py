#!/usr/bin/env python3
"""
Script to extract and analyze AQL queries from ablation test results.

This script extracts unique AQL queries from the ablation test results,
submits them to ArangoDB's explain function, and analyzes the results
to identify potential optimization opportunities.
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from db.db_config import IndalekoDBConfig


def setup_logging(verbose=False):
    """Set up logging for the script."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def extract_queries(metrics_file):
    """Extract unique AQL queries from the ablation test results.
    
    Args:
        metrics_file: Path to the impact_metrics.json file.
        
    Returns:
        dict: Dictionary mapping query hash to (query, bind_vars) tuple.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Extracting queries from {metrics_file}")
    
    # Dictionary to store unique queries
    unique_queries = {}
    
    try:
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
        
        # Process each query
        for query_id, query_data in metrics.items():
            natural_query = query_data.get("query_text", "Unknown query")
            results = query_data.get("results", {})
            
            for impact_key, impact_data in results.items():
                aql_query = impact_data.get("aql_query", "")
                if not aql_query:
                    continue
                
                # Sanitize and deduplicate queries
                aql_query = aql_query.strip()
                
                # Extract bind variables used in the query
                bind_vars = {}
                for param in ["query", "artist", "genre", "location", "location_name", "location_type", 
                             "task_type", "application", "project", "status", "event_type", "platform", 
                             "event_title", "participant", "file_type", "operation", "source", 
                             "path_fragment", "media_type", "creator", "title_fragment",
                             "from_timestamp", "to_timestamp"]:
                    if param in impact_data:
                        bind_vars[param] = impact_data[param]
                
                # Use a common value for truth_keys to simplify deduplication
                if "truth_keys" in impact_data:
                    bind_vars["truth_keys"] = ["example_key_1", "example_key_2"]
                
                # Create a hash of the query to deduplicate
                query_hash = hash(aql_query)
                
                collection_name = ""
                if "AblationMusicActivity" in aql_query:
                    collection_name = "AblationMusicActivity"
                elif "AblationLocationActivity" in aql_query:
                    collection_name = "AblationLocationActivity"
                elif "AblationTaskActivity" in aql_query:
                    collection_name = "AblationTaskActivity"
                elif "AblationCollaborationActivity" in aql_query:
                    collection_name = "AblationCollaborationActivity"
                elif "AblationStorageActivity" in aql_query:
                    collection_name = "AblationStorageActivity"
                elif "AblationMediaActivity" in aql_query:
                    collection_name = "AblationMediaActivity"
                
                if query_hash not in unique_queries:
                    unique_queries[query_hash] = {
                        "aql_query": aql_query,
                        "bind_vars": bind_vars,
                        "natural_query": natural_query,
                        "collection": collection_name,
                        "impact_key": impact_key
                    }
                    logger.debug(f"Added unique query: {aql_query}")
        
        logger.info(f"Extracted {len(unique_queries)} unique queries")
        return unique_queries
        
    except Exception as e:
        logger.error(f"Error extracting queries: {e}")
        return {}


def analyze_queries(unique_queries):
    """Analyze queries using ArangoDB's explain function.
    
    This function uses the ArangoDB HTTP API directly to explain queries.
    
    Args:
        unique_queries: Dictionary mapping query hash to (query, bind_vars) tuple.
        
    Returns:
        dict: Dictionary mapping query hash to explain results.
    """
    logger = logging.getLogger(__name__)
    logger.info("Analyzing queries with ArangoDB explain")
    
    explain_results = {}
    
    try:
        # Connect to ArangoDB
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        # Get ArangoDB connection details for direct API access
        connection = db._connection
        
        for query_hash, query_data in unique_queries.items():
            try:
                aql_query = query_data["aql_query"]
                bind_vars = query_data["bind_vars"]
                collection = query_data["collection"]
                
                # Prepare request for explain API
                explain_data = {
                    "query": aql_query,
                    "bindVars": bind_vars,
                    "options": {
                        "allPlans": True
                    }
                }
                
                # Execute explain using HTTP API
                logger.debug(f"Explaining query: {aql_query}")
                response = connection.post("/_api/explain", data=explain_data)
                
                if response.status_code == 200:
                    explain_result = response.body
                    
                    # Store the result
                    explain_results[query_hash] = {
                        "query_data": query_data,
                        "explain_result": explain_result
                    }
                    
                    logger.debug(f"Explained query with estimated cost: {explain_result.get('estimatedCost', 'unknown')}")
                else:
                    logger.error(f"Explain failed with status {response.status_code}: {response.body}")
                
            except Exception as e:
                logger.error(f"Error explaining query {aql_query}: {e}")
        
        logger.info(f"Analyzed {len(explain_results)} queries")
        return explain_results
        
    except Exception as e:
        logger.error(f"Error connecting to database or analyzing queries: {e}")
        return {}


def identify_index_opportunities(explain_results):
    """Identify potential index opportunities based on explain results.
    
    Args:
        explain_results: Dictionary mapping query hash to explain results.
        
    Returns:
        list: List of potential index recommendations.
    """
    logger = logging.getLogger(__name__)
    logger.info("Identifying indexing opportunities")
    
    # Collection to field mapping for potential indices
    index_candidates = defaultdict(set)
    
    # Analyze each explain result
    for query_hash, result_data in explain_results.items():
        try:
            query_data = result_data["query_data"]
            explain_result = result_data["explain_result"]
            collection = query_data["collection"]
            
            # Extract rules from the explain result
            rules = explain_result.get("rules", [])
            
            # Analyze the execution plan
            plans = explain_result.get("plans", [])
            if not plans:
                continue
                
            # Get the best plan (first one)
            best_plan = plans[0]
            
            # Extract nodes from the plan
            nodes = best_plan.get("nodes", [])
            for node in nodes:
                # Look for FilterNode or IndexNode
                node_type = node.get("type", "")
                
                if node_type == "IndexNode":
                    # Already using an index, check which one
                    index_info = node.get("indexes", [])
                    for idx in index_info:
                        logger.debug(f"Using index {idx.get('name', 'unknown')} for collection {collection}")
                
                elif node_type == "FilterNode":
                    # Potential index opportunity
                    expression = node.get("condition", "")
                    logger.debug(f"FilterNode condition: {expression}")
                    
                    # Parse the expression to extract fields
                    # This is a simplified approach and may need refinement
                    for field in ["artist", "genre", "location_name", "location_type", 
                                  "task_type", "application", "project", "status", 
                                  "event_type", "platform", "event_title", "file_type", 
                                  "operation", "source", "media_type", "creator", 
                                  "timestamp"]:
                        if f"doc.{field}" in expression:
                            index_candidates[collection].add(field)
                            logger.debug(f"Added index candidate: {collection}.{field}")
                
                elif node_type == "CalculationNode":
                    # Check for calculations that could benefit from indices
                    expression = node.get("expression", "")
                    if "LIKE" in expression or "FILTER" in expression:
                        logger.debug(f"Calculation expression: {expression}")
                        
                        # Extract fields from LIKE expressions
                        for field in ["path", "title", "name", "label"]:
                            if f"doc.{field}" in expression and "LIKE" in expression:
                                # This might benefit from a text index
                                index_candidates[collection].add(f"{field} (fulltext)")
                                logger.debug(f"Added fulltext index candidate: {collection}.{field}")
            
        except Exception as e:
            logger.error(f"Error analyzing explain result for query {query_hash}: {e}")
    
    # Generate recommendations
    recommendations = []
    for collection, fields in index_candidates.items():
        for field in fields:
            if "fulltext" in field:
                base_field = field.split(" ")[0]
                recommendations.append({
                    "collection": collection,
                    "field": base_field,
                    "type": "fulltext",
                    "recommendation": f"Create a fulltext index on {collection}.{base_field}"
                })
            else:
                recommendations.append({
                    "collection": collection,
                    "field": field,
                    "type": "persistent",
                    "recommendation": f"Create a persistent index on {collection}.{field}"
                })
    
    logger.info(f"Identified {len(recommendations)} potential index opportunities")
    return recommendations


def generate_index_script(recommendations, output_file):
    """Generate a JavaScript file to create the recommended indices.
    
    Args:
        recommendations: List of index recommendations.
        output_file: Path to write the JavaScript file.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating index creation script: {output_file}")
    
    try:
        with open(output_file, "w") as f:
            f.write("// Auto-generated script to create recommended indices for ablation testing\n")
            f.write("// Run in arangosh or with db.executeJS() in Python\n\n")
            
            # Group recommendations by collection
            by_collection = defaultdict(list)
            for rec in recommendations:
                by_collection[rec["collection"]].append(rec)
            
            for collection, recs in by_collection.items():
                f.write(f"// Indices for {collection}\n")
                f.write(f"var coll = db.{collection};\n\n")
                
                for i, rec in enumerate(recs):
                    field = rec["field"]
                    idx_type = rec["type"]
                    
                    if idx_type == "fulltext":
                        f.write(f"// Fulltext index for {field}\n")
                        f.write(f"try {{ coll.ensureIndex({{ type: 'fulltext', fields: ['{field}'], minLength: 3 }}); ")
                        f.write(f"print('Created fulltext index on {collection}.{field}'); }}\n")
                        f.write(f"catch (e) {{ print('Error creating fulltext index on {collection}.{field}: ' + e); }}\n\n")
                        
                    else:  # persistent
                        f.write(f"// Persistent index for {field}\n")
                        f.write(f"try {{ coll.ensureIndex({{ type: 'persistent', fields: ['{field}'] }}); ")
                        f.write(f"print('Created persistent index on {collection}.{field}'); }}\n")
                        f.write(f"catch (e) {{ print('Error creating persistent index on {collection}.{field}: ' + e); }}\n\n")
                
                f.write("\n")
        
        logger.info(f"Index script generated: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating index script: {e}")
        return False


def generate_python_index_script(recommendations, output_file):
    """Generate a Python script to create the recommended indices.
    
    Args:
        recommendations: List of index recommendations.
        output_file: Path to write the Python script.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating Python index creation script: {output_file}")
    
    try:
        with open(output_file, "w") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("\"\"\"Auto-generated script to create recommended indices for ablation testing.\"\"\"\n\n")
            f.write("import logging\n")
            f.write("import os\n")
            f.write("import sys\n")
            f.write("from pathlib import Path\n\n")
            
            f.write("# Set up environment\n")
            f.write("if os.environ.get(\"INDALEKO_ROOT\") is None:\n")
            f.write("    current_path = Path(__file__).parent.resolve()\n")
            f.write("    while not (Path(current_path) / \"Indaleko.py\").exists():\n")
            f.write("        current_path = Path(current_path).parent\n")
            f.write("    os.environ[\"INDALEKO_ROOT\"] = str(current_path)\n")
            f.write("    sys.path.insert(0, str(current_path))\n\n")
            
            f.write("from db.db_config import IndalekoDBConfig\n\n")
            
            f.write("def main():\n")
            f.write("    \"\"\"Create recommended indices for ablation testing.\"\"\"\n")
            f.write("    logging.basicConfig(level=logging.INFO, format=\"%(asctime)s - %(levelname)s - %(message)s\")\n")
            f.write("    logger = logging.getLogger(__name__)\n\n")
            
            f.write("    try:\n")
            f.write("        # Connect to ArangoDB\n")
            f.write("        db_config = IndalekoDBConfig()\n")
            f.write("        db = db_config.get_arangodb()\n")
            f.write("        logger.info(\"Connected to ArangoDB\")\n\n")
            
            # Group recommendations by collection
            by_collection = defaultdict(list)
            for rec in recommendations:
                by_collection[rec["collection"]].append(rec)
            
            for collection, recs in by_collection.items():
                f.write(f"        # Indices for {collection}\n")
                f.write(f"        coll = db.collection(\"{collection}\")\n")
                
                for i, rec in enumerate(recs):
                    field = rec["field"]
                    idx_type = rec["type"]
                    
                    if idx_type == "fulltext":
                        f.write(f"        # Fulltext index for {field}\n")
                        f.write(f"        try:\n")
                        f.write(f"            coll.add_fulltext_index([\"doc.{field}\"], min_length=3)\n")
                        f.write(f"            logger.info(f\"Created fulltext index on {collection}.{field}\")\n")
                        f.write(f"        except Exception as e:\n")
                        f.write(f"            logger.error(f\"Error creating fulltext index on {collection}.{field}: {{e}}\")\n\n")
                        
                    else:  # persistent
                        f.write(f"        # Persistent index for {field}\n")
                        f.write(f"        try:\n")
                        f.write(f"            coll.add_persistent_index([\"doc.{field}\"])\n")
                        f.write(f"            logger.info(f\"Created persistent index on {collection}.{field}\")\n")
                        f.write(f"        except Exception as e:\n")
                        f.write(f"            logger.error(f\"Error creating persistent index on {collection}.{field}: {{e}}\")\n\n")
                
                f.write("\n")
            
            f.write("    except Exception as e:\n")
            f.write("        logger.error(f\"Error: {e}\")\n")
            f.write("        return False\n\n")
            
            f.write("    logger.info(\"Index creation completed\")\n")
            f.write("    return True\n\n")
            
            f.write("if __name__ == \"__main__\":\n")
            f.write("    main()\n")
        
        logger.info(f"Python index script generated: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating Python index script: {e}")
        return False


def generate_report(explain_results, recommendations, output_file):
    """Generate a report of the analysis.
    
    Args:
        explain_results: Dictionary mapping query hash to explain results.
        recommendations: List of index recommendations.
        output_file: Path to write the report.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating analysis report: {output_file}")
    
    try:
        with open(output_file, "w") as f:
            f.write("# AQL Query Analysis Report\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- Analyzed {len(explain_results)} unique queries\n")
            f.write(f"- Identified {len(recommendations)} potential index opportunities\n\n")
            
            # Recommendations section
            f.write("## Index Recommendations\n\n")
            if recommendations:
                f.write("| Collection | Field | Index Type | Recommendation |\n")
                f.write("|------------|-------|------------|----------------|\n")
                
                for rec in recommendations:
                    collection = rec["collection"]
                    field = rec["field"]
                    idx_type = rec["type"]
                    recommendation = rec["recommendation"]
                    
                    f.write(f"| {collection} | {field} | {idx_type} | {recommendation} |\n")
            else:
                f.write("No index recommendations were identified.\n")
            
            f.write("\n## Analyzed Queries\n\n")
            
            # Queries section
            for query_hash, result_data in explain_results.items():
                query_data = result_data["query_data"]
                explain_result = result_data["explain_result"]
                
                aql_query = query_data["aql_query"]
                natural_query = query_data["natural_query"]
                collection = query_data["collection"]
                
                # Estimate cost from explain
                cost = explain_result.get("estimatedCost", "unknown")
                
                # Get nodes from the plan
                plans = explain_result.get("plans", [])
                if not plans:
                    continue
                best_plan = plans[0]
                nodes = best_plan.get("nodes", [])
                
                # Extract any index usage
                index_usage = []
                for node in nodes:
                    if node.get("type") == "IndexNode":
                        index_info = node.get("indexes", [])
                        for idx in index_info:
                            index_usage.append(idx.get("name", "unknown"))
                
                f.write(f"### Query on {collection}\n\n")
                f.write(f"Natural language query: \"{natural_query}\"\n\n")
                f.write("```aql\n")
                f.write(aql_query)
                f.write("\n```\n\n")
                
                f.write(f"- Estimated cost: {cost}\n")
                if index_usage:
                    f.write(f"- Uses indices: {', '.join(index_usage)}\n")
                else:
                    f.write("- No indices used\n")
                
                f.write("\n")
        
        logger.info(f"Analysis report generated: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Analyze AQL queries from ablation test results")
    parser.add_argument("--metrics-file", default="ablation_results_comprehensive/impact_metrics.json",
                        help="Path to the impact_metrics.json file from ablation test results")
    parser.add_argument("--output-dir", default="ablation_analysis",
                        help="Directory to save analysis results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Extract unique queries from metrics file
    unique_queries = extract_queries(args.metrics_file)
    if not unique_queries:
        logger.error("No queries found in metrics file")
        return False
    
    # Save extracted queries to a JSON file
    queries_file = os.path.join(args.output_dir, "unique_queries.json")
    with open(queries_file, "w") as f:
        json.dump(unique_queries, f, indent=2)
    logger.info(f"Saved {len(unique_queries)} unique queries to {queries_file}")
    
    # Analyze queries with ArangoDB explain
    explain_results = analyze_queries(unique_queries)
    if not explain_results:
        logger.error("No explain results generated")
        return False
    
    # Save explain results to a JSON file
    explain_file = os.path.join(args.output_dir, "explain_results.json")
    # Need to convert to a serializable format
    serializable_results = {}
    for query_hash, result_data in explain_results.items():
        serializable_results[str(query_hash)] = {
            "query_data": result_data["query_data"],
            "explain_result": result_data["explain_result"]
        }
    with open(explain_file, "w") as f:
        json.dump(serializable_results, f, indent=2)
    logger.info(f"Saved explain results to {explain_file}")
    
    # Identify potential index opportunities
    recommendations = identify_index_opportunities(explain_results)
    
    # Generate index script
    js_script_file = os.path.join(args.output_dir, "create_indices.js")
    generate_index_script(recommendations, js_script_file)
    
    # Generate Python index script
    py_script_file = os.path.join(args.output_dir, "create_indices.py")
    generate_python_index_script(recommendations, py_script_file)
    
    # Generate report
    report_file = os.path.join(args.output_dir, "analysis_report.md")
    from datetime import datetime
    generate_report(explain_results, recommendations, report_file)
    
    logger.info(f"Analysis completed, results saved to {args.output_dir}")
    return True


if __name__ == "__main__":
    main()