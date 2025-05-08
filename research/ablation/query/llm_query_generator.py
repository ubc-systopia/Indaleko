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
from query.utils.prompt_management.data_models.base import (
    PromptTemplate,
    PromptTemplateType,
)
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable
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
        self, llm_provider: str = "anthropic", model: str | None = None, use_prompt_manager: bool = True, **kwargs,
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

        # Initialize LLM connector
        try:
            self.llm = LLMConnectorFactory.create_connector(connector_type=llm_provider, model=model, **kwargs)
            self.logger.info(f"Successfully initialized {llm_provider} connector")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM connector: {e}")
            self.llm = None
            raise RuntimeError(f"Failed to initialize LLM connector: {e}")

        # Initialize PromptManager if requested
        self.use_prompt_manager = use_prompt_manager
        if use_prompt_manager:
            try:
                self.prompt_manager = PromptManager()
                self._ensure_query_template_exists()
                self.logger.info("Successfully initialized PromptManager")
            except Exception as e:
                self.logger.warning(f"Failed to initialize PromptManager, falling back to direct prompts: {e}")
                self.use_prompt_manager = False

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

            # If query generation failed, use a fallback approach
            if not query_text:
                self.logger.warning(f"LLM query generation failed, using fallback for query {i+1}")
                query_text, metadata = self._generate_fallback_query(act_type, difficulty)

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
        self, activity_type: ActivityType, difficulty: str, temperature: float = 0.7,
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

        if self.use_prompt_manager:
            return self._generate_query_with_prompt_manager(activity_type, difficulty, temperature)
        else:
            return self._generate_query_with_direct_prompt(activity_type, difficulty, temperature)

    def _generate_query_with_prompt_manager(
        self, activity_type: ActivityType, difficulty: str, temperature: float = 0.7,
    ) -> tuple[str, dict[str, Any]]:
        """Generate a query using the PromptManager.

        Args:
            activity_type: The activity type to target
            difficulty: The difficulty level (easy, medium, hard)
            temperature: Temperature for generation

        Returns:
            Tuple[str, Dict[str, Any]]: The generated query and its metadata
        """
        try:
            # Create variables for the template
            variables = [
                PromptVariable(name="activity_description", value=self.activity_descriptions[activity_type]),
                PromptVariable(name="difficulty_level", value=difficulty),
                PromptVariable(name="difficulty_description", value=self.difficulty_descriptions[difficulty]),
                PromptVariable(name="difficulty", value=difficulty),
                PromptVariable(name="activity_type", value=activity_type.name),
            ]

            # Generate prompt using PromptManager
            prompt_result = self.prompt_manager.create_prompt(
                template_id=self.QUERY_TEMPLATE_ID,
                variables=variables,
                optimize=True,
                evaluate_stability=True,
            )

            # Log token usage
            self.logger.debug(
                f"Generated prompt with {prompt_result.token_count} tokens "
                + f"(saved {prompt_result.token_savings} tokens)",
            )

            # Get LLM completion
            response_text, _ = self.llm.get_completion(user_prompt=prompt_result.prompt, temperature=temperature)

            # Parse JSON response
            try:
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
                    "prompt_manager_used": True,
                    "prompt_stability_score": prompt_result.stability_score,
                }

                return query_text, metadata

            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing LLM response: {e}")
                self.logger.debug(f"Raw response: {response_text}")
                return "", {}

        except Exception as e:
            self.logger.error(f"Error generating query with PromptManager: {e}")
            return "", {}

    def _generate_query_with_direct_prompt(
        self, activity_type: ActivityType, difficulty: str, temperature: float = 0.7,
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
            # Get completion from LLM
            response_text, _ = self.llm.get_completion(
                system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature,
            )

            # Parse JSON response
            try:
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

        except Exception as e:
            self.logger.error(f"Error generating query with direct prompt: {e}")
            return "", {}

    def _generate_fallback_query(self, activity_type: ActivityType, difficulty: str) -> tuple[str, dict[str, Any]]:
        """Generate a fallback query when LLM generation fails.

        Args:
            activity_type: The activity type to target
            difficulty: The difficulty level (easy, medium, hard)

        Returns:
            Tuple[str, Dict[str, Any]]: The generated query and its metadata
        """
        # Templates for each activity type
        templates = {
            ActivityType.MUSIC: [
                "Find documents I worked on while listening to {artist}",
                "Show me files I edited while listening to {genre} music",
                "What documents did I work on while {song} was playing?",
            ],
            ActivityType.LOCATION: [
                "Show files I accessed at {location}",
                "Find documents I worked on while at {location}",
                "What files did I edit when I was at {location}?",
            ],
            ActivityType.TASK: [
                "Find documents related to my {task_name} task",
                "Show me files associated with the {task_name} project",
                "What documents are part of my {task_name} work?",
            ],
            ActivityType.COLLABORATION: [
                "Show me files I shared during the {meeting_name} meeting",
                "Find documents we discussed in the {meeting_name} call",
                "What files did I present at the {meeting_name} meeting?",
            ],
            ActivityType.STORAGE: [
                "Find documents I saved in my {folder_name} folder",
                "Show me files I moved to the {folder_name} directory",
                "What documents did I download to {folder_name}?",
            ],
            ActivityType.MEDIA: [
                "Show me files I worked on while watching {video_name}",
                "Find documents I edited while streaming on {platform}",
                "What files did I access while watching {video_name}?",
            ],
        }

        # Parameters for each activity type
        parameters = {
            ActivityType.MUSIC: {
                "artist": ["Taylor Swift", "The Beatles", "Beyoncé", "Ed Sheeran", "Drake"],
                "genre": ["pop", "rock", "classical", "jazz", "hip hop"],
                "song": ["Heat Waves", "Blinding Lights", "Bad Habits", "Stay", "Good 4 U"],
            },
            ActivityType.LOCATION: {"location": ["home", "work", "coffee shop", "library", "airport", "hotel"]},
            ActivityType.TASK: {"task_name": ["coding", "writing", "research", "design", "presentation", "budget"]},
            ActivityType.COLLABORATION: {
                "meeting_name": ["team", "client", "strategy", "project", "weekly", "planning"],
            },
            ActivityType.STORAGE: {"folder_name": ["downloads", "documents", "projects", "work", "personal", "shared"]},
            ActivityType.MEDIA: {
                "video_name": ["YouTube videos", "Netflix", "tutorials", "lectures", "documentaries"],
                "platform": ["YouTube", "Netflix", "Hulu", "Disney+", "Prime Video"],
            },
        }

        # Select template and fill in parameters
        template = random.choice(templates[activity_type])
        param_values = {}

        # Extract parameter names from template
        import re

        param_names = re.findall(r"\{(\w+)\}", template)

        # Fill in parameters
        for param_name in param_names:
            if param_name in parameters[activity_type]:
                param_values[param_name] = random.choice(parameters[activity_type][param_name])
            else:
                param_values[param_name] = f"unknown-{param_name}"

        # Fill in template
        query_text = template
        for param_name, param_value in param_values.items():
            query_text = query_text.replace(f"{{{param_name}}}", param_value)

        # Create metadata
        metadata = {
            "template": template,
            "parameters": param_values,
            "entities": {"relevant_entities": list(param_values.values())},
            "activity_type": activity_type.name,
            "llm_generated": False,
            "fallback_used": True,
        }

        return query_text, metadata

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
        self, activity_type: ActivityType, count: int, entity_data: dict[str, Any],
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
