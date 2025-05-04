"""
Contradiction detection data models for the Prompt Management System.

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

from enum import Enum

from pydantic import Field

from data_models.base import IndalekoBaseModel


class ContradictionType(str, Enum):
    """Types of contradictions that can be detected in prompts."""

    LOGICAL = "logical"  # e.g., A and not A
    SEMANTIC = "semantic"  # e.g., conceptual clashes
    STRUCTURAL = "structural"  # e.g., cross-layer conflicts
    TEMPORAL = "temporal"  # e.g., time-based contradictions
    IDENTITY = "identity"  # e.g., role confusion
    NUMERICAL = "numerical"  # e.g., range conflicts
    FORMAT = "format"  # e.g., response format conflicts
    GUIDANCE = "guidance"  # e.g., contradictory guidance


class ContradictionPattern(IndalekoBaseModel):
    """A pattern for detecting contradictions in prompts."""

    name: str
    description: str
    pattern_type: ContradictionType
    severity: float  # 0.0 to 1.0, how severe the contradiction is

    # Detection components vary by pattern type
    # For example:
    positive_terms: list[str] | None = None  # Terms that conflict with negative terms
    negative_terms: list[str] | None = None  # Terms that conflict with positive terms
    mutually_exclusive: list[str] | None = None  # Set of terms where only one can be true
    regex_patterns: dict[str, str] | None = None  # Named regex patterns

    # Metadata for pattern management
    author: str | None = None
    created_by_llm: bool = False
    verified: bool = False
    examples: list[str] = Field(default_factory=list)

    def matches(self, text: str) -> bool:
        """
        Check if the contradiction pattern matches the given text.

        This is a basic implementation that should be extended with
        more sophisticated matching logic.

        Args:
            text: The text to check for contradictions

        Returns:
            True if the pattern matches, False otherwise
        """
        if not self.positive_terms or not self.negative_terms:
            return False

        # Check if any positive term AND any negative term are present
        positive_present = any(term.lower() in text.lower() for term in self.positive_terms)
        negative_present = any(term.lower() in text.lower() for term in self.negative_terms)

        return positive_present and negative_present


class DetectedContradiction(IndalekoBaseModel):
    """A contradiction detected in a prompt."""

    pattern_name: str
    contradiction_type: ContradictionType
    severity: float
    confidence: float  # 0.0 to 1.0, how confident the detection is
    evidence: dict[str, str]  # Map of term to context snippet where found
    location: str | None = None  # Where in the prompt the contradiction was found
    explanation: str | None = None  # Human-readable explanation


class PatternLibrary(IndalekoBaseModel):
    """A collection of contradiction patterns."""

    patterns: dict[ContradictionType, list[ContradictionPattern]] = Field(default_factory=dict)

    def add_pattern(self, pattern: ContradictionPattern) -> None:
        """
        Add a pattern to the library.

        Args:
            pattern: The pattern to add
        """
        if pattern.pattern_type not in self.patterns:
            self.patterns[pattern.pattern_type] = []
        self.patterns[pattern.pattern_type].append(pattern)

    def detect_contradictions(self, text: str) -> list[DetectedContradiction]:
        """
        Detect contradictions in the given text using all patterns.

        Args:
            text: The text to check for contradictions

        Returns:
            List of detected contradictions
        """
        results = []
        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.matches(text):
                    results.append(
                        DetectedContradiction(
                            pattern_name=pattern.name,
                            contradiction_type=pattern.pattern_type,
                            severity=pattern.severity,
                            confidence=0.8,  # TODO: Implement confidence calculation
                            evidence={},  # TODO: Extract evidence from text
                        ),
                    )
        return results
