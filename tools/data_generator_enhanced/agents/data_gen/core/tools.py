"""
Tool registry and base tool interface for data generation agents.

This module provides the foundation for tool management and execution
that agents use to perform their data generation tasks.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Tool(ABC):
    """Base class for all tools."""
    
    def __init__(self, name: str, description: str):
        """Initialize the tool.
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"Tool:{self.name}")
    
    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the tool with provided parameters.
        
        Args:
            parameters: Tool parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.
        
        This method should be overridden by subclasses to provide
        a specific schema for the tool parameters.
        
        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


class ToolRegistry:
    """Registry for all available tools."""
    
    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, Tool] = {}
        self.logger = logging.getLogger("ToolRegistry")
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the registry.
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools.
        
        Returns:
            List of all tool instances
        """
        return list(self.tools.values())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all registered tools.
        
        Returns:
            List of tool schemas
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool by name with provided parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If the tool is not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        self.logger.debug(f"Executing tool: {tool_name}")
        return tool.execute(parameters)