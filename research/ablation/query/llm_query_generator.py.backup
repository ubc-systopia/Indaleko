"""
LLM-based query generator for the ablation framework.

This module provides functionality to generate realistic activity-based search
queries using Indaleko's LLM infrastructure and PromptManager.
"""

import json
import logging
import os
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Adjust path for Indaleko imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from query.utils.llm_connector.factory import LLMConnectorFactory

from research.ablation.models.activity import ActivityType
from research.ablation.query.generator import TestQuery


class LLMQueryGenerator:
    """
    Generator for realistic activity-based search queries using LLMs.

    This class leverages Indaleko's LLM infrastructure and PromptManager
    to generate diverse and realistic natural language queries that target
    specific activity data types.
    """

    QUERY_TEMPLATE_ID = "ablation_query_generator"

    def __init__(
        self,
        llm_provider: str = "anthropic",
        model: str | None = None,
        use_prompt_manager: bool = True,
        api_key: str | None = None,
        **kwargs,
    ):
        """Initialize the LLM query generator.

        Args:
            llm_provider: The LLM provider to use (anthropic, openai, etc.)
            model: Specific model to use (defaults to provider's default)
            use_prompt_manager: Whether to use PromptManager for prompt management
            **kwargs: Additional arguments for the LLM connector
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing LLM query generator with provider: {llm_provider}")

        # Store the provider type for later use
        self.llm_provider = llm_provider

        # Initialize LLM connector
        # Pass API key if provided
        if api_key:
            self.llm = LLMConnectorFactory.create_connector(
                connector_type=llm_provider, model=model, api_key=api_key, **kwargs,
            )
        else:
            self.llm = LLMConnectorFactory.create_connector(connector_type=llm_provider, model=model, **kwargs)
        self.logger.info(f"Successfully initialized {llm_provider} connector")

        # Store connector class name for later parameter adaptation
        if self.llm:
            self.connector_class_name = self.llm.__class__.__name__
            self.logger.info(f"Using connector class: {self.connector_class_name}")
        else:
            self.logger.critical("Failed to initialize LLM connector")

        # Initialize PromptManager if requested and available

        # Activity type descriptions for prompting
        self.activity_descriptions = {
            ActivityType.MUSIC: "music listening activities (e.g., songs, artists, albums, playlists)",
            ActivityType.LOCATION: "location activities (e.g., places, coordinates, visits)",
            ActivityType.TASK: "task management activities (e.g., to-dos, projects, deadlines)",
            ActivityType.COLLABORATION: "collaboration activities (e.g., meetings, shared documents, messages)",
            ActivityType.STORAGE: "storage activities (e.g., file operations, downloads, folders)",
            ActivityType.MEDIA: "media consumption activities (e.g., videos, streaming services, content)",
        }

        # Difficulty level descriptions
        self.difficulty_descriptions = {
            "easy": "simple queries with direct activity references and minimal context",
            "medium": "moderately complex queries with some contextual information",
            "hard": "complex queries with ambiguous references or multiple activity contexts",
        }

    def _ensure_query_template_exists(self):
        """Ensure the ablation query generator template exists in the database."""
        template = self.prompt_manager.get_template(self.QUERY_TEMPLATE_ID)

        if not template:
            self.logger.info(f"Creating {self.QUERY_TEMPLATE_ID} template")

            # Create layered template
            layered_template = [
                {
                    "type": "immutable_context",
                    "content": "You are an expert at generating realistic natural language search queries that people might use to find files and documents based on their activities and context.\n\nYou generate search queries that reference $activity_description.",
                    "order": 1,
                },
                {
                    "type": "hard_constraints",
                    "content": '1. Generate ONE realistic search query that a person might use to find files or documents based on $activity_description.\n2. The query should be $difficulty_level difficulty level ($difficulty_description).\n3. Respond in the following JSON format:\n```json\n{\n  "query": "the search query text",\n  "entities": {\n    "relevant_entities": ["entity1", "entity2", ...]\n  },\n  "difficulty": "$difficulty",\n  "activity_type": "$activity_type",\n  "reasoning": "brief explanation of how this query relates to the activity type"\n}\n```\n4. Do not include any other text in your response.',
                    "order": 2,
                },
                {
                    "type": "soft_preferences",
                    "content": "- Make the query sound natural, as if a real person would say it\n- Vary the query structure and complexity based on the difficulty level\n- Include specific entities that would be relevant to the activity type\n- For easier queries, be more direct about the activity context\n- For harder queries, be more subtle or ambiguous about the activity context",
                    "order": 3,
                },
            ]

            # Create template
            new_template = PromptTemplate(
                template_id=self.QUERY_TEMPLATE_ID,
                template_text=json.dumps(layered_template),
                template_type=PromptTemplateType.LAYERED,
                description="Template for generating ablation study search queries",
                created_at=datetime.now(UTC),
                version="1.0",
            )

            # Save template
            self.prompt_manager.save_template(new_template)

    def generate_queries(
        self,
        count: int,
        activity_types: list[ActivityType] | None = None,
        difficulty_levels: list[str] | None = None,
        temperature: float = 0.7,
    ) -> list[TestQuery]:
        """Generate test queries using the LLM.

        Args:
            count: Number of queries to generate
            activity_types: Optional list of specific activity types to target
            difficulty_levels: Optional list of difficulty levels to include
            temperature: Temperature for LLM generation (higher = more creative)

        Returns:
            List[TestQuery]: List of generated test queries
        """
        self.logger.info(f"Generating {count} test queries using LLM")

        # Default to all activity types if not specified
        if activity_types is None:
            activity_types = list(ActivityType)

        # Default to all difficulty levels if not specified
        if difficulty_levels is None:
            difficulty_levels = ["easy", "medium", "hard"]

        # Generate queries
        queries = []
        for i in range(count):
            # Select an activity type for this query
            act_type = activity_types[i % len(activity_types)]

            # Select difficulty level
            difficulty = difficulty_levels[i % len(difficulty_levels)]

            # Generate query using LLM
            query_text, metadata = self._generate_query_with_llm(act_type, difficulty, temperature)

            # If query generation failed, fail immediately (fail-stop approach)
            if not query_text:
                self.logger.error(f"CRITICAL: LLM query generation failed for query {i+1}")
                self.logger.error("This is required for proper ablation testing - fix the query generator")
                sys.exit(1)  # Fail-stop immediately - no fallbacks

            # Generate synthetic matching document IDs
            match_count = self._get_match_count_for_difficulty(difficulty)
            expected_matches = self._generate_expected_matches(act_type, match_count, metadata.get("entities", {}))

            # Create query object
            query = TestQuery(
                query_text=query_text,
                activity_types=[act_type],
                difficulty=difficulty,
                expected_matches=expected_matches,
                metadata=metadata,
            )

            queries.append(query)

        return queries

    def _generate_query_with_llm(
        self,
        activity_type: ActivityType,
        difficulty: str,
        temperature: float = 0.7,
    ) -> tuple[str, dict[str, Any]]:
        """Generate a single query using the LLM.

        Args:
            activity_type: The activity type to target
            difficulty: The difficulty level (easy, medium, hard)
            temperature: Temperature for generation (higher = more creative)

        Returns:
            Tuple[str, Dict[str, Any]]: The generated query and its metadata
        """
        # Skip if LLM is not available
        if not self.llm:
            return "", {}

        return self._generate_query_with_direct_prompt(activity_type, difficulty, temperature)

    def _generate_query_with_direct_prompt(
        self,
        activity_type: ActivityType,
        difficulty: str,
        temperature: float = 0.7,
    ) -> tuple[str, dict[str, Any]]:
        """Generate a query using direct prompts (no PromptManager).

        Args:
            activity_type: The activity type to target
            difficulty: The difficulty level (easy, medium, hard)
            temperature: Temperature for generation

        Returns:
            Tuple[str, Dict[str, Any]]: The generated query and its metadata
        """
        # Create system prompt
        system_prompt = f"""You are an expert at generating realistic natural language search queries that people might use to find files and documents based on their activities and context.

