"""
Indaleko query tools package.

This package contains tools for parsing queries, translating them to database
languages, executing them, and processing the results.

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

from query.tools.base import (
    BaseTool,
    ToolDefinition,
    ToolInput,
    ToolOutput,
    ToolParameter,
)
from query.tools.registry import ToolRegistry, get_registry


# Add CognitiveMemoryQueryTool to exports
try:
    from query.tools.memory.cognitive_query import CognitiveMemoryQueryTool

    __all__ = [
        "BaseTool",
        "CognitiveMemoryQueryTool",
        "ToolDefinition",
        "ToolInput",
        "ToolOutput",
        "ToolParameter",
        "ToolRegistry",
        "get_registry",
    ]
except ImportError:
    # The CognitiveMemoryQueryTool might not be available
    __all__ = [
        "BaseTool",
        "ToolDefinition",
        "ToolInput",
        "ToolOutput",
        "ToolParameter",
        "ToolRegistry",
        "get_registry",
    ]

# Register default tools
registry = get_registry()
try:
    from query.tools.translation.nl_parser import NLParserTool

    registry.register_tool(NLParserTool)
except ImportError:
    pass

try:
    from query.tools.translation.aql_translator import AQLTranslatorTool

    registry.register_tool(AQLTranslatorTool)
except ImportError:
    pass

try:
    from query.tools.database.executor import QueryExecutorTool

    registry.register_tool(QueryExecutorTool)
except ImportError:
    pass

try:
    from query.tools.memory.cognitive_query import CognitiveMemoryQueryTool

    registry.register_tool(CognitiveMemoryQueryTool)
except ImportError:
    pass
