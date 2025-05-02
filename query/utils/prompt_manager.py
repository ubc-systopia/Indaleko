"""
Prompt management system for Indaleko.

This module provides tools for efficient prompt creation, optimization, 
and tracking to reduce token usage and improve LLM interactions.

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
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Dict, List, Optional, Union

import tiktoken
from icecream import ic
from pydantic import BaseModel, Field, field_validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# Configure logger for this module
logger = logging.getLogger(__name__)


class PromptFormat(Enum):
    """Supported prompt formats."""
    
    CHAT = auto()
    COMPLETION = auto()
    FUNCTION_CALL = auto()


class PromptOptimizationStrategy(Enum):
    """Optimization strategies for prompts."""
    
    WHITESPACE = auto()
    TRUNCATE = auto()
    SCHEMA_SIMPLIFY = auto()
    EXAMPLE_REDUCE = auto()
    CONTEXT_WINDOW = auto()
    CONTRADICTION_CHECK = auto()  # Rule-based contradiction check
    LLM_REVIEW = auto()  # LLM-powered review for cognitive dissonance
    ALL = auto()


class PromptStats(BaseModel):
    """Statistics about prompt usage."""
    
    prompt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_name: str
    tokens: int
    chars: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    optimized: bool = False
    original_tokens: Optional[int] = None
    optimization_strategies: List[str] = []
    execution_time_ms: Optional[float] = None
    model: Optional[str] = None
    
    class Config:
        """Configuration for the model."""
        
        json_schema_extra = {
            "example": {
                "prompt_id": "1234-5678-90ab-cdef",
                "template_name": "aql_translation",
                "tokens": 2500,
                "chars": 15000,
                "created_at": "2024-05-02T12:34:56.789Z",
                "optimized": True,
                "original_tokens": 3200,
                "optimization_strategies": ["WHITESPACE", "EXAMPLE_REDUCE"],
                "execution_time_ms": 456.78,
                "model": "gpt-4o"
            }
        }


class PromptTemplate(BaseModel):
    """Template for creating prompts."""
    
    name: str
    description: str
    format: PromptFormat
    system_template: str
    user_template: str
    tags: List[str] = []
    schema: Optional[Dict[str, Any]] = None
    examples: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    class Config:
        """Configuration for the model."""
        
        json_schema_extra = {
            "example": {
                "name": "aql_translation",
                "description": "Template for translating natural language to AQL",
                "format": "CHAT",
                "system_template": "You are a query translator...",
                "user_template": "Translate this query: {query}",
                "tags": ["query", "translation", "aql"],
                "schema": {"type": "object", "properties": {}},
                "examples": [{"query": "...", "output": "..."}]
            }
        }


class PromptRegistry:
    """Registry for prompt templates."""
    
    def __init__(self):
        """Initialize the registry."""
        self._templates: Dict[str, PromptTemplate] = {}
    
    def register(self, template: PromptTemplate) -> None:
        """Register a template."""
        self._templates[template.name] = template
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self._templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List all registered templates."""
        return list(self._templates.keys())
    
    def save_to_file(self, path: str) -> None:
        """Save templates to a file."""
        serialized = {
            name: template.model_dump() 
            for name, template in self._templates.items()
        }
        with open(path, 'w') as f:
            json.dump(serialized, f, default=str, indent=2)
    
    def load_from_file(self, path: str) -> None:
        """Load templates from a file."""
        with open(path, 'r') as f:
            serialized = json.load(f)
        
        for name, data in serialized.items():
            # Convert datetime strings back to datetime objects
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            
            # Convert format string to enum
            if 'format' in data and isinstance(data['format'], str):
                data['format'] = PromptFormat[data['format']]
                
            self._templates[name] = PromptTemplate(**data)


