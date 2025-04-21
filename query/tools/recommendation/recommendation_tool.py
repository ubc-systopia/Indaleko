"""
Recommendation tool for the Assistant API integration.

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

import os
import sys
import json
import uuid
from typing import Any, Dict, List, Optional

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.tools.base import BaseTool, ToolDefinition, ToolParameter, ToolInput, ToolOutput
from query.context.recommendations.engine import RecommendationEngine
from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationSource
)

# Import recommendation integration if available
try:
    from query.context.recommendations.archivist_integration import RecommendationArchivistIntegration
    HAS_ARCHIVIST_INTEGRATION = True
except ImportError:
    HAS_ARCHIVIST_INTEGRATION = False


class RecommendationTool(BaseTool):
    """
    Tool for generating and managing query recommendations.
    
    This tool integrates with the Recommendation Engine to provide contextualized
    query suggestions within the Assistant framework.
    """
    
    def __init__(self, recommendation_engine=None, archivist_integration=None):
        """
        Initialize the recommendation tool.
        
        Args:
            recommendation_engine: An existing RecommendationEngine instance
            archivist_integration: An existing RecommendationArchivistIntegration instance
        """
        super().__init__()
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.archivist_integration = archivist_integration
        
    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name="recommendation_tool",
            description="Generates query recommendations based on conversation context, user activities, and past queries",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="The action to perform: get_recommendations, provide_feedback, or get_stats",
                    required=True
                ),
                ToolParameter(
                    name="current_query",
                    type="string",
                    description="The current query being processed (optional)",
                    required=False
                ),
                ToolParameter(
                    name="context_data",
                    type="object",
                    description="Additional context data for generating recommendations",
                    required=False
                ),
                ToolParameter(
                    name="suggestion_id",
                    type="string",
                    description="The ID of a suggestion when providing feedback",
                    required=False
                ),
                ToolParameter(
                    name="feedback_type",
                    type="string",
                    description="The type of feedback: accepted, rejected, helpful, not_helpful, or irrelevant",
                    required=False
                ),
                ToolParameter(
                    name="max_results",
                    type="number",
                    description="Maximum number of recommendations to return",
                    required=False,
                    default=3
                )
            ]
        )
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """
        Execute the recommendation tool.
        
        Args:
            tool_input: The tool input.
            
        Returns:
            ToolOutput: The tool output.
        """
        # Extract parameters
        action = tool_input.parameters.get("action")
        current_query = tool_input.parameters.get("current_query", "")
        context_data = tool_input.parameters.get("context_data", {})
        suggestion_id = tool_input.parameters.get("suggestion_id")
        feedback_type = tool_input.parameters.get("feedback_type")
        max_results = tool_input.parameters.get("max_results", 3)
        
        # Process the action
        if action == "get_recommendations":
            return self._get_recommendations(current_query, context_data, max_results, tool_input.conversation_id)
        elif action == "provide_feedback":
            return self._provide_feedback(suggestion_id, feedback_type, tool_input.conversation_id)
        elif action == "get_stats":
            return self._get_stats()
        else:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Unknown action: {action}",
                tool_name=self.definition.name
            )
    
    def _get_recommendations(self, current_query: str, context_data: Dict[str, Any], 
                            max_results: int, conversation_id: Optional[str] = None) -> ToolOutput:
        """
        Get query recommendations.
        
        Args:
            current_query: The current query.
            context_data: Additional context data.
            max_results: Maximum number of recommendations to return.
            conversation_id: The conversation ID.
            
        Returns:
            ToolOutput: The tool output with recommendations.
        """
        try:
            # Process context data to extract information for generating recommendations
            processed_context = context_data.copy()
            
            # Add conversation ID if available
            if conversation_id:
                processed_context["conversation_id"] = conversation_id
            
            # If Archivist integration is available, get enhanced context
            if HAS_ARCHIVIST_INTEGRATION and self.archivist_integration:
                archivist_context = self.archivist_integration._prepare_context_data()
                processed_context.update(archivist_context)
            
            # Get recommendations from the engine
            recommendations = self.recommendation_engine.get_recommendations(
                current_query=current_query,
                context_data=processed_context,
                max_results=max_results
            )
            
            # Format the recommendations
            formatted_recommendations = []
            for rec in recommendations:
                formatted_recommendations.append({
                    "id": str(rec.suggestion_id),
                    "query": rec.query,
                    "description": rec.description,
                    "confidence": rec.confidence,
                    "source": rec.source.value
                })
            
            # Return the recommendations
            return ToolOutput(
                success=True,
                result={
                    "recommendations": formatted_recommendations,
                    "count": len(formatted_recommendations),
                    "current_query": current_query
                },
                error=None,
                tool_name=self.definition.name
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Error generating recommendations: {str(e)}",
                tool_name=self.definition.name
            )
    
    def _provide_feedback(self, suggestion_id: str, feedback_type: str, 
                         conversation_id: Optional[str] = None) -> ToolOutput:
        """
        Provide feedback on a recommendation.
        
        Args:
            suggestion_id: The suggestion ID.
            feedback_type: The type of feedback.
            conversation_id: The conversation ID.
            
        Returns:
            ToolOutput: The tool output.
        """
        try:
            # Validate feedback type
            try:
                feedback = FeedbackType(feedback_type.lower())
            except ValueError:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"Invalid feedback type: {feedback_type}. Valid types: {', '.join(f.value for f in FeedbackType)}",
                    tool_name=self.definition.name
                )
            
            # Convert suggestion ID to UUID
            try:
                uuid_suggestion_id = uuid.UUID(suggestion_id)
            except ValueError:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"Invalid suggestion ID: {suggestion_id}",
                    tool_name=self.definition.name
                )
            
            # Record feedback in the recommendation engine
            self.recommendation_engine.record_feedback(
                suggestion_id=uuid_suggestion_id,
                feedback=feedback
            )
            
            # If Archivist integration is available, also record there
            if HAS_ARCHIVIST_INTEGRATION and self.archivist_integration:
                # Map feedback types to positive/negative values
                feedback_value = 1.0 if feedback in [FeedbackType.ACCEPTED, FeedbackType.HELPFUL] else -1.0
                
                # Convert to suggestion format expected by Archivist integration
                source_to_type = {
                    "query_history": "QUERY",
                    "activity_context": "QUERY",
                    "entity_relationship": "RELATED_CONTENT",
                    "temporal_pattern": "REMINDER"
                }
                
                suggestion = None
                for rec in self.recommendation_engine.recent_suggestions.values():
                    if rec.suggestion_id == uuid_suggestion_id:
                        # Try to get the suggestion from Archivist to provide feedback
                        if hasattr(self.archivist_integration, 'proactive') and self.archivist_integration.proactive:
                            for sugg in self.archivist_integration.proactive.data.active_suggestions:
                                if sugg.context.get("recommendation_id") == str(rec.suggestion_id):
                                    self.archivist_integration.proactive.record_user_feedback(
                                        sugg.suggestion_id, feedback_value
                                    )
                                    break
                        break
            
            return ToolOutput(
                success=True,
                result={
                    "message": f"Feedback recorded: {feedback.value} for suggestion {suggestion_id}",
                    "feedback_type": feedback.value
                },
                error=None,
                tool_name=self.definition.name
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Error recording feedback: {str(e)}",
                tool_name=self.definition.name
            )
    
    def _get_stats(self) -> ToolOutput:
        """
        Get statistics about recommendations.
        
        Returns:
            ToolOutput: The tool output with statistics.
        """
        try:
            # Get stats from the recommendation engine
            stats = self.recommendation_engine.get_feedback_stats()
            
            return ToolOutput(
                success=True,
                result=stats,
                error=None,
                tool_name=self.definition.name
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Error retrieving statistics: {str(e)}",
                tool_name=self.definition.name
            )


class RecommendationAssistantIntegration:
    """
    Class for integrating recommendations with the Assistant API.
    
    This class manages the interaction between the Assistant API and the
    RecommendationEngine, updating conversation state with recommendations
    and handling recommendation-related actions.
    """
    
    def __init__(self, assistant, recommendation_engine=None, archivist_integration=None):
        """
        Initialize the integration.
        
        Args:
            assistant: The IndalekoAssistant instance
            recommendation_engine: An existing RecommendationEngine instance
            archivist_integration: An existing RecommendationArchivistIntegration instance
        """
        self.assistant = assistant
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.archivist_integration = archivist_integration
        
        # Create the recommendation tool
        self.recommendation_tool = RecommendationTool(
            recommendation_engine=self.recommendation_engine,
            archivist_integration=self.archivist_integration
        )
        
        # Register the tool with the assistant's registry
        self.assistant.tool_registry.register_tool(self.recommendation_tool)
    
    def update_conversation_context(self, conversation_id: str, 
                                  current_query: Optional[str] = None) -> None:
        """
        Update the conversation context with recommendations.
        
        Args:
            conversation_id: The conversation ID.
            current_query: The current query being processed.
        """
        # Get the conversation
        conversation = self.assistant.get_conversation(conversation_id)
        if not conversation:
            return
        
        # Get current context from the conversation
        context_data = {
            "recent_queries": [
                msg.content for msg in conversation.messages 
                if msg.role == "user" and self._is_likely_query(msg.content)
            ][-5:],
            "conversation_id": conversation_id
        }
        
        # If we have referenced memories, add them to context
        if conversation.referenced_memories:
            context_data["referenced_memories"] = [
                {
                    "memory_id": memory.memory_id,
                    "memory_type": memory.memory_type,
                    "summary": memory.summary
                }
                for memory in conversation.referenced_memories
            ]
        
        # If we have entities, add them to context
        if conversation.entities:
            context_data["entities"] = {
                name: {
                    "type": entity.type,
                    "value": entity.value,
                    "confidence": entity.confidence
                }
                for name, entity in conversation.entities.items()
            }
        
        # Get recommendations
        recommendations = self.recommendation_engine.get_recommendations(
            current_query=current_query,
            context_data=context_data,
            max_results=3
        )
        
        # Store recommendations in conversation context
        formatted_recommendations = []
        for rec in recommendations:
            formatted_recommendations.append({
                "id": str(rec.suggestion_id),
                "query": rec.query,
                "description": rec.description,
                "confidence": rec.confidence,
                "source": rec.source.value
            })
        
        # Store in context variables
        conversation.set_context_variable("recommendations", formatted_recommendations)
        conversation.set_context_variable("last_recommendation_time", conversation.updated_at)
    
    def _is_likely_query(self, message: str) -> bool:
        """
        Determine if a message is likely a query rather than a conversational message.
        
        Args:
            message: The message to analyze.
            
        Returns:
            bool: True if the message is likely a query, False otherwise.
        """
        # Define query indicators
        query_indicators = [
            "show me", "find", "search for", "look for", "get", "retrieve",
            "where is", "when did", "how many", "list all", "display", 
            "what is", "who is", "which", "where are"
        ]
        
        # Check for question marks
        has_question_mark = "?" in message
        
        # Check for query indicators
        message_lower = message.lower()
        has_query_indicator = any(indicator in message_lower for indicator in query_indicators)
        
        # Check length (queries tend to be shorter)
        is_short = len(message.split()) < 15
        
        # Check for command-like syntax (not conversational)
        starts_with_verb = any(message_lower.startswith(verb) for verb in [
            "show", "find", "search", "get", "list", "display", "retrieve"
        ])
        
        # Calculate a score based on these factors
        score = 0
        if has_question_mark:
            score += 1
        if has_query_indicator:
            score += 2
        if is_short:
            score += 1
        if starts_with_verb:
            score += 2
            
        # If score is at least 2, it's likely a query
        return score >= 2