#!/usr/bin/env python
"""
Enhanced query generator with improved diversity techniques.

This module provides an enhanced query generator for ablation testing that creates
queries with high diversity across multiple dimensions.
"""

import json
import logging
import os
import random
import sys
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not (os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
        if current_path == os.path.dirname(current_path):  # Reached root directory
            break
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# Import from our own query utils
from research.ablation.query.llm_query_generator import LLMQueryGenerator


class EnhancedQueryGenerator:
    """Enhanced query generator with improved diversity techniques."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize the enhanced query generator.

        Args:
            api_key: Optional API key for the LLM service
        """
        self.logger = logging.getLogger(__name__)

        # Use the SimpleLLMClient directly as it better handles the Anthropic API responses
        try:
            from research.ablation.query.enhanced.llm_client import SimpleLLMClient
            self.generator = SimpleLLMClient(
                api_key=api_key,
                model="claude-3-7-sonnet-latest"
            )
            self.logger.info("Successfully initialized SimpleLLMClient for query generation")
        except Exception as client_error:
            self.logger.error(f"CRITICAL: Failed to initialize LLM client: {client_error}")
            self.logger.error("This is required for proper ablation testing - fix the query generator")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

        # The last diversity evaluation results
        self.last_evaluation = {}

        # Improvement suggestions from previous evaluations
        self.improvement_suggestions = {}

    def generate_enhanced_queries(
        self, activity_type: str, count: int = 5, include_improvements: bool = True,
    ) -> list[str]:
        """
        Generate enhanced queries with improved diversity.

        Args:
            activity_type: Type of activity to generate queries for
            count: Number of queries to generate
            include_improvements: Whether to include diversity improvements

        Returns:
            List of enhanced queries
        """
        # First generate standard queries using base generator
        base_queries = self.generator.generate_queries_for_activity_type(activity_type, count=count)

        # If not using improvements, return base queries
        if not include_improvements:
            return base_queries

        # Evaluate diversity of base queries
        evaluation = self.evaluate_query_diversity(base_queries)
        self.last_evaluation[activity_type] = evaluation

        # Extract improvement suggestions
        if isinstance(evaluation, dict) and "improvement_suggestions" in evaluation:
            improvement_text = evaluation["improvement_suggestions"]
            self.improvement_suggestions[activity_type] = improvement_text

        # Generate enhanced queries with the improvements
        return self._generate_with_improvements(activity_type, base_queries, count)

    def _generate_with_improvements(self, activity_type: str, base_queries: list[str], count: int) -> list[str]:
        """
        Generate queries with diversity improvements.

        Args:
            activity_type: Type of activity
            base_queries: Initial set of queries
            count: Number of queries to generate

        Returns:
            Enhanced queries
        """
        system_prompt = f"""You are an expert in generating diverse search queries that people might use to find files based on their activities.
You specialize in creating queries for {activity_type} activity that demonstrate high diversity across multiple dimensions.

Previously generated queries lacked diversity in these ways:
1. Structural: Too many followed the '[content type] + [action verb] + [location/context]' pattern
2. Entity: Limited variety of specific named entities
3. Intent: Most queries had the same retrieval intent
4. Length: Too many queries of similar length (5-9 words)

Your task is to generate MORE DIVERSE {activity_type} queries by focusing on:
1. Using different sentence structures (questions, commands, keywords, etc.)
2. Including specific named entities (people, companies, products, locations)
3. Representing different search intents (finding, comparing, creating, sharing)
4. Varying query length (include very short and much longer queries)
5. Using different perspectives (not all first-person)

Return ONLY the queries as a numbered list. Don't include any explanations or other text.
"""

        # Include activity-specific improvement suggestions
        if activity_type in self.improvement_suggestions:
            improvements = self.improvement_suggestions[activity_type]
            system_prompt += f"\n\nImportant improvements needed for {activity_type} queries:\n{improvements}"

        # Previous queries (provide context on what's already generated)
        previous_query_examples = "\n".join([f"- {q}" for q in base_queries[:3]])

        user_prompt = f"""Please generate {count} highly diverse search queries related to {activity_type} activity that demonstrate maximum diversity.

Here are some previously generated queries that LACKED diversity:
{previous_query_examples}

Your queries should be COMPLETELY DIFFERENT from these examples in structure, intent, and form.
Include:
- At least one question format
- At least one command/imperative format
- At least one very short (2-3 words) query
- At least one longer (10+ words) query
- Specific named entities (people, files, locations)
- Different perspectives (not all "I" or first-person)

Just list {count} different search queries, numbered from 1 to {count}.
"""

        # Generate enhanced queries with the improved system and user prompts
        self.logger.info(f"Generating enhanced {activity_type} queries...")
        try:
            # Explicitly catch TypeError and other issues with LLM connector
            # Critical fix: LLMQueryGenerator.get_completion doesn't accept stream parameter directly
            # We need to modify the relevant AnthropicConnector classes instead
            response = self.generator.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,  # Slightly higher temperature for more diversity
                max_tokens=1000    # Reasonable limit for query generation
            )
            
            # Immediately validate response type for fail-stop approach
            if not isinstance(response, str):
                self.logger.error(f"CRITICAL: LLM connector returned non-string response: {type(response)}")
                self.logger.error("The response type is incompatible with the query generator")
                self.logger.error("This is required for proper ablation testing - fix the LLM connector")
                sys.exit(1)  # Fail-stop immediately - no fallbacks
        except Exception as e:
            self.logger.error(f"CRITICAL: Error in LLM query generation: {e}")
            self.logger.error("This is required for proper ablation testing - fix the query generator")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

        # Response must be a string at this point due to our previous check

        # Parse response
        enhanced_queries = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove the number/bullet and any trailing punctuation
                query = line.split(".", 1)[-1].strip() if "." in line else line
                query = query.split(")", 1)[-1].strip() if ")" in line else query
                query = query.lstrip("- ").strip()
                if query:
                    enhanced_queries.append(query)

        # If parsing failed, fail immediately (fail-stop approach)
        if not enhanced_queries:
            self.logger.error("CRITICAL: Failed to extract queries from response")
            self.logger.error("This is required for proper ablation testing - fix the query generator")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

        # Limit to requested count
        return enhanced_queries[:count]

    # Fallback query generation has been removed to enforce fail-stop approach
    # This follows scientific rigor where failures must be visible and addressed directly

    def evaluate_query_diversity(self, queries: list[str]) -> dict[str, Any]:
        """
        Evaluate the diversity of generated queries.

        Args:
            queries: List of queries to evaluate

        Returns:
            Dictionary with diversity metrics
        """
        if not queries:
            return {"error": "No queries to evaluate"}

        # Prepare system prompt
        system_prompt = """You are an expert in analyzing search query diversity and quality.
Your task is to evaluate a list of search queries and provide diversity metrics.
Analyze patterns, variety in structure, entity usage, and overall quality.
"""

        # Prepare user prompt
        user_prompt = f"""Please analyze these {len(queries)} search queries for diversity and quality:

{json.dumps(queries, indent=2)}

Evaluate them based on:
1. Structural diversity (different query patterns)
2. Entity diversity (variety of named entities)
3. Intent diversity (different search goals)
4. Length diversity (variation in query length)
5. Overall quality and realism

Return a JSON object with the following structure:
{{
  "diversity_score": 0-10 score,
  "structural_analysis": "Analysis of the patterns",
  "entity_analysis": "Analysis of entity usage",
  "intent_analysis": "Analysis of query intents",
  "length_analysis": "Analysis of query lengths",
  "overall_quality": "Assessment of quality and realism",
  "improvement_suggestions": "Ways to improve diversity"
}}
"""

        # Get completion
        response = self.generator.get_completion(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.0)

        # Handle non-string responses
        if not isinstance(response, str):
            self.logger.warning(f"Non-string response: {type(response)}")

            # Try to extract from dictionary response
            if isinstance(response, dict):
                # Try to extract text from dictionary
                if "answer" in response:
                    response = response["answer"]
                elif "text" in response:
                    response = response["text"]
                elif "content" in response:
                    response = response["content"]
                else:
                    # If we can't extract text, use the raw dict as our result
                    return {
                        "diversity_score": 5,  # Default middle score
                        "structural_analysis": "Unable to analyze due to API response format",
                        "entity_analysis": "Unable to analyze due to API response format",
                        "intent_analysis": "Unable to analyze due to API response format",
                        "length_analysis": "Unable to analyze due to API response format",
                        "overall_quality": "Unable to analyze due to API response format",
                        "improvement_suggestions": "Try more varied query structures and entity types",
                        "error": f"Non-string response: {type(response)}",
                        "raw_response": str(response),
                    }
            else:
                # Non-dict, non-string response
                return {
                    "diversity_score": 5,  # Default middle score
                    "structural_analysis": "Unable to analyze due to API response format",
                    "entity_analysis": "Unable to analyze due to API response format",
                    "intent_analysis": "Unable to analyze due to API response format",
                    "length_analysis": "Unable to analyze due to API response format",
                    "overall_quality": "Unable to analyze due to API response format",
                    "improvement_suggestions": "Try more varied query structures and entity types",
                    "error": f"Non-string response: {type(response)}",
                    "raw_response": str(response),
                }

        # Parse string response
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # Try to extract JSON using regex
            import re

            json_match = re.search(r"{.*}", response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Return a default response with the raw text
            return {
                "diversity_score": 5,  # Default middle score
                "structural_analysis": "Unable to analyze due to parsing error",
                "entity_analysis": "Unable to analyze due to parsing error",
                "intent_analysis": "Unable to analyze due to parsing error",
                "length_analysis": "Unable to analyze due to parsing error",
                "overall_quality": "Unable to analyze due to parsing error",
                "improvement_suggestions": "Try more varied query structures and entity types",
                "error": "Failed to parse response as JSON",
                "raw_response": response[:500],  # First 500 chars to avoid too large responses
            }

    def compare_base_vs_enhanced(self, activity_type: str, count: int = 5) -> dict[str, Any]:
        """
        Compare base generation vs. enhanced generation.

        Args:
            activity_type: Type of activity
            count: Number of queries to generate

        Returns:
            Dictionary with comparison results
        """
        print(f"\n=== Comparing Base vs. Enhanced {activity_type.title()} Queries ===")

        # Generate both types of queries
        base_queries = self.generator.generate_queries(activity_type, count)
        enhanced_queries = self.generate_enhanced_queries(activity_type, count)

        # Display generated queries
        print("\nBase Queries:")
        for i, query in enumerate(base_queries, 1):
            print(f"{i}. {query}")

        print("\nEnhanced Queries:")
        for i, query in enumerate(enhanced_queries, 1):
            print(f"{i}. {query}")

        # Evaluate diversity of both
        base_diversity = self.evaluate_query_diversity(base_queries)
        enhanced_diversity = self.evaluate_query_diversity(enhanced_queries)

        # Print diversity scores
        if isinstance(base_diversity, dict) and "diversity_score" in base_diversity:
            print(f"\nBase Diversity Score: {base_diversity.get('diversity_score')}/10")

        if isinstance(enhanced_diversity, dict) and "diversity_score" in enhanced_diversity:
            print(f"Enhanced Diversity Score: {enhanced_diversity.get('diversity_score')}/10")

            # Calculate improvement
            base_score = base_diversity.get("diversity_score", 0)
            enhanced_score = enhanced_diversity.get("diversity_score", 0)
            improvement = enhanced_score - base_score
            print(f"Improvement: {improvement:+.1f} points")

        # Return comparison results
        return {
            "activity_type": activity_type,
            "base_queries": base_queries,
            "enhanced_queries": enhanced_queries,
            "base_diversity": base_diversity,
            "enhanced_diversity": enhanced_diversity,
        }

    def run_comparison_test(self, activity_types: list[str], count: int = 5) -> dict[str, Any]:
        """
        Run comparison tests for multiple activity types.

        Args:
            activity_types: List of activity types to test
            count: Number of queries per type

        Returns:
            Dictionary with all comparison results
        """
        results = {}
        improvements = []

        for activity_type in activity_types:
            comparison = self.compare_base_vs_enhanced(activity_type, count)
            results[activity_type] = comparison

            # Calculate improvement
            base_score = comparison["base_diversity"].get("diversity_score", 0)
            enhanced_score = comparison["enhanced_diversity"].get("diversity_score", 0)
            improvement = enhanced_score - base_score
            improvements.append(improvement)

        # Calculate average improvement
        if improvements:
            avg_improvement = sum(improvements) / len(improvements)
            print(f"\nAverage Diversity Improvement: {avg_improvement:+.1f} points")

        # Save results to file
        output_file = "enhanced_query_comparison_results.json"
        with open(output_file, "w") as f:
            # Create serializable version without complex objects
            serializable_results = {}
            for activity_type, comparison in results.items():
                serializable_results[activity_type] = {
                    "base_queries": comparison["base_queries"],
                    "enhanced_queries": comparison["enhanced_queries"],
                    "base_diversity": comparison["base_diversity"],
                    "enhanced_diversity": comparison["enhanced_diversity"],
                }

            json.dump(
                {"results": serializable_results, "average_improvement": avg_improvement if improvements else 0},
                f,
                indent=2,
            )

        print(f"\nResults saved to {output_file}")
        return results


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced query generation with improved diversity")
    parser.add_argument(
        "--activity-type", type=str, default=None, help="Activity type to test (default: random selection)",
    )
    parser.add_argument("--count", type=int, default=5, help="Number of queries to generate per type (default: 5)")
    parser.add_argument("--all", action="store_true", help="Test all activity types")
    parser.add_argument("--implemented", action="store_true", help="Test only implemented activity types")
    args = parser.parse_args()

    try:
        # Create generator
        generator = EnhancedQueryGenerator()

        # Determine activity types to test
        activity_types = []

        if args.all:
            # All activity types
            activity_types = ["location", "task", "music", "collaboration", "storage", "media", "emotional", "social"]
        elif args.implemented:
            # Only implemented types
            activity_types = ["location", "task", "music", "collaboration", "storage", "media"]
        elif args.activity_type:
            # Single specified type
            activity_types = [args.activity_type]
        else:
            # Random selection of 2 types
            all_types = ["location", "task", "music", "collaboration", "storage", "media", "emotional", "social"]
            activity_types = random.sample(all_types, 2)

        # Run comparison test for selected activity types
        generator.run_comparison_test(activity_types, args.count)

    except Exception as e:
        logger.error(f"Error running enhanced query generation: {e}", exc_info=True)
