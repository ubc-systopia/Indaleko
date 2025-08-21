"""
OpenAI Request-based Assistant API implementation for Indaleko Archivist.

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

import json
import os
import sys
import time
import uuid

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import openai

from icecream import ic
from pydantic import BaseModel, Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from query.memory.archivist_memory import ArchivistMemory
from query.tools.base import ToolInput
from query.tools.registry import get_registry


class Message(BaseModel):
    """A message in a conversation."""

    role: str = Field(
        ...,
        description="The role of the message sender (user, assistant, system)",
    )
    content: str = Field(..., description="The content of the message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this message was created",
    )


class ConversationState(BaseModel):
    """State of a conversation with the assistant."""

    conversation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this conversation",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this conversation was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this conversation was last updated",
    )

    messages: list[Message] = Field(
        default_factory=list,
        description="The messages in this conversation",
    )

    execution_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context for the execution of this conversation",
    )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.now(UTC)


class RequestAssistant:
    """
    Indaleko Archivist implementation using OpenAI's latest Request-based API.
    This version allows the assistant to maintain conversation context and call tools.
    """

    # System instructions for the assistant
    ASSISTANT_INSTRUCTIONS = """You are Indaleko Archivist, a helpful AI that helps users find, understand, and manage their personal data.

    Indaleko is a unified personal index system that helps users find, understand, and manage their data across multiple storage services and devices.

    Your role is to:
    1. Help users find their data using natural language queries
    2. Explain relationships between files and other data objects
    3. Identify patterns and insights across different data sources
    4. Provide context-aware recommendations
    5. Remember user preferences and information for future sessions

    You have access to tools that can:
    - Parse natural language queries
    - Translate structured queries to AQL (ArangoDB Query Language)
    - Execute queries against the database
    - Analyze and present results
    - Update entity information when users provide clarifications

    Follow these guidelines:
    1. Be conversational and friendly
    2. Ask clarifying questions when the query is ambiguous
    3. Remember information the user shares about locations, preferences, and entities
    4. Explain what you're doing when using tools
    5. Format results in a clear, readable way
    6. For large result sets, summarize the key findings
    7. Suggest related queries when appropriate
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        db_config: IndalekoDBConfig | None = None,
        archivist_memory: ArchivistMemory | None = None,
        auto_save_memory: bool = True,
        enable_query_history: bool = True,
        query_cache_duration: int = 3600,  # 1 hour cache duration by default
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> None:
        """
        Initialize the Indaleko Request-based Assistant.

        Args:
            api_key (Optional[str]): The OpenAI API key. If None, will be loaded from config.
            model (str): The model to use for the assistant.
            db_config (Optional[IndalekoDBConfig]): Database configuration.
            archivist_memory (Optional[ArchivistMemory]): Existing archivist memory instance.
            auto_save_memory (bool): Whether to automatically save memory after updates.
            enable_query_history (bool): Whether to record database queries for optimization.
            query_cache_duration (int): How long to cache query results in seconds.
            progress_callback (Optional[Callable]): Callback for progress updates.
        """
        self.api_key = api_key if api_key else self._load_api_key()
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        self.tool_registry = get_registry()
        self.assistant_id = None
        self.conversations = {}
        self.db_config = db_config or IndalekoDBConfig()
        self.archivist_memory = archivist_memory or ArchivistMemory(self.db_config)
        self.auto_save_memory = auto_save_memory
        self.enable_query_history = enable_query_history
        self.query_cache_duration = query_cache_duration
        self.progress_callback = progress_callback
        self.query_cache = {}  # Simple in-memory cache for query results

        # Create or retrieve the assistant
        self._initialize_assistant()

    def _load_api_key(self) -> str:
        """
        Load the OpenAI API key from the config file.

        Returns:
            str: The API key.
        """
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        api_key_file = os.path.join(config_dir, "openai-key.ini")

        import configparser

        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")

        api_key = config["openai"]["api_key"]

        # Clean up quotes if present
        if api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
            api_key = api_key[1:-1]

        return api_key

    def _initialize_assistant(self) -> None:
        """Initialize the OpenAI Assistant, creating a new one if needed."""
        # Check if the assistant configuration is stored on disk
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        assistant_config_file = os.path.join(
            config_dir,
            "request-assistant-config.json",
        )

        if os.path.exists(assistant_config_file):
            # Load existing configuration
            with open(assistant_config_file) as f:
                config = json.load(f)
                self.assistant_id = config.get("assistant_id")

            # Verify the assistant still exists
            try:
                self.client.beta.assistants.retrieve(self.assistant_id)
                ic(f"Using existing assistant: {self.assistant_id}")
                return
            except Exception as e:
                ic(f"Error retrieving assistant: {e}")
                self.assistant_id = None

        # Create a new assistant
        tool_definitions = self._get_tool_definitions()

        # Load and enhance instructions with context
        instructions = self._build_assistant_instructions()

        # Create the assistant with chunked/summarized tool definitions
        assistant = self.client.beta.assistants.create(
            name="Indaleko Archivist",
            description="An assistant for finding, understanding, and managing personal data in Indaleko",
            instructions=instructions,
            model=self.model,
            tools=tool_definitions,
        )

        self.assistant_id = assistant.id
        ic(f"Created new assistant: {self.assistant_id}")

        # Save the configuration
        os.makedirs(config_dir, exist_ok=True)
        with open(assistant_config_file, "w") as f:
            json.dump({"assistant_id": self.assistant_id}, f)

    def _build_assistant_instructions(self) -> str:
        """
        Build comprehensive assistant instructions with database schema context.
        Handles token limitation by summarizing and chunking information.

        Returns:
            str: Enhanced instructions with schema information
        """
        # Start with our base instructions
        instructions = self.ASSISTANT_INSTRUCTIONS + "\n\n"

        # Add schema information about the collections
        instructions += "DATABASE SCHEMA INFORMATION\n"
        instructions += "--------------------------\n"

        try:
            # Get collection information from the database
            collection_names = self.db_config._arangodb.collections()

            # Filter to exclude system collections
            collection_names = [name for name in collection_names if not name.startswith("_")]

            # Add information about available collections
            instructions += f"Available collections in the database: {', '.join(collection_names)}\n\n"

            # Get more detailed schema for select collections that are most commonly used
            primary_collections = [
                "Objects",
                "Relationships",
                "ActivityContext",
                "MachineConfig",
                "Users",
                "NamedEntities",
            ]

            # Add information about these primary collections first
            for name in primary_collections:
                if name in collection_names:
                    instructions += self._get_collection_schema_summary(name)

            # Check if we're close to token limit before adding others
            if self._calculate_token_estimate(instructions) < 10000:  # Safe limit for instructions
                # Add other collections
                for name in collection_names:
                    if name not in primary_collections:
                        # Only add if we have room
                        collection_summary = self._get_collection_schema_summary(name)
                        if (
                            self._calculate_token_estimate(
                                instructions + collection_summary,
                            )
                            < 15000
                        ):
                            instructions += collection_summary

            # Add guidance about how to request additional schema information
            instructions += "\nNOTE: This is a summarized view of the database schema. If you need more details about a specific collection, you can request it during operation.\n"

        except Exception as e:
            ic(f"Error getting schema information: {e}")
            instructions += (
                "Error retrieving schema information. Schema information will be provided during operation.\n"
            )

        return instructions

    def _get_collection_schema_summary(self, collection_name: str) -> str:
        """
        Get a summary of the schema for a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            str: A formatted string with schema information.
        """
        summary = f"Collection: {collection_name}\n"

        try:
            # Get collection properties
            collection = self.db_config._arangodb.collection(collection_name)

            # Get collection information and properties
            collection_info = collection.properties()
            summary += f"- Type: {'Edge' if collection_info.get('type') == 3 else 'Document'} collection\n"
            summary += f"- System: {'Yes' if collection_info.get('isSystem') else 'No'}\n"

            # Count documents
            count = collection.count()
            summary += f"- Documents: {count}\n"

            # Get schema if available
            try:
                schema = collection.get_schema()
                if schema:
                    # Summarize the schema
                    summarized_schema = self._summarize_schema(schema, max_tokens=500)
                    schema_str = json.dumps(summarized_schema, indent=2)

                    # Only include if not too large
                    if len(schema_str) < 1000:
                        summary += f"- Schema summary: {schema_str}\n"
                    else:
                        summary += "- Schema: (Complex schema available, request details if needed)\n"
            except Exception:
                summary += "- Schema: Unable to retrieve schema\n"

            # Add field information
            try:
                # Sample a document to get field names
                if count > 0:
                    sample = collection.random()
                    if sample:
                        fields = list(sample.keys())
                        fields = [f for f in fields if not f.startswith("_")]
                        summary += f"- Sample fields: {', '.join(fields[:10])}"
                        if len(fields) > 10:
                            summary += " (and more)"
                        summary += "\n"
            except Exception:
                pass  # Skip field information if unavailable

        except Exception as e:
            summary += f"Error retrieving collection information: {e!s}\n"

        summary += "\n"
        return summary

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get OpenAI-compatible tool definitions from the registry.

        Returns:
            List[Dict[str, Any]]: Tool definitions in OpenAI format.
        """
        tools = []

        # Get all registered tools
        registered_tools = self.tool_registry.get_all_tools()

        for tool in registered_tools.values():
            # Convert our tool definition to OpenAI format
            definition = tool.definition

            # Create parameter schema
            parameters = {"type": "object", "properties": {}, "required": []}

            for param in definition.parameters:
                param_schema = {"type": param.type, "description": param.description}

                # Add default value if specified
                if param.default is not None:
                    param_schema["default"] = param.default

                parameters["properties"][param.name] = param_schema

                if param.required:
                    parameters["required"].append(param.name)

            # Add the tool
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": definition.name,
                        "description": definition.description,
                        "parameters": parameters,
                    },
                },
            )

        return tools

    def _calculate_token_estimate(self, text: str) -> int:
        """
        Calculate a rough estimate of token count for a string.
        This is a simple approximation - about 4 chars per token for English text.

        Args:
            text (str): The text to estimate tokens for.

        Returns:
            int: Estimated token count.
        """
        if isinstance(text, str):
            return len(text) // 4  # Simple approximation for strings
        # For non-string input, convert to string first
        try:
            text_str = str(text)
            return len(text_str) // 4
        except:
            # Fallback for objects that can't be converted to strings
            return 1000  # Assume it's a large object

    def _summarize_schema(
        self,
        schema: dict[str, Any],
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """
        Summarize a schema to reduce token usage, focusing on essential information.

        Args:
            schema (Dict[str, Any]): The schema to summarize.
            max_tokens (int): Maximum tokens to use in the summary.

        Returns:
            Dict[str, Any]: Summarized schema.
        """
        # If schema is small enough, return it as is
        schema_str = json.dumps(schema)
        if self._calculate_token_estimate(schema_str) <= max_tokens:
            return schema

        # For larger schemas, we'll create a simplified version
        summary = {}

        # Keep essential schema information
        if "type" in schema:
            summary["type"] = schema["type"]

        if "title" in schema:
            summary["title"] = schema["title"]

        if "description" in schema:
            summary["description"] = schema["description"]

        # Handle properties recursively but with limits
        if "properties" in schema:
            summary["properties"] = {}

            # Sort properties by importance (this is a heuristic)
            important_fields = [
                "id",
                "name",
                "type",
                "key",
                "label",
                "title",
                "description",
            ]
            sorted_props = sorted(
                schema["properties"].items(),
                key=lambda x: (
                    -10 if x[0].lower() in [f.lower() for f in important_fields] else 0,
                    len(json.dumps(x[1])),  # Prefer smaller properties
                ),
            )

            # Add properties until we approach max tokens
            current_estimate = self._calculate_token_estimate(json.dumps(summary))
            for prop_name, prop_value in sorted_props:
                # Create simplified property
                if isinstance(prop_value, dict):
                    simplified_prop = {
                        "type": prop_value.get("type", "object"),
                        "description": prop_value.get(
                            "description",
                            f"Property {prop_name}",
                        ),
                    }

                    # Add a note if this property had nested objects
                    if "properties" in prop_value:
                        simplified_prop["hasNestedProperties"] = True

                    prop_tokens = self._calculate_token_estimate(
                        json.dumps(simplified_prop),
                    )

                    if current_estimate + prop_tokens > max_tokens:
                        summary["properties"][prop_name] = {
                            "type": "omitted",
                            "description": "Property details omitted to reduce token usage",
                        }
                    else:
                        summary["properties"][prop_name] = simplified_prop
                        current_estimate += prop_tokens
                else:
                    # Non-dict property (should be rare in schemas)
                    summary["properties"][prop_name] = prop_value

        # Required fields
        if "required" in schema:
            summary["required"] = schema["required"]

        # Add a note about summarization
        summary["note"] = "This schema has been summarized to reduce token usage. Some details may be omitted."

        return summary

    def create_conversation(self) -> ConversationState:
        """
        Create a new conversation with the assistant.

        Returns:
            ConversationState: The conversation state.
        """
        # Create conversation state
        conversation = ConversationState()

        # Create thread in the Assistant API
        thread = self.client.beta.threads.create()

        # Store the thread ID in the execution context
        conversation.execution_context["thread_id"] = thread.id

        # Add a system message with the forward prompt from Archivist memory
        forward_prompt = self.archivist_memory.generate_forward_prompt()
        conversation.add_message("system", forward_prompt)

        # Store in our conversations dictionary
        self.conversations[conversation.conversation_id] = conversation

        return conversation

    def get_conversation(self, conversation_id: str) -> ConversationState | None:
        """
        Get a conversation by ID.

        Args:
            conversation_id (str): The conversation ID.

        Returns:
            Optional[ConversationState]: The conversation if found, None otherwise.
        """
        return self.conversations.get(conversation_id)

    def execute_tool(
        self,
        tool_call: dict[str, Any],
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Execute a tool call from the assistant.

        Args:
            tool_call (Dict[str, Any]): The tool call from the assistant.
            conversation_id (str): The conversation ID.

        Returns:
            Dict[str, Any]: The result of the tool execution.
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Extract tool information
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        ic(f"Executing tool: {function_name} with arguments: {arguments}")

        # Update progress if callback is provided
        if self.progress_callback:
            self.progress_callback(f"Executing {function_name}...", 0.5)

        # Create the tool input
        tool_input = ToolInput(
            tool_name=function_name,
            parameters=arguments,
            conversation_id=conversation_id,
            invocation_id=tool_call.id,
        )

        # Check cache for database queries before executing
        if function_name == "query_executor" and self.enable_query_history:
            # Only try cache for non-explain queries that aren't forced to execute
            query = arguments.get("query", "")
            bind_vars = arguments.get("bind_vars", {})
            explain_only = arguments.get("explain_only", False)
            force_execute = arguments.get("force_execute", False)

            if query and not explain_only and not force_execute:
                cached_result = self._check_query_cache(query, bind_vars)
                if cached_result:
                    # Create a successful result with the cached data
                    from query.tools.base import ToolOutput

                    result = ToolOutput(success=True, result=cached_result, error=None)

                    # Set execution time to 0 to indicate cached result
                    result.execution_time = 0.0
                    result.from_cache = True

                    if self.progress_callback:
                        self.progress_callback(
                            f"Retrieved from cache: {function_name}",
                            1.0,
                        )

                    # Skip further processing and return this cached result
                    if result.success:
                        return {
                            "output": json.dumps(
                                {
                                    "query": query,
                                    "bind_vars": bind_vars,
                                    "results": cached_result,
                                    "execution_time": 0,
                                    "from_cache": True,
                                },
                                default=str,
                            ),
                        }

        # Execute the tool (if not found in cache)
        result = self.tool_registry.execute_tool_input(tool_input)

        # Update progress if callback is provided
        if self.progress_callback:
            self.progress_callback(f"Finished executing {function_name}", 1.0)

        # Record database interactions for optimization and caching
        if function_name == "query_executor":
            self._record_database_interaction(tool_input, result)

        # Convert the result to a dictionary for the API
        if result.success:
            # Check if the result is too large (potential token issue)
            output_result = self._process_tool_result(result.result, function_name)
            output = {"output": json.dumps(output_result, default=str)}
        else:
            output = {
                "error": result.error,
                "output": json.dumps({"error": result.error}, default=str),
            }

        return output

    def _process_tool_result(self, result: Any, tool_name: str) -> Any:
        """
        Process and potentially compress tool results to manage token limit issues.

        Args:
            result (Any): The tool execution result.
            tool_name (str): The name of the tool that produced the result.

        Returns:
            Any: The processed result, potentially compressed or chunked.
        """
        # Convert to JSON string to check size
        result_str = json.dumps(result, default=str)
        estimated_tokens = self._calculate_token_estimate(result_str)

        # If the result is small enough, return as is
        if estimated_tokens < 4000:  # Safe limit for most operations
            return result

        # Handle different types of results based on tool
        if tool_name == "query_executor":
            # Handle large query results
            return self._process_query_results(result)
        if tool_name == "nl_parser" and isinstance(result, dict) and "collections" in result:
            # Handle large NL parser results
            return self._process_nl_parser_results(result)
        if isinstance(result, list):
            # Generic list handling (truncate if needed)
            return self._process_list_results(result)
        if isinstance(result, dict):
            # Generic dictionary handling (summarize if needed)
            return self._process_dict_results(result)

        # For everything else, handle based on type
        return self._compress_generic_result(result)

    def _process_query_results(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Process query executor results to handle token limitations.

        Args:
            result (Dict[str, Any]): The query execution result.

        Returns:
            Dict[str, Any]: The processed result.
        """
        processed_result = {}

        # Keep essential information
        if "query" in result:
            processed_result["query"] = result["query"]

        if "bind_vars" in result:
            processed_result["bind_vars"] = result["bind_vars"]

        if "execution_time" in result:
            processed_result["execution_time"] = result["execution_time"]

        # Handle result data specially
        if "results" in result:
            results = result["results"]

            if isinstance(results, list):
                # Count the original number of results
                original_count = len(results)

                # Process results
                if original_count > 50:
                    # If more than 50 results, keep only a subset
                    processed_result["results"] = results[:50]
                    processed_result["truncated"] = True
                    processed_result["total_results"] = original_count
                    processed_result["message"] = (
                        f"Response truncated to 50 of {original_count} results to manage token usage"
                    )
                else:
                    processed_result["results"] = results
            else:
                # Non-list results
                processed_result["results"] = results

        # Handle execution plan specially
        if "execution_plan" in result:
            # Simplify execution plan if needed
            plan = result["execution_plan"]
            plan_str = json.dumps(plan, default=str)
            estimated_tokens = self._calculate_token_estimate(plan_str)

            if estimated_tokens > 1000:
                # Simplify the plan
                simplified_plan = {"_is_explain_result": True}

                # Keep essential plan information
                if isinstance(plan, dict):
                    if "estimatedCost" in plan:
                        simplified_plan["estimatedCost"] = plan["estimatedCost"]
                    if "estimatedNrItems" in plan:
                        simplified_plan["estimatedNrItems"] = plan["estimatedNrItems"]

                    # Extract node types for a summary
                    if "nodes" in plan and isinstance(plan["nodes"], list):
                        node_types = {}
                        for node in plan["nodes"]:
                            node_type = node.get("type", "Unknown")
                            if node_type in node_types:
                                node_types[node_type] += 1
                            else:
                                node_types[node_type] = 1

                        simplified_plan["node_summary"] = node_types
                        # Include a couple of sample nodes
                        simplified_plan["sample_nodes"] = plan["nodes"][:2] if len(plan["nodes"]) > 2 else plan["nodes"]

                processed_result["execution_plan"] = simplified_plan
                processed_result["plan_simplified"] = True
            else:
                processed_result["execution_plan"] = plan

        return processed_result

    def _process_nl_parser_results(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Process NL parser results to handle token limitations.

        Args:
            result (Dict[str, Any]): The NL parser result.

        Returns:
            Dict[str, Any]: The processed result.
        """
        # Keep only essential information for large results
        processed_result = {}

        # Always keep these fields
        essential_fields = [
            "intent",
            "entities",
            "collections",
            "query",
            "is_successful",
        ]

        for field in essential_fields:
            if field in result:
                processed_result[field] = result[field]

        # Handle collections schema if present
        if "collections_schema" in result:
            schema = result["collections_schema"]
            schema_str = json.dumps(schema, default=str)
            estimated_tokens = self._calculate_token_estimate(schema_str)

            if estimated_tokens > 2000:
                # Simplify by just including collection names
                processed_result["collections_schema"] = {
                    "names": list(schema.keys()),
                    "note": "Schema details omitted to manage token usage",
                }
            else:
                processed_result["collections_schema"] = schema

        # Add a note about processing
        if len(result) > len(processed_result):
            processed_result["note"] = "Some details omitted to manage token usage"

        return processed_result

    def _process_list_results(self, result: list[Any]) -> list[Any]:
        """
        Process list results to handle token limitations.

        Args:
            result (List[Any]): The list result.

        Returns:
            List[Any]: The processed list.
        """
        # Convert to string to check size
        result_str = json.dumps(result, default=str)
        estimated_tokens = self._calculate_token_estimate(result_str)

        if estimated_tokens < 4000:
            return result

        # Truncate the list if too large
        if len(result) > 20:
            return {
                "truncated_results": result[:20],
                "total_items": len(result),
                "note": f"Response truncated to 20 of {len(result)} items to manage token usage",
            }

        # For smaller lists with large items, process each item
        processed_items = []
        for item in result:
            if isinstance(item, dict):
                # Summarize the dictionary
                item_str = json.dumps(item, default=str)
                if self._calculate_token_estimate(item_str) > 400:
                    # Keep only a subset of keys for large items
                    keys = list(item.keys())
                    if len(keys) > 10:
                        simplified_item = {k: item[k] for k in keys[:10]}
                        simplified_item["..."] = f"{len(keys) - 10} more fields omitted"
                        processed_items.append(simplified_item)
                    else:
                        processed_items.append(item)
                else:
                    processed_items.append(item)
            else:
                processed_items.append(item)

        return processed_items

    def _process_dict_results(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Process dictionary results to handle token limitations.

        Args:
            result (Dict[str, Any]): The dictionary result.

        Returns:
            Dict[str, Any]: The processed dictionary.
        """
        # Convert to string to check size
        result_str = json.dumps(result, default=str)
        estimated_tokens = self._calculate_token_estimate(result_str)

        if estimated_tokens < 4000:
            return result

        # For large dictionaries, keep only the most important fields
        # Identify important fields (heuristic)
        important_fields = [
            "id",
            "name",
            "key",
            "title",
            "description",
            "type",
            "query",
            "result",
            "error",
            "status",
            "message",
        ]

        # Build a processed result with important fields first
        processed_result = {}

        # Add important fields first
        for field in important_fields:
            if field in result:
                processed_result[field] = result[field]

        # If we still have token budget, add other fields
        other_fields = [k for k in result if k not in important_fields]

        # Sort other fields by size (smallest first)
        other_fields.sort(key=lambda k: len(json.dumps(result[k], default=str)))

        # Add as many other fields as we can fit
        current_estimate = self._calculate_token_estimate(
            json.dumps(processed_result, default=str),
        )
        for field in other_fields:
            field_value = result[field]
            field_str = json.dumps(field_value, default=str)
            field_tokens = self._calculate_token_estimate(field_str)

            if current_estimate + field_tokens < 4000:
                processed_result[field] = field_value
                current_estimate += field_tokens
            else:
                # Mark that we had to truncate
                processed_result["..."] = "Additional fields omitted to manage token usage"
                break

        return processed_result

    def _compress_generic_result(self, result: Any) -> Any:
        """
        Compress a generic result to handle token limitations.

        Args:
            result (Any): The result to compress.

        Returns:
            Any: The compressed result.
        """
        result_str = str(result)

        # If not too large, return as is
        if len(result_str) < 16000:  # Roughly 4000 tokens
            return result

        # Otherwise, truncate with a note
        truncated = result_str[:15000] + "..."
        return {
            "truncated_result": truncated,
            "original_length": len(result_str),
            "note": "Result truncated to manage token usage",
        }

    def process_message(
        self,
        conversation_id: str,
        message_content: str,
    ) -> dict[str, Any]:
        """
        Process a user message in the conversation.

        Args:
            conversation_id (str): The conversation ID.
            message_content (str): The user message.

        Returns:
            Dict[str, Any]: The response data.
        """
        # Get the conversation state
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            # Create a new conversation if one doesn't exist
            conversation = self.create_conversation()
            conversation_id = conversation.conversation_id

        # Add the message to the conversation state
        conversation.add_message("user", message_content)

        # Get the thread ID
        thread_id = conversation.execution_context.get("thread_id")
        if not thread_id:
            raise ValueError(f"Thread ID not found for conversation: {conversation_id}")

        # Add the message to the thread
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content,
        )

        # Create a run with the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
        )

        # Wait for the run to complete or require action
        response = self._wait_for_run(thread_id, run.id, conversation_id)

        # Update archivist memory
        self.update_archivist_memory(conversation)

        return response

    def update_archivist_memory(self, conversation: ConversationState) -> None:
        """
        Update the Archivist memory with information from the conversation.

        Args:
            conversation (ConversationState): The conversation state.
        """
        # Extract conversation for memory updating
        user_messages = [msg for msg in conversation.messages if msg.role == "user"]
        [msg for msg in conversation.messages if msg.role == "assistant"]

        if not user_messages:
            return

        # Extract potential preferences and insights
        for msg in user_messages[-5:]:  # Only process the last 5 messages
            content = msg.content.lower()

            # Look for location mentions
            if any(loc in content for loc in ["home", "work", "office", "school"]):
                self.archivist_memory.add_insight(
                    "location",
                    "User frequently refers to specific locations in queries",
                    0.6,
                )

            # Look for time references
            if any(time_ref in content for time_ref in ["yesterday", "last week", "recent", "old", "new"]):
                self.archivist_memory.add_insight(
                    "temporal",
                    "User often uses temporal constraints in searches",
                    0.7,
                )

            # Look for format preferences
            if "format" in content or any(fmt in content for fmt in ["pdf", "doc", "image", "photo", "spreadsheet"]):
                self.archivist_memory._update_content_preferences(
                    {
                        "get_recent_queries": lambda n: [
                            type("obj", (object,), {"OriginalQuery": msg.content}) for msg in user_messages[-n:]
                        ],
                    },
                )

            # Extract named entities from user messages to improve query capabilities
            self._extract_and_store_named_entities(msg.content)

        # Update the continuation context
        self.archivist_memory.memory.continuation_context = f"Recent conversation topics: {', '.join([m.content[:50] + '...' if len(m.content) > 50 else m.content for m in user_messages[-2:]])}"

        # Save memory if auto-save is enabled
        if self.auto_save_memory:
            self.archivist_memory.save_memory()

    def _extract_and_store_named_entities(self, text: str) -> None:
        """
        Extract and store named entities from text to improve query capabilities.

        This method extracts entities like people, places, devices, and time references
        and stores them in the Named Entities collection for future use.

        Args:
            text (str): The text to extract entities from.
        """
        try:
            # Skip empty or too short text
            if not text or len(text) < 10:
                return

            # Use the LLM to extract entities via tool execution
            entity_types = [
                "person",  # Person names (e.g., "Dr. Jones")
                "location",  # Places (e.g., "Hawaii", "New York")
                "organization",  # Organizations (e.g., "Google", "University of Washington")
                "device",  # Devices (e.g., "phone", "laptop")
                "event",  # Events (e.g., "conference", "meeting")
                "document",  # Document types or names (e.g., "report", "budget spreadsheet")
            ]

            # Format entity extraction prompt
            extraction_prompt = f"""
            Extract named entities from the following text. For each entity, provide:
            1. The entity text (exact text from input)
            2. The entity type (one of: {', '.join(entity_types)})
            3. A confidence score (0.0-1.0)

            Text: "{text}"

            Return results as a JSON array of objects with keys: "text", "type", "confidence"
            """

            # Create a simplified OpenAI client for this extraction
            # We don't use the full assistant API for this simple extraction task
            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using a smaller model for efficiency
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise entity extraction system. Extract entities exactly as they appear.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            content = response.choices[0].message.content
            entities_data = json.loads(content)

            if "entities" in entities_data and isinstance(
                entities_data["entities"],
                list,
            ):
                entities = entities_data["entities"]
            else:
                # If the response doesn't have the expected format, try to find an array
                for value in entities_data.values():
                    if isinstance(value, list) and len(value) > 0:
                        entities = value
                        break
                else:
                    # No list found, use the whole response if it's a list
                    entities = entities_data if isinstance(entities_data, list) else []

            # Skip if no entities found
            if not entities:
                return

            ic(f"Extracted {len(entities)} entities from text")

            # Store valid entities in the database
            self._store_named_entities(entities)

        except Exception as e:
            ic(f"Error extracting entities: {e}")

    def _store_named_entities(self, entities: list[dict[str, Any]]) -> None:
        """
        Store extracted named entities in the database.

        Args:
            entities (List[Dict[str, Any]]): List of extracted entity data.
        """
        try:
            # Check if we have the NamedEntities collection
            collection_name = "NamedEntities"
            if not self.db_config._arangodb.has_collection(collection_name):
                ic(
                    f"Collection {collection_name} does not exist, skipping entity storage",
                )
                return

            collection = self.db_config._arangodb.collection(collection_name)

            # Import needed data models
            from data_models.named_entity import IndalekoNamedEntityDataModel
            from data_models.record import IndalekoRecordDataModel
            from data_models.source_identifier import IndalekoSourceIdentifierDataModel

            # Process each entity
            for entity_data in entities:
                # Skip entities with low confidence
                confidence = float(entity_data.get("confidence", 0))
                if confidence < 0.7:
                    continue

                entity_text = entity_data.get("text", "").strip()
                entity_type = entity_data.get("type", "unknown").lower()

                # Skip invalid entries
                if not entity_text or entity_text == "":
                    continue

                # Normalize the entity type
                if entity_type not in [
                    "person",
                    "location",
                    "organization",
                    "device",
                    "event",
                    "document",
                ]:
                    # Map to closest standard type
                    if entity_type in ["company", "business", "school", "university"]:
                        entity_type = "organization"
                    elif entity_type in ["place", "city", "country", "address"]:
                        entity_type = "location"
                    elif entity_type in ["phone", "laptop", "computer", "tablet"]:
                        entity_type = "device"
                    elif entity_type in [
                        "file",
                        "spreadsheet",
                        "presentation",
                        "paper",
                    ]:
                        entity_type = "document"
                    else:
                        entity_type = "unknown"

                # Create the entity model
                entity_model = IndalekoNamedEntityDataModel(
                    Record=IndalekoRecordDataModel(
                        SourceIdentifier=IndalekoSourceIdentifierDataModel(
                            Identifier=str(uuid.uuid4()),
                            Version="1.0",
                            Description="Named Entity from Archivist Conversation",
                        ),
                        Timestamp=datetime.now(UTC),
                    ),
                    name=entity_text,
                    entity_type=entity_type,
                    description="Entity extracted from user conversation",
                    confidence=confidence,
                    tags=[entity_type, "conversation_extracted"],
                )

                # Check if similar entity already exists
                aql_query = """
                FOR e IN @@collection
                FILTER LOWER(e.name) == LOWER(@name) AND e.entity_type == @type
                LIMIT 1
                RETURN e
                """

                try:
                    cursor = self.db_config._arangodb.aql.execute(
                        aql_query,
                        bind_vars={
                            "@collection": collection_name,
                            "name": entity_text,
                            "type": entity_type,
                        },
                    )
                    existing_entities = list(cursor)

                    if existing_entities:
                        # Entity already exists, skip
                        continue

                    # Insert the new entity
                    doc = json.loads(entity_model.model_dump_json())
                    collection.insert(doc)
                    ic(f"Stored new entity: {entity_text} ({entity_type})")

                except Exception as e:
                    ic(f"Error checking/storing entity {entity_text}: {e}")

        except Exception as e:
            ic(f"Error storing entities: {e}")

    def _wait_for_run(
        self,
        thread_id: str,
        run_id: str,
        conversation_id: str,
        auto_refresh: bool = True,
    ) -> dict[str, Any]:
        """
        Wait for an assistant run to complete or require action.

        Args:
            thread_id (str): The thread ID.
            run_id (str): The run ID.
            conversation_id (str): The conversation ID.
            auto_refresh (bool): Whether to automatically refresh context on token limit errors.

        Returns:
            Dict[str, Any]: The response data.
        """
        # Start waiting for the run to complete
        while True:
            # Get the run status
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
            )

            # Update progress if callback is provided
            if self.progress_callback:
                progress_message = f"Processing: {run.status}"
                progress_value = 0.5
                if run.status == "completed":
                    progress_message = "Completed processing"
                    progress_value = 1.0
                elif run.status in ["failed", "cancelled", "expired"]:
                    progress_message = f"Error: {run.status}"
                    progress_value = 1.0
                self.progress_callback(progress_message, progress_value)

            # Check the status
            if run.status == "completed":
                # Get the latest messages
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)

                # Get the latest assistant message
                assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
                if not assistant_messages:
                    return {
                        "conversation_id": conversation_id,
                        "response": "No response generated.",
                        "action": "text",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }

                latest_message = assistant_messages[0]

                # Extract and process the content
                message_content = ""
                for content_part in latest_message.content:
                    if content_part.type == "text":
                        message_content += content_part.text.value

                # Add the message to our conversation state
                conversation = self.get_conversation(conversation_id)
                conversation.add_message("assistant", message_content)

                return {
                    "conversation_id": conversation_id,
                    "response": message_content,
                    "action": "text",
                    "message_id": latest_message.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            if run.status == "requires_action":
                # Handle required actions (tool calls)
                if run.required_action and run.required_action.type == "submit_tool_outputs":
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []

                    # Process tool calls

                    for tool_call in tool_calls:
                        # Execute the tool
                        output = self.execute_tool(tool_call, conversation_id)

                        # Add to outputs
                        tool_outputs.append(
                            {
                                "tool_call_id": tool_call.id,
                                "output": output.get(
                                    "output",
                                    json.dumps(
                                        {"error": output.get("error", "Unknown error")},
                                    ),
                                ),
                            },
                        )

                    # Submit the tool outputs
                    self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run_id,
                        tool_outputs=tool_outputs,
                    )

                # Continue waiting for completion
                continue

            if run.status in ["failed", "cancelled", "expired"]:
                # Get the error details
                error_code = run.last_error.code if run.last_error else "unknown_error"
                error_message = run.last_error.message if run.last_error else "Unknown error"

                # Check for token limit error
                is_token_limit_error = (
                    error_code in ["context_length_exceeded", "max_tokens_exceeded"]
                    or "token limit" in error_message.lower()
                    or "context length" in error_message.lower()
                )

                # Handle token limit error with auto-refresh if enabled
                if is_token_limit_error and auto_refresh:
                    try:
                        # Get the conversation
                        conversation = self.get_conversation(conversation_id)

                        # Get the last message from the user (that caused the token limit error)
                        user_messages = [msg for msg in conversation.messages if msg.role == "user"]
                        if user_messages:
                            last_user_message = user_messages[-1]

                            # Add a system message about refreshing context
                            refresh_message = "The conversation context window is full. Refreshing context to continue the conversation."
                            conversation.add_message("system", refresh_message)

                            # Refresh the context
                            self.refresh_context(conversation_id)

                            # Process the last user message in the new thread
                            return self.process_message(
                                conversation_id=conversation_id,
                                message_content=last_user_message.content,
                            )
                    except Exception as refresh_error:
                        ic(f"Error during context refresh: {refresh_error}")
                        # Fallback to error handling

                # Add the error to our conversation state
                conversation = self.get_conversation(conversation_id)
                error_summary = f"Run {run_id} {run.status}: {error_message}"
                conversation.add_message("system", f"Error: {error_summary}")

                # If it's a token limit error, add a helpful message
                if is_token_limit_error:
                    error_message = f"{error_message}\n\nThe conversation has reached the token limit. Try using the refresh_context method to continue or start a new conversation."

                return {
                    "conversation_id": conversation_id,
                    "response": error_message,
                    "action": "error",
                    "error_code": error_code,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            # Wait before checking again
            time.sleep(1)

    def save_conversations(self, file_path: str) -> None:
        """
        Save all conversations to a file.

        Args:
            file_path (str): The file path.
        """
        data = {
            conversation_id: conversation.model_dump() for conversation_id, conversation in self.conversations.items()
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_conversations(self, file_path: str) -> None:
        """
        Load conversations from a file.

        Args:
            file_path (str): The file path.
        """
        try:
            with open(file_path) as f:
                data = json.load(f)

            for conversation_id, conversation_data in data.items():
                # Convert string timestamps back to datetime
                if "created_at" in conversation_data:
                    conversation_data["created_at"] = datetime.fromisoformat(
                        conversation_data["created_at"],
                    )
                if "updated_at" in conversation_data:
                    conversation_data["updated_at"] = datetime.fromisoformat(
                        conversation_data["updated_at"],
                    )

                for message in conversation_data.get("messages", []):
                    if "timestamp" in message:
                        message["timestamp"] = datetime.fromisoformat(
                            message["timestamp"],
                        )

                # Recreate conversation state
                conversation = ConversationState(**conversation_data)
                self.conversations[conversation_id] = conversation
        except (FileNotFoundError, json.JSONDecodeError) as e:
            ic(f"Error loading conversations: {e}")

    def _record_database_interaction(self, tool_input: Any, result: Any) -> None:
        """
        Record database interactions for optimization and query caching.

        Args:
            tool_input: The input to the query executor tool.
            result: The result from the query execution.
        """
        if not self.enable_query_history:
            return

        # Extract query information
        try:
            parameters = tool_input.parameters
            query = parameters.get("query", "")
            bind_vars = parameters.get("bind_vars", {})
            explain_only = parameters.get("explain_only", False)

            # Skip if no query or if error
            if not query or not result.success:
                return

            # Cache the query result for potential reuse
            if not explain_only:
                query_key = self._generate_query_cache_key(query, bind_vars)
                self.query_cache[query_key] = {
                    "result": result.result,
                    "timestamp": datetime.now(UTC),
                    "execution_time": getattr(result, "execution_time", None),
                }

            # Record to the database for long-term storage and analysis
            try:
                # Import here to avoid circular imports
                from data_models.record import IndalekoRecordDataModel
                from data_models.source_identifier import (
                    IndalekoSourceIdentifierDataModel,
                )
                from query.query_processing.query_history import (
                    IndalekoQueryHistoryDataModel,
                )

                # Measure result size to check if it's too large
                result_size = self._estimate_result_size(result.result)
                result_count = len(result.result) if isinstance(result.result, list) else 1

                # For large results (>1MB), store metadata only and truncate the results
                # This prevents creating huge query history records
                max_size_bytes = 1024 * 1024  # 1MB max
                truncated_results = False
                execution_plan = getattr(result, "execution_plan", None)

                # Get truncated results for large result sets
                if result_size > max_size_bytes:
                    if isinstance(result.result, list) and len(result.result) > 0:
                        # Truncate results to first few items
                        max_items = 10
                        truncated_results = True

                        # Store information about truncation
                        stored_result = {
                            "truncated": True,
                            "original_size_bytes": result_size,
                            "original_count": result_count,
                            "sample_items": result.result[:max_items],
                            "message": f"Result truncated: {result_size/1024/1024:.2f}MB exceeded the 1MB limit",
                        }
                    else:
                        # For non-list large results, just store metadata
                        truncated_results = True
                        stored_result = {
                            "truncated": True,
                            "original_size_bytes": result_size,
                            "message": f"Result too large to store: {result_size/1024/1024:.2f}MB",
                        }

                    # Also truncate execution plan if needed
                    if execution_plan and len(json.dumps(execution_plan)) > 100000:  # ~100KB limit
                        if isinstance(execution_plan, dict):
                            # Keep only essential parts
                            simplified_plan = {
                                "estimatedCost": execution_plan.get("estimatedCost"),
                                "estimatedNrItems": execution_plan.get(
                                    "estimatedNrItems",
                                ),
                                "note": "Execution plan truncated due to size",
                            }
                            execution_plan = simplified_plan
                else:
                    # For smaller results, store the complete result
                    stored_result = result.result

                # Create a query history entry
                history_entry = IndalekoQueryHistoryDataModel(
                    Record=IndalekoRecordDataModel(
                        SourceIdentifier=IndalekoSourceIdentifierDataModel(
                            Identifier=str(uuid.uuid4()),
                            Version="1.0",
                            Description="Request-based Assistant Query",
                        ),
                        Timestamp=datetime.now(UTC),
                    ),
                    OriginalQuery=query,
                    TranslatedQuery=query,  # For AQL, original and translated are the same
                    QueryLanguage="AQL",
                    ExecutionTime=getattr(result, "execution_time", 0.0),
                    SuccessStatus=True,
                    ResultCount=result_count,
                    ExecutionPlan=execution_plan,
                    RankedResults=stored_result if not explain_only else None,
                    Truncated=truncated_results,
                )

                # Check if we have query history collection
                collection_name = "QueryHistory"
                if self.db_config._arangodb.has_collection(collection_name):
                    collection = self.db_config._arangodb.collection(collection_name)
                    # Save as document
                    doc = json.loads(history_entry.model_dump_json())
                    collection.insert(doc)

                    if truncated_results:
                        ic(
                            f"Recorded truncated query to history: {query[:50]} (original size: {result_size/1024/1024:.2f}MB)",
                        )
                    else:
                        ic(f"Recorded query to history: {query[:50]}")
            except Exception as e:
                ic(f"Error recording query history: {e}")

        except Exception as e:
            ic(f"Error processing database interaction: {e}")

    def _estimate_result_size(self, result: Any) -> int:
        """
        Estimate the size of a result in bytes.

        Args:
            result: The result to estimate the size of.

        Returns:
            int: Estimated size in bytes.
        """
        try:
            # Convert to JSON string to get approximate size
            result_json = json.dumps(result, default=str)
            return len(result_json.encode("utf-8"))
        except Exception:
            # For objects that can't be directly serialized
            try:
                import sys

                if isinstance(result, list):
                    # Estimate based on first few items
                    if len(result) == 0:
                        return 0
                    if len(result) > 10:
                        avg_size = sum(sys.getsizeof(str(item)) for item in result[:10]) / 10
                        return int(avg_size * len(result))
                    return sum(sys.getsizeof(str(item)) for item in result)
                return sys.getsizeof(str(result))
            except:
                # Fallback to a conservative estimate
                return 5 * 1024 * 1024  # Assume 5MB by default

    def _generate_query_cache_key(self, query: str, bind_vars: dict[str, Any]) -> str:
        """
        Generate a cache key for a query to enable result reuse.

        Args:
            query: The AQL query string.
            bind_vars: The bind variables for the query.

        Returns:
            str: A cache key string.
        """
        # Normalize the query by removing whitespace
        normalized_query = " ".join(query.split())

        # Combine with bind vars and create a hash
        combined = f"{normalized_query}_{json.dumps(bind_vars, sort_keys=True)}"
        import hashlib

        return hashlib.md5(combined.encode()).hexdigest()

    def _check_query_cache(
        self,
        query: str,
        bind_vars: dict[str, Any],
    ) -> Any | None:
        """
        Check if we have a cached result for this query.

        Args:
            query: The AQL query string.
            bind_vars: The bind variables for the query.

        Returns:
            Optional[Any]: The cached result or None if not found/expired.
        """
        if not self.enable_query_history:
            return None

        query_key = self._generate_query_cache_key(query, bind_vars)

        if query_key in self.query_cache:
            cache_entry = self.query_cache[query_key]
            cache_time = cache_entry["timestamp"]
            current_time = datetime.now(UTC)

            # Check if cache is still valid
            if (current_time - cache_time).total_seconds() < self.query_cache_duration:
                ic(f"Cache hit for query: {query[:50]}")
                return cache_entry["result"]
            # Remove expired entry
            del self.query_cache[query_key]

        return None

    def get_forward_prompt(self) -> str:
        """
        Get the forward prompt from the Archivist memory.

        Returns:
            str: The forward prompt.
        """
        return self.archivist_memory.generate_forward_prompt()

    def load_forward_prompt(self, prompt: str) -> None:
        """
        Load a forward prompt into the Archivist memory.

        Args:
            prompt (str): The forward prompt.
        """
        self.archivist_memory.update_from_forward_prompt(prompt)

        # Save memory if auto-save is enabled
        if self.auto_save_memory:
            self.archivist_memory.save_memory()

    def refresh_context(self, conversation_id: str) -> dict[str, Any]:
        """
        Refresh the conversation context by creating a new thread with summarized context.
        Use this when the context window becomes full but you want to continue the conversation.

        Args:
            conversation_id (str): The conversation ID.

        Returns:
            Dict[str, Any]: The result of the refresh operation.
        """
        # Get the conversation
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Get the old thread ID
        old_thread_id = conversation.execution_context.get("thread_id")
        if not old_thread_id:
            raise ValueError(f"Thread ID not found for conversation: {conversation_id}")

        # Create a new thread
        new_thread = self.client.beta.threads.create()
        new_thread_id = new_thread.id

        # Create a summary of the conversation
        summary = self._create_conversation_summary(conversation)

        # Store the old thread ID in the context
        conversation.execution_context["previous_thread_id"] = old_thread_id

        # Update the thread ID
        conversation.execution_context["thread_id"] = new_thread_id

        # Add the summary as a system message
        self.client.beta.threads.messages.create(
            thread_id=new_thread_id,
            role="user",
            content=summary,
        )

        # Create a run with the assistant to acknowledge the summary
        run = self.client.beta.threads.runs.create(
            thread_id=new_thread_id,
            assistant_id=self.assistant_id,
        )

        # Wait for the run to complete
        self._wait_for_run(new_thread_id, run.id, conversation_id)

        # Return success
        return {
            "conversation_id": conversation_id,
            "new_thread_id": new_thread_id,
            "old_thread_id": old_thread_id,
            "summary": summary,
            "status": "success",
        }

    def _create_conversation_summary(self, conversation: ConversationState) -> str:
        """
        Create a summary of the conversation for context refreshing.

        Args:
            conversation (ConversationState): The conversation state.

        Returns:
            str: The conversation summary.
        """
        # Start with a header
        summary = "CONVERSATION SUMMARY AND CONTINUATION\n"
        summary += "=====================================\n\n"

        # Get user and assistant messages
        user_msgs = [msg for msg in conversation.messages if msg.role == "user"]
        assistant_msgs = [msg for msg in conversation.messages if msg.role == "assistant"]

        # Add key topics section
        summary += "KEY TOPICS AND INFORMATION\n"

        # Generate list of topics from the user messages
        if user_msgs:
            # Extract keywords from user messages
            all_user_text = " ".join([msg.content for msg in user_msgs])
            all_user_text = all_user_text.lower()

            # Simple keyword extraction - in a real implementation, we would use NLP
            # or could delegate this to another LLM call
            common_words = [
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "with",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "can",
                "could",
                "would",
                "should",
                "will",
                "shall",
                "may",
                "might",
                "must",
                "that",
                "this",
                "these",
                "those",
                "it",
                "they",
                "them",
                "their",
                "his",
                "her",
                "he",
                "she",
                "I",
                "me",
                "my",
                "we",
                "us",
                "our",
            ]

            words = all_user_text.split()
            word_counts = {}

            for word in words:
                word = word.strip(".,?!:;()[]{}\"'")
                if word and len(word) > 3 and word not in common_words:
                    if word in word_counts:
                        word_counts[word] += 1
                    else:
                        word_counts[word] = 1

            # Get top keywords
            sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            top_keywords = [word for word, count in sorted_words[:10]]

            if top_keywords:
                summary += f"Key topics: {', '.join(top_keywords)}\n\n"

        # Add recent messages section (last 3 exchanges)
        summary += "RECENT MESSAGES\n"

        # Get the last exchanges (up to 3)
        max_exchanges = 3
        recent_exchanges = []

        # Start from the end and work backward
        for i in range(len(user_msgs) - 1, -1, -1):
            if len(recent_exchanges) >= max_exchanges:
                break

            user_msg = user_msgs[i]

            # Find corresponding assistant message
            assistant_response = None
            for j in range(len(assistant_msgs) - 1, -1, -1):
                if assistant_msgs[j].timestamp > user_msg.timestamp:
                    assistant_response = assistant_msgs[j]
                    break

            # Add the exchange
            exchange = {
                "user": user_msg.content,
                "assistant": (assistant_response.content if assistant_response else "No response"),
            }

            recent_exchanges.insert(0, exchange)

        # Add to summary
        for i, exchange in enumerate(recent_exchanges, 1):
            summary += f"Exchange {i}:\n"
            summary += f"User: {exchange['user']}\n"
            summary += f"Assistant: {exchange['assistant']}\n\n"

        # Add note about continuation
        summary += "NOTE: This is a continuation of a previous conversation. The context window was refreshed to allow for further interaction. Please maintain continuity with the topics and information above.\n"

        return summary


def main() -> None:
    """Test the RequestAssistant."""
    assistant = RequestAssistant()

    # Create a conversation
    conversation = assistant.create_conversation()
    conversation_id = conversation.conversation_id

    # Test a message
    assistant.process_message(
        conversation_id=conversation_id,
        message_content="How can you help me find my files?",
    )


    # Test a query
    assistant.process_message(
        conversation_id=conversation_id,
        message_content="Find documents about Indaleko",
    )



if __name__ == "__main__":
    main()
