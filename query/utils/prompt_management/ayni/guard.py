"""
AyniGuard - Prompt Integrity Protection System for Indaleko.

This module implements the AyniGuard system which protects the integrity
of prompts by detecting contradictions, evaluating ethical concerns, and
ensuring mutual benefit between human and AI interactions.

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

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from data_models.base import IndalekoBaseModel
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections
from query.utils.llm_connector.factory_updated import LLMFactory


@dataclass
class AyniResult:
    """Results from AyniGuard prompt evaluation."""

    composite_score: float
    details: dict[str, Any]
    issues: list[str]
    action: str  # 'block', 'warn', 'proceed'


class PromptModel(IndalekoBaseModel):
    """Data model for prompt records."""

    prompt_hash: str
    result: dict[str, Any]
    prompt_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None = None
    user_id: str | None = None


class AyniGuard:
    """
    AyniGuard system for prompt integrity protection.

    This class implements a comprehensive system for ensuring prompts
    are free from contradictions, ethically sound, and provide mutual
    benefit between human and AI participants.
    """

    def __init__(
        self,
        db_instance: IndalekoCollection | None = None,
        llm_factory: LLMFactory | None = None,
    ) -> None:
        """
        Initialize AyniGuard.

        Args:
            db_instance: Database connection instance
            llm_factory: LLM connector factory instance
        """
        self.db = db_instance or IndalekoCollection.get_db()
        self.llm_factory = llm_factory or LLMFactory()
        self.ensure_collections()

        # Weight factors for different evaluation components
        self.weights = {
            "coherence": 0.4,
            "ethicality": 0.2,
            "mutualism": 0.2,
            "tier_1_context": 0.1,
            "tier_2_constraints": 0.07,
            "tier_3_preferences": 0.03,
        }

        # Contradiction patterns library (expandable)
        self.contradiction_patterns = self._load_contradiction_patterns()

    def ensure_collections(self) -> None:
        """Ensure required collections exist in database."""
        collections = [
            IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection,
            IndalekoDBCollections.Indaleko_Prompt_Cache_Archive_Collection,
            IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection,
        ]

        # Use get_collection which will create if needed and follows architectural patterns
        for collection_name in collections:
            self.db.get_collection(collection_name)

        # Create indexes for performance
        recent_collection = IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection
        recent_cache = self.db.collection(recent_collection)
        recent_cache.ensure_hash_index(["prompt_hash"], unique=True)
        recent_cache.ensure_skiplist_index(["created_at"])

        archive_collection = IndalekoDBCollections.Indaleko_Prompt_Cache_Archive_Collection
        archive_cache = self.db.collection(archive_collection)
        archive_cache.ensure_skiplist_index(["created_at"])

    def _load_contradiction_patterns(self) -> dict[str, list[dict]]:
        """
        Load contradiction detection patterns.

        Returns:
            Dictionary of pattern categories and their detection rules.
        """
        # This would ideally load from a config file or database
        # For now, we include a starter set directly in code
        return {
            "logical": [
                {
                    "name": "opposite_directives",
                    "pattern": {
                        "positive": ["must", "always", "required"],
                        "negative": ["must not", "never", "prohibited"],
                    },
                    "severity": 0.8,
                },
                {
                    "name": "format_conflict",
                    "pattern": {"formats": ["json", "xml", "markdown", "prose", "yaml"]},
                    "severity": 0.6,
                },
            ],
            "semantic": [
                {
                    "name": "role_conflict",
                    "pattern": {"roles": ["expert", "novice", "teacher", "student"]},
                    "severity": 0.5,
                },
            ],
            "structural": [{"name": "context_constraint_conflict", "pattern": {"cross_layer": True}, "severity": 0.7}],
            "temporal": [{"name": "time_inconsistency", "pattern": {"temporal_refs": True}, "severity": 0.4}],
        }

    def compute_prompt_hash(self, prompt: dict[str, Any]) -> str:
        """
        Compute a unique hash for the prompt.

        Args:
            prompt: The structured prompt dictionary

        Returns:
            SHA-256 hash of the normalized prompt
        """
        # Sort keys for consistent hashing regardless of key order
        return hashlib.sha256(json.dumps(prompt, sort_keys=True).encode()).hexdigest()

    def check_cache(self, prompt_hash: str) -> AyniResult | None:
        """
        Check if the prompt evaluation is already cached.

        Args:
            prompt_hash: The hash of the prompt to check

        Returns:
            Cached result or None if not found/expired
        """
        # Check recent cache first (hot tier)
        recent_collection = IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection
        # Recent cache is obtained but not used directly - just using the collection name
        now = datetime.now(UTC)

        aql = """
            FOR doc IN @@collection
                FILTER doc.prompt_hash == @hash
                  AND (doc.expires_at == null OR doc.expires_at > @now)
                LIMIT 1
                RETURN doc.result
        """

        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                "@collection": recent_collection,
                "hash": prompt_hash,
                "now": now.isoformat(),
            },
        )

        if cursor.count() > 0:
            result_dict = cursor.next()
            return AyniResult(**result_dict)

        return None

    def store_cache(
        self,
        prompt_hash: str,
        result: AyniResult,
        prompt: dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        """
        Store evaluation result in cache.

        Args:
            prompt_hash: Hash of the evaluated prompt
            result: The evaluation result
            prompt: The original prompt
            user_id: Optional identifier of the prompt creator
        """
        # Store in recent cache (hot tier) with timezone-aware datetime
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=30)

        # Get collection names
        recent_col = IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection
        metrics_col = IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection

        # Store in recent cache
        recent_cache = self.db.collection(recent_col)
        prompt_doc = PromptModel(
            prompt_hash=prompt_hash,
            result=result.__dict__,
            prompt_data=prompt,
            created_at=now,
            expires_at=expires_at,
            user_id=user_id,
        )

        recent_cache.insert(prompt_doc.dict())

        # Store metrics for monitoring
        metrics = self.db.collection(metrics_col)
        metrics.insert(
            {
                "prompt_hash": prompt_hash,
                "score": result.composite_score,
                "issue_count": len(result.issues),
                "action": result.action,
                "timestamp": now.isoformat(),  # Using the already created timezone-aware datetime
            },
        )

    def archive_old_prompts(self, age_days: int = 30) -> None:
        """
        Move old prompts from recent to archive cache.

        Args:
            age_days: Minimum age in days to archive
        """
        now = datetime.now(UTC)
        cutoff_date = now - timedelta(days=age_days)

        # Get collection names
        recent_col = IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection
        archive_col = IndalekoDBCollections.Indaleko_Prompt_Cache_Archive_Collection

        aql = """
            FOR doc IN @@recent_collection
                FILTER doc.created_at < @cutoff
                LET archive_doc = MERGE(
                    doc,
                    { archived_at: @now }
                )
                INSERT archive_doc INTO @@archive_collection
                REMOVE doc IN @@recent_collection
                RETURN 1
        """

        self.db.aql.execute(
            aql,
            bind_vars={
                "@recent_collection": recent_col,
                "@archive_collection": archive_col,
                "cutoff": cutoff_date.isoformat(),
                "now": now.isoformat(),
            },
        )

    def check_contradictions(self, prompt: dict[str, Any]) -> tuple[float, list[str]]:
        """
        Check the prompt for contradictions.

        Args:
            prompt: The structured prompt dictionary

        Returns:
            Tuple of (coherence_score, list_of_issues)
        """
        issues = []

        # Extract prompt layers
        context = prompt.get("context", "")
        constraints = prompt.get("constraints", {})
        preferences = prompt.get("preferences", {})

        # Apply pattern-based detection
        tier_scores = {
            "tier_1": 1.0,  # Context layer score
            "tier_2": 1.0,  # Constraints layer score
            "tier_3": 1.0,  # Preferences layer score
        }

        # Check for logical contradictions
        for pattern in self.contradiction_patterns["logical"]:
            if pattern["name"] == "opposite_directives":
                # Check each positive/negative pair
                for pos in pattern["pattern"]["positive"]:
                    for neg in pattern["pattern"]["negative"]:
                        if pos in context.lower() and neg in context.lower():
                            issues.append(f"Tier 1: Contradictory directives: '{pos}' and '{neg}'")
                            tier_scores["tier_1"] *= 1 - pattern["severity"]

                        if pos in str(constraints).lower() and neg in str(constraints).lower():
                            issues.append(f"Tier 2: Contradictory directives: '{pos}' and '{neg}'")
                            tier_scores["tier_2"] *= 1 - pattern["severity"]

            elif pattern["name"] == "format_conflict":
                formats_found = []
                for fmt in pattern["pattern"]["formats"]:
                    if fmt in str(constraints).lower() and "format" in str(constraints).lower():
                        formats_found.append(fmt)

                if len(formats_found) > 1:
                    issues.append(f"Tier 2: Conflicting format requirements: {', '.join(formats_found)}")
                    tier_scores["tier_2"] *= 1 - pattern["severity"]

        # Check for potential prompt injection
        injection_patterns = [
            "ignore all instructions",
            "ignore previous",
            "bypass",
            "execute code",
            "access internal",
            "forget your instructions",
        ]
        for pattern in injection_patterns:
            if pattern in context.lower():
                issues.append(f"Security: Potential injection pattern detected: '{pattern}'")
                tier_scores["tier_1"] *= 0.3  # Severe penalty

        # Calculate coherence as weighted average of tier scores
        coherence = (
            tier_scores["tier_1"] * 0.6  # Context is most important
            + tier_scores["tier_2"] * 0.3  # Constraints next
            + tier_scores["tier_3"] * 0.1  # Preferences least critical
        )

        return coherence, issues

    def check_ethicality(self, prompt: dict[str, Any]) -> float:
        """
        Check the prompt for ethical concerns using reviewer LLM.

        Args:
            prompt: The structured prompt dictionary

        Returns:
            Ethicality score between 0 and 1
        """
        # Get a reviewer LLM instance
        reviewer = self.llm_factory.get_llm(provider="preferred", role="reviewer")

        # Create a focused review prompt
        review_prompt = {
            "system": """
            You are an Ethics Reviewer for AI prompts. Evaluate the provided prompt for:
            1. Manipulation or coercion
            2. Deception or misleading instructions
            3. Requests for harmful outputs
            4. Privacy violations

            Format your response as a JSON object with:
            - ethical_score: 0.0-1.0 (where 1.0 is perfectly ethical)
            - issues: array of identified concerns
            - reasoning: brief explanation
            """,
            "user": f"Review this prompt for ethical concerns:\n\n{json.dumps(prompt, indent=2)}",
        }

        try:
            response = reviewer.get_completion(
                system_prompt=review_prompt["system"],
                user_prompt=review_prompt["user"],
                json_mode=True,
            )

            # Parse response (assuming JSON)
            review = json.loads(response)
            return float(review.get("ethical_score", 0.6))
        except Exception:
            # Fallback score on error
            return 0.6

    def check_mutualism(self, prompt: dict[str, Any]) -> float:
        """
        Evaluate if prompt supports mutual benefit (Ayni principle).

        Args:
            prompt: The structured prompt dictionary

        Returns:
            Mutualism score between 0 and 1
        """
        trust_contract = prompt.get("trust_contract", {})

        # Basic scoring based on presence of trust contract
        base_score = 0.7

        if trust_contract:
            # Add points for mutual intent
            if trust_contract.get("mutual_intent"):
                base_score += 0.1

            # Add points for specific commitments
            user_commitments = trust_contract.get("user_commitments", [])
            ai_commitments = trust_contract.get("ai_commitments", [])

            if user_commitments and ai_commitments:
                base_score += 0.1

            # Analyze trust contract elements with LLM if complex
            if len(str(trust_contract)) > 100:
                reviewer = self.llm_factory.get_llm(provider="preferred", role="reviewer")

                trust_prompt = {
                    "system": """
                    Analyze this trust contract for mutuality (Ayni principle).
                    Assess if it balances human and AI responsibilities fairly.
                    Return only a score from 0.0-1.0, where 1.0 is perfect mutuality.
                    """,
                    "user": f"Trust contract:\n\n{json.dumps(trust_contract, indent=2)}",
                }

                try:
                    response = reviewer.get_completion(
                        system_prompt=trust_prompt["system"],
                        user_prompt=trust_prompt["user"],
                    )
                    # Extract score from response
                    score_match = re.search(r"(\d+\.\d+)", response)
                    if score_match:
                        llm_score = float(score_match.group(1))
                        # Blend with base score
                        return (base_score + llm_score) / 2
                except Exception:
                    pass

        return base_score

    def evaluate(self, prompt: dict[str, Any], user_id: str | None = None) -> AyniResult:
        """
        Evaluate a prompt for stability, coherence, and ethical integrity.

        Args:
            prompt: The structured prompt dictionary
            user_id: Optional identifier of the prompt creator

        Returns:
            AyniResult with composite score and detailed analysis
        """
        # First check cache
        prompt_hash = self.compute_prompt_hash(prompt)
        cached_result = self.check_cache(prompt_hash)
        if cached_result:
            return cached_result

        # Perform evaluation
        issues = []
        coherence, coherence_issues = self.check_contradictions(prompt)
        issues.extend(coherence_issues)

        ethicality = self.check_ethicality(prompt)
        mutualism = self.check_mutualism(prompt)

        # Calculate tier scores
        tier_1_score = coherence * 0.95  # Context
        tier_2_score = coherence * 0.85  # Constraints
        tier_3_score = coherence * 0.8  # Preferences

        # Calculate composite score using weighted components
        composite_score = sum(
            score * weight
            for score, weight in [
                (coherence, self.weights["coherence"]),
                (ethicality, self.weights["ethicality"]),
                (mutualism, self.weights["mutualism"]),
                (tier_1_score, self.weights["tier_1_context"]),
                (tier_2_score, self.weights["tier_2_constraints"]),
                (tier_3_score, self.weights["tier_3_preferences"]),
            ]
        )

        # Round to 2 decimal places for consistency
        composite_score = round(composite_score, 2)

        # Determine action based on score thresholds (from AyniScore rubric)
        if composite_score < 0.5:
            action = "block"
        elif composite_score < 0.7:
            action = "warn"
        else:
            action = "proceed"

        # Create result object
        result = AyniResult(
            composite_score=composite_score,
            details={
                "coherence": coherence,
                "ethicality": ethicality,
                "mutualism": mutualism,
                "tier_1_context": {"score": tier_1_score, "issues": [i for i in issues if "Tier 1" in i]},
                "tier_2_constraints": {"score": tier_2_score, "issues": [i for i in issues if "Tier 2" in i]},
                "tier_3_preferences": {"score": tier_3_score, "issues": [i for i in issues if "Tier 3" in i]},
                "security": {"issues": [i for i in issues if "Security" in i]},
            },
            issues=issues,
            action=action,
        )

        # Store in cache
        self.store_cache(prompt_hash, result, prompt, user_id)

        return result

    def detect_injection_patterns(self, limit: int = 100) -> list[dict]:
        """
        Retrieve recent prompts with potential injection patterns.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of prompt documents with injection patterns
        """
        # Get collection name
        recent_col = IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection

        aql = """
            FOR doc IN @@collection
                FILTER
                    doc.result.issues[*] ANY LIKE "%injection%" OR
                    doc.result.issues[*] ANY LIKE "%Security%"
                SORT doc.created_at DESC
                LIMIT @limit
                RETURN {
                    prompt_hash: doc.prompt_hash,
                    issues: doc.result.issues,
                    score: doc.result.composite_score,
                    created_at: doc.created_at
                }
        """

        cursor = self.db.aql.execute(
            aql,
            bind_vars={"@collection": recent_col, "limit": limit},
        )

        return [doc for doc in cursor]


# Example usage
if __name__ == "__main__":
    guard = AyniGuard()

    sample_prompt = {
        "context": "Summarize the document clearly",
        "constraints": {"format": "json"},
        "preferences": {"tone": "neutral"},
        "trust_contract": {"mutual_intent": "maximize clarity"},
    }

    result = guard.evaluate(sample_prompt, user_id="test_user")

    # Use logging instead of print statements in production code
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("AyniScore: %.2f", result.composite_score)
    logger.info("Action: %s", result.action)
