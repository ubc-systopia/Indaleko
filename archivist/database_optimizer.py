"""
Database performance optimization component for the Archivist.

This module analyzes query patterns and performance data to automatically
suggest database optimizations such as indexes, views, and query rewrites.

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
import json
import uuid
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import time

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.query_history import QueryHistory
from query.memory.archivist_memory import ArchivistMemory, SearchInsight
from data_models.db_index import IndexType
# pylint: enable=wrong-import-position


class IndexRecommendation(BaseModel):
    """Recommendation for a database index."""
    
    collection: str = Field(..., description="Collection to create index on")
    fields: List[str] = Field(..., description="Fields to include in the index")
    index_type: str = Field(..., description="Type of index (hash, skiplist, persistent, fulltext)")
    stored_values: List[str] = Field(default_factory=list, description="Fields to store in the index")
    estimated_impact: float = Field(default=0.0, description="Estimated impact score (higher is better)")
    estimated_cost: float = Field(default=0.0, description="Estimated maintenance cost")
    affected_queries: List[str] = Field(default_factory=list, description="Queries that would benefit")
    explanation: str = Field(default="", description="Explanation of why this index is recommended")
    created: bool = Field(default=False, description="Whether this index has been created")
    creation_time: Optional[datetime] = Field(default=None, description="When the index was created")
    index_id: Optional[str] = Field(default=None, description="ID of the created index")
    
    def get_creation_command(self) -> Dict[str, Any]:
        """Get the ArangoDB command to create this index."""
        cmd = {
            "collection": self.collection,
            "type": self.index_type,
            "fields": self.fields,
        }
        
        if self.stored_values:
            cmd["storedValues"] = self.stored_values
            
        return cmd
    
    def short_description(self) -> str:
        """Get a short description of this index recommendation."""
        field_str = ", ".join(self.fields)
        stored_str = f" with stored values: {', '.join(self.stored_values)}" if self.stored_values else ""
        return f"{self.index_type} index on {self.collection}({field_str}){stored_str}"


class ViewRecommendation(BaseModel):
    """Recommendation for an ArangoDB view."""
    
    name: str = Field(..., description="Name for the view")
    collections: List[str] = Field(..., description="Collections to include in the view")
    fields: Dict[str, List[str]] = Field(..., description="Fields to include in the view by collection")
    primary_sort: Optional[List[Dict[str, str]]] = Field(default=None, description="Primary sort fields")
    estimated_impact: float = Field(default=0.0, description="Estimated impact score (higher is better)")
    affected_queries: List[str] = Field(default_factory=list, description="Queries that would benefit")
    explanation: str = Field(default="", description="Explanation of why this view is recommended")
    created: bool = Field(default=False, description="Whether this view has been created")
    creation_time: Optional[datetime] = Field(default=None, description="When the view was created")
    view_id: Optional[str] = Field(default=None, description="ID of the created view")
    
    def get_creation_command(self) -> Dict[str, Any]:
        """Get the ArangoDB command to create this view."""
        # Build view links
        links = {}
        for collection in self.collections:
            links[collection] = {
                "analyzers": ["text_en"],
                "includeAllFields": False,
                "fields": {}
            }
            
            # Add fields for this collection
            if collection in self.fields:
                for field in self.fields[collection]:
                    links[collection]["fields"][field] = {"analyzers": ["text_en"]}
        
        # Build the command
        cmd = {
            "name": self.name,
            "type": "arangosearch",
            "links": links
        }
        
        # Add primary sort if specified
        if self.primary_sort:
            cmd["primarySort"] = self.primary_sort
            
        return cmd
    
    def short_description(self) -> str:
        """Get a short description of this view recommendation."""
        collection_str = ", ".join(self.collections)
        field_count = sum(len(fields) for fields in self.fields.values())
        return f"ArangoSearch view '{self.name}' on {collection_str} with {field_count} fields"


class QueryOptimization(BaseModel):
    """Recommendation for an AQL query optimization."""
    
    original_query: str = Field(..., description="Original AQL query")
    optimized_query: str = Field(..., description="Optimized AQL query")
    optimization_type: str = Field(..., description="Type of optimization")
    estimated_speedup: float = Field(default=0.0, description="Estimated speedup factor")
    explanation: str = Field(default="", description="Explanation of the optimization")
    verified: bool = Field(default=False, description="Whether this optimization has been verified")
    verification_speedup: Optional[float] = Field(default=None, description="Measured speedup factor")
    
    def short_description(self) -> str:
        """Get a short description of this query optimization."""
        return f"{self.optimization_type} optimization with {self.estimated_speedup:.1f}x estimated speedup"


class OptimizationLog(BaseModel):
    """Log of an applied optimization."""
    
    optimization_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this optimization")
    optimization_type: str = Field(..., description="Type of optimization (index, view, query)")
    description: str = Field(..., description="Description of the optimization")
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When it was applied")
    performance_before: float = Field(..., description="Performance metric before optimization")
    performance_after: Optional[float] = Field(default=None, description="Performance metric after optimization")
    impact: Optional[float] = Field(default=None, description="Measured impact (e.g., speedup factor)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed information about the optimization")


class DatabaseOptimizer:
    """
    Analyzes query patterns and performance to recommend database optimizations.
    
    This component is responsible for:
    - Analyzing query history to identify access patterns
    - Generating index recommendations
    - Suggesting view creation for better text search
    - Proposing query rewrites for performance
    - Tracking the impact of applied optimizations
    """
    
    def __init__(self, db_connection, archivist_memory=None, query_history=None):
        """
        Initialize the database optimizer.
        
        Args:
            db_connection: ArangoDB connection
            archivist_memory: Optional ArchivistMemory instance
            query_history: Optional QueryHistory instance
        """
        self.db = db_connection
        self.memory = archivist_memory or ArchivistMemory()
        self.query_history = query_history or QueryHistory()
        self.logger = logging.getLogger("DatabaseOptimizer")
        
        # Cache of collection schema information
        self._collection_schemas = {}
        self._existing_indexes = {}
        self._existing_views = {}
        
        # Optimization history
        self.optimization_logs = []
        
        # Load existing database objects
        self._load_database_info()
    
    def _load_database_info(self):
        """Load information about collections, indexes, and views."""
        # Get collection information
        collections = self.db.collections()
        for collection_name in [c for c in collections if not c.startswith("_")]:
            try:
                # Get collection info
                collection = self.db.collection(collection_name)
                
                # Get sample document to infer schema
                sample = next(collection.all().limit(1), None)
                if sample:
                    self._collection_schemas[collection_name] = self._infer_schema(sample)
                
                # Get existing indexes
                indexes = collection.indexes()
                self._existing_indexes[collection_name] = indexes
                
            except Exception as e:
                self.logger.error(f"Error loading info for collection {collection_name}: {e}")
        
        # Get view information
        try:
            views = self.db.views()
            for view in views:
                view_info = self.db.view(view)
                self._existing_views[view] = view_info
        except Exception as e:
            self.logger.error(f"Error loading views: {e}")
    
    def _infer_schema(self, document):
        """Infer schema from a document."""
        def get_type(value):
            if isinstance(value, dict):
                return {"type": "object", "properties": {k: get_type(v) for k, v in value.items()}}
            elif isinstance(value, list):
                if value:
                    return {"type": "array", "items": get_type(value[0])}
                return {"type": "array"}
            elif isinstance(value, str):
                return {"type": "string"}
            elif isinstance(value, int):
                return {"type": "integer"}
            elif isinstance(value, float):
                return {"type": "number"}
            elif isinstance(value, bool):
                return {"type": "boolean"}
            else:
                return {"type": "null"}
        
        return get_type(document)
    
    def analyze_query_patterns(self, time_period=timedelta(days=7)):
        """
        Analyze recent query patterns to identify optimization opportunities.
        
        Args:
            time_period: Time period to analyze
            
        Returns:
            Dict with analysis results
        """
        # Get recent queries
        cutoff_time = datetime.now(timezone.utc) - time_period
        recent_queries = self.query_history.get_queries_after(cutoff_time)
        
        if not recent_queries:
            return {
                "message": "No queries found in the specified time period.",
                "recommendations": []
            }
        
        # Extract frequently accessed attributes and their collections
        attribute_access = self._extract_attribute_access(recent_queries)
        
        # Identify slow queries
        slow_queries = self._identify_slow_queries(recent_queries)
        
        # Identify common filter patterns
        filter_patterns = self._extract_filter_patterns(recent_queries)
        
        # Identify common search patterns
        search_patterns = self._extract_search_patterns(recent_queries)
        
        # Generate recommendations
        index_recommendations = self._generate_index_recommendations(
            attribute_access, filter_patterns, slow_queries
        )
        
        view_recommendations = self._generate_view_recommendations(
            search_patterns, slow_queries
        )
        
        query_optimizations = self._generate_query_optimizations(slow_queries)
        
        return {
            "analyzed_queries": len(recent_queries),
            "slow_queries": len(slow_queries),
            "attribute_access": attribute_access,
            "filter_patterns": filter_patterns,
            "search_patterns": search_patterns,
            "index_recommendations": index_recommendations,
            "view_recommendations": view_recommendations,
            "query_optimizations": query_optimizations
        }
    
    def _extract_attribute_access(self, queries):
        """
        Extract frequently accessed attributes from queries.
        
        Args:
            queries: List of query history entries
            
        Returns:
            Dict mapping collection.attribute to access frequency
        """
        attribute_access = {}
        
        for query in queries:
            # Skip if no AQL
            if not hasattr(query, "Query") or not query.Query:
                continue
                
            aql = query.Query
            
            # Extract collection-field pairs using regex
            # This is a simplified approach; a proper AQL parser would be better
            collection_references = re.findall(r'FOR\s+\w+\s+IN\s+(\w+)', aql, re.IGNORECASE)
            
            for collection in collection_references:
                # Skip system collections
                if collection.startswith('_'):
                    continue
                    
                # Find FILTER statements that reference this collection
                # This is a simplified approach that won't catch all cases
                filter_matches = re.findall(
                    r'FILTER\s+(\w+)\.([a-zA-Z0-9_.]+)\s', 
                    aql,
                    re.IGNORECASE
                )
                
                for var, attr in filter_matches:
                    # Try to match the variable to its collection
                    collection_var_match = re.search(
                        rf'FOR\s+({var})\s+IN\s+{collection}', 
                        aql,
                        re.IGNORECASE
                    )
                    
                    if collection_var_match:
                        # Build the access key: collection.attribute
                        access_key = f"{collection}.{attr}"
                        
                        # Increment access count
                        if access_key not in attribute_access:
                            attribute_access[access_key] = {
                                "collection": collection,
                                "attribute": attr,
                                "filter_count": 0,
                                "sort_count": 0,
                                "total_count": 0,
                                "queries": []
                            }
                        
                        attribute_access[access_key]["filter_count"] += 1
                        attribute_access[access_key]["total_count"] += 1
                        
                        # Add query to list if not already there
                        query_id = getattr(query, "QueryId", str(hash(aql)))
                        if query_id not in attribute_access[access_key]["queries"]:
                            attribute_access[access_key]["queries"].append(query_id)
                
                # Find SORT statements
                sort_matches = re.findall(
                    r'SORT\s+(\w+)\.([a-zA-Z0-9_.]+)\s', 
                    aql,
                    re.IGNORECASE
                )
                
                for var, attr in sort_matches:
                    # Try to match the variable to its collection
                    collection_var_match = re.search(
                        rf'FOR\s+({var})\s+IN\s+{collection}', 
                        aql,
                        re.IGNORECASE
                    )
                    
                    if collection_var_match:
                        # Build the access key: collection.attribute
                        access_key = f"{collection}.{attr}"
                        
                        # Increment access count
                        if access_key not in attribute_access:
                            attribute_access[access_key] = {
                                "collection": collection,
                                "attribute": attr,
                                "filter_count": 0,
                                "sort_count": 0,
                                "total_count": 0,
                                "queries": []
                            }
                        
                        attribute_access[access_key]["sort_count"] += 1
                        attribute_access[access_key]["total_count"] += 1
                        
                        # Add query to list if not already there
                        query_id = getattr(query, "QueryId", str(hash(aql)))
                        if query_id not in attribute_access[access_key]["queries"]:
                            attribute_access[access_key]["queries"].append(query_id)
        
        # Sort by total access count
        return dict(sorted(
            attribute_access.items(), 
            key=lambda x: x[1]["total_count"], 
            reverse=True
        ))
    
    def _identify_slow_queries(self, queries, threshold_ms=500):
        """
        Identify slow queries based on execution time.
        
        Args:
            queries: List of query history entries
            threshold_ms: Threshold in milliseconds to consider a query slow
            
        Returns:
            List of slow query entries
        """
        slow_queries = []
        
        for query in queries:
            # Skip if no execution time or AQL
            if (not hasattr(query, "Query") or not query.Query or
                not hasattr(query, "ExecutionTimeMs")):
                continue
                
            # Check if execution time exceeds threshold
            execution_time = getattr(query, "ExecutionTimeMs", 0)
            if execution_time > threshold_ms:
                slow_queries.append(query)
        
        # Sort by execution time (slowest first)
        return sorted(
            slow_queries,
            key=lambda q: getattr(q, "ExecutionTimeMs", 0),
            reverse=True
        )
    
    def _extract_filter_patterns(self, queries):
        """
        Extract common filter patterns from queries.
        
        Args:
            queries: List of query history entries
            
        Returns:
            Dict mapping filter patterns to frequency
        """
        filter_patterns = {}
        
        for query in queries:
            # Skip if no AQL
            if not hasattr(query, "Query") or not query.Query:
                continue
                
            aql = query.Query
            
            # Extract FILTER statements
            filter_statements = re.findall(
                r'FILTER\s+(.+?)(?=\s+(?:SORT|LIMIT|RETURN|LET|FOR|COLLECT)|$)', 
                aql,
                re.IGNORECASE | re.DOTALL
            )
            
            for filter_stmt in filter_statements:
                # Normalize the statement (remove specific values)
                normalized = self._normalize_filter_statement(filter_stmt)
                
                if normalized:
                    if normalized not in filter_patterns:
                        filter_patterns[normalized] = {
                            "pattern": normalized,
                            "count": 0,
                            "queries": []
                        }
                    
                    filter_patterns[normalized]["count"] += 1
                    
                    # Add query to list if not already there
                    query_id = getattr(query, "QueryId", str(hash(aql)))
                    if query_id not in filter_patterns[normalized]["queries"]:
                        filter_patterns[normalized]["queries"].append(query_id)
        
        # Sort by frequency
        return dict(sorted(
            filter_patterns.items(), 
            key=lambda x: x[1]["count"], 
            reverse=True
        ))
    
    def _normalize_filter_statement(self, filter_stmt):
        """
        Normalize a filter statement by removing specific values.
        
        Args:
            filter_stmt: The filter statement to normalize
            
        Returns:
            Normalized filter statement
        """
        # Replace string literals with placeholders
        normalized = re.sub(r'"[^"]*"', '"STRING_VALUE"', filter_stmt)
        normalized = re.sub(r"'[^']*'", "'STRING_VALUE'", normalized)
        
        # Replace numeric literals with placeholders
        normalized = re.sub(r'\b\d+\b', 'NUMERIC_VALUE', normalized)
        
        # Replace date literals with placeholders
        normalized = re.sub(
            r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?\b', 
            'DATE_VALUE', 
            normalized
        )
        
        return normalized.strip()
    
    def _extract_search_patterns(self, queries):
        """
        Extract common search patterns from queries.
        
        Args:
            queries: List of query history entries
            
        Returns:
            Dict mapping search patterns to frequency
        """
        search_patterns = {}
        
        for query in queries:
            # Skip if no AQL
            if not hasattr(query, "Query") or not query.Query:
                continue
                
            aql = query.Query
            
            # Extract SEARCH statements (ArangoSearch)
            search_statements = re.findall(
                r'SEARCH\s+(.+?)(?=\s+(?:SORT|LIMIT|RETURN|LET|FOR|COLLECT)|$)', 
                aql,
                re.IGNORECASE | re.DOTALL
            )
            
            for search_stmt in search_statements:
                # Normalize the statement
                normalized = self._normalize_search_statement(search_stmt)
                
                if normalized:
                    if normalized not in search_patterns:
                        search_patterns[normalized] = {
                            "pattern": normalized,
                            "count": 0,
                            "queries": []
                        }
                    
                    search_patterns[normalized]["count"] += 1
                    
                    # Add query to list if not already there
                    query_id = getattr(query, "QueryId", str(hash(aql)))
                    if query_id not in search_patterns[normalized]["queries"]:
                        search_patterns[normalized]["queries"].append(query_id)
                        
                    # Extract collections and fields being searched
                    collections_fields = self._extract_search_collections_fields(aql, search_stmt)
                    if collections_fields:
                        if "collections_fields" not in search_patterns[normalized]:
                            search_patterns[normalized]["collections_fields"] = []
                        
                        for cf in collections_fields:
                            if cf not in search_patterns[normalized]["collections_fields"]:
                                search_patterns[normalized]["collections_fields"].append(cf)
        
        # Sort by frequency
        return dict(sorted(
            search_patterns.items(), 
            key=lambda x: x[1]["count"], 
            reverse=True
        ))
    
    def _normalize_search_statement(self, search_stmt):
        """
        Normalize a search statement by removing specific values.
        
        Args:
            search_stmt: The search statement to normalize
            
        Returns:
            Normalized search statement
        """
        # Replace string literals with placeholders
        normalized = re.sub(r'"[^"]*"', '"STRING_VALUE"', search_stmt)
        normalized = re.sub(r"'[^']*'", "'STRING_VALUE'", normalized)
        
        return normalized.strip()
    
    def _extract_search_collections_fields(self, aql, search_stmt):
        """
        Extract collections and fields being searched.
        
        Args:
            aql: The full AQL query
            search_stmt: The search statement
            
        Returns:
            List of (collection, field) tuples
        """
        collections_fields = []
        
        # Extract variable references in search statement
        var_refs = re.findall(r'(\w+)\.([a-zA-Z0-9_.]+)', search_stmt)
        
        # Match variables to collections
        for var, field in var_refs:
            # Find collection for this variable
            collection_match = re.search(
                rf'FOR\s+{var}\s+IN\s+(\w+)', 
                aql,
                re.IGNORECASE
            )
            
            if collection_match:
                collection = collection_match.group(1)
                collections_fields.append((collection, field))
        
        return collections_fields
    
    def _generate_index_recommendations(self, attribute_access, filter_patterns, slow_queries):
        """
        Generate index recommendations based on query patterns.
        
        Args:
            attribute_access: Dict mapping collection.attribute to access frequency
            filter_patterns: Dict mapping filter patterns to frequency
            slow_queries: List of slow query entries
            
        Returns:
            List of IndexRecommendation objects
        """
        recommendations = []
        
        # Identify attributes frequently used in filters
        frequent_filters = {
            key: info for key, info in attribute_access.items()
            if info["filter_count"] >= 3  # Minimum filter threshold
        }
        
        # Identify attributes frequently used in sorts
        frequent_sorts = {
            key: info for key, info in attribute_access.items()
            if info["sort_count"] >= 3  # Minimum sort threshold
        }
        
        # Process filter attributes for hash/skiplist indexes
        for key, info in frequent_filters.items():
            collection = info["collection"]
            attribute = info["attribute"]
            filter_count = info["filter_count"]
            queries = info["queries"]
            
            # Skip if we don't have collection schema info
            if collection not in self._collection_schemas:
                continue
                
            # Skip if this collection+attribute already has an index
            if self._has_index(collection, [attribute]):
                continue
                
            # Determine index type based on attribute type and usage pattern
            index_type = self._determine_index_type(collection, attribute)
            if not index_type:
                continue
            
            # For frequently queried attributes, include stored values
            # to avoid document lookups
            stored_values = []
            if filter_count >= 5:
                # Find commonly returned fields for these queries
                returned_fields = self._extract_returned_fields(collection, queries)
                if returned_fields:
                    stored_values = returned_fields[:5]  # Limit to top 5 fields
            
            # Calculate estimated impact
            estimated_impact = self._calculate_index_impact(
                collection, [attribute], index_type, queries
            )
            
            # Create recommendation
            recommendation = IndexRecommendation(
                collection=collection,
                fields=[attribute],
                index_type=index_type,
                stored_values=stored_values,
                estimated_impact=estimated_impact,
                affected_queries=queries,
                explanation=f"This index addresses {filter_count} queries that filter on {collection}.{attribute}."
            )
            
            recommendations.append(recommendation)
        
        # Process sort attributes for skiplist indexes
        for key, info in frequent_sorts.items():
            collection = info["collection"]
            attribute = info["attribute"]
            sort_count = info["sort_count"]
            queries = info["queries"]
            
            # Skip if we don't have collection schema info
            if collection not in self._collection_schemas:
                continue
                
            # Skip if this collection+attribute already has an index
            if self._has_index(collection, [attribute]):
                continue
            
            # For sort operations, we need a skiplist index
            index_type = "skiplist"
            
            # Calculate estimated impact
            estimated_impact = self._calculate_index_impact(
                collection, [attribute], index_type, queries
            )
            
            # Create recommendation
            recommendation = IndexRecommendation(
                collection=collection,
                fields=[attribute],
                index_type=index_type,
                stored_values=[],
                estimated_impact=estimated_impact,
                affected_queries=queries,
                explanation=f"This index addresses {sort_count} queries that sort on {collection}.{attribute}."
            )
            
            recommendations.append(recommendation)
        
        # Look for compound index opportunities
        compound_indexes = self._identify_compound_indexes(attribute_access)
        for fields, info in compound_indexes.items():
            collection = info["collection"]
            attribute_list = info["fields"]
            query_count = info["query_count"]
            queries = info["queries"]
            
            # Skip if we don't have collection schema info
            if collection not in self._collection_schemas:
                continue
                
            # Skip if this collection+attributes already has an index
            if self._has_index(collection, attribute_list):
                continue
            
            # For compound indexes, skiplist is usually best
            index_type = "skiplist"
            
            # For frequently queried attributes, include stored values
            stored_values = []
            if query_count >= 5:
                # Find commonly returned fields for these queries
                returned_fields = self._extract_returned_fields(collection, queries)
                if returned_fields:
                    stored_values = returned_fields[:5]  # Limit to top 5 fields
            
            # Calculate estimated impact
            estimated_impact = self._calculate_index_impact(
                collection, attribute_list, index_type, queries
            )
            
            # Create recommendation
            fields_str = ", ".join(attribute_list)
            recommendation = IndexRecommendation(
                collection=collection,
                fields=attribute_list,
                index_type=index_type,
                stored_values=stored_values,
                estimated_impact=estimated_impact,
                affected_queries=queries,
                explanation=f"This compound index addresses {query_count} queries that filter on {collection}.{fields_str}."
            )
            
            recommendations.append(recommendation)
        
        # Add index recommendations for particularly slow queries
        for query in slow_queries[:10]:  # Limit to top 10 slowest
            # Extract collection references
            aql = getattr(query, "Query", "")
            collection_matches = re.findall(r'FOR\s+(\w+)\s+IN\s+(\w+)', aql, re.IGNORECASE)
            
            for var, collection in collection_matches:
                # Skip system collections
                if collection.startswith('_'):
                    continue
                
                # Extract filter attributes for this collection
                filter_attrs = re.findall(
                    rf'FILTER\s+{var}\.([a-zA-Z0-9_.]+)\s', 
                    aql,
                    re.IGNORECASE
                )
                
                if filter_attrs:
                    # Skip if this collection+attribute already has an index
                    if self._has_index(collection, filter_attrs):
                        continue
                    
                    # Determine index type
                    index_type = self._determine_index_type(collection, filter_attrs[0])
                    if not index_type:
                        continue
                    
                    # Calculate estimated impact
                    estimated_impact = float(getattr(query, "ExecutionTimeMs", 0)) / 1000
                    
                    # Create recommendation
                    recommendation = IndexRecommendation(
                        collection=collection,
                        fields=filter_attrs,
                        index_type=index_type,
                        stored_values=[],
                        estimated_impact=estimated_impact,
                        affected_queries=[getattr(query, "QueryId", str(hash(aql)))],
                        explanation=f"This index addresses a slow query that took {estimated_impact:.2f}s to execute."
                    )
                    
                    recommendations.append(recommendation)
        
        # Sort by estimated impact and remove duplicates
        unique_recommendations = {}
        for rec in recommendations:
            key = f"{rec.collection}_{','.join(rec.fields)}_{rec.index_type}"
            if key not in unique_recommendations or rec.estimated_impact > unique_recommendations[key].estimated_impact:
                unique_recommendations[key] = rec
        
        # Return sorted list
        return sorted(
            unique_recommendations.values(),
            key=lambda r: r.estimated_impact,
            reverse=True
        )
    
    def _has_index(self, collection, fields):
        """
        Check if a collection already has an index on given fields.
        
        Args:
            collection: Collection name
            fields: List of field names
            
        Returns:
            True if an index exists, False otherwise
        """
        if collection not in self._existing_indexes:
            return False
        
        for index in self._existing_indexes[collection]:
            # Skip primary and edge indexes
            if index["type"] in ["primary", "edge"]:
                continue
                
            # Check if fields match exactly (order matters for skiplist but we'll ignore that for now)
            index_fields = index.get("fields", [])
            if set(index_fields) == set(fields):
                return True
        
        return False
    
    def _determine_index_type(self, collection, attribute):
        """
        Determine the appropriate index type for an attribute.
        
        Args:
            collection: Collection name
            attribute: Attribute name
            
        Returns:
            Index type (hash, skiplist, fulltext) or None if inappropriate
        """
        # Default to skiplist if we can't determine the type
        if collection not in self._collection_schemas:
            return "skiplist"
        
        # Navigate to the attribute type in the schema
        schema = self._collection_schemas[collection]
        parts = attribute.split('.')
        
        current = schema
        for part in parts:
            if current.get("type") == "object" and "properties" in current and part in current["properties"]:
                current = current["properties"][part]
            else:
                return "skiplist"  # Default if we can't resolve
        
        # Determine index type based on attribute type
        attr_type = current.get("type")
        
        if attr_type == "string":
            # For long text fields, consider fulltext
            # For shorter fields or identifiers, use hash
            return "hash"  # We'll use hash by default for strings
        elif attr_type in ["integer", "number"]:
            # For numeric fields, use skiplist for range queries
            return "skiplist"
        elif attr_type == "boolean":
            # Hash is better for boolean fields
            return "hash"
        else:
            # Default to skiplist for unknown types
            return "skiplist"
    
    def _extract_returned_fields(self, collection, query_ids, max_fields=5):
        """
        Extract commonly returned fields for a set of queries.
        
        Args:
            collection: Collection name
            query_ids: List of query IDs
            max_fields: Maximum number of fields to return
            
        Returns:
            List of field names
        """
        field_counts = {}
        
        # Get the queries
        for query_id in query_ids:
            query = self.query_history.get_query_by_id(query_id)
            if not query or not hasattr(query, "Query"):
                continue
                
            aql = query.Query
            
            # Extract RETURN statement
            return_matches = re.findall(
                r'RETURN\s+(.+?)(?=\s+(?:LIMIT|FOR|COLLECT|$))', 
                aql,
                re.IGNORECASE | re.DOTALL
            )
            
            for return_stmt in return_matches:
                # Look for field references that match this collection
                collection_vars = {}
                
                # Find variables bound to this collection
                var_matches = re.findall(
                    rf'FOR\s+(\w+)\s+IN\s+{collection}', 
                    aql,
                    re.IGNORECASE
                )
                
                for var in var_matches:
                    collection_vars[var] = collection
                
                # Extract fields referenced in the return statement
                for var in collection_vars:
                    field_matches = re.findall(
                        rf'{var}\.([a-zA-Z0-9_.]+)', 
                        return_stmt,
                        re.IGNORECASE
                    )
                    
                    for field in field_matches:
                        if field not in field_counts:
                            field_counts[field] = 0
                        field_counts[field] += 1
        
        # Return top fields
        return [
            field for field, count in sorted(
                field_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:max_fields]
        ]
    
    def _identify_compound_indexes(self, attribute_access):
        """
        Identify opportunities for compound indexes.
        
        Args:
            attribute_access: Dict mapping collection.attribute to access frequency
            
        Returns:
            Dict mapping compound index fields to info
        """
        # Group attributes by collection and query
        collection_query_attrs = {}
        
        for key, info in attribute_access.items():
            collection = info["collection"]
            attribute = info["attribute"]
            
            if collection not in collection_query_attrs:
                collection_query_attrs[collection] = {}
            
            for query_id in info["queries"]:
                if query_id not in collection_query_attrs[collection]:
                    collection_query_attrs[collection][query_id] = []
                    
                collection_query_attrs[collection][query_id].append(attribute)
        
        # Look for queries that access multiple attributes in the same collection
        compound_candidates = {}
        
        for collection, query_attrs in collection_query_attrs.items():
            # Count attribute combinations
            attr_combinations = {}
            
            for query_id, attrs in query_attrs.items():
                if len(attrs) > 1:
                    # Sort attributes to create a consistent key
                    key = tuple(sorted(attrs))
                    
                    if key not in attr_combinations:
                        attr_combinations[key] = {
                            "fields": list(key),
                            "collection": collection,
                            "query_count": 0,
                            "queries": []
                        }
                    
                    attr_combinations[key]["query_count"] += 1
                    attr_combinations[key]["queries"].append(query_id)
            
            # Add promising combinations
            for key, info in attr_combinations.items():
                if info["query_count"] >= 3:  # Minimum threshold
                    compound_candidates[key] = info
        
        return compound_candidates
    
    def _calculate_index_impact(self, collection, fields, index_type, query_ids):
        """
        Calculate the estimated impact of an index.
        
        Args:
            collection: Collection name
            fields: List of field names
            index_type: Type of index
            query_ids: List of query IDs that would benefit
            
        Returns:
            Estimated impact score
        """
        impact = 0.0
        
        # Get the queries
        for query_id in query_ids:
            query = self.query_history.get_query_by_id(query_id)
            if not query:
                continue
                
            # Use execution time as a factor
            exec_time = getattr(query, "ExecutionTimeMs", 0) / 1000  # Convert to seconds
            
            # More weight for longer queries
            impact += exec_time
        
        # Add bonus for fields with frequent access
        for field in fields:
            key = f"{collection}.{field}"
            if key in self._extract_attribute_access([]):
                info = self._extract_attribute_access([])[key]
                impact += info["total_count"] * 0.1
        
        # Adjust for index type (persistent indexes may have higher maintenance costs)
        if index_type == "persistent":
            impact *= 0.9
        
        # Adjust for number of fields (compound indexes are more specific)
        if len(fields) > 1:
            impact *= 1.2
        
        return impact
    
    def _generate_view_recommendations(self, search_patterns, slow_queries):
        """
        Generate ArangoSearch view recommendations.
        
        Args:
            search_patterns: Dict mapping search patterns to frequency
            slow_queries: List of slow query entries
            
        Returns:
            List of ViewRecommendation objects
        """
        recommendations = []
        
        # Check if there are search patterns
        if not search_patterns:
            return recommendations
        
        # Group search patterns by collection
        collection_patterns = {}
        
        for pattern, info in search_patterns.items():
            if "collections_fields" not in info:
                continue
                
            for collection, field in info["collections_fields"]:
                if collection not in collection_patterns:
                    collection_patterns[collection] = {
                        "fields": set(),
                        "count": 0,
                        "queries": []
                    }
                
                collection_patterns[collection]["fields"].add(field)
                collection_patterns[collection]["count"] += info["count"]
                collection_patterns[collection]["queries"].extend(info["queries"])
        
        # Create view recommendations for collections with significant search usage
        for collection, info in collection_patterns.items():
            # Skip if fewer than 3 searches
            if info["count"] < 3:
                continue
                
            # Skip if collection doesn't exist
            if collection not in self._collection_schemas:
                continue
            
            # Skip if a view already exists for this collection
            if self._has_view_for_collection(collection):
                continue
            
            # Create view name
            view_name = f"{collection}_view"
            
            # Prepare fields
            fields_dict = {collection: list(info["fields"])}
            
            # Calculate estimated impact
            queries = list(set(info["queries"]))
            estimated_impact = self._calculate_view_impact(collection, list(info["fields"]), queries)
            
            # Create recommendation
            recommendation = ViewRecommendation(
                name=view_name,
                collections=[collection],
                fields=fields_dict,
                estimated_impact=estimated_impact,
                affected_queries=queries,
                explanation=f"This view addresses {info['count']} searches on {collection} collection."
            )
            
            recommendations.append(recommendation)
        
        # Check for multi-collection view opportunities
        if len(collection_patterns) > 1:
            # Find collections that are often searched together
            collection_pairs = {}
            
            for pattern, info in search_patterns.items():
                if "collections_fields" not in info or len(set(cf[0] for cf in info["collections_fields"])) <= 1:
                    continue
                
                # Get unique collections in this pattern
                collections = list(set(cf[0] for cf in info["collections_fields"]))
                
                # Create collection pair key (sorted for consistency)
                key = tuple(sorted(collections))
                
                if key not in collection_pairs:
                    collection_pairs[key] = {
                        "collections": collections,
                        "fields": {},
                        "count": 0,
                        "queries": []
                    }
                    
                    # Initialize fields dict
                    for col in collections:
                        collection_pairs[key]["fields"][col] = set()
                
                # Add fields for each collection
                for collection, field in info["collections_fields"]:
                    if collection in collection_pairs[key]["fields"]:
                        collection_pairs[key]["fields"][collection].add(field)
                
                collection_pairs[key]["count"] += info["count"]
                collection_pairs[key]["queries"].extend(info["queries"])
            
            # Create multi-collection view recommendations
            for key, info in collection_pairs.items():
                # Skip if fewer than 2 searches
                if info["count"] < 2:
                    continue
                
                # Create view name
                view_name = "_".join(info["collections"]) + "_view"
                
                # Prepare fields
                fields_dict = {
                    col: list(fields) for col, fields in info["fields"].items()
                }
                
                # Calculate estimated impact
                queries = list(set(info["queries"]))
                collections = info["collections"]
                all_fields = [f for fields in info["fields"].values() for f in fields]
                estimated_impact = self._calculate_view_impact(collections, all_fields, queries)
                
                # Create recommendation
                recommendation = ViewRecommendation(
                    name=view_name,
                    collections=collections,
                    fields=fields_dict,
                    estimated_impact=estimated_impact,
                    affected_queries=queries,
                    explanation=f"This multi-collection view addresses {info['count']} searches across {', '.join(collections)}."
                )
                
                recommendations.append(recommendation)
        
        # Sort by estimated impact
        return sorted(
            recommendations,
            key=lambda r: r.estimated_impact,
            reverse=True
        )
    
    def _has_view_for_collection(self, collection):
        """
        Check if a view already exists for a collection.
        
        Args:
            collection: Collection name
            
        Returns:
            True if a view exists, False otherwise
        """
        for view_name, view_info in self._existing_views.items():
            # Check if this is an ArangoSearch view
            if view_info.get("type") != "arangosearch":
                continue
                
            # Check if this view includes the collection
            links = view_info.get("links", {})
            if collection in links:
                return True
        
        return False
    
    def _calculate_view_impact(self, collections, fields, query_ids):
        """
        Calculate the estimated impact of a view.
        
        Args:
            collections: Collection name or list of names
            fields: List of field names
            query_ids: List of query IDs that would benefit
            
        Returns:
            Estimated impact score
        """
        impact = 0.0
        
        if isinstance(collections, str):
            collections = [collections]
        
        # Get the queries
        for query_id in query_ids:
            query = self.query_history.get_query_by_id(query_id)
            if not query:
                continue
                
            # Use execution time as a factor
            exec_time = getattr(query, "ExecutionTimeMs", 0) / 1000  # Convert to seconds
            
            # Full-text search is typically much slower than index lookups,
            # so the potential speedup is higher
            impact += exec_time * 2
        
        # Adjust for number of collections (multi-collection views are more powerful)
        if len(collections) > 1:
            impact *= 1.5
        
        # Adjust for number of fields
        impact *= min(1 + len(fields) * 0.1, 2.0)
        
        return impact
    
    def _generate_query_optimizations(self, slow_queries):
        """
        Generate query optimization recommendations.
        
        Args:
            slow_queries: List of slow query entries
            
        Returns:
            List of QueryOptimization objects
        """
        recommendations = []
        
        for query in slow_queries[:5]:  # Limit to top 5 slowest
            aql = getattr(query, "Query", "")
            
            # Skip short queries
            if len(aql) < 50:
                continue
                
            # Look for optimization opportunities
            optimizations = []
            
            # Check for FILTER after FOR without index
            if re.search(r'FOR\s+\w+\s+IN\s+\w+\s+FILTER', aql, re.IGNORECASE):
                optimizations.append({
                    "type": "add_index_for_filter",
                    "description": "Add an index for the FILTER condition"
                })
            
            # Check for nested loops
            if aql.count("FOR ") > 1:
                optimizations.append({
                    "type": "optimize_nested_loops",
                    "description": "Consider using JOINs or subqueries instead of nested loops"
                })
            
            # Check for COLLECT without index
            if "COLLECT " in aql:
                optimizations.append({
                    "type": "add_index_for_collect",
                    "description": "Add an index for the COLLECT keys"
                })
            
            # Check for large result sets without LIMIT
            if "LIMIT " not in aql:
                optimizations.append({
                    "type": "add_limit",
                    "description": "Add LIMIT to avoid large result sets"
                })
            
            # Create optimization recommendation for each opportunity
            for opt in optimizations:
                # Here we would ideally generate an optimized version of the query
                # Since that requires detailed query analysis, we'll just flag it for now
                
                # Calculate estimated speedup
                exec_time = getattr(query, "ExecutionTimeMs", 0) / 1000  # Convert to seconds
                estimated_speedup = 2.0  # Assume 2x speedup as a baseline
                
                recommendation = QueryOptimization(
                    original_query=aql,
                    optimized_query=aql,  # Placeholder; we're not actually rewriting the query
                    optimization_type=opt["type"],
                    estimated_speedup=estimated_speedup,
                    explanation=f"{opt['description']} for query that took {exec_time:.2f}s to execute."
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def create_index(self, recommendation):
        """
        Create an index based on a recommendation.
        
        Args:
            recommendation: IndexRecommendation object
            
        Returns:
            Dict with creation result
        """
        # Skip if already created
        if recommendation.created:
            return {"status": "already_created", "index_id": recommendation.index_id}
        
        try:
            collection_name = recommendation.collection
            
            # Get the collection
            collection = self.db.collection(collection_name)
            
            # Create the index
            cmd = recommendation.get_creation_command()
            result = collection.add_index(cmd)
            
            # Update recommendation object
            recommendation.created = True
            recommendation.creation_time = datetime.now(timezone.utc)
            recommendation.index_id = result["id"]
            
            # Log the optimization
            self._log_optimization(
                "index",
                recommendation.short_description(),
                None,  # We don't know the before performance yet
                None,  # We don't know the after performance yet
                recommendation.model_dump()
            )
            
            # Refresh existing indexes
            self._existing_indexes[collection_name] = collection.indexes()
            
            return {
                "status": "success",
                "message": f"Created {recommendation.index_type} index on {collection_name}",
                "index_id": result["id"],
                "recommendation": recommendation.model_dump()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creating index: {str(e)}",
                "recommendation": recommendation.model_dump()
            }
    
    def create_view(self, recommendation):
        """
        Create a view based on a recommendation.
        
        Args:
            recommendation: ViewRecommendation object
            
        Returns:
            Dict with creation result
        """
        # Skip if already created
        if recommendation.created:
            return {"status": "already_created", "view_id": recommendation.view_id}
        
        try:
            # Create the view
            cmd = recommendation.get_creation_command()
            result = self.db.create_view(cmd["name"], cmd["type"], cmd.get("properties", {}))
            
            # Update recommendation object
            recommendation.created = True
            recommendation.creation_time = datetime.now(timezone.utc)
            recommendation.view_id = result["id"]
            
            # Log the optimization
            self._log_optimization(
                "view",
                recommendation.short_description(),
                None,  # We don't know the before performance yet
                None,  # We don't know the after performance yet
                recommendation.model_dump()
            )
            
            # Refresh existing views
            self._existing_views = {view: self.db.view(view) for view in self.db.views()}
            
            return {
                "status": "success",
                "message": f"Created view '{cmd['name']}'",
                "view_id": result["id"],
                "recommendation": recommendation.model_dump()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creating view: {str(e)}",
                "recommendation": recommendation.model_dump()
            }
    
    def evaluate_optimization(self, optimization_id, affected_queries):
        """
        Evaluate the impact of an optimization.
        
        Args:
            optimization_id: ID of the optimization to evaluate
            affected_queries: List of query IDs to benchmark
            
        Returns:
            Dict with evaluation results
        """
        # Find the optimization log
        optimization_log = None
        for log in self.optimization_logs:
            if log.optimization_id == optimization_id:
                optimization_log = log
                break
                
        if not optimization_log:
            return {"status": "error", "message": "Optimization not found"}
        
        # Collect before/after performance data
        before_performance = optimization_log.performance_before
        after_performances = []
        
        # Execute each affected query to measure performance
        for query_id in affected_queries:
            query = self.query_history.get_query_by_id(query_id)
            if not query or not hasattr(query, "Query"):
                continue
                
            aql = query.Query
            bind_vars = getattr(query, "BindVars", {})
            
            try:
                # Execute query and measure time
                start_time = time.time()
                self.db.aql.execute(aql, bind_vars=bind_vars)
                end_time = time.time()
                
                # Calculate execution time
                exec_time = (end_time - start_time) * 1000  # Convert to ms
                after_performances.append(exec_time)
                
            except Exception as e:
                self.logger.error(f"Error executing query {query_id}: {e}")
        
        # Calculate average performance after optimization
        if after_performances:
            after_performance = sum(after_performances) / len(after_performances)
            
            # Calculate impact (speedup factor)
            impact = before_performance / after_performance if after_performance > 0 else 0
            
            # Update optimization log
            optimization_log.performance_after = after_performance
            optimization_log.impact = impact
            
            return {
                "status": "success",
                "before_performance": before_performance,
                "after_performance": after_performance,
                "speedup_factor": impact,
                "evaluation": "Significant improvement" if impact > 1.5 else
                             "Moderate improvement" if impact > 1.1 else
                             "Minimal improvement" if impact > 1.0 else
                             "No improvement" if impact >= 0.9 else
                             "Performance regression"
            }
        
        return {"status": "error", "message": "No queries were successfully executed"}
    
    def _log_optimization(self, opt_type, description, perf_before, perf_after, details):
        """
        Log an applied optimization.
        
        Args:
            opt_type: Type of optimization
            description: Description of the optimization
            perf_before: Performance metric before optimization
            perf_after: Performance metric after optimization
            details: Detailed information about the optimization
            
        Returns:
            The created log entry
        """
        log = OptimizationLog(
            optimization_type=opt_type,
            description=description,
            performance_before=perf_before if perf_before is not None else 0.0,
            performance_after=perf_after,
            impact=perf_after / perf_before if perf_before and perf_after else None,
            details=details
        )
        
        self.optimization_logs.append(log)
        
        # Add an insight to the Archivist memory
        if self.memory:
            self.memory.add_insight(
                category="database_optimization",
                insight=f"Applied {opt_type} optimization: {description}",
                confidence=0.9
            )
        
        return log
    
    def get_ongoing_optimizations(self):
        """
        Get a summary of ongoing optimization efforts.
        
        Returns:
            Dict with optimization statistics
        """
        return {
            "total_optimizations": len(self.optimization_logs),
            "index_optimizations": len([log for log in self.optimization_logs if log.optimization_type == "index"]),
            "view_optimizations": len([log for log in self.optimization_logs if log.optimization_type == "view"]),
            "query_optimizations": len([log for log in self.optimization_logs if log.optimization_type == "query"]),
            "successful_optimizations": len([log for log in self.optimization_logs if log.impact and log.impact > 1.1]),
            "recent_optimizations": [
                {
                    "type": log.optimization_type,
                    "description": log.description,
                    "applied_at": log.applied_at,
                    "impact": log.impact
                }
                for log in sorted(self.optimization_logs, key=lambda x: x.applied_at, reverse=True)[:5]
            ]
        }


def main():
    """Test the database optimizer."""
    from Indaleko import Indaleko
    
    # Connect to database
    indaleko = Indaleko()
    indaleko.connect()
    
    # Create optimizer
    optimizer = DatabaseOptimizer(indaleko.db)
    
    # Analyze query patterns
    analysis = optimizer.analyze_query_patterns()
    
    # Print index recommendations
    print("\nIndex Recommendations:")
    for i, rec in enumerate(analysis.get("index_recommendations", []), 1):
        print(f"{i}. {rec.short_description()}")
        print(f"   Impact: {rec.estimated_impact:.2f}")
        print(f"   Explanation: {rec.explanation}")
    
    # Print view recommendations
    print("\nView Recommendations:")
    for i, rec in enumerate(analysis.get("view_recommendations", []), 1):
        print(f"{i}. {rec.short_description()}")
        print(f"   Impact: {rec.estimated_impact:.2f}")
        print(f"   Explanation: {rec.explanation}")
    
    # Print query optimizations
    print("\nQuery Optimizations:")
    for i, rec in enumerate(analysis.get("query_optimizations", []), 1):
        print(f"{i}. {rec.short_description()}")
        print(f"   Speedup: {rec.estimated_speedup:.2f}x")
        print(f"   Explanation: {rec.explanation}")


if __name__ == "__main__":
    main()