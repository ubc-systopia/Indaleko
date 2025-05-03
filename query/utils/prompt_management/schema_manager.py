"""
Schema Manager for optimizing schema representations in prompts.

Project Indaleko.
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

import hashlib
import json
import re
import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SchemaStats(BaseModel):
    """Statistics about a schema optimization."""

    original_size: int
    optimized_size: int
    token_reduction: int
    properties_removed: int
    descriptions_shortened: int
    whitespace_removed: int
    duplicates_eliminated: int

    @property
    def reduction_percentage(self) -> float:
        """Calculate the percentage reduction in size."""
        if self.original_size == 0:
            return 0.0
        return (self.original_size - self.optimized_size) / self.original_size * 100.0


class SchemaManager:
    """
    Manages schema optimization for LLM prompts.

    This class provides tools for optimizing JSON schemas to reduce token count
    while preserving semantic meaning, including:

    1. De-duplication of repeated schema structures
    2. Whitespace normalization
    3. Description shortening
    4. Optional property elimination
    5. Type simplification

    The goal is to reduce token usage while maintaining schema validity.
    """

    def __init__(self, max_cache_size: int = 100):
        """
        Initialize the SchemaManager.

        Args:
            max_cache_size: Maximum number of schemas to cache
        """
        self._schema_cache: dict[str, dict[str, Any]] = {}
        self._stats_cache: dict[str, SchemaStats] = {}
        self._max_cache_size = max_cache_size

    def _get_schema_hash(self, schema: dict[str, Any]) -> str:
        """
        Generate a deterministic hash for a schema.

        Args:
            schema: The schema to hash

        Returns:
            Hash string of the schema
        """
        schema_json = json.dumps(schema, sort_keys=True)
        return hashlib.md5(schema_json.encode()).hexdigest()

    def _prune_cache(self) -> None:
        """
        Remove old entries from the cache if it exceeds the maximum size.
        """
        if len(self._schema_cache) > self._max_cache_size:
            # Simple strategy: remove the first N/4 entries
            prune_count = self._max_cache_size // 4
            keys_to_remove = list(self._schema_cache.keys())[:prune_count]

            for key in keys_to_remove:
                self._schema_cache.pop(key, None)
                self._stats_cache.pop(key, None)

    def _normalize_whitespace(self, schema_str: str) -> str:
        """
        Normalize whitespace in a JSON schema string.

        Args:
            schema_str: JSON schema string

        Returns:
            Normalized schema string
        """
        # Apply regex substitutions for whitespace normalization
        # Remove newlines and extra spaces
        normalized = re.sub(r"\s+", " ", schema_str)

        # Remove spaces after/before brackets and braces
        normalized = re.sub(r"\s*{\s*", "{", normalized)
        normalized = re.sub(r"\s*}\s*", "}", normalized)
        normalized = re.sub(r"\s*\[\s*", "[", normalized)
        normalized = re.sub(r"\s*\]\s*", "]", normalized)

        # Remove spaces around colons and commas
        normalized = re.sub(r"\s*:\s*", ":", normalized)
        normalized = re.sub(r"\s*,\s*", ",", normalized)

        return normalized

    def _shorten_description(self, description: str, max_length: int = 100) -> str:
        """
        Shorten a schema description while preserving meaning.

        Args:
            description: The schema description
            max_length: Maximum length for the description

        Returns:
            Shortened description
        """
        # Constants
        MIN_SPLIT_LENGTH = 20  # Minimum length to use split method with ellipsis
        ELLIPSIS = "..."
        ELLIPSIS_LENGTH = len(ELLIPSIS)
        
        if not description or len(description) <= max_length:
            return description

        # Keep first part and last part, add ellipsis in the middle
        if max_length < MIN_SPLIT_LENGTH:
            # If very short, just truncate with ellipsis
            return description[: max_length - ELLIPSIS_LENGTH] + ELLIPSIS

        # Otherwise, keep beginning and end
        half_length = (max_length - ELLIPSIS_LENGTH) // 2
        return description[:half_length] + ELLIPSIS + description[-half_length:]

    def _simplify_types(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Simplify complex type definitions when possible.

        Args:
            schema: The schema to simplify

        Returns:
            Simplified schema
        """
        result = schema.copy()

        # Constants
        nullable_type_count = 2  # Number of types in a nullable field (e.g., ["string", "null"])
        
        # Process type field if present
        if "type" in result and isinstance(result["type"], list):
            # If "null" is one of the types, convert to ["type", null]
            types = result["type"]
            if len(types) == nullable_type_count and "null" in types:
                other_type = next(t for t in types if t != "null")
                result["type"] = other_type
                result["nullable"] = True

        # Process properties recursively
        if "properties" in result and isinstance(result["properties"], dict):
            for prop_name, prop_schema in result["properties"].items():
                if isinstance(prop_schema, dict):
                    result["properties"][prop_name] = self._simplify_types(prop_schema)

        # Process items for arrays
        if "items" in result and isinstance(result["items"], dict):
            result["items"] = self._simplify_types(result["items"])

        return result

    def _deduplicate_definitions(
        self, schema: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Find and deduplicate repeated schema structures.

        Args:
            schema: The schema to deduplicate

        Returns:
            Tuple of (deduplicated schema, definitions dictionary)
        """
        # This is a simplified implementation
        # A more sophisticated version would identify common patterns
        result = schema.copy()
        definitions = {}

        # Currently just extracting existing definitions
        if "$defs" in result:
            definitions.update(result.pop("$defs", {}))
        if "definitions" in result:
            definitions.update(result.pop("definitions", {}))

        # Future enhancement: Implement pattern detection for repeated structures

        return result, definitions

    def optimize_schema(
        self, schema: dict[str, Any], token_budget: int | None = None
    ) -> dict[str, Any]:
        """
        Optimize a schema to reduce token count.

        Args:
            schema: The schema to optimize
            token_budget: Optional maximum token count (aggressive optimization if provided)

        Returns:
            Optimized schema
        """
        # Check cache first
        schema_hash = self._get_schema_hash(schema)
        if schema_hash in self._schema_cache:
            logger.debug("Schema cache hit")
            return self._schema_cache[schema_hash]

        # Make a deep copy to avoid modifying the original
        working_schema = json.loads(json.dumps(schema))
        original_size = len(json.dumps(working_schema))

        # Track optimization statistics
        stats = SchemaStats(
            original_size=original_size,
            optimized_size=0,
            token_reduction=0,
            properties_removed=0,
            descriptions_shortened=0,
            whitespace_removed=0,
            duplicates_eliminated=0,
        )

        # 1. Extract and deduplicate definitions
        deduplicated_schema, definitions = self._deduplicate_definitions(working_schema)
        if definitions:
            deduplicated_schema["$defs"] = definitions
            stats.duplicates_eliminated = len(definitions)

        # 2. Simplify types
        simplified_schema = self._simplify_types(deduplicated_schema)

        # 3. Shorten descriptions
        def process_descriptions(obj: dict[str, Any]) -> int:
            count = 0
            if "description" in obj and isinstance(obj["description"], str):
                original = obj["description"]
                obj["description"] = self._shorten_description(original)
                if obj["description"] != original:
                    count += 1

            # Process nested properties
            if "properties" in obj and isinstance(obj["properties"], dict):
                for prop_schema in obj["properties"].values():
                    if isinstance(prop_schema, dict):
                        count += process_descriptions(prop_schema)

            # Process items for arrays
            if "items" in obj and isinstance(obj["items"], dict):
                count += process_descriptions(obj["items"])

            return count

        stats.descriptions_shortened = process_descriptions(simplified_schema)

        # 4. Remove optional properties if we exceed token budget
        if token_budget is not None:
            # Future enhancement: Implement token counting and selective property removal
            pass

        # 5. Normalize whitespace in the JSON representation
        final_json = json.dumps(simplified_schema)
        compressed_json = self._normalize_whitespace(final_json)
        stats.whitespace_removed = len(final_json) - len(compressed_json)

        # Convert back to dictionary
        optimized_schema = json.loads(compressed_json)

        # Update stats
        stats.optimized_size = len(compressed_json)
        stats.token_reduction = stats.original_size - stats.optimized_size

        # Cache the result
        self._schema_cache[schema_hash] = optimized_schema
        self._stats_cache[schema_hash] = stats
        self._prune_cache()

        return optimized_schema

    def get_optimization_stats(self, schema: dict[str, Any]) -> SchemaStats | None:
        """
        Get optimization statistics for a schema.

        Args:
            schema: The schema to get stats for

        Returns:
            Optimization statistics if available, None otherwise
        """
        schema_hash = self._get_schema_hash(schema)
        return self._stats_cache.get(schema_hash)


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    example_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The person's name (first, middle, last).",
            },
            "age": {"type": ["integer", "null"], "description": "The age of the person in years."},
            "address": {
                "type": "object",
                "properties": {
                    "street": {
                        "type": "string",
                        "description": "Street address with building number.",
                    },
                    "city": {"type": "string", "description": "The city where the person resides."},
                },
            },
        },
    }

    schema_manager = SchemaManager()
    optimized = schema_manager.optimize_schema(example_schema)
    stats = schema_manager.get_optimization_stats(example_schema)

    # Using % formatting as recommended instead of f-strings for logging
    logger.info("Schema optimization complete: %.2f%% reduction", stats.reduction_percentage)