You generate search queries that reference {self.activity_descriptions[activity_type]}.

The queries should reflect how real users would naturally search for files based on their contextual memory of activities.
"""

        # Create user prompt
        user_prompt = f"""Generate ONE realistic search query that a person might use to find files or documents based on {self.activity_descriptions[activity_type]}.

The query should be {difficulty} difficulty level ({self.difficulty_descriptions[difficulty]}).

Respond in the following JSON format:
{{
  "query": "the search query text",
  "entities": {{
    "relevant_entities": ["entity1", "entity2", ...]
  }},
  "difficulty": "{difficulty}",
  "activity_type": "{activity_type.name}",
  "reasoning": "brief explanation of how this query relates to the activity type"
}}

Do not include any other text in your response.
"""

        try:
            # Use our enhanced get_completion method that handles different connector types
            response_text = self.get_completion(
                system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature,
            )

            # Extract JSON from the response (in case there's additional text)
            import re

            json_match = re.search(r"({.*})", response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                self.logger.debug(f"Extracted JSON: {json_text[:100]}...")
                response = json.loads(json_text)
            else:
                # Try parsing the whole response
                response = json.loads(response_text)

            query_text = response.get("query", "")

            # Clean up the query if needed
            if query_text.startswith('"') and query_text.endswith('"'):
                query_text = query_text[1:-1]

            # Extract metadata
            metadata = {
                "entities": response.get("entities", {}),
                "reasoning": response.get("reasoning", ""),
                "activity_type": response.get("activity_type", activity_type.name),
                "llm_generated": True,
                "prompt_manager_used": False,
            }

            return query_text, metadata

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return "", {}


    # Fallback query generation has been removed to enforce fail-stop approach
    # This follows scientific rigor where failures must be visible and addressed directly

    def _get_match_count_for_difficulty(self, difficulty: str) -> int:
        """Get the number of expected matches based on difficulty level.

        Args:
            difficulty: The difficulty level of the query

        Returns:
            int: The number of expected matches
        """
        # The harder the query, the fewer matches we expect
        difficulty_map = {
            "easy": random.randint(5, 15),  # Many matches for easy queries
            "medium": random.randint(3, 8),  # Moderate number of matches
            "hard": random.randint(1, 4),  # Few matches for hard queries
        }
        return difficulty_map.get(difficulty, 5)  # Default to 5 matches

    def _generate_expected_matches(
        self,
        activity_type: ActivityType,
        count: int,
        entity_data: dict[str, Any],
    ) -> list[str]:
        """Generate synthetic document IDs that should match a query.

        This method creates realistic document IDs with a consistent pattern
        that can be used as ground truth for evaluating query results.

        Args:
            activity_type: The activity type targeted by the query
            count: The number of matching documents to generate
            entity_data: Entity data from the query generation

        Returns:
            List[str]: List of document IDs that should match the query
        """
        matches = []

        # Create a deterministic but unique prefix for this activity type
        activity_prefix = f"ablation_{activity_type.name.lower()}"

        # Extract relevant entities from entity data
        entities = entity_data.get("relevant_entities", [])
        entity_string = "_".join(str(e).lower().replace(" ", "_") for e in entities[:2]) if entities else ""

        # Generate synthetic document IDs
        for i in range(count):
            # Create a document ID with a pattern like:
            # "Objects/ablation_music_taylor_swift_1"
            doc_id = f"Objects/{activity_prefix}"
            if entity_string:
                doc_id += f"_{entity_string}"
            doc_id += f"_{i+1}"

            matches.append(doc_id)

        return matches

    def get_completion(self, user_prompt: str, system_prompt: str | None = None, temperature: float = 0.7) -> str:
        """Get a completion from the LLM.

        This method is used by the EnhancedQueryGenerator to generate
        diverse queries and evaluate diversity.

        Args:
            user_prompt: The user prompt to send to the LLM
            system_prompt: Optional system prompt to provide context
            temperature: Temperature for generation (higher = more creative)

        Returns:
            str: The LLM's response text
        """
        # Skip if LLM is not available
        if not self.llm:
            self.logger.error("Cannot get completion: LLM not available")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

        from icecream import ic

        try:
            # Log which connector we're using to help debug parameter issues
            self.logger.info(ic(f"Getting completion using connector: {self.connector_class_name}"))

            # Different connectors expect different parameter formats and return values
            # We need to adapt our call based on the specific connector
            if self.connector_class_name == "AnthropicConnector":
                # Check the parameters by directly inspecting the method signature
                import inspect

                signature = inspect.signature(self.llm.get_completion)
                param_names = list(signature.parameters.keys())
                self.logger.info(ic(f"AnthropicConnector.get_completion params: {param_names}"))

                # Check return annotation to see if we should expect a tuple or single value
                return_tuple = False
                if hasattr(signature, "return_annotation"):
                    return_tuple = str(signature.return_annotation).startswith("tuple")
                    self.logger.info(f"Return annotation: {signature.return_annotation}, is tuple: {return_tuple}")

                # For the original connector, params are (context, question, schema)
                if "context" in param_names and "question" in param_names and "schema" in param_names:
                    self.logger.info("Using original AnthropicConnector format (context, question, schema)")
                    ic(f"system_prompt: {system_prompt}, user_prompt: {user_prompt}")
                    result = self.llm.get_completion(
                        context=system_prompt or "You are a helpful assistant.",
                        question=user_prompt,
                        schema={"type": "string"},
                    )
                # For the refactored connector, params are (system_prompt, user_prompt)
                elif "system_prompt" in param_names and "user_prompt" in param_names:
                    self.logger.info("Using refactored AnthropicConnector format (system_prompt, user_prompt)")
                    # Adding max_tokens parameter to avoid the streaming warning
                    result = self.llm.get_completion(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        max_tokens=10000  # Limiting token output to avoid streaming warning
                    )
                else:
                    # Fall back to a generic format as last resort
                    self.logger.warning(f"Unknown AnthropicConnector parameter format: {param_names}")
                    direct_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
                    result = self.llm.get_completion(prompt=direct_prompt, temperature=temperature)

                # Handle different return types (single value or tuple)
                if isinstance(result, tuple) and len(result) >= 1:
                    self.logger.info("Result is a tuple, extracting first element")
                    response_text = result[0]
                elif isinstance(result, dict):
                    self.logger.warning("Result is a dictionary, not a tuple or string as expected")
                    # Handle dict response, which shouldn't happen but is causing errors
                    if "text" in result:
                        self.logger.info("Found 'text' key in dictionary response, using that")
                        response_text = result["text"]
                    elif "content" in result:
                        self.logger.info("Found 'content' key in dictionary response, using that")
                        response_text = result["content"]
                    elif "message" in result:
                        self.logger.info("Found 'message' key in dictionary response, using that")
                        response_text = result["message"]
                    elif "answer" in result:
                        self.logger.info("Found 'answer' key in dictionary response, using that")
                        response_text = result["answer"]
                    else:
                        self.logger.error(f"CRITICAL: Dictionary response with no usable text field: {result}")
                        self.logger.error("This is required for proper ablation testing - fix the LLM connector")
                        sys.exit(1)  # Fail-stop immediately - no fallbacks
                else:
                    self.logger.info("Result is not a tuple or dict, using as is")
                    response_text = result

                # Final check that we have a string response
                if not isinstance(response_text, str):
                    self.logger.error(f"CRITICAL: Final response is not a string: {type(response_text)}")
                    self.logger.error("This is required for proper ablation testing - fix the LLM connector")
                    sys.exit(1)  # Fail-stop immediately - no fallbacks

                return response_text

            else:
                # For other connectors, use a standard format
                self.logger.info(f"Using standard format for {self.connector_class_name}")
                direct_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

                # Try get_completion first
                result = self.llm.get_completion(prompt=direct_prompt, temperature=temperature)

                # Handle different return types (single value or tuple)
                if isinstance(result, tuple) and len(result) >= 1:
                    self.logger.info("Result is a tuple, extracting first element")
                    response_text = result[0]
                elif isinstance(result, dict):
                    self.logger.warning("Result is a dictionary, not a tuple or string as expected")
                    # Handle dict response, which shouldn't happen but is causing errors
                    if "text" in result:
                        self.logger.info("Found 'text' key in dictionary response, using that")
                        response_text = result["text"]
                    elif "content" in result:
                        self.logger.info("Found 'content' key in dictionary response, using that")
                        response_text = result["content"]
                    elif "message" in result:
                        self.logger.info("Found 'message' key in dictionary response, using that")
                        response_text = result["message"]
                    elif "answer" in result:
                        self.logger.info("Found 'answer' key in dictionary response, using that")
                        response_text = result["answer"]
                    else:
                        self.logger.error(f"CRITICAL: Dictionary response with no usable text field: {result}")
                        self.logger.error("This is required for proper ablation testing - fix the LLM connector")
                        sys.exit(1)  # Fail-stop immediately - no fallbacks
                else:
                    self.logger.info("Result is not a tuple or dict, using as is")
                    response_text = result

                # Final check that we have a string response
                if not isinstance(response_text, str):
                    self.logger.error(f"CRITICAL: Final response is not a string: {type(response_text)}")
                    self.logger.error("This is required for proper ablation testing - fix the LLM connector")
                    sys.exit(1)  # Fail-stop immediately - no fallbacks

                return response_text

        except Exception as e:
            self.logger.error(f"CRITICAL: Unexpected error in get_completion: {e}")
            self.logger.error("This is required for proper ablation testing - fix the LLM connector infrastructure")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

    def generate_queries_for_activity_type(
        self,
        activity_type: str,
        count: int = 5,
        difficulty_levels: list[str] | None = None,
        temperature: float = 0.7,
    ) -> list[str]:
        """Generate queries for a specific activity type string.

        This is a convenience method used by the EnhancedQueryGenerator to
        generate simple text queries without the full TestQuery objects.

        Args:
            activity_type: String name of the activity type (e.g., "music", "location")
            count: Number of queries to generate
            difficulty_levels: Optional list of difficulty levels to include
            temperature: Temperature for generation (higher = more creative)

        Returns:
            List[str]: List of query strings for the activity type
        """
        self.logger.info(f"Generating {count} queries for activity type: {activity_type}")

        # Map string activity type to ActivityType enum
        activity_type_map = {
            "music": ActivityType.MUSIC,
            "location": ActivityType.LOCATION,
            "task": ActivityType.TASK,
            "collaboration": ActivityType.COLLABORATION,
            "storage": ActivityType.STORAGE,
            "media": ActivityType.MEDIA,
        }

        # Get the ActivityType enum value, defaulting to LOCATION if not found
        activity_enum = activity_type_map.get(activity_type.lower(), ActivityType.LOCATION)

        # Default to all difficulty levels if not specified
        if difficulty_levels is None:
            difficulty_levels = ["easy", "medium", "hard"]

        # Set up system and user prompts
        activity_description = self.activity_descriptions[activity_enum]
        system_prompt = f"""You are an expert at generating realistic search queries for {activity_description}.
