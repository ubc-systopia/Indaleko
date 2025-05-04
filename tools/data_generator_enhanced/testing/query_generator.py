#!/usr/bin/env python3
"""Query generation for testing search functionality.

This module provides utilities for generating AQL queries based on
natural language queries and metadata patterns.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from jinja2 import Template


class QueryTemplate:
    """Template for generating AQL queries."""

    def __init__(self, template: str, description: str = ""):
        """Initialize a query template.

        Args:
            template: Jinja2 template string for the query
            description: Optional description of the template
        """
        self.template_string = template
        self.description = description
        self.template = Template(template)
        self.logger = logging.getLogger(self.__class__.__name__)

    def render(self, **kwargs: Any) -> str:
        """Render the template with the given parameters.

        Args:
            **kwargs: Parameters to substitute in the template

        Returns:
            Rendered query string
        """
        try:
            return self.template.render(**kwargs)
        except Exception as e:
            self.logger.error(f"Error rendering template: {e}")
            raise ValueError(f"Failed to render query template: {e}") from e


class QueryGenerator:
    """Generator for AQL queries from natural language queries."""

    # Common query templates for different patterns
    TEMPLATES = {
        "file_by_name": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER LIKE(doc.Name, @name_pattern, true)
            RETURN doc
            """,
            "Find files by name pattern"
        ),
        "file_by_extension": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER LIKE(doc.Name, @extension_pattern, true)
            RETURN doc
            """,
            "Find files by extension"
        ),
        "file_by_size_range": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.Size >= @min_size AND doc.Size <= @max_size
            RETURN doc
            """,
            "Find files by size range"
        ),
        "file_by_time_range": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.ModificationTime >= @start_time AND doc.ModificationTime <= @end_time
            RETURN doc
            """,
            "Find files by modification time range"
        ),
        "file_with_semantic": QueryTemplate(
            """
            FOR sem IN SemanticData
            FILTER sem.@attribute == @value
            FOR doc IN Objects
            FILTER doc._key == sem.Object
            RETURN doc
            """,
            "Find files by semantic attribute"
        ),
        "file_with_activity": QueryTemplate(
            """
            FOR act IN @@activity_collection
            FILTER act.@attribute == @value
            FOR doc IN Objects
            FILTER doc._key == act.Object
            RETURN doc
            """,
            "Find files by activity context"
        ),
        "file_with_location": QueryTemplate(
            """
            FOR loc IN ActivityContext_GeoLocation
            FILTER GEO_DISTANCE(loc.Latitude, loc.Longitude, @lat, @lon) <= @radius
            FOR doc IN Objects
            FILTER doc._key == loc.Object
            RETURN doc
            """,
            "Find files by geographic location"
        ),
    }

    def __init__(self, llm_connector: Optional[Any] = None):
        """Initialize a query generator.

        Args:
            llm_connector: Optional LLM connector for advanced NL parsing
        """
        self.llm_connector = llm_connector
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_from_nl(self, nl_query: str, metadata_context: Dict[str, Any]) -> str:
        """Generate an AQL query from a natural language query.

        Args:
            nl_query: Natural language query
            metadata_context: Metadata context for substitution

        Returns:
            Generated AQL query
        """
        # This is a simplified version that doesn't actually use an LLM
        # In a real implementation, we would use the LLM connector to parse the NL query

        # For now, use pattern matching to identify query type and parameters
        query_type, params = self._parse_nl_query(nl_query, metadata_context)

        if query_type in self.TEMPLATES:
            template = self.TEMPLATES[query_type]
            return template.render(**params)
        else:
            self.logger.warning(f"No template found for query type: {query_type}")
            # Fall back to a simple query
            return self._generate_fallback_query(nl_query, metadata_context)

    def _parse_nl_query(self, nl_query: str, metadata_context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Parse a natural language query to identify the query type and parameters.

        Args:
            nl_query: Natural language query
            metadata_context: Metadata context for substitution

        Returns:
            Tuple of (query_type, parameters)
        """
        nl_query = nl_query.lower()

        # Simple pattern matching for demonstration
        if "by name" in nl_query or "named" in nl_query or "filename" in nl_query:
            pattern = metadata_context.get("name_pattern", "%test%")
            return "file_by_name", {"name_pattern": pattern}

        elif "extension" in nl_query or "file type" in nl_query:
            extension = metadata_context.get("extension", ".txt")
            pattern = f"%{extension}"
            return "file_by_extension", {"extension_pattern": pattern}

        elif "size" in nl_query or "large" in nl_query or "small" in nl_query:
            min_size = metadata_context.get("min_size", 0)
            max_size = metadata_context.get("max_size", 1_000_000_000)
            return "file_by_size_range", {"min_size": min_size, "max_size": max_size}

        elif "recent" in nl_query or "modified" in nl_query or "created" in nl_query or "last week" in nl_query:
            end_time = datetime.now().timestamp()
            start_time = (datetime.now() - timedelta(days=7)).timestamp()

            if "last month" in nl_query:
                start_time = (datetime.now() - timedelta(days=30)).timestamp()
            elif "yesterday" in nl_query:
                start_time = (datetime.now() - timedelta(days=1)).timestamp()

            return "file_by_time_range", {"start_time": start_time, "end_time": end_time}

        elif "location" in nl_query or "near" in nl_query or "at" in nl_query:
            lat = metadata_context.get("latitude", 37.7749)
            lon = metadata_context.get("longitude", -122.4194)
            radius = metadata_context.get("radius", 10000)  # meters
            return "file_with_location", {"lat": lat, "lon": lon, "radius": radius}

        # Default to a simple name search
        return "file_by_name", {"name_pattern": "%"}

    def _generate_fallback_query(self, nl_query: str, metadata_context: Dict[str, Any]) -> str:
        """Generate a fallback query when no specific template matches.

        Args:
            nl_query: Natural language query
            metadata_context: Metadata context for substitution

        Returns:
            Fallback AQL query
        """
        return """
        FOR doc IN Objects
        LIMIT 100
        RETURN doc
        """

    def generate_from_criteria(self, criteria: Dict[str, Any]) -> str:
        """Generate an AQL query from criteria.

        Args:
            criteria: Dictionary of criteria for the query

        Returns:
            Generated AQL query
        """
        query_parts = []

        # Start with basic FOR clause
        query = "FOR doc IN Objects\n"

        # Add filters based on criteria
        filters = []

        if "name" in criteria:
            filters.append(f"LIKE(doc.Name, '{criteria['name']}', true)")

        if "extension" in criteria:
            ext = criteria["extension"]
            if not ext.startswith("."):
                ext = f".{ext}"
            filters.append(f"LIKE(doc.Name, '%{ext}', true)")

        if "min_size" in criteria and "max_size" in criteria:
            filters.append(f"doc.Size >= {criteria['min_size']} AND doc.Size <= {criteria['max_size']}")
        elif "min_size" in criteria:
            filters.append(f"doc.Size >= {criteria['min_size']}")
        elif "max_size" in criteria:
            filters.append(f"doc.Size <= {criteria['max_size']}")

        if "start_time" in criteria and "end_time" in criteria:
            filters.append(f"doc.ModificationTime >= {criteria['start_time']} AND doc.ModificationTime <= {criteria['end_time']}")

        # Add FILTER clause if there are filters
        if filters:
            query += f"FILTER {' AND '.join(filters)}\n"

        # Add LIMIT and RETURN clauses
        limit = criteria.get("limit", 100)
        query += f"LIMIT {limit}\n"
        query += "RETURN doc"

        return query
