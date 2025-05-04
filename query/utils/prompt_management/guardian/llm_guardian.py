"""
LLMGuardian coordinator for prompt management system.

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
import logging
import time
from collections import OrderedDict
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field

from data_models.base import IndalekoBaseModel
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections
from query.utils.llm_connector.factory_updated import LLMFactory
from query.utils.prompt_management.ayni.guard import AyniGuard
from query.utils.prompt_management.guardian.prompt_guardian import (
    PromptGuardian,
    VerificationLevel,
)
from query.utils.prompt_management.prompt_manager import (
    PromptEvaluationResult,
    PromptManager,
    PromptVariable,
)
from query.utils.prompt_management.schema_manager import SchemaManager

logger = logging.getLogger(__name__)


class LLMRequestMode(str, Enum):
    """Request modes for LLM calls."""

    SAFE = "safe"  # Block prompts that don't pass verification
    WARN = "warn"  # Warn on prompts that don't pass verification
    FORCE = "force"  # Force execution even if verification fails


class LLMRequestLog(IndalekoBaseModel):
    """Log entry for LLM request activity."""

    request_id: str
    prompt_hash: str
    template_id: str | None = None
    user_id: str | None = None
    provider: str
    model: str | None = None
    verification_level: str
    request_mode: str
    allowed: bool
    blocked: bool
    token_count: int
    original_token_count: int
    token_savings: int
    verification_time_ms: int
    total_time_ms: int
    stability_score: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_LLM_Request_Log_Collection


class TokenUsageStats(IndalekoBaseModel):
    """Token usage statistics."""

    user_id: str | None = None
    provider: str
    model: str | None = None
    total_requests: int
    total_tokens: int
    total_original_tokens: int
    total_token_savings: int
    avg_token_savings_percent: float
    day: str  # ISO format date YYYY-MM-DD
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection


class LLMGuardian:
    """
    Coordinator for prompt management and LLM interactions.

    This class brings together all components of the prompt management system:
    - PromptManager for template processing and optimization
    - PromptGuardian for verification and security
    - LLM connectors for model interaction

    It provides a unified interface for optimized and secure LLM interactions
    with comprehensive logging and analytics.
    """

    def __init__(
        self,
        db_instance: IndalekoCollection | None = None,
        prompt_manager: PromptManager | None = None,
        prompt_guardian: PromptGuardian | None = None,
        llm_factory: LLMFactory | None = None,
        schema_manager: SchemaManager | None = None,
        default_verification_level: VerificationLevel = VerificationLevel.STANDARD,
        default_request_mode: LLMRequestMode = LLMRequestMode.SAFE,
    ) -> None:
        """
        Initialize LLMGuardian.

        Args:
            db_instance: Database connection instance
            prompt_manager: PromptManager instance
            prompt_guardian: PromptGuardian instance
            llm_factory: LLMFactory instance
            schema_manager: SchemaManager instance
            default_verification_level: Default verification level
            default_request_mode: Default request mode
        """
        # Initialize database connection
        self.db = db_instance or IndalekoCollection.get_db()

        # Initialize schema manager
        self.schema_manager = schema_manager or SchemaManager()

        # Initialize AyniGuard (will be shared with other components)
        self.ayni_guard = AyniGuard(db_instance=self.db)

        # Initialize prompt manager
        self.prompt_manager = prompt_manager or PromptManager(
            db_instance=self.db,
            ayni_guard=self.ayni_guard,
            schema_manager=self.schema_manager,
        )

        # Initialize prompt guardian
        self.prompt_guardian = prompt_guardian or PromptGuardian(
            db_instance=self.db,
            ayni_guard=self.ayni_guard,
            default_verification_level=default_verification_level,
        )

        # Initialize LLM factory
        self.llm_factory = llm_factory or LLMFactory()

        # Set defaults
        self.default_verification_level = default_verification_level
        self.default_request_mode = default_request_mode

        # Initialize in-memory cache for prompt results
        self._memory_cache = OrderedDict()
        self._memory_cache_max_size = 100

        # Ensure collections exist
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Ensure required collections exist in database."""
        collections = [
            IndalekoDBCollections.Indaleko_LLM_Request_Log_Collection,
            IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection,
        ]

        for collection_name in collections:
            self.db.get_collection(collection_name)

    def _generate_request_id(self) -> str:
        """
        Generate a unique request ID.

        Returns:
            Unique request ID
        """
        import time
        import uuid

        # Generate a UUID and append timestamp for uniqueness
        timestamp = int(time.time() * 1000)
        random_id = uuid.uuid4().hex[:8]

        return f"{random_id}-{timestamp}"

    def _get_memory_cache(self, prompt_hash: str) -> dict[str, Any] | None:
        """
        Get cached prompt result from memory cache.

        Args:
            prompt_hash: Hash of the prompt

        Returns:
            Cached result or None if not found
        """
        # Check if in memory cache
        if prompt_hash in self._memory_cache:
            # Move to end to mark as recently used (LRU policy)
            result = self._memory_cache.pop(prompt_hash)
            self._memory_cache[prompt_hash] = result
            return result

        return None

    def _add_memory_cache(self, prompt_hash: str, result: dict[str, Any]) -> None:
        """
        Add result to in-memory cache with LRU eviction policy.

        Args:
            prompt_hash: Hash of the prompt
            result: Result to cache
        """
        # If cache is full, remove oldest item (first item in OrderedDict)
        if len(self._memory_cache) >= self._memory_cache_max_size:
            self._memory_cache.popitem(last=False)

        # Add to cache
        self._memory_cache[prompt_hash] = result

    def _log_request(
        self,
        request_id: str,
        prompt_hash: str,
        template_id: str | None,
        user_id: str | None,
        provider: str,
        model: str | None,
        verification_level: str,
        request_mode: str,
        allowed: bool,
        blocked: bool,
        prompt_result: PromptEvaluationResult,
        verification_time_ms: int,
        total_time_ms: int,
    ) -> None:
        """
        Log LLM request.

        Args:
            request_id: Unique request ID
            prompt_hash: Hash of the prompt
            template_id: Optional template ID
            user_id: Optional user ID
            provider: LLM provider
            model: Optional model name
            verification_level: Verification level used
            request_mode: Request mode used
            allowed: Whether the prompt was allowed by verification
            blocked: Whether the request was blocked
            prompt_result: Prompt evaluation result
            verification_time_ms: Time spent on verification (ms)
            total_time_ms: Total time spent on the request (ms)
        """
        log_entry = LLMRequestLog(
            request_id=request_id,
            prompt_hash=prompt_hash,
            template_id=template_id,
            user_id=user_id,
            provider=provider,
            model=model,
            verification_level=verification_level,
            request_mode=request_mode,
            allowed=allowed,
            blocked=blocked,
            token_count=prompt_result.token_count,
            original_token_count=prompt_result.original_token_count,
            token_savings=prompt_result.token_savings,
            verification_time_ms=verification_time_ms,
            total_time_ms=total_time_ms,
            stability_score=prompt_result.stability_score,
        )

        collection = self.db.collection(IndalekoDBCollections.Indaleko_LLM_Request_Log_Collection)
        collection.insert(log_entry.dict())

        # Update token usage statistics
        self._update_token_stats(
            user_id=user_id,
            provider=provider,
            model=model,
            token_count=prompt_result.token_count,
            original_token_count=prompt_result.original_token_count,
            token_savings=prompt_result.token_savings,
        )

    def _update_token_stats(
        self,
        user_id: str | None,
        provider: str,
        model: str | None,
        token_count: int,
        original_token_count: int,
        token_savings: int,
    ) -> None:
        """
        Update token usage statistics.

        Args:
            user_id: Optional user ID
            provider: LLM provider
            model: Optional model name
            token_count: Token count for the request
            original_token_count: Original token count before optimization
            token_savings: Token savings from optimization
        """
        # Get today's date in ISO format (YYYY-MM-DD)
        today = datetime.now(UTC).date().isoformat()

        collection = self.db.collection(IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection)

        # Build filter for finding existing stats
        filters = {
            "day": today,
            "provider": provider,
        }

        if user_id:
            filters["user_id"] = user_id
        else:
            filters["user_id"] = None

        if model:
            filters["model"] = model
        else:
            filters["model"] = None

        # Try to find existing stats
        cursor = collection.find(filters)

        if cursor.count() > 0:
            # Update existing stats
            stats = cursor.next()
            stats_id = stats["_id"]

            # Calculate new values
            total_requests = stats["total_requests"] + 1
            total_tokens = stats["total_tokens"] + token_count
            total_original_tokens = stats["total_original_tokens"] + original_token_count
            total_token_savings = stats["total_token_savings"] + token_savings

            # Calculate average savings percent
            if total_original_tokens > 0:
                avg_token_savings_percent = (total_token_savings / total_original_tokens) * 100
            else:
                avg_token_savings_percent = 0

            # Update stats
            collection.update(
                {
                    "_id": stats_id,
                    "total_requests": total_requests,
                    "total_tokens": total_tokens,
                    "total_original_tokens": total_original_tokens,
                    "total_token_savings": total_token_savings,
                    "avg_token_savings_percent": avg_token_savings_percent,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
        else:
            # Create new stats
            # Calculate savings percent
            if original_token_count > 0:
                avg_token_savings_percent = (token_savings / original_token_count) * 100
            else:
                avg_token_savings_percent = 0

            # Create new stats
            stats = TokenUsageStats(
                user_id=user_id,
                provider=provider,
                model=model,
                total_requests=1,
                total_tokens=token_count,
                total_original_tokens=original_token_count,
                total_token_savings=token_savings,
                avg_token_savings_percent=avg_token_savings_percent,
                day=today,
            )

            collection.insert(stats.dict())

    def get_completion_from_prompt(
        self,
        prompt: str,
        provider: str = "preferred",
        model: str | None = None,
        system_prompt: str | None = None,
        verification_level: VerificationLevel | None = None,
        request_mode: LLMRequestMode | None = None,
        user_id: str | None = None,
        optimize: bool = True,
        options: dict[str, Any] | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        """
        Get completion from a raw prompt.

        Args:
            prompt: Raw prompt text
            provider: LLM provider
            model: Optional model name
            system_prompt: Optional system prompt (for compatible providers)
            verification_level: Verification level
            request_mode: Request mode
            user_id: Optional user ID
            optimize: Whether to optimize the prompt
            options: Additional options for the LLM provider

        Returns:
            Tuple of (completion text, metadata)
        """
        start_time = time.time()

        # Use defaults if not specified
        level = verification_level or self.default_verification_level
        mode = request_mode or self.default_request_mode

        # Generate request ID
        request_id = self._generate_request_id()

        # Prepare metadata to return
        metadata = {
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "verification_level": level.value,
            "request_mode": mode.value,
            "optimized": optimize,
            "blocked": False,
        }

        # Convert text prompt to structured format
        structured_prompt = self.prompt_guardian._convert_to_structured(prompt)
        prompt_hash = self.ayni_guard.compute_prompt_hash(structured_prompt)
        metadata["prompt_hash"] = prompt_hash

        # Create cache key
        cache_key_data = {
            "prompt_hash": prompt_hash,
            "provider": provider,
            "model": model,
            "system_prompt": system_prompt,
            "optimize": optimize,
        }
        cache_key = hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()

        # Check in-memory cache
        cached_result = self._get_memory_cache(cache_key)
        if cached_result:
            logger.debug(f"In-memory cache hit for prompt with hash {prompt_hash[:8]}")
            # Add cache metadata
            cached_result["cache_hit"] = True
            cached_result["cache_source"] = "memory"
            return cached_result.get("completion"), cached_result

        # Apply optimization if requested
        if optimize:
            # Optimize any JSON schemas in the prompt
            prompt = self.prompt_manager._normalize_whitespace(prompt)
            prompt = self.prompt_manager._optimize_schema_objects(prompt)

            # Update structured prompt
            structured_prompt = self.prompt_guardian._convert_to_structured(prompt)

        # Get token counts
        token_count = self.prompt_manager._token_estimator(prompt)
        original_token_count = token_count  # Same for raw prompt
        token_savings = 0

        # Verify prompt
        verification_start = time.time()
        verification = self.prompt_guardian.verify_prompt(
            prompt=structured_prompt,
            level=level,
            user_id=user_id,
        )
        verification_time_ms = int((time.time() - verification_start) * 1000)

        # Update metadata
        metadata["verification"] = {
            "allowed": verification.allowed,
            "action": verification.action,
            "score": verification.score,
            "reasons": verification.reasons,
            "warnings": verification.warnings,
            "time_ms": verification_time_ms,
        }

        # Create fake PromptEvaluationResult for logging
        prompt_result = PromptEvaluationResult(
            prompt=prompt,
            token_count=token_count,
            original_token_count=original_token_count,
            token_savings=token_savings,
            stability_score=verification.score,
            stability_details={},
            prompt_hash=prompt_hash,
        )

        # Check if prompt is allowed
        if not verification.allowed:
            if mode == LLMRequestMode.SAFE:
                # Block the request
                metadata["blocked"] = True
                metadata["block_reason"] = verification.reasons[0] if verification.reasons else "Failed verification"
                metadata["recommendation"] = verification.recommendation

                # Log the request
                total_time_ms = int((time.time() - start_time) * 1000)
                self._log_request(
                    request_id=request_id,
                    prompt_hash=prompt_hash,
                    template_id=None,
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    verification_level=level.value,
                    request_mode=mode.value,
                    allowed=verification.allowed,
                    blocked=True,
                    prompt_result=prompt_result,
                    verification_time_ms=verification_time_ms,
                    total_time_ms=total_time_ms,
                )

                return None, metadata

            if mode == LLMRequestMode.WARN:
                # Add warnings to metadata
                metadata["warnings"] = verification.warnings
                metadata["recommendation"] = verification.recommendation

        # Get LLM connector
        llm = self.llm_factory.get_llm(provider=provider, model=model)

        # Set up options
        provider_options = options or {}

        # Get completion with system prompt if provided (for compatible providers)
        if system_prompt:
            completion = llm.get_completion(
                system_prompt=system_prompt,
                user_prompt=prompt,
                **provider_options,
            )
        else:
            # For providers that don't support system prompts
            completion = llm.get_completion(
                user_prompt=prompt,
                **provider_options,
            )

        # Calculate total time
        total_time_ms = int((time.time() - start_time) * 1000)
        metadata["total_time_ms"] = total_time_ms

        # Log the request
        self._log_request(
            request_id=request_id,
            prompt_hash=prompt_hash,
            template_id=None,
            user_id=user_id,
            provider=provider,
            model=model,
            verification_level=level.value,
            request_mode=mode.value,
            allowed=verification.allowed,
            blocked=False,
            prompt_result=prompt_result,
            verification_time_ms=verification_time_ms,
            total_time_ms=total_time_ms,
        )

        # Add to in-memory cache
        cache_entry = metadata.copy()
        cache_entry["completion"] = completion
        self._add_memory_cache(cache_key, cache_entry)

        return completion, metadata

    def get_completion_from_template(
        self,
        template_id: str,
        variables: list[PromptVariable],
        provider: str = "preferred",
        model: str | None = None,
        system_prompt: str | None = None,
        verification_level: VerificationLevel | None = None,
        request_mode: LLMRequestMode | None = None,
        user_id: str | None = None,
        optimize: bool = True,
        evaluate_stability: bool = True,
        options: dict[str, Any] | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        """
        Get completion from a template.

        Args:
            template_id: Template ID
            variables: List of variables to bind
            provider: LLM provider
            model: Optional model name
            system_prompt: Optional system prompt (for compatible providers)
            verification_level: Verification level
            request_mode: Request mode
            user_id: Optional user ID
            optimize: Whether to optimize the prompt
            evaluate_stability: Whether to evaluate prompt stability
            options: Additional options for the LLM provider

        Returns:
            Tuple of (completion text, metadata)
        """
        start_time = time.time()

        # Use defaults if not specified
        level = verification_level or self.default_verification_level
        mode = request_mode or self.default_request_mode

        # Generate request ID
        request_id = self._generate_request_id()

        # Prepare metadata to return
        metadata = {
            "request_id": request_id,
            "template_id": template_id,
            "provider": provider,
            "model": model,
            "verification_level": level.value,
            "request_mode": mode.value,
            "optimized": optimize,
            "variables": [var.dict() for var in variables],
            "blocked": False,
        }

        # Create template-based caching key (separate from prompt hash)
        cache_key_data = {
            "template_id": template_id,
            "variables": [var.dict() for var in variables],
            "optimize": optimize,
            "level": level.value,
        }
        template_cache_key = hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()

        # Check in-memory cache using the template cache key
        cached_result = self._get_memory_cache(template_cache_key)
        if cached_result:
            logger.debug(f"In-memory cache hit for template {template_id}")
            # Add cache metadata
            cached_result["cache_hit"] = True
            cached_result["cache_source"] = "memory"
            return cached_result.get("completion"), cached_result

        # Create the prompt
        prompt_result = self.prompt_manager.create_prompt(
            template_id=template_id,
            variables=variables,
            optimize=optimize,
            evaluate_stability=evaluate_stability,
        )

        metadata["prompt_hash"] = prompt_result.prompt_hash

        # Get prompt text and structured format
        prompt = prompt_result.prompt
        structured_prompt = self.prompt_guardian._convert_to_structured(prompt)

        # Verify prompt
        verification_start = time.time()
        verification = self.prompt_guardian.verify_prompt(
            prompt=structured_prompt,
            level=level,
            user_id=user_id,
        )
        verification_time_ms = int((time.time() - verification_start) * 1000)

        # Update metadata
        metadata["verification"] = {
            "allowed": verification.allowed,
            "action": verification.action,
            "score": verification.score,
            "reasons": verification.reasons,
            "warnings": verification.warnings,
            "time_ms": verification_time_ms,
        }

        metadata["token_metrics"] = {
            "token_count": prompt_result.token_count,
            "original_token_count": prompt_result.original_token_count,
            "token_savings": prompt_result.token_savings,
            "savings_percent": (
                (prompt_result.token_savings / prompt_result.original_token_count * 100)
                if prompt_result.original_token_count > 0
                else 0
            ),
        }

        # Check if prompt is allowed
        if not verification.allowed:
            if mode == LLMRequestMode.SAFE:
                # Block the request
                metadata["blocked"] = True
                metadata["block_reason"] = verification.reasons[0] if verification.reasons else "Failed verification"
                metadata["recommendation"] = verification.recommendation

                # Log the request
                total_time_ms = int((time.time() - start_time) * 1000)
                self._log_request(
                    request_id=request_id,
                    prompt_hash=prompt_result.prompt_hash,
                    template_id=template_id,
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    verification_level=level.value,
                    request_mode=mode.value,
                    allowed=verification.allowed,
                    blocked=True,
                    prompt_result=prompt_result,
                    verification_time_ms=verification_time_ms,
                    total_time_ms=total_time_ms,
                )

                return None, metadata

            if mode == LLMRequestMode.WARN:
                # Add warnings to metadata
                metadata["warnings"] = verification.warnings
                metadata["recommendation"] = verification.recommendation

        # Get LLM connector
        llm = self.llm_factory.get_llm(provider=provider, model=model)

        # Set up options
        provider_options = options or {}

        # Get completion with system prompt if provided (for compatible providers)
        if system_prompt:
            completion = llm.get_completion(
                system_prompt=system_prompt,
                user_prompt=prompt,
                **provider_options,
            )
        else:
            # For providers that don't support system prompts
            completion = llm.get_completion(
                user_prompt=prompt,
                **provider_options,
            )

        # Calculate total time
        total_time_ms = int((time.time() - start_time) * 1000)
        metadata["total_time_ms"] = total_time_ms

        # Log the request
        self._log_request(
            request_id=request_id,
            prompt_hash=prompt_result.prompt_hash,
            template_id=template_id,
            user_id=user_id,
            provider=provider,
            model=model,
            verification_level=level.value,
            request_mode=mode.value,
            allowed=verification.allowed,
            blocked=False,
            prompt_result=prompt_result,
            verification_time_ms=verification_time_ms,
            total_time_ms=total_time_ms,
        )

        # Add to in-memory cache
        cache_entry = metadata.copy()
        cache_entry["completion"] = completion
        self._add_memory_cache(template_cache_key, cache_entry)

        return completion, metadata

    def get_token_usage_stats(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        user_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Get token usage statistics.

        Args:
            start_date: Optional start date (ISO format YYYY-MM-DD)
            end_date: Optional end date (ISO format YYYY-MM-DD)
            user_id: Optional user ID filter
            provider: Optional provider filter
            model: Optional model filter

        Returns:
            Token usage statistics
        """
        collection = self.db.collection(IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection)

        # Build filter conditions
        filters = []

        if start_date:
            filters.append("doc.day >= @start_date")

        if end_date:
            filters.append("doc.day <= @end_date")

        if user_id:
            filters.append("doc.user_id == @user_id")

        if provider:
            filters.append("doc.provider == @provider")

        if model:
            filters.append("doc.model == @model")

        # Build AQL query
        aql = """
            FOR doc IN @@collection
        """

        if filters:
            aql += f" FILTER {' AND '.join(filters)}"

        aql += """
            COLLECT AGGREGATE
                total_requests = SUM(doc.total_requests),
                total_tokens = SUM(doc.total_tokens),
                total_original_tokens = SUM(doc.total_original_tokens),
                total_token_savings = SUM(doc.total_token_savings)
            RETURN {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_original_tokens": total_original_tokens,
                "total_token_savings": total_token_savings,
                "average_tokens_per_request": total_requests > 0 ? total_tokens / total_requests : 0,
                "savings_percent": total_original_tokens > 0 ? (total_token_savings / total_original_tokens) * 100 : 0
            }
        """

        # Build bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection,
        }

        if start_date:
            bind_vars["start_date"] = start_date

        if end_date:
            bind_vars["end_date"] = end_date

        if user_id:
            bind_vars["user_id"] = user_id

        if provider:
            bind_vars["provider"] = provider

        if model:
            bind_vars["model"] = model

        # Execute query
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)

        if cursor.count() > 0:
            return cursor.next()

        # Return empty stats if no data
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_original_tokens": 0,
            "total_token_savings": 0,
            "average_tokens_per_request": 0,
            "savings_percent": 0,
        }

    def get_token_usage_by_day(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        user_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get token usage by day.

        Args:
            start_date: Optional start date (ISO format YYYY-MM-DD)
            end_date: Optional end date (ISO format YYYY-MM-DD)
            user_id: Optional user ID filter
            provider: Optional provider filter
            model: Optional model filter

        Returns:
            List of daily token usage statistics
        """
        collection = self.db.collection(IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection)

        # Build filter conditions
        filters = []

        if start_date:
            filters.append("doc.day >= @start_date")

        if end_date:
            filters.append("doc.day <= @end_date")

        if user_id:
            filters.append("doc.user_id == @user_id")

        if provider:
            filters.append("doc.provider == @provider")

        if model:
            filters.append("doc.model == @model")

        # Build AQL query
        aql = """
            FOR doc IN @@collection
        """

        if filters:
            aql += f" FILTER {' AND '.join(filters)}"

        aql += """
            COLLECT day = doc.day
            AGGREGATE
                total_requests = SUM(doc.total_requests),
                total_tokens = SUM(doc.total_tokens),
                total_original_tokens = SUM(doc.total_original_tokens),
                total_token_savings = SUM(doc.total_token_savings)
            SORT day ASC
            RETURN {
                "day": day,
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_original_tokens": total_original_tokens,
                "total_token_savings": total_token_savings,
                "average_tokens_per_request": total_requests > 0 ? total_tokens / total_requests : 0,
                "savings_percent": total_original_tokens > 0 ? (total_token_savings / total_original_tokens) * 100 : 0
            }
        """

        # Build bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection,
        }

        if start_date:
            bind_vars["start_date"] = start_date

        if end_date:
            bind_vars["end_date"] = end_date

        if user_id:
            bind_vars["user_id"] = user_id

        if provider:
            bind_vars["provider"] = provider

        if model:
            bind_vars["model"] = model

        # Execute query
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)

        return [doc for doc in cursor]

    def get_token_usage_by_provider(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get token usage by provider.

        Args:
            start_date: Optional start date (ISO format YYYY-MM-DD)
            end_date: Optional end date (ISO format YYYY-MM-DD)
            user_id: Optional user ID filter

        Returns:
            List of token usage statistics by provider
        """
        collection = self.db.collection(IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection)

        # Build filter conditions
        filters = []

        if start_date:
            filters.append("doc.day >= @start_date")

        if end_date:
            filters.append("doc.day <= @end_date")

        if user_id:
            filters.append("doc.user_id == @user_id")

        # Build AQL query
        aql = """
            FOR doc IN @@collection
        """

        if filters:
            aql += f" FILTER {' AND '.join(filters)}"

        aql += """
            COLLECT provider = doc.provider
            AGGREGATE
                total_requests = SUM(doc.total_requests),
                total_tokens = SUM(doc.total_tokens),
                total_original_tokens = SUM(doc.total_original_tokens),
                total_token_savings = SUM(doc.total_token_savings)
            SORT total_tokens DESC
            RETURN {
                "provider": provider,
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_original_tokens": total_original_tokens,
                "total_token_savings": total_token_savings,
                "average_tokens_per_request": total_requests > 0 ? total_tokens / total_requests : 0,
                "savings_percent": total_original_tokens > 0 ? (total_token_savings / total_original_tokens) * 100 : 0
            }
        """

        # Build bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection,
        }

        if start_date:
            bind_vars["start_date"] = start_date

        if end_date:
            bind_vars["end_date"] = end_date

        if user_id:
            bind_vars["user_id"] = user_id

        # Execute query
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)

        return [doc for doc in cursor]