Your queries should capture how real users would search for files based on their {activity_type} activities.
Make the queries diverse in structure, length, and complexity.
"""

        user_prompt = f"""Generate {count} realistic search queries related to {activity_description}.

Each query should be something a person might type to find files or documents related to their {activity_type} activities.
Make the queries diverse in format, structure, and complexity.
Some should be questions, some commands, some just keywords.
Vary the length from very short (2-3 words) to longer complex queries.

Just list {count} different search queries, numbered from 1 to {count}.
"""

        # Generate queries using our enhanced get_completion method
        response = self.get_completion(system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature)

        self.logger.info(f"Got response of length {len(response)} for {activity_type} queries")

        # Parse the response
        queries = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove the number/bullet and any trailing punctuation
                query = line.split(".", 1)[-1].strip() if "." in line else line
                query = query.split(")", 1)[-1].strip() if ")" in line else query
                query = query.lstrip("- ").strip()
                if query:
                    queries.append(query)

        # If parsing failed or returned no queries, fail immediately (fail-stop approach)
        if not queries:
            self.logger.error("CRITICAL: Failed to parse queries from LLM response")
            self.logger.error("This is required for proper ablation testing - fix the query generator")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

        self.logger.info(f"Generated {len(queries)} queries for {activity_type}")

        # Limit to requested count
        return queries[:count]
