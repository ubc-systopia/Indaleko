#!/usr/bin/env python3
"""Enhanced Query Generator for model-based data testing.

This module provides an improved query generator specifically designed to work with
model-based data formats and support advanced query patterns.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from jinja2 import Template

# Import the base query generator
from .query_generator import QueryGenerator, QueryTemplate


class ModelBasedQueryGenerator(QueryGenerator):
    """Enhanced query generator for model-based data testing."""

    # Additional templates specific to model-based data
    MODEL_TEMPLATES = {
        # Storage object queries
        "model_file_by_name": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER LIKE(doc.Label, @name_pattern, true)
            RETURN doc
            """,
            "Find files by name pattern (model-based)"
        ),
        "model_file_by_extension": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.Record.Attributes.Extension == @extension
            RETURN doc
            """,
            "Find files by extension (model-based)"
        ),
        "model_file_by_path": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER LIKE(doc.Record.Attributes.Path, @path_pattern, true)
            RETURN doc
            """,
            "Find files by path pattern (model-based)"
        ),
        "model_file_by_size_range": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.Record.Attributes.Size >= @min_size AND doc.Record.Attributes.Size <= @max_size
            RETURN doc
            """,
            "Find files by size range (model-based)"
        ),
        "model_file_by_time_range": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.Timestamps[0].Value >= @start_time AND doc.Timestamps[0].Value <= @end_time
            RETURN doc
            """,
            "Find files by modification time range (model-based)"
        ),

        # Semantic metadata queries
        "model_file_by_mime_type": QueryTemplate(
            """
            FOR sem IN SemanticMetadata
            FILTER sem.Record.Attributes.MimeType == @mime_type
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == sem.ObjectIdentifier
            RETURN doc
            """,
            "Find files by MIME type (model-based)"
        ),
        "model_file_by_checksum": QueryTemplate(
            """
            FOR sem IN SemanticMetadata
            FILTER sem.Record.Attributes.Checksum == @checksum
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == sem.ObjectIdentifier
            RETURN doc
            """,
            "Find files by checksum (model-based)"
        ),
        "model_file_by_content": QueryTemplate(
            """
            FOR sem IN SemanticMetadata
            FILTER LIKE(sem.Content.Extract, @content_pattern, true)
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == sem.ObjectIdentifier
            RETURN doc
            """,
            "Find files by content (model-based)"
        ),

        # Activity queries
        "model_file_by_activity_type": QueryTemplate(
            """
            FOR act IN Activities
            FILTER act.Record.ActivityType == @activity_type
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == act.Record.ObjectIdentifier
            RETURN doc
            """,
            "Find files by activity type (model-based)"
        ),
        "model_file_by_activity_time": QueryTemplate(
            """
            FOR act IN Activities
            FILTER act.Timestamp >= @start_time AND act.Timestamp <= @end_time
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == act.Record.ObjectIdentifier
            RETURN doc
            """,
            "Find files by activity time (model-based)"
        ),
        "model_file_by_user": QueryTemplate(
            """
            FOR act IN Activities
            FILTER act.Record.UserID == @user_id
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == act.Record.ObjectIdentifier
            RETURN doc
            """,
            "Find files by user (model-based)"
        ),

        # Relationship queries
        "model_related_files": QueryTemplate(
            """
            FOR rel IN Relationships
            FILTER rel._from == @object_id OR rel._to == @object_id
            LET related_id = rel._from == @object_id ? rel._to : rel._from
            FOR doc IN Objects
            FILTER doc._id == related_id
            RETURN doc
            """,
            "Find files related to a given file (model-based)"
        ),
        "model_files_by_relationship_type": QueryTemplate(
            """
            FOR rel IN Relationships
            FILTER rel.Record.RelationshipType == @relationship_type
            FOR doc IN Objects
            FILTER doc._id == rel._from OR doc._id == rel._to
            RETURN doc
            """,
            "Find files with a specific relationship type (model-based)"
        ),

        # Machine config queries
        "model_files_by_machine": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.Record.MachineID == @machine_id
            RETURN doc
            """,
            "Find files from a specific machine (model-based)"
        ),

        # Combined queries
        "model_semantic_and_activity": QueryTemplate(
            """
            FOR sem IN SemanticMetadata
            FILTER sem.Record.Attributes.MimeType == @mime_type
            FOR act IN Activities
            FILTER act.Record.ActivityType == @activity_type
            FILTER act.Record.ObjectIdentifier == sem.ObjectIdentifier
            FOR doc IN Objects
            FILTER doc.ObjectIdentifier == sem.ObjectIdentifier
            RETURN doc
            """,
            "Find files with both semantic and activity criteria (model-based)"
        ),
        "model_recent_large_files": QueryTemplate(
            """
            FOR doc IN Objects
            FILTER doc.Record.Attributes.Size >= @min_size
            LET timestamp_entry = (
                FOR ts IN doc.Timestamps
                FILTER ts.Label == "Modified"
                LIMIT 1
                RETURN ts
            )[0]
            FILTER timestamp_entry.Value >= @start_time
            RETURN doc
            """,
            "Find recently modified large files (model-based)"
        ),
    }

    def __init__(self, llm_connector: Optional[Any] = None, use_model_templates: bool = True):
        """Initialize an enhanced query generator.

        Args:
            llm_connector: Optional LLM connector for advanced NL parsing
            use_model_templates: Whether to use model-based templates by default
        """
        super().__init__(llm_connector)

        # Add model-based templates to the templates dictionary
        self.TEMPLATES.update(self.MODEL_TEMPLATES)

        # Flag to prefer model-based templates
        self.use_model_templates = use_model_templates

    def generate_from_nl(self, nl_query: str, metadata_context: Dict[str, Any]) -> str:
        """Generate an AQL query from a natural language query.

        Args:
            nl_query: Natural language query
            metadata_context: Metadata context for substitution

        Returns:
            Generated AQL query
        """
        # Try to use LLM if available
        if self.llm_connector and metadata_context.get("use_llm", True):
            try:
                return self._generate_from_llm(nl_query, metadata_context)
            except Exception as e:
                self.logger.warning(f"Error generating query with LLM: {e}")
                # Fall back to pattern matching

        # Use pattern matching
        query_type, params = self._parse_model_query(nl_query, metadata_context)

        if query_type in self.TEMPLATES:
            template = self.TEMPLATES[query_type]
            return template.render(**params)
        else:
            self.logger.warning(f"No template found for query type: {query_type}")
            # Fall back to a simple query
            return self._generate_fallback_query(nl_query, metadata_context)

    def _generate_from_llm(self, nl_query: str, metadata_context: Dict[str, Any]) -> str:
        """Generate a query using an LLM.

        Args:
            nl_query: Natural language query
            metadata_context: Metadata context for substitution

        Returns:
            Generated AQL query
        """
        if not self.llm_connector:
            raise ValueError("No LLM connector available")

        # Construct the prompt
        prompt = f"""
        Generate an ArangoDB AQL query based on the following natural language query:

        "{nl_query}"

        The database contains the following collections:
        - Objects: Storage metadata with fields:
          - ObjectIdentifier: unique ID
          - Label: file name
          - Record.Attributes: file attributes (Size, Path, Extension, etc.)
          - Timestamps: array of timestamp objects with Label and Value fields

        - SemanticMetadata: Semantic information with fields:
          - ObjectIdentifier: refers to Objects
          - Record.Attributes: semantic attributes (MimeType, Checksum, etc.)
          - Content.Extract: extracted content text

        - Activities: Activity metadata with fields:
          - Record.ActivityType: type of activity (e.g., FileAccess, FileEdit)
          - Record.ObjectIdentifier: refers to Objects
          - Record.UserID: user who performed the activity
          - Timestamp: when the activity occurred

        - Relationships: Connections between objects with fields:
          - _from: source object ID
          - _to: target object ID
          - Record.RelationshipType: type of relationship

        Return only the AQL query without explanations or additional text.
        """

        # Call the LLM
        response = self.llm_connector.generate(prompt)

        # Extract the AQL query
        query_match = re.search(r'```(?:aql)?\s*(FOR.*?)```', response, re.DOTALL)
        if query_match:
            return query_match.group(1).strip()
        else:
            return response.strip()

    def _parse_model_query(self, nl_query: str, metadata_context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Parse a natural language query for model-based templates.

        Args:
            nl_query: Natural language query
            metadata_context: Metadata context for substitution

        Returns:
            Tuple of (query_type, parameters)
        """
        nl_query = nl_query.lower()

        # Determine if we should prefer model-based templates
        prefer_model = self.use_model_templates or metadata_context.get("use_model_templates", False)

        # Pattern matching for model-based templates
        if "mime" in nl_query or "media type" in nl_query or "content type" in nl_query:
            mime_type = metadata_context.get("mime_type", "application/pdf")
            return "model_file_by_mime_type", {"mime_type": mime_type}

        elif "content" in nl_query or "containing" in nl_query or "text" in nl_query:
            content_pattern = metadata_context.get("content_pattern", "%report%")
            return "model_file_by_content", {"content_pattern": content_pattern}

        elif "activity" in nl_query or "edited" in nl_query or "accessed" in nl_query:
            activity_type = "FileEdit" if "edit" in nl_query else "FileAccess"
            return "model_file_by_activity_type", {"activity_type": activity_type}

        elif "user" in nl_query or "by me" in nl_query or "someone" in nl_query:
            user_id = metadata_context.get("user_id", "user123")
            return "model_file_by_user", {"user_id": user_id}

        elif "related" in nl_query or "connected" in nl_query or "linked" in nl_query:
            object_id = metadata_context.get("object_id", "Objects/123456")
            return "model_related_files", {"object_id": object_id}

        elif "machine" in nl_query or "device" in nl_query or "computer" in nl_query:
            machine_id = metadata_context.get("machine_id", "machine123")
            return "model_files_by_machine", {"machine_id": machine_id}

        # Use basic patterns with model-based templates if preferred
        elif "by name" in nl_query or "named" in nl_query or "filename" in nl_query:
            pattern = metadata_context.get("name_pattern", "%test%")
            return "model_file_by_name" if prefer_model else "file_by_name", {"name_pattern": pattern}

        elif "extension" in nl_query or "file type" in nl_query:
            extension = metadata_context.get("extension", ".txt")
            if prefer_model:
                # Remove leading dot for model-based template
                if extension.startswith("."):
                    extension = extension[1:]
                return "model_file_by_extension", {"extension": extension}
            else:
                pattern = f"%{extension}"
                return "file_by_extension", {"extension_pattern": pattern}

        elif "path" in nl_query or "folder" in nl_query or "directory" in nl_query:
            path_pattern = metadata_context.get("path_pattern", "%/Documents/%")
            return "model_file_by_path", {"path_pattern": path_pattern}

        elif "size" in nl_query or "large" in nl_query or "small" in nl_query:
            min_size = metadata_context.get("min_size", 0)
            max_size = metadata_context.get("max_size", 1_000_000_000)
            return "model_file_by_size_range" if prefer_model else "file_by_size_range", {
                "min_size": min_size,
                "max_size": max_size
            }

        elif "recent" in nl_query or "modified" in nl_query or "created" in nl_query or "last week" in nl_query:
            end_time = datetime.now(timezone.utc).isoformat()
            if "last month" in nl_query:
                start_time = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            elif "yesterday" in nl_query:
                start_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            else:
                start_time = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

            return "model_file_by_time_range" if prefer_model else "file_by_time_range", {
                "start_time": start_time,
                "end_time": end_time
            }

        # Combined queries
        if ("recent" in nl_query or "modified" in nl_query) and ("large" in nl_query or "size" in nl_query):
            min_size = metadata_context.get("min_size", 1000000)  # Default 1MB for "large"
            start_time = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

            return "model_recent_large_files", {
                "min_size": min_size,
                "start_time": start_time
            }

        if ("mime" in nl_query or "content type" in nl_query) and ("activity" in nl_query or "edited" in nl_query):
            mime_type = metadata_context.get("mime_type", "application/pdf")
            activity_type = "FileEdit" if "edit" in nl_query else "FileAccess"

            return "model_semantic_and_activity", {
                "mime_type": mime_type,
                "activity_type": activity_type
            }

        # Default to a simple name search
        pattern = metadata_context.get("name_pattern", "%")
        return "model_file_by_name" if prefer_model else "file_by_name", {"name_pattern": pattern}

    def generate_from_criteria(self, criteria: Dict[str, Any]) -> str:
        """Generate an AQL query from criteria.

        Args:
            criteria: Dictionary of criteria for the query

        Returns:
            Generated AQL query
        """
        # Check if we should use model-based templates
        if criteria.get("use_model_templates", self.use_model_templates):
            return self._generate_model_criteria_query(criteria)
        else:
            return super().generate_from_criteria(criteria)

    def _generate_model_criteria_query(self, criteria: Dict[str, Any]) -> str:
        """Generate a model-based AQL query from criteria.

        Args:
            criteria: Dictionary of criteria for the query

        Returns:
            Generated AQL query
        """
        query_parts = []
        collection = criteria.get("collection", "Objects")

        # Start with basic FOR clause
        query = f"FOR doc IN {collection}\n"

        # Add filters based on criteria
        filters = []

        # Handle different types of criteria
        if "name" in criteria:
            filters.append(f"LIKE(doc.Label, '{criteria['name']}', true)")

        if "extension" in criteria:
            ext = criteria["extension"]
            if ext.startswith("."):
                ext = ext[1:]
            filters.append(f"doc.Record.Attributes.Extension == '{ext}'")

        if "path" in criteria:
            filters.append(f"LIKE(doc.Record.Attributes.Path, '{criteria['path']}', true)")

        if "mime_type" in criteria:
            # This requires a join with SemanticMetadata
            return self._generate_semantic_criteria_query(criteria)

        if "activity_type" in criteria:
            # This requires a join with Activities
            return self._generate_activity_criteria_query(criteria)

        if "min_size" in criteria and "max_size" in criteria:
            filters.append(f"doc.Record.Attributes.Size >= {criteria['min_size']} AND doc.Record.Attributes.Size <= {criteria['max_size']}")
        elif "min_size" in criteria:
            filters.append(f"doc.Record.Attributes.Size >= {criteria['min_size']}")
        elif "max_size" in criteria:
            filters.append(f"doc.Record.Attributes.Size <= {criteria['max_size']}")

        if "start_time" in criteria and "end_time" in criteria:
            # Find modification timestamp
            query += f"""
            LET timestamp_entry = (
                FOR ts IN doc.Timestamps
                FILTER ts.Label == "Modified"
                LIMIT 1
                RETURN ts
            )[0]
            """
            filters.append(f"timestamp_entry.Value >= '{criteria['start_time']}' AND timestamp_entry.Value <= '{criteria['end_time']}'")

        if "machine_id" in criteria:
            filters.append(f"doc.Record.MachineID == '{criteria['machine_id']}'")

        # Add FILTER clause if there are filters
        if filters:
            query += f"FILTER {' AND '.join(filters)}\n"

        # Sort if specified
        if "sort_field" in criteria and "sort_direction" in criteria:
            field = criteria["sort_field"]
            direction = criteria["sort_direction"]

            # Handle special fields
            if field == "size":
                query += f"SORT doc.Record.Attributes.Size {direction}\n"
            elif field == "modified":
                query += f"""
                SORT timestamp_entry.Value {direction}
                """
            else:
                query += f"SORT doc.{field} {direction}\n"

        # Add LIMIT and RETURN clauses
        limit = criteria.get("limit", 100)
        query += f"LIMIT {limit}\n"
        query += "RETURN doc"

        return query

    def _generate_semantic_criteria_query(self, criteria: Dict[str, Any]) -> str:
        """Generate a query for criteria involving semantic metadata.

        Args:
            criteria: Dictionary of criteria for the query

        Returns:
            Generated AQL query
        """
        query = "FOR sem IN SemanticMetadata\n"

        # Build semantic filters
        filters = []

        if "mime_type" in criteria:
            filters.append(f"sem.Record.Attributes.MimeType == '{criteria['mime_type']}'")

        if "checksum" in criteria:
            filters.append(f"sem.Record.Attributes.Checksum == '{criteria['checksum']}'")

        if "content_pattern" in criteria:
            filters.append(f"LIKE(sem.Content.Extract, '{criteria['content_pattern']}', true)")

        # Add semantic filters
        if filters:
            query += f"FILTER {' AND '.join(filters)}\n"

        # Join with Objects
        query += "FOR doc IN Objects\n"
        query += "FILTER doc.ObjectIdentifier == sem.ObjectIdentifier\n"

        # Add file filters
        file_filters = []

        if "name" in criteria:
            file_filters.append(f"LIKE(doc.Label, '{criteria['name']}', true)")

        if "min_size" in criteria and "max_size" in criteria:
            file_filters.append(f"doc.Record.Attributes.Size >= {criteria['min_size']} AND doc.Record.Attributes.Size <= {criteria['max_size']}")
        elif "min_size" in criteria:
            file_filters.append(f"doc.Record.Attributes.Size >= {criteria['min_size']}")
        elif "max_size" in criteria:
            file_filters.append(f"doc.Record.Attributes.Size <= {criteria['max_size']}")

        # Add file filters if any
        if file_filters:
            query += f"FILTER {' AND '.join(file_filters)}\n"

        # Add LIMIT and RETURN clauses
        limit = criteria.get("limit", 100)
        query += f"LIMIT {limit}\n"
        query += "RETURN doc"

        return query

    def _generate_activity_criteria_query(self, criteria: Dict[str, Any]) -> str:
        """Generate a query for criteria involving activities.

        Args:
            criteria: Dictionary of criteria for the query

        Returns:
            Generated AQL query
        """
        query = "FOR act IN Activities\n"

        # Build activity filters
        filters = []

        if "activity_type" in criteria:
            filters.append(f"act.Record.ActivityType == '{criteria['activity_type']}'")

        if "user_id" in criteria:
            filters.append(f"act.Record.UserID == '{criteria['user_id']}'")

        if "start_time" in criteria and "end_time" in criteria:
            filters.append(f"act.Timestamp >= '{criteria['start_time']}' AND act.Timestamp <= '{criteria['end_time']}'")

        # Add activity filters
        if filters:
            query += f"FILTER {' AND '.join(filters)}\n"

        # Join with Objects
        query += "FOR doc IN Objects\n"
        query += "FILTER doc.ObjectIdentifier == act.Record.ObjectIdentifier\n"

        # Add file filters
        file_filters = []

        if "name" in criteria:
            file_filters.append(f"LIKE(doc.Label, '{criteria['name']}', true)")

        if "extension" in criteria:
            ext = criteria["extension"]
            if ext.startswith("."):
                ext = ext[1:]
            file_filters.append(f"doc.Record.Attributes.Extension == '{ext}'")

        # Add file filters if any
        if file_filters:
            query += f"FILTER {' AND '.join(file_filters)}\n"

        # Add LIMIT and RETURN clauses
        limit = criteria.get("limit", 100)
        query += f"LIMIT {limit}\n"
        query += "RETURN doc"

        return query
