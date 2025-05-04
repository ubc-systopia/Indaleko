"""
Prompt Manager for layered template processing and optimization.

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

import json
import logging
import re
from datetime import UTC, datetime
from functools import lru_cache
from string import Template
from typing import Any

from pydantic import BaseModel, Field, validator

from data_models.base import IndalekoBaseModel
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections
from query.utils.prompt_management.ayni.guard import AyniGuard
from query.utils.prompt_management.data_models.base import (
    PromptTemplate,
    PromptTemplateType,
)
from query.utils.prompt_management.schema_manager import SchemaManager

logger = logging.getLogger(__name__)


class PromptVariable(BaseModel):
    """A variable that can be used in a prompt template."""

    name: str
    value: Any
    description: str | None = None
    required: bool = True


class PromptEvaluationResult(BaseModel):
    """Result of prompt evaluation."""

    prompt: str
    token_count: int
    original_token_count: int
    token_savings: int
    stability_score: float
    stability_details: dict[str, Any]
    prompt_hash: str


class PromptLayer(BaseModel):
    """A layer of the prompt template."""

    layer_type: str  # "immutable_context", "hard_constraints", "soft_preferences", "trust_contract"
    content: str
    order: int

    @validator("layer_type")
    def validate_layer_type(cls, v: str) -> str:
        """Validate the layer type."""
        valid_types = ["immutable_context", "hard_constraints", "soft_preferences", "trust_contract"]
        if v not in valid_types:
            raise ValueError(f"Layer type must be one of {valid_types}")
        return v


class PromptMetrics(IndalekoBaseModel):
    """Metrics for prompt optimization."""

    prompt_hash: str
    template_id: str
    token_count: int
    original_token_count: int
    token_savings: int
    stability_score: float
    evaluation_time_ms: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection


class PromptManager:
    """
    Manages prompt creation, optimization, and evaluation.

    This class provides tools for:
    1. Template-based prompt generation
    2. Layered prompt composition
    3. Variable binding with validation
    4. Token optimization
    5. Stability evaluation with AyniGuard

    The goal is to standardize prompt creation while reducing token usage
    and ensuring high-quality prompts.
    """

    def __init__(
        self,
        db_instance: IndalekoCollection | None = None,
        ayni_guard: AyniGuard | None = None,
        schema_manager: SchemaManager | None = None,
        token_estimator: callable | None = None,
    ) -> None:
        """
        Initialize PromptManager.

        Args:
            db_instance: Database connection instance
            ayni_guard: AyniGuard instance for stability evaluation
            schema_manager: SchemaManager for schema optimization
            token_estimator: Function for estimating token count
        """
        self.db = db_instance or IndalekoCollection.get_db()
        self.ayni_guard = ayni_guard or AyniGuard(db_instance=self.db)
        self.schema_manager = schema_manager or SchemaManager()
        self._token_estimator = token_estimator or self._default_token_estimator
        self._template_cache = {}  # Cache for compiled templates
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Ensure required collections exist in database."""
        collections = [
            IndalekoDBCollections.Indaleko_Prompt_Templates_Collection,
            IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection,
        ]

        for collection_name in collections:
            self.db.get_collection(collection_name)

    def _default_token_estimator(self, text: str) -> int:
        """
        Default token count estimation function.

        This is a very simple estimator that uses whitespace as a rough
        approximation. For production, replace with a model-specific
        tokenizer.

        Args:
            text: Text to estimate token count for

        Returns:
            Estimated token count
        """
        # Rough approximation, replace with model-specific tokenizer
        # GPT tokenizers typically count about 0.75 tokens per word
        words = text.split()
        return len(words) + int(len(words) * 0.3)

    @lru_cache(maxsize=1024)
    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text with LRU caching for performance.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Replace multiple spaces with single space - collapse all whitespace sequences
        normalized = re.sub(r"\s+", " ", text)

        # Remove spaces at start of lines
        normalized = re.sub(r"^ +", "", normalized, flags=re.MULTILINE)

        # Replace multiple newlines with single newline - more aggressive
        normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)

        # Apply more aggressive whitespace optimization
        normalized = re.sub(r"[\t ]+", " ", normalized)

        # Remove trailing whitespace and leading/trailing spaces
        normalized = normalized.strip()

        return normalized

    def _compile_template(self, template_str: str) -> Template:
        """
        Compile and cache a template for reuse.

        Args:
            template_str: Template string to compile

        Returns:
            Compiled Template object
        """
        # Check if template is already in cache
        if template_str in self._template_cache:
            return self._template_cache[template_str]

        # Compile template
        compiled = Template(template_str)

        # Cache for future use (up to a reasonable size)
        if len(self._template_cache) < 1000:  # Prevent unbounded growth
            self._template_cache[template_str] = compiled

        return compiled

    def _bind_variables(self, template: str, variables: list[PromptVariable]) -> str:
        """
        Bind variables to template with optimized approach.

        Args:
            template: Template string with $var placeholders
            variables: List of variables to bind

        Returns:
            Template with variables substituted

        Raises:
            ValueError: If required variables are missing
        """
        # Create dictionary of variable values - convert values to string at binding time
        var_dict = {var.name: str(var.value) for var in variables}

        # Fast path: if there are no variables, return template as is
        if not var_dict:
            return template

        # Fast check: if no variables in template, return as is
        if "$" not in template:
            return template

        # Optimized variable detection - match only once
        template_vars = set(re.findall(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", template))

        # Fast check for missing variables
        missing_vars = [
            var_name
            for var_name in template_vars
            if var_name not in var_dict and any(v.required and v.name == var_name for v in variables)
        ]

        if missing_vars:
            raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")

        # Get or compile template
        compiled_template = self._compile_template(template)

        # Apply substitution with the compiled template
        return compiled_template.safe_substitute(var_dict)

    @lru_cache(maxsize=128)
    def _compose_layer_header(self, layer_type: str, content: str) -> str:
        """
        Compose a layer header with content - cached for reuse.

        Args:
            layer_type: Type of layer
            content: Layer content

        Returns:
            Formatted layer with header
        """
        if layer_type == "immutable_context":
            return f"# Context\n{content}"
        elif layer_type == "hard_constraints":
            return f"# Requirements\n{content}"
        elif layer_type == "soft_preferences":
            return f"# Preferences\n{content}"
        elif layer_type == "trust_contract":
            return f"# Agreement\n{content}"
        else:
            return f"# {layer_type.replace('_', ' ').title()}\n{content}"

    def _compose_layered_prompt(self, layers: list[PromptLayer]) -> str:
        """
        Compose a prompt from ordered layers with optimized processing.

        Args:
            layers: List of prompt layers

        Returns:
            Composed prompt
        """
        # Fast path for single layer
        if len(layers) == 1:
            layer = layers[0]
            return self._compose_layer_header(layer.layer_type, layer.content)

        # Sort layers by order
        sorted_layers = sorted(layers, key=lambda layer: layer.order)

        # Pre-allocate the required capacity for better performance
        composed_parts = []
        composed_parts.extend(self._compose_layer_header(layer.layer_type, layer.content) for layer in sorted_layers)

        return "\n\n".join(composed_parts)

    @lru_cache(maxsize=128)
    def _optimize_schema(self, schema_str: str) -> str:
        """
        Optimize a JSON schema string with caching.

        Args:
            schema_str: JSON schema string

        Returns:
            Optimized schema string or original if invalid
        """
        try:
            schema = json.loads(schema_str)

            # Skip optimization if it doesn't look like a schema
            if "type" not in schema and "properties" not in schema:
                return schema_str

            optimized = self.schema_manager.optimize_schema(schema)
            return json.dumps(optimized, indent=2)
        except (json.JSONDecodeError, Exception):
            # If we can't parse it, return the original
            return schema_str

    def _optimize_schema_objects(self, text: str) -> str:
        """
        Find and optimize JSON schema objects in text with cached processing.

        Args:
            text: Text that may contain JSON schemas

        Returns:
            Text with optimized JSON schemas
        """
        # Fast path for non-schema content
        if "```json" not in text and "```\n{" not in text:
            return text

        # Look for JSON schema pattern
        schema_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"

        def replace_schema(match):
            schema_str = match.group(1)
            optimized = self._optimize_schema(schema_str)

            # Only format if it was actually optimized
            if optimized != schema_str:
                return f"```json\n{optimized}\n```"
            else:
                return match.group(0)

        return re.sub(schema_pattern, replace_schema, text)

    def get_template(self, template_id: str) -> PromptTemplate | None:
        """
        Get a prompt template by ID.

        Args:
            template_id: Template ID

        Returns:
            Template or None if not found
        """
        collection = self.db.collection(IndalekoDBCollections.Indaleko_Prompt_Templates_Collection)

        cursor = collection.find({"_key": template_id})
        if cursor.count() > 0:
            template_data = cursor.next()
            return PromptTemplate(**template_data)

        return None

    def save_template(self, template: PromptTemplate) -> str:
        """
        Save a template to the database.

        Args:
            template: Template to save

        Returns:
            Template ID
        """
        collection = self.db.collection(IndalekoDBCollections.Indaleko_Prompt_Templates_Collection)

        # Convert to dict for storing in database
        template_dict = template.dict()

        # Insert or update
        if hasattr(template, "_key") and template._key:
            template_dict["_key"] = template._key
            collection.update(template_dict)
            return template._key
        else:
            result = collection.insert(template_dict)
            return result["_key"]

    def create_prompt(
        self,
        template_id: str,
        variables: list[PromptVariable],
        optimize: bool = True,
        evaluate_stability: bool = True,
    ) -> PromptEvaluationResult:
        """
        Create a prompt from a template.

        Args:
            template_id: Template ID
            variables: List of variables to bind
            optimize: Whether to optimize the prompt
            evaluate_stability: Whether to evaluate prompt stability

        Returns:
            Prompt evaluation result

        Raises:
            ValueError: If template is not found or variables are invalid
        """
        # Get the template
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Bind variables to template
        if template.template_type == PromptTemplateType.SIMPLE:
            prompt = self._bind_variables(template.template_text, variables)
        elif template.template_type == PromptTemplateType.LAYERED:
            # Parse the template text as JSON
            try:
                layers_data = json.loads(template.template_text)
                layers = []

                for layer_data in layers_data:
                    # Bind variables to each layer
                    content = self._bind_variables(layer_data["content"], variables)
                    layers.append(
                        PromptLayer(
                            layer_type=layer_data["type"],
                            content=content,
                            order=layer_data["order"],
                        ),
                    )

                prompt = self._compose_layered_prompt(layers)
            except json.JSONDecodeError:
                raise ValueError("Invalid layered template format")
        else:
            raise ValueError(f"Unsupported template type: {template.template_type}")

        # Get token count before optimization
        original_token_count = self._token_estimator(prompt)

        # Optimize if requested
        if optimize:
            # Normalize whitespace
            prompt = self._normalize_whitespace(prompt)

            # Optimize any JSON schemas in the prompt
            prompt = self._optimize_schema_objects(prompt)

        # Get token count after optimization
        token_count = self._token_estimator(prompt)
        token_savings = original_token_count - token_count

        # Evaluate stability if requested
        stability_score = 1.0
        stability_details = {}
        prompt_hash = ""

        if evaluate_stability:
            # Create structured prompt for AyniGuard
            structured_prompt = self._create_structured_prompt(prompt)

            # Evaluate stability
            evaluation = self.ayni_guard.evaluate(structured_prompt)
            prompt_hash = self.ayni_guard.compute_prompt_hash(structured_prompt)

            stability_score = evaluation.composite_score
            stability_details = evaluation.details

            # Record metrics
            self._record_metrics(
                prompt_hash=prompt_hash,
                template_id=template_id,
                token_count=token_count,
                original_token_count=original_token_count,
                token_savings=token_savings,
                stability_score=stability_score,
            )

        return PromptEvaluationResult(
            prompt=prompt,
            token_count=token_count,
            original_token_count=original_token_count,
            token_savings=token_savings,
            stability_score=stability_score,
            stability_details=stability_details,
            prompt_hash=prompt_hash,
        )

    def _create_structured_prompt(self, prompt: str) -> dict[str, Any]:
        """
        Convert a text prompt to a structured prompt for AyniGuard.

        Args:
            prompt: Prompt text

        Returns:
            Structured prompt
        """
        # Simple parsing of sections
        sections = {}

        # Extract sections by headings
        context_match = re.search(r"# Context\s+(.*?)(?=# |$)", prompt, re.DOTALL)
        if context_match:
            sections["context"] = context_match.group(1).strip()

        requirements_match = re.search(r"# Requirements\s+(.*?)(?=# |$)", prompt, re.DOTALL)
        if requirements_match:
            sections["constraints"] = requirements_match.group(1).strip()

        preferences_match = re.search(r"# Preferences\s+(.*?)(?=# |$)", prompt, re.DOTALL)
        if preferences_match:
            sections["preferences"] = preferences_match.group(1).strip()

        agreement_match = re.search(r"# Agreement\s+(.*?)(?=# |$)", prompt, re.DOTALL)
        if agreement_match:
            sections["trust_contract"] = {"mutual_intent": agreement_match.group(1).strip()}

        # If no sections were found, use the whole prompt as context
        if not sections:
            sections["context"] = prompt

        return sections

    def _record_metrics(
        self,
        prompt_hash: str,
        template_id: str,
        token_count: int,
        original_token_count: int,
        token_savings: int,
        stability_score: float,
    ) -> None:
        """
        Record optimization metrics.

        Args:
            prompt_hash: Unique hash for the prompt
            template_id: Template ID
            token_count: Final token count
            original_token_count: Original token count before optimization
            token_savings: Token count saved by optimization
            stability_score: Prompt stability score
        """
        metrics = PromptMetrics(
            prompt_hash=prompt_hash,
            template_id=template_id,
            token_count=token_count,
            original_token_count=original_token_count,
            token_savings=token_savings,
            stability_score=stability_score,
            evaluation_time_ms=0,  # Not tracked in this implementation
        )

        collection = self.db.collection(IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection)
        collection.insert(metrics.dict())

    def get_metrics(self, template_id: str | None = None) -> list[dict[str, Any]]:
        """
        Get optimization metrics.

        Args:
            template_id: Optional template ID to filter by

        Returns:
            List of metrics
        """
        collection = self.db.collection(IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection)

        if template_id:
            cursor = collection.find({"template_id": template_id})
        else:
            cursor = collection.all()

        return [doc for doc in cursor]

    def calculate_token_savings(self, template_id: str | None = None) -> dict[str, Any]:
        """
        Calculate token savings statistics.

        Args:
            template_id: Optional template ID to filter by

        Returns:
            Dictionary with token savings statistics
        """
        metrics = self.get_metrics(template_id)

        if not metrics:
            return {
                "total_prompts": 0,
                "total_token_savings": 0,
                "total_tokens_before": 0,
                "total_tokens_after": 0,
                "average_savings_percent": 0,
                "average_stability_score": 0,
            }

        total_prompts = len(metrics)
        total_token_savings = sum(m["token_savings"] for m in metrics)
        total_tokens_before = sum(m["original_token_count"] for m in metrics)
        total_tokens_after = sum(m["token_count"] for m in metrics)

        average_savings_percent = 0
        if total_tokens_before > 0:
            average_savings_percent = (total_token_savings / total_tokens_before) * 100

        average_stability_score = sum(m["stability_score"] for m in metrics) / total_prompts

        return {
            "total_prompts": total_prompts,
            "total_token_savings": total_token_savings,
            "total_tokens_before": total_tokens_before,
            "total_tokens_after": total_tokens_after,
            "average_savings_percent": average_savings_percent,
            "average_stability_score": average_stability_score,
        }
