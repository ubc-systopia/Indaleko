"""
Base data models for the Prompt Management System.

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

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field

from data_models.base import IndalekoBaseModel
from db.db_collections import IndalekoDBCollections


class PromptTemplateType(str, Enum):
    """Types of prompt templates."""

    SYSTEM = "system"
    USER = "user"
    FUNCTION = "function"
    SCHEMA = "schema"
    EXAMPLE = "example"
    COMPOSITE = "composite"


class TemplateVariable(IndalekoBaseModel):
    """A variable that can be used in a prompt template."""

    name: str
    description: str
    default_value: Any | None = None
    required: bool = True
    type_hint: str = "str"


class PromptTemplate(IndalekoBaseModel):
    """A template for creating prompts."""

    name: str
    template_type: PromptTemplateType
    template_text: str
    description: str
    variables: list[TemplateVariable] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Prompt_Templates_Collection


class LayeredPrompt(IndalekoBaseModel):
    """A structured prompt with layers for different content types."""

    immutable_context: str = ""
    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    soft_preferences: dict[str, Any] = Field(default_factory=dict)
    trust_contract: dict[str, Any] | None = None


class PromptIssue(IndalekoBaseModel):
    """An issue detected in a prompt."""

    issue_type: str  # contradiction, ambiguity, etc.
    description: str
    severity: float  # 0.0 to 1.0
    confidence: float  # Reviewer's confidence in this issue
    location: str | None = None  # Which part of the prompt has the issue


class AyniResult(IndalekoBaseModel):
    """Result of an AyniGuard prompt evaluation."""

    composite_score: float
    details: dict[str, Any]
    issues: list[str]
    action: str  # 'block', 'warn', 'proceed'


class PromptCacheEntry(IndalekoBaseModel):
    """A cached prompt evaluation entry."""

    prompt_hash: str
    prompt_data: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    user_id: str | None = None

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection


class PromptArchiveEntry(IndalekoBaseModel):
    """An archived prompt evaluation entry."""

    prompt_hash: str
    prompt_data: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime
    archived_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Prompt_Cache_Archive_Collection


class StabilityMetric(IndalekoBaseModel):
    """A metric tracking prompt stability."""

    prompt_hash: str
    score: float
    issue_count: int
    action: str  # 'block', 'warn', 'proceed'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection


class ConflictPair:
    """A pair of terms that conflict with each other."""

    term1: str
    term2: str
    severity: float  # 0.0 to 1.0
    context: str | None = None  # Additional context about why they conflict
