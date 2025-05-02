"""
Database Schema Visualization Tool for Indaleko.

This module provides tools to visualize the Indaleko database schema,
including collections, relationships, and key indexes.

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

from indaleko.tools.db_schema_viz.schema_extractor import extract_collections, extract_relationships
from indaleko.tools.db_schema_viz.schema_analyzer import group_collections, analyze_indexes
from indaleko.tools.db_schema_viz.graphviz_generator import generate_dot, generate_output

__all__ = [
    'extract_collections',
    'extract_relationships',
    'group_collections',
    'analyze_indexes',
    'generate_dot',
    'generate_output',
]