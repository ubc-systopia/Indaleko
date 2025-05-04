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
from typing import Any

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
    default: Any | None = None
    enum: list[Any] | None = None


class ToolDefinition(BaseModel):
    """Definition of a tool."""

    name: str
    description: str
    parameters: list[ToolParameter]
    returns: dict[str, Any]
    examples: list[dict[str, Any]] | None = None


class ToolInput(BaseModel):
    """Input data for a tool invocation."""

    tool_name: str
    parameters: dict[str, Any]
    conversation_id: str | None = None
    invocation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    llm_connector: Any = None  # LLM connector instance to use for the tool


class ToolOutput(BaseModel):
    """Output data from a tool invocation."""

    tool_name: str
    success: bool
    result: Any | None = None
    error: str | None = None
    trace: str | None = None
    elapsed_time: float
    invocation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProgressCallback(BaseModel):
    """Callback data for tool progress updates."""

    tool_name: str
    stage: str
    message: str
    progress: float = 0.0  # 0.0 to 1.0
    data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BaseTool(ABC):
    """Base class for all Indaleko tools."""

    def __init__(self, **kwargs):
        """
        Initialize the tool.

        Args:
            **kwargs: Additional arguments including:
                - llm_connector: LLM connector to use with this tool
                - progress_callback: Callback function for progress updates
        """
        self._progress_callback = kwargs.get("progress_callback", None)
        self._llm_connector = kwargs.get("llm_connector", None)

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""

    @abstractmethod
    def execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Execute the tool with the given input.

        Args:
            input_data (ToolInput): The input parameters for the tool.

        Returns:
            ToolOutput: The result of the tool execution.
        """

    def set_progress_callback(self, callback_func: callable) -> None:
        """
        Set a callback function to receive progress updates during tool execution.

        Args:
            callback_func (callable): A function that takes a ProgressCallback object.
                                     Set to None to disable progress updates.
        """
        self._progress_callback = callback_func

    def report_progress(
        self,
        stage: str,
        message: str,
        progress: float = 0.0,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Report progress during tool execution.

        Args:
            stage (str): The current execution stage (e.g., "parsing", "translating", "executing")
            message (str): A human-readable message describing the current status
            progress (float, optional): Progress value between 0.0 and 1.0. Defaults to 0.0.
            data (Dict[str, Any], optional): Additional data to include with the progress report
        """
        if self._progress_callback is not None:
            callback_data = ProgressCallback(
                tool_name=self.definition.name,
                stage=stage,
                message=message,
                progress=progress,
                data=data,
            )
            self._progress_callback(callback_data)

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
            raise ValueError(
                f"Tool name mismatch: {input_data.tool_name} != {self.definition.name}",
            )

        # Check required parameters
        for param in self.definition.parameters:
            if param.required and param.name not in input_data.parameters:
                raise ValueError(f"Missing required parameter: {param.name}")

        # Check parameter types and enum values
        for name, value in input_data.parameters.items():
            # Find the parameter definition
            param_def = next(
                (p for p in self.definition.parameters if p.name == name),
                None,
            )
            if param_def is None:
                raise ValueError(f"Unknown parameter: {name}")

            # Check type
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
            }
            expected_type = type_map.get(param_def.type)
            if expected_type and not isinstance(value, expected_type):
                raise ValueError(
                    f"Parameter {name} has wrong type: {type(value).__name__} != {param_def.type}",
                )

            # Check enum values
            if param_def.enum is not None and value not in param_def.enum:
                raise ValueError(
                    f"Parameter {name} has invalid value: {value} not in {param_def.enum}",
                )

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
                invocation_id=input_data.invocation_id,
            )
