"""
OpenAI Assistant API implementation for Indaleko.

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

from datetime import UTC, datetime
from typing import Any

import openai

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.state import ConversationState
from query.tools.base import ToolInput
from query.tools.registry import get_registry


# Import Query Context Integration components if available
try:
    from query.context.activity_provider import QueryActivityProvider
    from query.context.relationship import QueryRelationshipDetector

    HAS_QUERY_CONTEXT = True
except ImportError:
    HAS_QUERY_CONTEXT = False

# Import Recommendation Integration components if available
try:
    from query.context.recommendations.archivist_integration import (
        RecommendationArchivistIntegration,
    )
    from query.context.recommendations.engine import RecommendationEngine
    from query.tools.recommendation import RecommendationAssistantIntegration

    HAS_RECOMMENDATIONS = True
except ImportError:
    HAS_RECOMMENDATIONS = False


class IndalekoAssistant:
    """Indaleko Assistant implementation using OpenAI's Assistant API."""

    # System instructions for the assistant
    ASSISTANT_INSTRUCTIONS = """You are Indaleko Assistant, a helpful AI that helps users find and understand their personal data.

    Indaleko is a unified personal index system that helps users find, understand, and manage their data across multiple storage services and devices.

    Your role is to:
    1. Help users formulate queries to find their data
    2. Ask clarifying questions when needed
    3. Explain query results in a helpful way
    4. Suggest refinements to improve search results

    You have access to tools that can:
    - Parse natural language queries
    - Translate structured queries to AQL (ArangoDB Query Language)
    - Execute queries against the database
    - Analyze and present results

    Follow these guidelines:
    1. Be conversational but concise
    2. Ask clarifying questions when the query is ambiguous
    3. Explain what you're doing when using tools
    4. Format results in a clear, readable way
    5. For large result sets, summarize the key findings
    6. Suggest related queries when appropriate
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        enable_query_context: bool = True,
        enable_recommendations: bool = True,
        archivist_memory=None,
        recommendation_engine=None,
        debug: bool = False,
    ) -> None:
        """
        Initialize the Indaleko Assistant.

        Args:
            api_key (Optional[str]): The OpenAI API key. If None, will be loaded from config.
            model (str): The model to use for the assistant.
            enable_query_context (bool): Whether to enable Query Context Integration.
            enable_recommendations (bool): Whether to enable Recommendation Integration.
            archivist_memory: Optional existing ArchivistMemory instance.
            recommendation_engine: Optional existing RecommendationEngine instance.
            debug (bool): Whether to enable debug output.
        """
        self.api_key = api_key if api_key else self._load_api_key()
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        self.tool_registry = get_registry()
        self.assistant_id = None
        self.conversations = {}
        self.debug = debug

        # Initialize Query Context Integration if available and enabled
        self.query_context_provider = None
        self.query_relationship_detector = None

        if enable_query_context and HAS_QUERY_CONTEXT:
            self.query_context_provider = QueryActivityProvider(debug=debug)
            self.query_relationship_detector = QueryRelationshipDetector(debug=debug)
            ic("Query Context Integration enabled for Assistant.")

        # Initialize Recommendation Integration if available and enabled
        self.recommendation_engine = recommendation_engine
        self.archivist_integration = None
        self.recommendation_integration = None

        if enable_recommendations and HAS_RECOMMENDATIONS:
            # Initialize recommendation engine if not provided
            if not self.recommendation_engine:
                self.recommendation_engine = RecommendationEngine(debug=debug)

            # Try to initialize Archivist integration if available
            try:
                from query.memory.archivist_memory import ArchivistMemory
                from query.memory.proactive_archivist import ProactiveArchivist

                # Use provided archivist_memory or create a new one
                archivist_memory = archivist_memory or ArchivistMemory()
                proactive_archivist = ProactiveArchivist(archivist_memory)

                # Create archivist integration
                self.archivist_integration = RecommendationArchivistIntegration(
                    cli_instance=None,  # Not needed for this integration
                    archivist_memory=archivist_memory,
                    proactive_archivist=proactive_archivist,
                    recommendation_engine=self.recommendation_engine,
                    debug=debug,
                )

                ic("Archivist Integration enabled for Recommendations.")
            except ImportError:
                ic("Archivist Memory not available for Recommendation Integration.")

            # Create recommendation integration
            self.recommendation_integration = RecommendationAssistantIntegration(
                assistant=self,
                recommendation_engine=self.recommendation_engine,
                archivist_integration=self.archivist_integration,
            )

            ic("Recommendation Integration enabled for Assistant.")

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
        assistant_config_file = os.path.join(config_dir, "assistant-config.json")

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

        assistant = self.client.beta.assistants.create(
            name="Indaleko Assistant",
            description="An assistant for finding and understanding personal data in Indaleko",
            instructions=self.ASSISTANT_INSTRUCTIONS,
            model=self.model,
            tools=tool_definitions,
        )

        self.assistant_id = assistant.id
        ic(f"Created new assistant: {self.assistant_id}")

        # Save the configuration
        os.makedirs(config_dir, exist_ok=True)
        with open(assistant_config_file, "w") as f:
            json.dump({"assistant_id": self.assistant_id}, f)

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
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        ic(f"Executing tool: {function_name} with arguments: {arguments}")

        # Create the tool input
        tool_input = ToolInput(
            tool_name=function_name,
            parameters=arguments,
            conversation_id=conversation_id,
            invocation_id=tool_call["id"],
        )

        # Execute the tool
        result = self.tool_registry.execute_tool(tool_input)

        # Convert the result to a dictionary for the API
        if result.success:
            output = {"output": json.dumps(result.result, default=str)}
        else:
            output = {
                "error": result.error,
                "output": json.dumps({"error": result.error}, default=str),
            }

        return output

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

        # Record the query in the activity context system if enabled
        query_activity = None
        is_query = self._is_likely_query(message_content)

        if hasattr(self, "query_context_provider") and self.query_context_provider:
            if is_query:
                # Determine relationship with previous query if available
                relationship_type = None
                previous_query_id = None

                # Check if this conversation has previous messages
                previous_messages = [
                    msg for msg in conversation.messages if msg.role == "user" and msg != conversation.messages[-1]
                ]

                if previous_messages and self.query_relationship_detector:
                    previous_query = previous_messages[-1].content
                    current_query = message_content

                    # Detect relationship between current and previous query
                    relationship = self.query_relationship_detector.detect_relationship(
                        previous_query,
                        current_query,
                    )

                    if relationship:
                        relationship_type = relationship.value

                        # Get previous query activity ID from context variables if available
                        prev_query_activity_id = conversation.get_context_variable(
                            "last_query_activity_id",
                        )
                        if prev_query_activity_id:
                            previous_query_id = uuid.UUID(prev_query_activity_id)

                # Record the query as an activity
                query_activity = self.query_context_provider.record_query(
                    query_text=message_content,
                    relationship_type=relationship_type,
                    previous_query_id=previous_query_id,
                )

                # Store the query activity ID in context variables
                if query_activity:
                    conversation.set_context_variable(
                        "last_query_activity_id",
                        str(query_activity.query_id),
                    )
                    conversation.set_context_variable("is_query", True)

                    # Add as a referenced activity in conversation state
                    conversation.add_referenced_memory(
                        memory_id=str(query_activity.query_id),
                        memory_type="query_activity",
                        summary=f"Query: {message_content}",
                    )

        # Update recommendations if this is a query and recommendation integration is enabled
        if is_query and hasattr(self, "recommendation_integration") and self.recommendation_integration:
            # Update conversation context with recommendations
            self.recommendation_integration.update_conversation_context(
                conversation_id=conversation_id,
                current_query=message_content,
            )

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
        return self._wait_for_run(thread_id, run.id, conversation_id)


    def _wait_for_run(
        self,
        thread_id: str,
        run_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Wait for an assistant run to complete or require action.

        Args:
            thread_id (str): The thread ID.
            run_id (str): The run ID.
            conversation_id (str): The conversation ID.

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

                    for tool_call in tool_calls:
                        # Execute the tool
                        output = self.execute_tool(tool_call, conversation_id)

                        # Update query activity with results if this is a query_executor tool
                        if (
                            tool_call["function"]["name"] == "query_executor"
                            and hasattr(self, "query_context_provider")
                            and self.query_context_provider
                        ):

                            conversation = self.get_conversation(conversation_id)
                            if conversation and conversation.get_context_variable(
                                "is_query",
                                False,
                            ):
                                # Get the query activity ID from context variables
                                query_activity_id = conversation.get_context_variable(
                                    "last_query_activity_id",
                                )

                                if query_activity_id:
                                    # Extract result information
                                    try:
                                        result_data = json.loads(
                                            output.get("output", "{}"),
                                        )
                                        result_count = 0

                                        # Try to determine result count based on response format
                                        if isinstance(result_data, list):
                                            result_count = len(result_data)
                                        elif isinstance(result_data, dict) and "result" in result_data:
                                            if isinstance(result_data["result"], list):
                                                result_count = len(
                                                    result_data["result"],
                                                )

                                        # Update the query activity with results
                                        self.query_context_provider.update_query_results(
                                            query_id=uuid.UUID(query_activity_id),
                                            results={"count": result_count},
                                            execution_time=result_data.get(
                                                "execution_time",
                                                None,
                                            ),
                                        )
                                    except Exception as e:
                                        if self.debug:
                                            ic(f"Error updating query results: {e}")

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
                # Handle failure
                error_message = (
                    f"Run {run_id} {run.status}: {run.last_error.message if run.last_error else 'Unknown error'}"
                )

                # Add the error to our conversation state
                conversation = self.get_conversation(conversation_id)
                conversation.add_message("system", f"Error: {error_message}")

                return {
                    "conversation_id": conversation_id,
                    "response": error_message,
                    "action": "error",
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

    def _is_likely_query(self, message: str) -> bool:
        """
        Determine if a message is likely a query rather than a conversational message.

        Args:
            message (str): The message to analyze.

        Returns:
            bool: True if the message is likely a query, False otherwise.
        """
        # Define query indicators
        query_indicators = [
            "show me",
            "find",
            "search for",
            "look for",
            "get",
            "retrieve",
            "where is",
            "when did",
            "how many",
            "list all",
            "display",
            "what is",
            "who is",
            "which",
            "where are",
        ]

        # Check for question marks
        has_question_mark = "?" in message

        # Check for query indicators
        message_lower = message.lower()
        has_query_indicator = any(indicator in message_lower for indicator in query_indicators)

        # Check length (queries tend to be shorter)
        is_short = len(message.split()) < 15

        # Check for command-like syntax (not conversational)
        starts_with_verb = any(
            message_lower.startswith(verb) for verb in ["show", "find", "search", "get", "list", "display", "retrieve"]
        )

        # Calculate a score based on these factors
        score = 0
        if has_question_mark:
            score += 1
        if has_query_indicator:
            score += 2
        if is_short:
            score += 1
        if starts_with_verb:
            score += 2

        # If score is at least 2, it's likely a query
        return score >= 2
