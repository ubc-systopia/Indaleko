"""
Query history-based recommendation provider for the Contextual Query Recommendation Engine.

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

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from icecream import ic

from query.context.activity_provider import QueryActivityProvider
from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationSource,
)
from query.context.navigation import QueryNavigator
from query.context.recommendations.base import RecommendationProvider
from query.context.relationship import QueryRelationshipDetector, RelationshipType


class QueryHistoryRecommender(RecommendationProvider):
    """
    Generates query suggestions based on query history and relationships.
    
    This recommender analyzes patterns in the user's past queries and their relationships
    to suggest relevant new queries based on common refinement patterns, successful
    queries, and topic exploration paths.
    """
    
    def __init__(
        self, 
        query_provider: Optional[QueryActivityProvider] = None,
        query_navigator: Optional[QueryNavigator] = None,
        relationship_detector: Optional[QueryRelationshipDetector] = None,
        debug: bool = False
    ):
        """
        Initialize the query history recommender.
        
        Args:
            query_provider: Provider for query activities
            query_navigator: Navigator for exploring query relationships
            relationship_detector: Detector for identifying relationships between queries
            debug: Whether to enable debug output
        """
        super().__init__(RecommendationSource.QUERY_HISTORY, debug)
        
        # Initialize components or create new ones if not provided
        self.query_provider = query_provider or QueryActivityProvider(debug=debug)
        self.query_navigator = query_navigator or QueryNavigator(debug=debug)
        self.relationship_detector = relationship_detector or QueryRelationshipDetector(debug=debug)
        
        # Cache of successful queries and their result counts
        self.successful_queries = {}  # {query_text: result_count}
        
        # Cache of query patterns by relationship type
        self.refinement_patterns = {}  # {pattern: count}
        self.broadening_patterns = {}  # {pattern: count}
        self.pivot_patterns = {}  # {pattern: count}
        
        # Initialize with historical data
        self._initialize_from_history()
    
    def _initialize_from_history(self) -> None:
        """Initialize the recommender from historical data."""
        # Get recent query activities
        recent_activities = self.query_provider.get_recent_query_activities(limit=50)
        
        # Extract successful queries
        for activity in recent_activities:
            # Consider queries with results as successful
            if activity.result_count is not None and activity.result_count > 0:
                self.successful_queries[activity.query_text] = activity.result_count
        
        # Extract patterns from relationships
        for activity in recent_activities:
            if activity.relationship_type and activity.previous_query_id:
                # Find the previous query
                prev_activity = self.query_provider.get_query_activity(activity.previous_query_id)
                if prev_activity:
                    # Extract pattern based on relationship type
                    if activity.relationship_type == RelationshipType.REFINEMENT.value:
                        self._extract_refinement_pattern(prev_activity.query_text, activity.query_text)
                    elif activity.relationship_type == RelationshipType.BROADENING.value:
                        self._extract_broadening_pattern(prev_activity.query_text, activity.query_text)
                    elif activity.relationship_type == RelationshipType.PIVOT.value:
                        self._extract_pivot_pattern(prev_activity.query_text, activity.query_text)
    
    def _extract_refinement_pattern(self, previous_query: str, current_query: str) -> None:
        """
        Extract refinement pattern from a query pair.
        
        Args:
            previous_query: The previous, more general query
            current_query: The current, more specific query
        """
        # Simple pattern: adding terms
        for term in self._extract_terms(current_query):
            if term not in self._extract_terms(previous_query):
                # This term was added in the refinement
                pattern = f"add_term:{term}"
                self.refinement_patterns[pattern] = self.refinement_patterns.get(pattern, 0) + 1
        
        # Pattern: adding constraints
        for constraint_type, constraints in self._extract_constraints(current_query).items():
            prev_constraints = self._extract_constraints(previous_query).get(constraint_type, set())
            new_constraints = constraints - prev_constraints
            for constraint in new_constraints:
                pattern = f"add_constraint:{constraint_type}:{constraint}"
                self.refinement_patterns[pattern] = self.refinement_patterns.get(pattern, 0) + 1
    
    def _extract_broadening_pattern(self, previous_query: str, current_query: str) -> None:
        """
        Extract broadening pattern from a query pair.
        
        Args:
            previous_query: The previous, more specific query
            current_query: The current, more general query
        """
        # Simple pattern: removing terms
        for term in self._extract_terms(previous_query):
            if term not in self._extract_terms(current_query):
                # This term was removed in the broadening
                pattern = f"remove_term:{term}"
                self.broadening_patterns[pattern] = self.broadening_patterns.get(pattern, 0) + 1
        
        # Pattern: removing constraints
        for constraint_type, constraints in self._extract_constraints(previous_query).items():
            curr_constraints = self._extract_constraints(current_query).get(constraint_type, set())
            removed_constraints = constraints - curr_constraints
            for constraint in removed_constraints:
                pattern = f"remove_constraint:{constraint_type}:{constraint}"
                self.broadening_patterns[pattern] = self.broadening_patterns.get(pattern, 0) + 1
    
    def _extract_pivot_pattern(self, previous_query: str, current_query: str) -> None:
        """
        Extract pivot pattern from a query pair.
        
        Args:
            previous_query: The previous query
            current_query: The current, pivoted query
        """
        # Extract common and different terms
        prev_terms = self._extract_terms(previous_query)
        curr_terms = self._extract_terms(current_query)
        
        common_terms = prev_terms.intersection(curr_terms)
        pivot_terms = curr_terms - prev_terms
        
        # Record pivot patterns based on common terms
        for common_term in common_terms:
            for pivot_term in pivot_terms:
                pattern = f"pivot:{common_term}:{pivot_term}"
                self.pivot_patterns[pattern] = self.pivot_patterns.get(pattern, 0) + 1
    
    def _extract_terms(self, query: str) -> Set[str]:
        """
        Extract significant terms from a query.
        
        Args:
            query: The query to extract terms from
            
        Returns:
            Set of significant terms
        """
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter out common stop words
        stop_words = {"the", "and", "or", "in", "on", "at", "to", "of", "for", "with", "by", "as", "a", "an", "show", "find", "get", "me"}
        return {word for word in words if word not in stop_words and len(word) > 2}
    
    def _extract_constraints(self, query: str) -> Dict[str, Set[str]]:
        """
        Extract constraints from a query.
        
        Args:
            query: The query to extract constraints from
            
        Returns:
            Dictionary mapping constraint types to sets of constraints
        """
        constraints = {
            "time": set(),
            "file_type": set(),
            "location": set(),
            "person": set()
        }
        
        # Time constraints
        time_patterns = [
            (r'\byesterday\b', "yesterday"),
            (r'\btoday\b', "today"),
            (r'\blast\s+week\b', "last_week"),
            (r'\blast\s+month\b', "last_month"),
            (r'\blast\s+year\b', "last_year"),
            (r'\brecent\b', "recent"),
            (r'\bold\b', "old")
        ]
        for pattern, constraint in time_patterns:
            if re.search(pattern, query.lower()):
                constraints["time"].add(constraint)
        
        # File type constraints
        file_patterns = [
            (r'\bpdf\b', "pdf"),
            (r'\bdoc\b|\bdocx\b|\bdocument\b', "document"),
            (r'\bjpg\b|\bjpeg\b|\bpng\b|\bimage\b|\bphoto\b|\bpicture\b', "image"),
            (r'\bmp3\b|\bwav\b|\baudio\b|\bsound\b|\bmusic\b', "audio"),
            (r'\bmp4\b|\bmov\b|\bvideo\b', "video"),
            (r'\bxls\b|\bxlsx\b|\bspreadsheet\b', "spreadsheet"),
            (r'\btxt\b|\btext\b', "text")
        ]
        for pattern, constraint in file_patterns:
            if re.search(pattern, query.lower()):
                constraints["file_type"].add(constraint)
        
        # Location constraints
        location_patterns = [
            (r'\bfolder\b', "folder"),
            (r'\bdirectory\b', "directory"),
            (r'\bpath\b', "path"),
            (r'\blocal\b', "local"),
            (r'\bcloud\b', "cloud"),
            (r'\bdropbox\b', "dropbox"),
            (r'\bgoogle\s+drive\b', "google_drive"),
            (r'\bonedrive\b', "onedrive")
        ]
        for pattern, constraint in location_patterns:
            if re.search(pattern, query.lower()):
                constraints["location"].add(constraint)
        
        return {k: v for k, v in constraints.items() if v}
    
    def _apply_pattern_to_query(self, query: str, pattern: str) -> Optional[str]:
        """
        Apply a pattern to generate a new query.
        
        Args:
            query: The base query
            pattern: The pattern to apply
            
        Returns:
            New query or None if pattern cannot be applied
        """
        parts = pattern.split(":", 2)
        if len(parts) < 2:
            return None
            
        action = parts[0]
        
        if action == "add_term" and len(parts) == 2:
            term = parts[1]
            if term not in self._extract_terms(query):
                return f"{query} {term}"
                
        elif action == "add_constraint" and len(parts) == 3:
            constraint_type = parts[1]
            constraint = parts[2]
            
            # Simple constraint application
            if constraint_type == "time":
                if "time" not in query.lower() and constraint not in query.lower():
                    time_phrases = {
                        "yesterday": "from yesterday",
                        "today": "from today",
                        "last_week": "from last week",
                        "last_month": "from last month",
                        "last_year": "from last year",
                        "recent": "recent",
                        "old": "older than 6 months"
                    }
                    return f"{query} {time_phrases.get(constraint, constraint)}"
                    
            elif constraint_type == "file_type":
                if constraint not in query.lower():
                    return f"{query} {constraint} files"
                    
            elif constraint_type == "location":
                if constraint not in query.lower():
                    return f"{query} in {constraint}"
                    
        elif action == "remove_term" and len(parts) == 2:
            term = parts[1]
            if term in self._extract_terms(query):
                # Naive implementation - could be improved
                return re.sub(r'\b' + re.escape(term) + r'\b', '', query).strip()
                
        elif action == "remove_constraint" and len(parts) == 3:
            # For removing constraints, we'd need more sophisticated parsing
            # This is a simplified implementation
            constraint_type = parts[1]
            constraint = parts[2]
            
            if constraint in query.lower():
                # Naive implementation - could be improved
                return re.sub(r'\b' + re.escape(constraint) + r'\b', '', query).strip()
                
        elif action == "pivot" and len(parts) == 3:
            common_term = parts[1]
            pivot_term = parts[2]
            
            if common_term in self._extract_terms(query) and pivot_term not in self._extract_terms(query):
                # Add the pivot term
                return f"{query} {pivot_term}"
                
        return None
    
    def generate_suggestions(
        self,
        current_query: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        max_suggestions: int = 10
    ) -> List[QuerySuggestion]:
        """
        Generate query suggestions based on query history.
        
        Args:
            current_query: The current query, if any
            context_data: Additional context data
            max_suggestions: Maximum number of suggestions to generate
            
        Returns:
            List of query suggestions
        """
        suggestions = []
        context_data = context_data or {}
        
        # 1. Suggestions based on successful past queries
        successful_suggestions = self._generate_successful_query_suggestions(current_query, context_data)
        suggestions.extend(successful_suggestions)
        
        # 2. Suggestions based on refinement patterns
        if current_query:
            refinement_suggestions = self._generate_refinement_suggestions(current_query, context_data)
            suggestions.extend(refinement_suggestions)
        
        # 3. Suggestions based on broadening patterns
        if current_query:
            broadening_suggestions = self._generate_broadening_suggestions(current_query, context_data)
            suggestions.extend(broadening_suggestions)
        
        # 4. Suggestions based on pivot patterns
        if current_query:
            pivot_suggestions = self._generate_pivot_suggestions(current_query, context_data)
            suggestions.extend(pivot_suggestions)
        
        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:max_suggestions]
    
    def _generate_successful_query_suggestions(
        self, 
        current_query: Optional[str],
        context_data: Dict[str, Any]
    ) -> List[QuerySuggestion]:
        """
        Generate suggestions based on successful past queries.
        
        Args:
            current_query: The current query, if any
            context_data: Additional context data
            
        Returns:
            List of query suggestions
        """
        suggestions = []
        
        # Get recent activities with results
        recent_successful = []
        for query_text, result_count in self.successful_queries.items():
            # Skip if this is the current query
            if current_query and query_text.lower() == current_query.lower():
                continue
                
            # Skip if too similar to current query
            if current_query and self._query_similarity(query_text, current_query) > 0.8:
                continue
                
            recent_successful.append((query_text, result_count))
        
        # Sort by result count (higher is better)
        recent_successful.sort(key=lambda x: x[1], reverse=True)
        
        # Create suggestions for top queries
        for query_text, result_count in recent_successful[:5]:
            # Calculate confidence based on result count
            confidence_factor = min(result_count / 10, 1.0) if result_count > 0 else 0.5
            
            # Create suggestion
            suggestion = self.create_suggestion(
                query_text=query_text,
                rationale=f"This query returned {result_count} results in a previous search",
                confidence=confidence_factor * 0.7,  # Adjust base confidence
                source_context={
                    "result_count": result_count,
                    "type": "successful_query"
                },
                relevance_factors={
                    "result_count": confidence_factor,
                    "recency": 0.7  # Assuming relatively recent
                },
                tags=["successful_query", "historical"]
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_refinement_suggestions(
        self, 
        current_query: str,
        context_data: Dict[str, Any]
    ) -> List[QuerySuggestion]:
        """
        Generate suggestions based on refinement patterns.
        
        Args:
            current_query: The current query
            context_data: Additional context data
            
        Returns:
            List of query suggestions
        """
        suggestions = []
        
        # Find top refinement patterns
        top_patterns = sorted(
            self.refinement_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # Apply patterns to current query
        for pattern, count in top_patterns:
            refined_query = self._apply_pattern_to_query(current_query, pattern)
            if refined_query and refined_query != current_query:
                # Calculate confidence based on pattern frequency
                pattern_confidence = min(count / 5, 0.9)
                
                # Extract pattern type and details
                pattern_parts = pattern.split(":", 2)
                pattern_type = pattern_parts[0]
                pattern_details = ":".join(pattern_parts[1:]) if len(pattern_parts) > 1 else ""
                
                # Create suggestion
                suggestion = self.create_suggestion(
                    query_text=refined_query,
                    rationale=self._get_refinement_rationale(pattern),
                    confidence=pattern_confidence,
                    source_context={
                        "pattern": pattern,
                        "pattern_count": count,
                        "original_query": current_query,
                        "type": "refinement"
                    },
                    relevance_factors={
                        "pattern_frequency": pattern_confidence,
                        "query_similarity": 0.7
                    },
                    tags=["refinement", pattern_type, pattern_details]
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_broadening_suggestions(
        self, 
        current_query: str,
        context_data: Dict[str, Any]
    ) -> List[QuerySuggestion]:
        """
        Generate suggestions based on broadening patterns.
        
        Args:
            current_query: The current query
            context_data: Additional context data
            
        Returns:
            List of query suggestions
        """
        suggestions = []
        
        # Find top broadening patterns
        top_patterns = sorted(
            self.broadening_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Apply patterns to current query
        for pattern, count in top_patterns:
            broadened_query = self._apply_pattern_to_query(current_query, pattern)
            if broadened_query and broadened_query != current_query:
                # Calculate confidence based on pattern frequency
                pattern_confidence = min(count / 5, 0.8)  # Slightly lower base confidence than refinement
                
                # Extract pattern type and details
                pattern_parts = pattern.split(":", 2)
                pattern_type = pattern_parts[0]
                pattern_details = ":".join(pattern_parts[1:]) if len(pattern_parts) > 1 else ""
                
                # Create suggestion
                suggestion = self.create_suggestion(
                    query_text=broadened_query,
                    rationale=self._get_broadening_rationale(pattern),
                    confidence=pattern_confidence,
                    source_context={
                        "pattern": pattern,
                        "pattern_count": count,
                        "original_query": current_query,
                        "type": "broadening"
                    },
                    relevance_factors={
                        "pattern_frequency": pattern_confidence,
                        "query_similarity": 0.6
                    },
                    tags=["broadening", pattern_type, pattern_details]
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_pivot_suggestions(
        self, 
        current_query: str,
        context_data: Dict[str, Any]
    ) -> List[QuerySuggestion]:
        """
        Generate suggestions based on pivot patterns.
        
        Args:
            current_query: The current query
            context_data: Additional context data
            
        Returns:
            List of query suggestions
        """
        suggestions = []
        
        # Find top pivot patterns
        top_patterns = sorted(
            self.pivot_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Apply patterns to current query
        for pattern, count in top_patterns:
            pivoted_query = self._apply_pattern_to_query(current_query, pattern)
            if pivoted_query and pivoted_query != current_query:
                # Calculate confidence based on pattern frequency
                pattern_confidence = min(count / 5, 0.7)  # Lower base confidence for pivots
                
                # Extract pattern details
                pattern_parts = pattern.split(":", 3)
                if len(pattern_parts) >= 3:
                    common_term = pattern_parts[1]
                    pivot_term = pattern_parts[2]
                    
                    # Create suggestion
                    suggestion = self.create_suggestion(
                        query_text=pivoted_query,
                        rationale=f"People who search for '{common_term}' also look for '{pivot_term}'",
                        confidence=pattern_confidence,
                        source_context={
                            "pattern": pattern,
                            "pattern_count": count,
                            "original_query": current_query,
                            "common_term": common_term,
                            "pivot_term": pivot_term,
                            "type": "pivot"
                        },
                        relevance_factors={
                            "pattern_frequency": pattern_confidence,
                            "query_similarity": 0.5
                        },
                        tags=["pivot", common_term, pivot_term]
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _get_refinement_rationale(self, pattern: str) -> str:
        """
        Get a human-readable rationale for a refinement pattern.
        
        Args:
            pattern: The refinement pattern
            
        Returns:
            Human-readable rationale
        """
        parts = pattern.split(":", 2)
        if len(parts) < 2:
            return "Refine your search based on common patterns"
            
        action = parts[0]
        
        if action == "add_term" and len(parts) == 2:
            term = parts[1]
            return f"Add '{term}' to narrow your search results"
            
        elif action == "add_constraint" and len(parts) == 3:
            constraint_type = parts[1]
            constraint = parts[2]
            
            if constraint_type == "time":
                return f"Add time constraint '{constraint}' to focus on specific timeframe"
            elif constraint_type == "file_type":
                return f"Specify '{constraint}' file type to filter results"
            elif constraint_type == "location":
                return f"Narrow search to '{constraint}' location"
            else:
                return f"Add '{constraint}' constraint to refine results"
                
        return "Refine your search based on common patterns"
    
    def _get_broadening_rationale(self, pattern: str) -> str:
        """
        Get a human-readable rationale for a broadening pattern.
        
        Args:
            pattern: The broadening pattern
            
        Returns:
            Human-readable rationale
        """
        parts = pattern.split(":", 2)
        if len(parts) < 2:
            return "Broaden your search to find more results"
            
        action = parts[0]
        
        if action == "remove_term" and len(parts) == 2:
            term = parts[1]
            return f"Remove '{term}' to find more general results"
            
        elif action == "remove_constraint" and len(parts) == 3:
            constraint_type = parts[1]
            constraint = parts[2]
            
            if constraint_type == "time":
                return f"Remove time constraint '{constraint}' to see results from all time periods"
            elif constraint_type == "file_type":
                return f"Remove '{constraint}' file type filter to see all file types"
            elif constraint_type == "location":
                return f"Search beyond '{constraint}' location to find more results"
            else:
                return f"Remove '{constraint}' constraint to broaden results"
                
        return "Broaden your search to find more results"
    
    def _query_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate similarity between two queries.
        
        Args:
            query1: First query
            query2: Second query
            
        Returns:
            Similarity score (0.0-1.0)
        """
        terms1 = self._extract_terms(query1)
        terms2 = self._extract_terms(query2)
        
        if not terms1 or not terms2:
            return 0.0
            
        # Jaccard similarity: intersection / union
        intersection = len(terms1.intersection(terms2))
        union = len(terms1.union(terms2))
        
        return intersection / union if union > 0 else 0.0
    
    def update_from_feedback(
        self,
        suggestion: QuerySuggestion,
        feedback: FeedbackType,
        result_count: Optional[int] = None
    ) -> None:
        """
        Update internal models based on feedback.
        
        Args:
            suggestion: The suggestion that received feedback
            feedback: The type of feedback provided
            result_count: Number of results from the suggested query, if applicable
        """
        query_text = suggestion.query_text
        source_context = suggestion.source_context
        
        # Update successful queries cache
        if (self.is_positive_feedback(feedback) and 
            result_count is not None and 
            result_count > 0):
            self.successful_queries[query_text] = result_count
        
        # Update pattern statistics
        if source_context and "type" in source_context and "pattern" in source_context:
            suggestion_type = source_context["type"]
            pattern = source_context["pattern"]
            
            if self.is_positive_feedback(feedback):
                # Increase pattern count for positive feedback
                if suggestion_type == "refinement" and pattern in self.refinement_patterns:
                    self.refinement_patterns[pattern] += 1
                elif suggestion_type == "broadening" and pattern in self.broadening_patterns:
                    self.broadening_patterns[pattern] += 1
                elif suggestion_type == "pivot" and pattern in self.pivot_patterns:
                    self.pivot_patterns[pattern] += 1
            
            elif self.is_negative_feedback(feedback):
                # Decrease pattern count for negative feedback
                if suggestion_type == "refinement" and pattern in self.refinement_patterns:
                    self.refinement_patterns[pattern] = max(0, self.refinement_patterns[pattern] - 1)
                elif suggestion_type == "broadening" and pattern in self.broadening_patterns:
                    self.broadening_patterns[pattern] = max(0, self.broadening_patterns[pattern] - 1)
                elif suggestion_type == "pivot" and pattern in self.pivot_patterns:
                    self.pivot_patterns[pattern] = max(0, self.pivot_patterns[pattern] - 1)