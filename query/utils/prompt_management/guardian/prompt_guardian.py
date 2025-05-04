"""
PromptGuardian for prompt verification and security enforcement.

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
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from data_models.base import IndalekoBaseModel
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections
from pydantic import BaseModel, Field

from query.utils.prompt_management.ayni.guard import AyniGuard, AyniResult
from query.utils.prompt_management.data_models.base import PromptTemplate

logger = logging.getLogger(__name__)


class VerificationLevel(str, Enum):
    """Verification levels for prompt guardian."""

    NONE = "none"  # No verification
    BASIC = "basic"  # Basic checks only
    STANDARD = "standard"  # Standard verification (default)
    STRICT = "strict"  # Strict verification
    PARANOID = "paranoid"  # Paranoid verification


class VerificationResult(BaseModel):
    """Result of prompt verification."""

    allowed: bool
    action: str  # "block", "warn", "proceed"
    score: float
    reasons: List[str]
    warnings: List[str]
    verification_time_ms: int
    trust_contract_valid: bool
    has_injection_patterns: bool
    security_issues: List[str]
    ethical_issues: List[str]
    recommendation: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationLog(IndalekoBaseModel):
    """Log entry for verification activity."""

    prompt_hash: str
    user_id: Optional[str] = None
    allowed: bool
    action: str
    score: float
    verification_level: str
    verification_time_ms: int
    reasons: List[str]
    warnings: List[str]
    trust_contract_valid: bool
    has_injection_patterns: bool
    security_issue_count: int
    ethical_issue_count: int
    verification_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def get_collection_name(cls) -> str:
        """Get the ArangoDB collection name for this model."""
        return IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection


class SecurityPolicy(BaseModel):
    """Security policy for prompt verification."""

    min_stability_score: Dict[str, float] = Field(
        default_factory=lambda: {
            VerificationLevel.NONE.value: 0.0,
            VerificationLevel.BASIC.value: 0.4,
            VerificationLevel.STANDARD.value: 0.6,
            VerificationLevel.STRICT.value: 0.75,
            VerificationLevel.PARANOID.value: 0.85,
        }
    )
    
    trust_contract_required: Dict[str, bool] = Field(
        default_factory=lambda: {
            VerificationLevel.NONE.value: False,
            VerificationLevel.BASIC.value: False,
            VerificationLevel.STANDARD.value: False,
            VerificationLevel.STRICT.value: True,
            VerificationLevel.PARANOID.value: True,
        }
    )
    
    banned_patterns: Set[str] = Field(
        default_factory=lambda: {
            "ignore all instructions",
            "ignore previous instructions",
            "disregard the above",
            "execute code without checking",
            "bypass security",
            "access internal systems",
            "provide unrestricted access",
            "forget your training",
        }
    )


class PromptGuardian:
    """
    Guardian system for prompt verification and security enforcement.
    
    This class provides a comprehensive system for verifying prompts
    before they are sent to LLMs, ensuring they meet security and ethical
    requirements.
    
    Features:
    - Multiple verification levels
    - Integration with AyniGuard for stability analysis
    - Trust contract verification
    - Injection pattern detection
    - Security policy enforcement
    - Verification logging and analytics
    """

    def __init__(
        self,
        db_instance: Optional[IndalekoCollection] = None,
        ayni_guard: Optional[AyniGuard] = None,
        security_policy: Optional[SecurityPolicy] = None,
        default_verification_level: VerificationLevel = VerificationLevel.STANDARD,
    ) -> None:
        """
        Initialize PromptGuardian.
        
        Args:
            db_instance: Database connection instance
            ayni_guard: AyniGuard instance for stability evaluation
            security_policy: Security policy for verification
            default_verification_level: Default verification level
        """
        self.db = db_instance or IndalekoCollection.get_db()
        self.ayni_guard = ayni_guard or AyniGuard(db_instance=self.db)
        self.security_policy = security_policy or SecurityPolicy()
        self.default_verification_level = default_verification_level
        self._verification_cache = {}  # In-memory cache for verification results
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Ensure required collections exist in database."""
        collections = [
            IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection,
        ]

        for collection_name in collections:
            self.db.get_collection(collection_name)

    def _check_banned_patterns(self, prompt_text: str) -> List[str]:
        """
        Check for banned patterns in prompt text with early return optimization.
        
        Args:
            prompt_text: Prompt text to check
            
        Returns:
            List of found banned patterns
        """
        # Fast path for short or empty prompts
        if len(prompt_text) < 10:
            return []
            
        found_patterns = []
        
        # Convert to lowercase for case-insensitive matching - do only once
        lower_prompt = prompt_text.lower()
        
        # For more efficient checking of patterns, first check if any known
        # trigger words exist in the prompt before doing full pattern checking
        trigger_words = ["ignore", "bypass", "disregard", "forget", "execute", "unrestricted", "access"]
        
        # Early return if no trigger words found
        if not any(word in lower_prompt for word in trigger_words):
            return []
        
        # Now check full patterns only if trigger words are found
        for pattern in self.security_policy.banned_patterns:
            if pattern.lower() in lower_prompt:
                found_patterns.append(pattern)
                # For PARANOID mode, we can return immediately after finding first pattern
                # This is commented out as it changes behavior slightly, but would be more efficient
                # if verification_level == VerificationLevel.PARANOID:
                #    return found_patterns
        
        return found_patterns
    
    def _check_trust_contract(self, structured_prompt: Dict[str, Any]) -> bool:
        """
        Check if the prompt has a valid trust contract.
        
        Args:
            structured_prompt: Structured prompt to check
            
        Returns:
            True if the trust contract is valid, False otherwise
        """
        # Check if trust contract exists
        if "trust_contract" not in structured_prompt:
            return False
        
        trust_contract = structured_prompt["trust_contract"]
        
        # Basic check - must have some content
        if not trust_contract or not isinstance(trust_contract, (dict, str)):
            return False
        
        # If it's a string, just check for non-emptiness
        if isinstance(trust_contract, str):
            return len(trust_contract.strip()) > 0
        
        # If it's a dict, check for mutual_intent or user_commitments
        return "mutual_intent" in trust_contract or "user_commitments" in trust_contract

    def _extract_issues(self, ayni_result: AyniResult) -> Dict[str, List[str]]:
        """
        Extract security and ethical issues from AyniResult.
        
        Args:
            ayni_result: AyniResult from evaluation
            
        Returns:
            Dictionary of security and ethical issues
        """
        security_issues = []
        ethical_issues = []
        
        # Extract security issues
        if "security" in ayni_result.details:
            security = ayni_result.details["security"]
            if "issues" in security:
                security_issues.extend(security["issues"])
        
        # Look for ethical issues in all issues
        ethical_keywords = [
            "ethical", "ethics", "moral", "harmful", "offensive", 
            "inappropriate", "bias", "privacy", "personal data"
        ]
        
        for issue in ayni_result.issues:
            lower_issue = issue.lower()
            if any(keyword in lower_issue for keyword in ethical_keywords):
                ethical_issues.append(issue)
        
        return {
            "security_issues": security_issues,
            "ethical_issues": ethical_issues,
        }

    def _log_verification(
        self, result: VerificationResult, prompt_hash: str, user_id: Optional[str], level: str
    ) -> None:
        """
        Log verification activity.
        
        Args:
            result: Verification result
            prompt_hash: Hash of the verified prompt
            user_id: Optional user identifier
            level: Verification level used
        """
        log_entry = VerificationLog(
            prompt_hash=prompt_hash,
            user_id=user_id,
            allowed=result.allowed,
            action=result.action,
            score=result.score,
            verification_level=level,
            verification_time_ms=result.verification_time_ms,
            reasons=result.reasons,
            warnings=result.warnings,
            trust_contract_valid=result.trust_contract_valid,
            has_injection_patterns=result.has_injection_patterns,
            security_issue_count=len(result.security_issues),
            ethical_issue_count=len(result.ethical_issues),
        )
        
        collection = self.db.collection(
            IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection
        )
        collection.insert(log_entry.dict())

    def _generate_recommendation(self, result: VerificationResult) -> str:
        """
        Generate a recommendation for improving the prompt.
        
        Args:
            result: Verification result
            
        Returns:
            Recommendation string
        """
        if result.allowed:
            if not result.warnings:
                return "No issues found. Prompt is safe to use."
            
            return "Prompt is allowed but with warnings. Consider addressing the warnings."
        
        recommendations = []
        
        if not result.trust_contract_valid:
            recommendations.append(
                "Add a trust contract section describing mutual expectations "
                "between the user and the AI."
            )
        
        if result.has_injection_patterns:
            recommendations.append(
                "Remove potentially harmful patterns like 'ignore instructions' "
                "or 'bypass security'."
            )
        
        for issue in result.security_issues:
            recommendations.append(f"Address security issue: {issue}")
        
        for issue in result.ethical_issues:
            recommendations.append(f"Address ethical issue: {issue}")
        
        if result.score < 0.6:
            recommendations.append(
                "The prompt stability score is low. Consider making the prompt "
                "more consistent and removing contradictions."
            )
        
        if not recommendations:
            recommendations.append(
                "The prompt does not meet security requirements. "
                "Please review and try again."
            )
        
        return "\n".join(recommendations)

    def verify_prompt(
        self,
        prompt: Union[str, Dict[str, Any]],
        level: Optional[VerificationLevel] = None,
        user_id: Optional[str] = None,
    ) -> VerificationResult:
        """
        Verify a prompt against security policies with caching for performance.
        
        Args:
            prompt: Prompt text or structured prompt
            level: Verification level
            user_id: Optional user identifier
            
        Returns:
            Verification result
        """
        start_time = time.time()
        
        # Use default level if not specified
        verification_level = level or self.default_verification_level
        
        # Skip verification if level is NONE
        if verification_level == VerificationLevel.NONE:
            return VerificationResult(
                allowed=True,
                action="proceed",
                score=1.0,
                reasons=["Verification disabled"],
                warnings=[],
                verification_time_ms=0,
                trust_contract_valid=True,
                has_injection_patterns=False,
                security_issues=[],
                ethical_issues=[],
            )
            
        # Convert to structured format for consistent handling
        if isinstance(prompt, str):
            structured_prompt = self._convert_to_structured(prompt)
        else:
            structured_prompt = prompt
            
        # Compute hash for cache lookup
        prompt_hash = self.ayni_guard.compute_prompt_hash(structured_prompt)
        
        # Create cache key that includes verification level
        cache_key = f"{prompt_hash}:{verification_level.value}"
        
        # Check cache first
        if cache_key in self._verification_cache:
            # Return cached result with updated timestamp
            cached_result = self._verification_cache[cache_key]
            cached_result.timestamp = datetime.now(timezone.utc)
            return cached_result
        
        # Initialize result variables
        reasons = []
        warnings = []
        allowed = True
        
        # Convert string prompt to structured format if needed
        if isinstance(prompt, str):
            structured_prompt = self._convert_to_structured(prompt)
        else:
            structured_prompt = prompt
        
        prompt_text = self._get_prompt_text(structured_prompt)
        prompt_hash = self.ayni_guard.compute_prompt_hash(structured_prompt)
        
        # Check for banned patterns
        banned_patterns = self._check_banned_patterns(prompt_text)
        has_injection_patterns = len(banned_patterns) > 0
        
        if has_injection_patterns:
            reasons.append(f"Found banned patterns: {', '.join(banned_patterns)}")
            
            # In PARANOID mode, any banned pattern is a blocker
            if verification_level == VerificationLevel.PARANOID:
                allowed = False
            else:
                warnings.append(f"Potentially harmful patterns detected: {', '.join(banned_patterns)}")
        
        # Check for trust contract
        trust_contract_valid = self._check_trust_contract(structured_prompt)
        
        if not trust_contract_valid and self.security_policy.trust_contract_required[verification_level.value]:
            reasons.append("Trust contract is required but not provided or invalid")
            allowed = False
        
        # Evaluate stability with AyniGuard
        ayni_result = self.ayni_guard.evaluate(structured_prompt, user_id)
        stability_score = ayni_result.composite_score
        
        # Check if score meets minimum threshold
        min_score = self.security_policy.min_stability_score[verification_level.value]
        
        if stability_score < min_score:
            reasons.append(f"Stability score {stability_score} is below minimum threshold {min_score}")
            allowed = False
        
        # Extract issues
        issues = self._extract_issues(ayni_result)
        security_issues = issues["security_issues"]
        ethical_issues = issues["ethical_issues"]
        
        # In STRICT and PARANOID modes, any security issue is a blocker
        if security_issues and verification_level in [VerificationLevel.STRICT, VerificationLevel.PARANOID]:
            reasons.append(f"Security issues detected: {', '.join(security_issues)}")
            allowed = False
        elif security_issues:
            warnings.extend([f"Security concern: {issue}" for issue in security_issues])
        
        # In PARANOID mode, any ethical issue is a blocker
        if ethical_issues and verification_level == VerificationLevel.PARANOID:
            reasons.append(f"Ethical issues detected: {', '.join(ethical_issues)}")
            allowed = False
        elif ethical_issues:
            warnings.extend([f"Ethical concern: {issue}" for issue in ethical_issues])
        
        # Determine action based on AyniResult
        action = ayni_result.action
        
        # Override action based on verification result
        if not allowed:
            action = "block"
        elif action == "block" and verification_level != VerificationLevel.PARANOID:
            # Downgrade to warning for non-paranoid levels
            action = "warn"
        
        # Calculate verification time
        verification_time_ms = int((time.time() - start_time) * 1000)
        
        # Create verification result
        result = VerificationResult(
            allowed=allowed,
            action=action,
            score=stability_score,
            reasons=reasons,
            warnings=warnings,
            verification_time_ms=verification_time_ms,
            trust_contract_valid=trust_contract_valid,
            has_injection_patterns=has_injection_patterns,
            security_issues=security_issues,
            ethical_issues=ethical_issues,
        )
        
        # Add recommendation
        result.recommendation = self._generate_recommendation(result)
        
        # Log verification
        self._log_verification(result, prompt_hash, user_id, verification_level.value)
        
        # Cache the result (up to a reasonable limit)
        if len(self._verification_cache) < 1000:  # Prevent unbounded growth
            self._verification_cache[cache_key] = result
        
        return result

    def _convert_to_structured(self, prompt_text: str) -> Dict[str, Any]:
        """
        Convert a text prompt to structured format.
        
        Args:
            prompt_text: Prompt text
            
        Returns:
            Structured prompt
        """
        # Simple parsing of sections
        sections = {}
        
        # Extract sections by headings
        context_match = re.search(r'# Context\s+(.*?)(?=# |$)', prompt_text, re.DOTALL)
        if context_match:
            sections["context"] = context_match.group(1).strip()
        
        requirements_match = re.search(r'# Requirements\s+(.*?)(?=# |$)', prompt_text, re.DOTALL)
        if requirements_match:
            sections["constraints"] = requirements_match.group(1).strip()
        
        preferences_match = re.search(r'# Preferences\s+(.*?)(?=# |$)', prompt_text, re.DOTALL)
        if preferences_match:
            sections["preferences"] = preferences_match.group(1).strip()
        
        agreement_match = re.search(r'# Agreement\s+(.*?)(?=# |$)', prompt_text, re.DOTALL)
        if agreement_match:
            sections["trust_contract"] = {
                "mutual_intent": agreement_match.group(1).strip()
            }
        
        # If no sections were found, use the whole prompt as context
        if not sections:
            sections["context"] = prompt_text
        
        return sections

    def _get_prompt_text(self, structured_prompt: Dict[str, Any]) -> str:
        """
        Get plain text representation of a structured prompt.
        
        Args:
            structured_prompt: Structured prompt
            
        Returns:
            Plain text representation
        """
        parts = []
        
        if "context" in structured_prompt:
            parts.append(f"# Context\n{structured_prompt['context']}")
        
        if "constraints" in structured_prompt:
            parts.append(f"# Requirements\n{structured_prompt['constraints']}")
        
        if "preferences" in structured_prompt:
            parts.append(f"# Preferences\n{structured_prompt['preferences']}")
        
        if "trust_contract" in structured_prompt:
            trust_contract = structured_prompt["trust_contract"]
            if isinstance(trust_contract, dict) and "mutual_intent" in trust_contract:
                parts.append(f"# Agreement\n{trust_contract['mutual_intent']}")
            elif isinstance(trust_contract, str):
                parts.append(f"# Agreement\n{trust_contract}")
            else:
                parts.append(f"# Agreement\n{json.dumps(trust_contract, indent=2)}")
        
        return "\n\n".join(parts)

    def get_verification_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get verification logs.
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            user_id: Optional user ID filter
            limit: Maximum number of logs to return
            
        Returns:
            List of verification logs
        """
        collection = self.db.collection(
            IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection
        )
        
        # Build filter conditions
        filters = []
        
        if start_time:
            filters.append("doc.verification_timestamp >= @start_time")
        
        if end_time:
            filters.append("doc.verification_timestamp <= @end_time")
        
        if user_id:
            filters.append("doc.user_id == @user_id")
        
        # Build AQL query
        aql = "FOR doc IN @@collection"
        
        if filters:
            aql += f" FILTER {' AND '.join(filters)}"
        
        aql += " SORT doc.verification_timestamp DESC LIMIT @limit RETURN doc"
        
        # Build bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection,
            "limit": limit,
        }
        
        if start_time:
            bind_vars["start_time"] = start_time.isoformat()
        
        if end_time:
            bind_vars["end_time"] = end_time.isoformat()
        
        if user_id:
            bind_vars["user_id"] = user_id
        
        # Execute query
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        
        return [doc for doc in cursor]

    def get_verification_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get verification metrics.
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            user_id: Optional user ID filter
            
        Returns:
            Verification metrics
        """
        collection = self.db.collection(
            IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection
        )
        
        # Build filter conditions
        filters = []
        
        if start_time:
            filters.append("doc.verification_timestamp >= @start_time")
        
        if end_time:
            filters.append("doc.verification_timestamp <= @end_time")
        
        if user_id:
            filters.append("doc.user_id == @user_id")
        
        # Build AQL query
        aql = """
            FOR doc IN @@collection
        """
        
        if filters:
            aql += f" FILTER {' AND '.join(filters)}"
        
        aql += """
            COLLECT AGGREGATE
                total = COUNT(),
                allowed = COUNT(doc.allowed == true),
                blocked = COUNT(doc.allowed == false),
                avg_score = AVERAGE(doc.score),
                warnings = SUM(LENGTH(doc.warnings)),
                security_issues = SUM(doc.security_issue_count),
                ethical_issues = SUM(doc.ethical_issue_count),
                trust_contract_valid = COUNT(doc.trust_contract_valid == true),
                trust_contract_invalid = COUNT(doc.trust_contract_valid == false),
                has_injection = COUNT(doc.has_injection_patterns == true),
                avg_verification_time = AVERAGE(doc.verification_time_ms)
            RETURN {
                "total_verifications": total,
                "allowed_count": allowed,
                "blocked_count": blocked,
                "allowed_percent": total > 0 ? (allowed / total) * 100 : 0,
                "avg_stability_score": avg_score,
                "warning_count": warnings,
                "security_issue_count": security_issues,
                "ethical_issue_count": ethical_issues,
                "trust_contract_valid_count": trust_contract_valid,
                "trust_contract_invalid_count": trust_contract_invalid,
                "injection_pattern_count": has_injection,
                "avg_verification_time_ms": avg_verification_time
            }
        """
        
        # Build bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection,
        }
        
        if start_time:
            bind_vars["start_time"] = start_time.isoformat()
        
        if end_time:
            bind_vars["end_time"] = end_time.isoformat()
        
        if user_id:
            bind_vars["user_id"] = user_id
        
        # Execute query
        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        
        if cursor.count() > 0:
            return cursor.next()
        
        # Return empty metrics if no data
        return {
            "total_verifications": 0,
            "allowed_count": 0,
            "blocked_count": 0,
            "allowed_percent": 0,
            "avg_stability_score": 0,
            "warning_count": 0,
            "security_issue_count": 0,
            "ethical_issue_count": 0,
            "trust_contract_valid_count": 0,
            "trust_contract_invalid_count": 0,
            "injection_pattern_count": 0,
            "avg_verification_time_ms": 0,
        }