class PromptManager:
    """Manager for optimizing and tracking prompts."""
    
    def __init__(
        self, 
        max_tokens: int = 4000,
        encoding_name: str = "cl100k_base",
        stats_capacity: int = 100,
        registry: Optional[PromptRegistry] = None,
        schema_rules: Optional[Dict[str, List[str]]] = None,
        llm_client = None
    ):
        """
        Initialize the prompt manager.
        
        Args:
            max_tokens: Maximum tokens for prompts
            encoding_name: Name of the encoding to use for tokenization
            stats_capacity: Maximum number of stats entries to keep in memory
            registry: Optional registry to use for templates
            schema_rules: Dictionary of schema rules to check for contradictions
                Format: {"pattern_to_find": ["allowed_terms", "forbidden_terms"], ...}
            llm_client: Optional LLM client for LLM_REVIEW strategy
        """
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding(encoding_name)
        self.registry = registry or PromptRegistry()
        self._stats: List[PromptStats] = []
        self._stats_capacity = stats_capacity
        self.llm_client = llm_client
        
        # Initialize schema rules with defaults if not provided
        self.schema_rules = schema_rules or {
            # Default rules for Record.Attributes access
            r"Record\.Attributes?": [
                # Correct ways to access attributes in ArangoDB collections
                "Record.Attributes.Path", 
                "Record.Attributes.Size",
                "Record.Attributes.ModifiedTime",
                "Record.Attributes.CreationTime",
                "Record.Attributes.MimeType",
                
                # Incorrect patterns to detect
                "Record.Attribute.",  # Missing 's' in Attributes
                "DO NOT USE Record.Attribute",  # Contradiction warning
                "Record.attribute",  # Wrong case
            ]
        }
        
        # Register optimization functions
        self._optimization_functions = {
            PromptOptimizationStrategy.WHITESPACE: self._remove_redundant_whitespace,
            PromptOptimizationStrategy.TRUNCATE: self._truncate_text,
            PromptOptimizationStrategy.SCHEMA_SIMPLIFY: self._simplify_schema,
            PromptOptimizationStrategy.EXAMPLE_REDUCE: self._reduce_examples,
            PromptOptimizationStrategy.CONTEXT_WINDOW: self._window_context,
            PromptOptimizationStrategy.CONTRADICTION_CHECK: self._resolve_contradictions,
            PromptOptimizationStrategy.LLM_REVIEW: self._llm_review_contradictions,
        }
    
    def register_template(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self.registry.register(template)
    
    def create_system_prompt(self, template_name: str, **kwargs) -> str:
        """Create a system prompt from a template."""
        template = self.registry.get(template_name)
        if template is None:
            raise ValueError(f"Template {template_name} not found")
        
        # Format the system template
        return template.system_template.format(**kwargs)
    
    def create_user_prompt(self, template_name: str, **kwargs) -> str:
        """Create a user prompt from a template."""
        template = self.registry.get(template_name)
        if template is None:
            raise ValueError(f"Template {template_name} not found")
        
        # Format the user template
        return template.user_template.format(**kwargs)
    
    def create_prompt(
        self, 
        template_name: str, 
        optimize: bool = True,
        strategies: List[PromptOptimizationStrategy] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Create a prompt from a template with variables.
        
        Args:
            template_name: Name of the template to use
            optimize: Whether to optimize the prompt
            strategies: List of optimization strategies to use
            **kwargs: Variables to format the template with
            
        Returns:
            Dictionary with 'system' and 'user' prompts
        """
        template = self.registry.get(template_name)
        if template is None:
            raise ValueError(f"Template {template_name} not found")
        
        # Format the templates
        system_prompt = template.system_template.format(**kwargs)
        user_prompt = template.user_template.format(**kwargs)
        
        # Create the combined prompt for token counting
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Measure token count
        original_tokens = len(self.tokenizer.encode(combined_prompt))
        tokens = original_tokens
        chars = len(combined_prompt)
        
        # Optimize if requested and needed
        applied_strategies = []
        if optimize and tokens > self.max_tokens:
            strategies = strategies or [PromptOptimizationStrategy.ALL]
            
            # If ALL is in strategies, replace with all specific strategies
            if PromptOptimizationStrategy.ALL in strategies:
                strategies = [
                    s for s in PromptOptimizationStrategy 
                    if s != PromptOptimizationStrategy.ALL
                ]
            
            # Apply optimization strategies
            system_prompt, user_prompt, applied_strategies = self.optimize_prompt(
                system_prompt, 
                user_prompt, 
                strategies
            )
            
            # Recalculate token count
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            tokens = len(self.tokenizer.encode(combined_prompt))
            chars = len(combined_prompt)
        
        # Record prompt stats
        self._record_stats(
            template_name=template_name,
            tokens=tokens,
            chars=chars,
            optimized=bool(applied_strategies),
            original_tokens=original_tokens if applied_strategies else None,
            optimization_strategies=[s.name for s in applied_strategies]
        )
        
        # Log prompt stats
        logger.info(
            f"Prompt {template_name}: {tokens} tokens, {chars} chars, "
            f"optimization: {', '.join([s.name for s in applied_strategies]) if applied_strategies else 'None'}"
        )
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def optimize_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        strategies: List[PromptOptimizationStrategy]
    ) -> tuple[str, str, List[PromptOptimizationStrategy]]:
        """
        Optimize prompts to fit within token limits.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            strategies: List of optimization strategies to apply
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt, applied strategies)
        """
        applied_strategies = []
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        total_tokens = len(self.tokenizer.encode(combined_prompt))
        
        # Skip optimization if already within limits
        if total_tokens <= self.max_tokens:
            return system_prompt, user_prompt, applied_strategies
        
        # Apply strategies in order of least to most destructive
        order = [
            PromptOptimizationStrategy.CONTRADICTION_CHECK,  # Rule-based contradiction check first
            PromptOptimizationStrategy.LLM_REVIEW,           # Then LLM-based review if available
            PromptOptimizationStrategy.WHITESPACE,
            PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
            PromptOptimizationStrategy.EXAMPLE_REDUCE,
            PromptOptimizationStrategy.CONTEXT_WINDOW,
            PromptOptimizationStrategy.TRUNCATE,
        ]
        
        # Filter to only requested strategies, maintaining order
        ordered_strategies = [s for s in order if s in strategies]
        
        # Apply strategies until under token limit
        for strategy in ordered_strategies:
            # Skip if we're already under the limit
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            if len(self.tokenizer.encode(combined_prompt)) <= self.max_tokens:
                break
                
            # Apply the strategy
            optimization_fn = self._optimization_functions[strategy]
            system_prompt, user_prompt = optimization_fn(system_prompt, user_prompt)
            applied_strategies.append(strategy)
        
        return system_prompt, user_prompt, applied_strategies
    
    def _record_stats(self, **kwargs) -> None:
        """
        Record prompt stats.
        
        Args:
            **kwargs: Stats to record
        """
        stats = PromptStats(**kwargs)
        
        # Add to stats list, maintaining capacity limit
        self._stats.append(stats)
        if len(self._stats) > self._stats_capacity:
            self._stats.pop(0)
    
    def get_stats(self) -> List[PromptStats]:
        """Get prompt stats."""
        return self._stats
    
    def clear_stats(self) -> None:
        """Clear prompt stats."""
        self._stats = []
    
    def _remove_redundant_whitespace(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Remove redundant whitespace from prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # Function to remove redundant whitespace from a string
        def clean(text: str) -> str:
            # Replace multiple newlines with a single newline
            text = re.sub(r'\n\s*\n', '\n\n', text)
            # Replace more than two consecutive newlines with two newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Replace multiple spaces with a single space
            text = re.sub(r' +', ' ', text)
            # Remove spaces at the beginning of lines
            text = re.sub(r'\n +', '\n', text)
            return text.strip()
        
        return clean(system_prompt), clean(user_prompt)
    
    def _truncate_text(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Truncate prompts to fit within token limits.
        
        This is a last resort strategy that directly truncates the system prompt.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # Calculate target token count
        combined_tokens = len(self.tokenizer.encode(f"{system_prompt}\n\n{user_prompt}"))
        excess_tokens = combined_tokens - self.max_tokens
        
        # Only truncate if necessary
        if excess_tokens <= 0:
            return system_prompt, user_prompt
        
        # Prioritize preserving the user prompt
        user_tokens = len(self.tokenizer.encode(user_prompt))
        system_tokens = len(self.tokenizer.encode(system_prompt))
        
        # If user prompt is already too large, we have to truncate it
        if user_tokens > self.max_tokens * 0.8:
            # We'll keep 80% of the limit for the user prompt
            user_limit = int(self.max_tokens * 0.8)
            system_limit = self.max_tokens - user_limit
            
            # Encode, truncate, and decode
            user_token_ids = self.tokenizer.encode(user_prompt)[:user_limit]
            system_token_ids = self.tokenizer.encode(system_prompt)[:system_limit]
            
            user_prompt = self.tokenizer.decode(user_token_ids)
            system_prompt = self.tokenizer.decode(system_token_ids)
        else:
            # Truncate system prompt to fit
            max_system_tokens = system_tokens - excess_tokens - 10  # Buffer of 10 tokens
            system_token_ids = self.tokenizer.encode(system_prompt)[:max_system_tokens]
            system_prompt = self.tokenizer.decode(system_token_ids)
        
        return system_prompt, user_prompt
    
    def _simplify_schema(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Simplify schema in prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # This is a more complex optimization that requires understanding the schema format
        # Placeholder implementation - in a real system, this would parse and simplify JSON schemas
        
        # Look for schema blocks in the system prompt
        schema_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        
        def simplify_schema_json(match):
            try:
                # Parse the schema
                schema_text = match.group(1)
                schema = json.loads(schema_text)
                
                # Simplify the schema - remove descriptions, examples, etc.
                if isinstance(schema, dict):
                    # Remove description fields
                    if 'description' in schema:
                        del schema['description']
                    
                    # Simplify properties
                    if 'properties' in schema and isinstance(schema['properties'], dict):
                        for prop_name, prop_value in schema['properties'].items():
                            if isinstance(prop_value, dict):
                                # Remove description and examples from properties
                                for field in ['description', 'example', 'examples']:
                                    if field in prop_value:
                                        del prop_value[field]
                
                # Return the simplified schema
                return f"```json\n{json.dumps(schema, indent=2)}\n```"
            except json.JSONDecodeError:
                # If we can't parse the schema, return the original
                return match.group(0)
        
        # Apply the simplification to the system prompt
        system_prompt = re.sub(schema_pattern, simplify_schema_json, system_prompt, flags=re.DOTALL)
        
        return system_prompt, user_prompt
    
    def _reduce_examples(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Reduce examples in prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # Strategy: Find example blocks and reduce their number
        example_patterns = [
            # Match blocks that start with "Example" or "Examples"
            (r'(?:Example|Examples)[^\n]*\n((?:.*\n)+?)(?:\n\s*\n|\Z)', 0.5),
            # Match markdown-style examples
            (r'(?:```|~~~).*\n((?:.*\n)+?)(?:```|~~~)', 0.7),
            # Match numbered examples
            (r'(?:\d+\.\s.*\n)+', 0.5),
        ]
        
        for pattern, keep_ratio in example_patterns:
            # Find examples in the system prompt
            matches = list(re.finditer(pattern, system_prompt, re.MULTILINE))
            
            if matches:
                # If we have matches, determine how many to keep
                num_examples = len(matches)
                keep_count = max(1, int(num_examples * keep_ratio))
                
                # If we're keeping all, no changes needed
                if keep_count >= num_examples:
                    continue
                
                # Keep the first example and evenly distributed others
                indices_to_keep = [0]  # Always keep the first example
                if keep_count > 1:
                    # Add additional examples, evenly distributed
                    step = (num_examples - 1) / (keep_count - 1)
                    indices_to_keep.extend([
                        int(i * step) + 1 for i in range(keep_count - 1)
                    ])
                
                # Create a new system prompt with only the kept examples
                sections = []
                last_end = 0
                
                for i, match in enumerate(matches):
                    if i in indices_to_keep:
                        # Add text before the example
                        if match.start() > last_end:
                            sections.append(system_prompt[last_end:match.start()])
                        # Add the example
                        sections.append(system_prompt[match.start():match.end()])
                    last_end = match.end()
                
                # Add any remaining text
                if last_end < len(system_prompt):
                    sections.append(system_prompt[last_end:])
                
                # Join sections to create the new system prompt
                system_prompt = ''.join(sections)
        
        return system_prompt, user_prompt
    
    def _window_context(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Apply context windowing to prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # Focus on the most important parts of the context
        
        # Split the system prompt into sections
        # Heuristic: Look for markdown headings or all-caps sections
        section_pattern = r'(#+\s+.*?\n|[A-Z][A-Z\s]+:)'
        sections = re.split(section_pattern, system_prompt)
        
        # Identify and keep essential sections
        # Prioritize sections in this order:
        essential_keywords = [
            "instruction", "format", "output", "requirement", 
            "schema", "rule", "constraint", "role"
        ]
        
        # Calculate importance scores for each section
        scored_sections = []
        for i in range(0, len(sections) - 1, 2):
            if i + 1 < len(sections):
                # Each section consists of a heading and content
                heading = sections[i]
                content = sections[i + 1]
                
                # Calculate score based on keyword presence and section length
                score = 0
                for keyword in essential_keywords:
                    if keyword.lower() in heading.lower():
                        score += 5
                    if keyword.lower() in content.lower():
                        score += 1
                
                # Adjust score by length (penalty for very long sections)
                length_factor = min(1.0, 500 / max(1, len(content)))
                score *= length_factor
                
                scored_sections.append((heading, content, score))
        
        # Sort by score and keep the highest scored sections
        scored_sections.sort(key=lambda x: x[2], reverse=True)
        
        # Rebuild system prompt with only the highest-scored sections
        # Keep at least 1 section and at most half of the sections
        keep_count = max(1, len(scored_sections) // 2)
        
        # Build new system prompt
        new_system_sections = []
        for heading, content, _ in scored_sections[:keep_count]:
            new_system_sections.append(heading)
            new_system_sections.append(content)
        
        new_system_prompt = ''.join(new_system_sections)
        
        # Check if we've reduced enough
        if len(self.tokenizer.encode(new_system_prompt)) < len(self.tokenizer.encode(system_prompt)) * 0.7:
            return new_system_prompt, user_prompt
        else:
            # If the reduction wasn't significant, fall back to simple truncation
            return self._truncate_text(system_prompt, user_prompt)
            
    def _llm_review_contradictions(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Use an LLM to review and fix contradictions in prompts.
        
        This implements the Ayni principle - collaborating with AI to improve prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # Skip if no LLM client is available
        if self.llm_client is None:
            logger.warning("LLM_REVIEW strategy requested but no LLM client provided")
            return system_prompt, user_prompt
            
        try:
            # Create a review prompt that positions the system prompt as an "untrusted" input
            review_system_prompt = """
            You are a prompt engineer specializing in detecting and fixing contradictions, 
            cognitive dissonance, and inconsistencies in LLM instructions.
            
            You must review the provided prompt and identify any:
            1. Direct contradictions (e.g., "always use X" vs "never use X")
            2. Inconsistent examples that contradict instructions
            3. Terminology inconsistencies (e.g., "Record.Attribute" vs "Record.Attributes")
            4. Logical inconsistencies in schema or data models
            5. Unclear or ambiguous instructions that could confuse an LLM
            
            IMPORTANT: Only modify the prompt to fix contradictions and inconsistencies. 
            Do not change the overall intent or add/remove functionality.
            
            RETURN FORMAT:
            ```json
            {
                "contradictions_found": boolean,
                "fixed_prompt": "The entire fixed prompt goes here",
                "changes": [
                    {"type": "contradiction", "description": "Description of what was fixed"},
                    ...
                ]
            }
            ```
            
            If no contradictions are found, return the original prompt unchanged.
            """
            
            review_user_prompt = f"""
            Please review this prompt for contradictions and inconsistencies:
            
            ```
            {system_prompt}
            ```
            
            Fix any issues you find while preserving the original intent and functionality.
            """
            
            # Call the LLM to review the prompt
            response = self.llm_client.chat.completions.create(
                model="gpt-4-turbo",  # Or another appropriate model
                messages=[
                    {"role": "system", "content": review_system_prompt},
                    {"role": "user", "content": review_user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extract the response
            review_result = json.loads(response.choices[0].message.content)
            
            # Check if contradictions were found
            if review_result.get("contradictions_found", False):
                # Log the changes
                for change in review_result.get("changes", []):
                    logger.info(f"LLM-detected contradiction: {change['description']}")
                
                # Replace the system prompt with the fixed version
                fixed_prompt = review_result.get("fixed_prompt", system_prompt)
                return fixed_prompt, user_prompt
                
            # If no contradictions were found, return the original prompt
            return system_prompt, user_prompt
            
        except Exception as e:
            # Log the error but don't fail
            logger.error(f"Error in LLM review: {str(e)}")
            return system_prompt, user_prompt
    
    def _resolve_contradictions(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """
        Detect and resolve contradictions in prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Tuple of (optimized system prompt, optimized user prompt)
        """
        # We'll focus on system prompt only, as that's where most contradictions occur
        # User prompt is typically just a query
        
        # First, check for explicit contradictions (direct statements that conflict)
        # Then check for schema inconsistencies
        
        # Track changes for logging
        changes_made = []
        original_prompt = system_prompt
                
        # Check for schema rule contradictions
        for pattern, rules in self.schema_rules.items():
            # Extract canonical/correct terms and patterns to fix
            # Assume first few elements are correct examples, later ones are incorrect
            split_point = len(rules) // 2
            correct_terms = rules[:split_point]
            incorrect_patterns = rules[split_point:]
            
            # Check if any incorrect patterns appear in the prompt
            for incorrect in incorrect_patterns:
                if incorrect in system_prompt:
                    # Find a suitable replacement from correct terms
                    replacement = correct_terms[0] if correct_terms else pattern
                    
                    # Special case for warnings/instructions
                    if "DO NOT USE" in incorrect:
                        # Remove the warning entirely if it contradicts correct usage elsewhere
                        for correct in correct_terms:
                            if correct in system_prompt:
                                # Find the line with the warning and remove it
                                lines = system_prompt.split("\n")
                                filtered_lines = [
                                    line for line in lines 
                                    if incorrect not in line
                                ]
                                system_prompt = "\n".join(filtered_lines)
                                changes_made.append(f"Removed contradictory warning: '{incorrect}'")
                    else:
                        # Replace incorrect pattern with correct one
                        system_prompt = system_prompt.replace(incorrect, replacement)
                        changes_made.append(f"Fixed schema pattern: '{incorrect}' → '{replacement}'")
        
        # Look for explicit contradictory statements
        contradiction_patterns = [
            # Pattern: first part, second part (contradictory statements)
            (r"do not use (\w+)", r"use \1"),
            (r"never use (\w+)", r"\1 is recommended"),
            (r"avoid using (\w+)", r"\1 is preferred"),
        ]
        
        for pattern1, pattern2 in contradiction_patterns:
            # Look for first pattern
            matches1 = re.finditer(pattern1, system_prompt, re.IGNORECASE)
            for match1 in matches1:
                term = match1.group(1)
                # Look for contradictory second pattern
                if re.search(pattern2.replace(r"\1", re.escape(term)), system_prompt, re.IGNORECASE):
                    # Remove the "do not use" instruction
                    start, end = match1.span()
                    line_start = system_prompt.rfind("\n", 0, start) + 1
                    line_end = system_prompt.find("\n", end)
                    if line_end == -1:
                        line_end = len(system_prompt)
                    
                    # Remove the line with the negative instruction
                    system_prompt = system_prompt[:line_start] + system_prompt[line_end:]
                    changes_made.append(f"Removed contradictory instruction about '{term}'")
        
        # Specifically look for example contradictions
        # Find examples based on common formatting patterns
        example_blocks = []
        example_patterns = [
            r'Example\s*\d*:\s*(.+?)(?=Example\s*\d*:|$)',  # Example 1: ... content ...
            r'```(?:\w+)?\s*(.+?)```',  # Code blocks
        ]
        
        for pattern in example_patterns:
            matches = re.finditer(pattern, system_prompt, re.DOTALL)
            for match in matches:
                example_blocks.append(match.group(1))
        
        # Check each example for contradictions with the schema rules
        for i, example in enumerate(example_blocks):
            for pattern, rules in self.schema_rules.items():
                split_point = len(rules) // 2
                correct_terms = rules[:split_point]
                incorrect_patterns = rules[split_point:]
                
                # Check if any incorrect patterns appear in the example
                for incorrect in incorrect_patterns:
                    if incorrect in example:
                        # If the incorrect pattern is in an example, replace it
                        if len(correct_terms) > 0:
                            corrected_example = example.replace(incorrect, correct_terms[0])
                            system_prompt = system_prompt.replace(example, corrected_example)
                            changes_made.append(f"Fixed example {i+1}: '{incorrect}' → '{correct_terms[0]}'")
        
        # Log changes if any were made
        if changes_made:
            logger.info(f"Contradiction resolution applied: {', '.join(changes_made)}")
            
        return system_prompt, user_prompt


# Example usage
def create_aql_translation_template() -> PromptTemplate:
    """Create a template for AQL translation."""
    return PromptTemplate(
        name="aql_translation",
        description="Template for translating natural language to AQL",
        format=PromptFormat.CHAT,
        system_template=dedent("""\
            You are a query translator that converts natural language queries into AQL (ArangoDB Query Language).
            
            # Available Collections:
            - Objects: Contains file system objects with Record.Attributes containing metadata
            - Activities: Contains user activities with timestamps and metadata
            - SemanticData: Contains extracted semantic information from files
            
            # Output Format:
            You should return a valid AQL query that retrieves data matching the user's request.
            The query should include FILTER, SORT, and LIMIT clauses as appropriate.
            
            # Examples:
            
            Query: Find all PDF files
            AQL: ```
            FOR doc IN Objects
            FILTER doc.Record.Attributes.MimeType == "application/pdf"
            RETURN doc
            ```
            
            Query: Show me files modified yesterday
            AQL: ```
            FOR doc IN Objects
            FILTER DATE_DIFF(doc.Record.Attributes.ModifiedTime, DATE_NOW(), "d") <= 1
            SORT doc.Record.Attributes.ModifiedTime DESC
            RETURN doc
            ```
        """),
        user_template="Translate this query to AQL: {query}",
        tags=["query", "translation", "aql"]
    )


def create_nl_parser_template() -> PromptTemplate:
    """Create a template for natural language parsing."""
    return PromptTemplate(
        name="nl_parser",
        description="Template for parsing natural language queries",
        format=PromptFormat.CHAT,
        system_template=dedent("""\
            You are a natural language parser that extracts entities and intent from user queries.
            
            # Output Schema:
            ```json
            {
                "intent": "search" | "analyze" | "compare" | "summarize",
                "entities": {
                    "file_type": string,
                    "time_range": string,
                    "location": string,
                    "size": string,
                    "content": string
                },
                "categories": ["storage", "activity", "semantic"]
            }
            ```
            
            # Entity Types:
            - file_type: PDF, DOCX, image, video, etc.
            - time_range: yesterday, last week, between dates, etc.
            - location: path, directory, cloud service, etc.
            - size: small, large, >10MB, etc.
            - content: text contained in files
            
            # Examples:
            
            Query: Find all PDF files created last week
            Output: ```json
            {
                "intent": "search",
                "entities": {
                    "file_type": "PDF",
                    "time_range": "last week",
                    "location": null,
                    "size": null,
                    "content": null
                },
                "categories": ["storage"]
            }
            ```
            
            Query: Show me large video files that mention project alpha
            Output: ```json
            {
                "intent": "search",
                "entities": {
                    "file_type": "video",
                    "time_range": null,
                    "location": null,
                    "size": "large",
                    "content": "project alpha"
                },
                "categories": ["storage", "semantic"]
            }
            ```
        """),
        user_template="Parse this query: {query}",
        tags=["query", "parser", "entities", "intent"]
    )


def main():
    """Example usage of the prompt manager."""
    # Initialize prompt manager
    prompt_manager = PromptManager(max_tokens=4000)
    
    # Register templates
    prompt_manager.register_template(create_aql_translation_template())
    prompt_manager.register_template(create_nl_parser_template())
    
    # Create prompts
    parser_prompt = prompt_manager.create_prompt(
        template_name="nl_parser",
        query="Find all PDF files created last week"
    )
    
    aql_prompt = prompt_manager.create_prompt(
        template_name="aql_translation",
        query="Find all PDF files created last week"
    )
    
    # Display token counts
    parser_tokens = len(prompt_manager.tokenizer.encode(
        f"{parser_prompt['system']}\n\n{parser_prompt['user']}"
    ))
    aql_tokens = len(prompt_manager.tokenizer.encode(
        f"{aql_prompt['system']}\n\n{aql_prompt['user']}"
    ))
    
    print(f"Parser prompt tokens: {parser_tokens}")
    print(f"AQL prompt tokens: {aql_tokens}")
    
    # Get stats
    stats = prompt_manager.get_stats()
    for stat in stats:
        print(f"Template: {stat.template_name}, Tokens: {stat.tokens}")


if __name__ == "__main__":
    main()