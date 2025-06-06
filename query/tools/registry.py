"""
Tool registry for Indaleko tools.

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

import importlib
import os
import pkgutil
import sys

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.tools.base import BaseTool, ToolDefinition, ToolInput, ToolOutput


class ToolRegistry:
    """Registry for Indaleko tools."""

    _instance = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools = {}
            cls._instance._tool_instances = {}
            cls._instance._progress_callback = None
        return cls._instance

    def register_tool(self, tool_class: type[BaseTool]) -> None:
        """
        Register a tool class.

        Args:
            tool_class (Type[BaseTool]): The tool class to register.
        """
        # Create an instance to get the definition
        tool_instance = tool_class()
        definition = tool_instance.definition

        # Register the tool class
        self._tools[definition.name] = tool_class
        self._tool_instances[definition.name] = tool_instance

        # Set the progress callback if one is registered
        if self._progress_callback is not None:
            tool_instance.set_progress_callback(self._progress_callback)

        ic(f"Registered tool: {definition.name}")

    def get_tool(self, name: str) -> BaseTool | None:
        """
        Get a tool instance by name.

        Args:
            name (str): The name of the tool.

        Returns:
            Optional[BaseTool]: The tool instance, or None if not found.
        """
        return self._tool_instances.get(name)

    def get_all_tools(self) -> dict[str, BaseTool]:
        """
        Get all registered tool instances.

        Returns:
            Dict[str, BaseTool]: A dictionary of tool names to tool instances.
        """
        return self._tool_instances.copy()

    def get_all_definitions(self) -> dict[str, ToolDefinition]:
        """
        Get all tool definitions.

        Returns:
            Dict[str, ToolDefinition]: A dictionary of tool names to tool definitions.
        """
        return {name: tool.definition for name, tool in self._tool_instances.items()}

    def set_progress_callback(self, callback_func: callable) -> None:
        """
        Set a global callback function for all tools in the registry.

        Args:
            callback_func (callable): A function that takes a ProgressCallback object.
                                     Set to None to disable progress updates.
        """
        self._progress_callback = callback_func

        # Update all existing tool instances
        for tool in self._tool_instances.values():
            tool.set_progress_callback(callback_func)

    def execute_tool(
        self,
        name: str,
        parameters: dict,
        progress_callback: callable = None,
    ) -> ToolOutput:
        """
        Execute a tool with the given parameters.

        Args:
            name (str): The name of the tool to execute.
            parameters (dict): The parameters to pass to the tool.
            progress_callback (callable, optional): A callback function for progress updates.
                                                  Overrides the registry's global callback.

        Returns:
            ToolOutput: The result of the tool execution.

        Raises:
            ValueError: If the tool is not found.
        """
        # Create a ToolInput object
        input_data = ToolInput(tool_name=name, parameters=parameters)

        return self.execute_tool_input(input_data, progress_callback)

    def execute_tool_input(
        self,
        input_data: ToolInput,
        progress_callback: callable = None,
    ) -> ToolOutput:
        """
        Execute a tool with the given input.

        Args:
            input_data (ToolInput): The input parameters for the tool.
            progress_callback (callable, optional): A callback function for progress updates.
                                                  Overrides the registry's global callback.

        Returns:
            ToolOutput: The result of the tool execution.

        Raises:
            ValueError: If the tool is not found.
        """
        tool = self.get_tool(input_data.tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {input_data.tool_name}")

        # Set the callback for this execution if provided
        if progress_callback is not None:
            original_callback = tool._progress_callback
            tool.set_progress_callback(progress_callback)

        try:
            return tool.wrapped_execute(input_data)
        finally:
            # Restore the original callback if we changed it
            if progress_callback is not None:
                tool.set_progress_callback(original_callback)

    def discover_tools(self, package_name: str = "query.tools") -> None:
        """
        Discover and register all tools in the specified package.

        Args:
            package_name (str): The name of the package to search.
        """
        package = importlib.import_module(package_name)

        # Get the package directory
        package_dir = os.path.dirname(package.__file__)

        # Find all submodules
        for _, name, is_pkg in pkgutil.iter_modules([package_dir]):
            full_name = f"{package_name}.{name}"

            if is_pkg:
                # Recursively discover tools in subpackages
                self.discover_tools(full_name)
            else:
                try:
                    # Import the module
                    module = importlib.import_module(full_name)

                    # Find all classes that inherit from BaseTool
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseTool) and attr is not BaseTool:
                            self.register_tool(attr)
                except Exception as e:
                    ic(f"Error loading tool module {full_name}: {e}")


# Singleton instance
tool_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """
    Get the tool registry instance.

    Returns:
        ToolRegistry: The tool registry instance.
    """
    return tool_registry
