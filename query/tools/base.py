"""
Base classes and interfaces for Indaleko tools.

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
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    
    name: str
    description: str
    type: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseModel):
    """Definition of a tool."""
    
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None
    

class ToolInput(BaseModel):
    """Input data for a tool invocation."""
    
    tool_name: str
    parameters: Dict[str, Any]
    conversation_id: Optional[str] = None
    invocation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolOutput(BaseModel):
    """Output data from a tool invocation."""
    
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    trace: Optional[str] = None
    elapsed_time: float
    invocation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BaseTool(ABC):
    """Base class for all Indaleko tools."""
    
    def __init__(self):
        """Initialize the tool."""
        pass
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        pass
    
    @abstractmethod
    def execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Execute the tool with the given input.
        
        Args:
            input_data (ToolInput): The input parameters for the tool.
            
        Returns:
            ToolOutput: The result of the tool execution.
        """
        pass
    
    def validate_input(self, input_data: ToolInput) -> None:
        """
        Validate that the input data matches the tool's parameter specifications.
        
        Args:
            input_data (ToolInput): The input data to validate.
            
        Raises:
            ValueError: If the input data is invalid.
        """
        # Check that the tool name matches
        if input_data.tool_name != self.definition.name:
            raise ValueError(f"Tool name mismatch: {input_data.tool_name} != {self.definition.name}")
        
        # Check required parameters
        for param in self.definition.parameters:
            if param.required and param.name not in input_data.parameters:
                raise ValueError(f"Missing required parameter: {param.name}")
        
        # Check parameter types and enum values
        for name, value in input_data.parameters.items():
            # Find the parameter definition
            param_def = next((p for p in self.definition.parameters if p.name == name), None)
            if param_def is None:
                raise ValueError(f"Unknown parameter: {name}")
            
            # Check type
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict
            }
            expected_type = type_map.get(param_def.type)
            if expected_type and not isinstance(value, expected_type):
                raise ValueError(f"Parameter {name} has wrong type: {type(value).__name__} != {param_def.type}")
            
            # Check enum values
            if param_def.enum is not None and value not in param_def.enum:
                raise ValueError(f"Parameter {name} has invalid value: {value} not in {param_def.enum}")
    
    def wrapped_execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Wrapper for execute method that handles timing, validation, and error handling.
        
        Args:
            input_data (ToolInput): The input parameters for the tool.
            
        Returns:
            ToolOutput: The result of the tool execution.
        """
        start_time = time.time()
        
        try:
            # Validate input
            self.validate_input(input_data)
            
            # Execute the tool
            result = self.execute(input_data)
            elapsed_time = time.time() - start_time
            result.elapsed_time = elapsed_time
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            # Capture the stack trace
            trace = traceback.format_exc()
            
            # Create an error result
            return ToolOutput(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                trace=trace,
                elapsed_time=elapsed_time,
                invocation_id=input_data.invocation_id
            )