"""
Example demonstrating the PromptManager usage.

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
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from query.utils.prompt_management.data_models.base import PromptTemplate, PromptTemplateType, TemplateVariable
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable
from db.collection import IndalekoCollection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_example_templates(prompt_manager):
    """Create example templates in the database."""
    # Simple template
    simple_template = PromptTemplate(
        name="Simple Question Template",
        template_type=PromptTemplateType.SIMPLE,
        template_text="You are an AI assistant. Please answer the following question: $question",
        description="A simple template for asking questions",
        variables=[
            TemplateVariable(
                name="question",
                description="The question to ask",
                required=True,
                default_value="",
                example="What is the capital of France?",
            )
        ],
    )
    
    simple_template_id = prompt_manager.save_template(simple_template)
    logger.info(f"Created simple template with ID: {simple_template_id}")
    
    # Layered template
    layered_template_content = [
        {
            "type": "immutable_context",
            "content": "You are an AI coding assistant specializing in $language programming.",
            "order": 1,
        },
        {
            "type": "hard_constraints",
            "content": "Always include error handling in your code. Never use deprecated APIs. Ensure security best practices are followed.",
            "order": 2,
        },
        {
            "type": "soft_preferences",
            "content": "Try to write code that is idiomatic for $language. Prefer clarity over cleverness.",
            "order": 3,
        },
        {
            "type": "trust_contract",
            "content": "I will provide clear requirements, you will provide well-structured code solutions with explanations.",
            "order": 4,
        },
    ]
    
    layered_template = PromptTemplate(
        name="Code Assistant Template",
        template_type=PromptTemplateType.LAYERED,
        template_text=json.dumps(layered_template_content),
        description="A layered template for code assistance",
        variables=[
            TemplateVariable(
                name="language",
                description="The programming language",
                required=True,
                default_value="Python",
                example="Python",
            )
        ],
    )
    
    layered_template_id = prompt_manager.save_template(layered_template)
    logger.info(f"Created layered template with ID: {layered_template_id}")
    
    return simple_template_id, layered_template_id


def main():
    """Run the example."""
    # Initialize the database connection
    db = IndalekoCollection.get_db()
    
    # Initialize the prompt manager
    prompt_manager = PromptManager(db_instance=db)
    
    # Create example templates
    simple_id, layered_id = create_example_templates(prompt_manager)
    
    # Use the simple template
    variables = [
        PromptVariable(
            name="question",
            value="What is the most efficient sorting algorithm for nearly-sorted data?",
            required=True,
        )
    ]
    
    result = prompt_manager.create_prompt(
        template_id=simple_id,
        variables=variables,
        optimize=True,
        evaluate_stability=True,
    )
    
    logger.info("-" * 50)
    logger.info("Simple Template Result:")
    logger.info(f"Prompt: {result.prompt}")
    logger.info(f"Token count: {result.token_count}")
    logger.info(f"Original token count: {result.original_token_count}")
    logger.info(f"Token savings: {result.token_savings}")
    logger.info(f"Stability score: {result.stability_score}")
    
    # Use the layered template
    variables = [
        PromptVariable(
            name="language",
            value="JavaScript",
            required=True,
        )
    ]
    
    result = prompt_manager.create_prompt(
        template_id=layered_id,
        variables=variables,
        optimize=True,
        evaluate_stability=True,
    )
    
    logger.info("-" * 50)
    logger.info("Layered Template Result:")
    logger.info(f"Prompt:\n{result.prompt}")
    logger.info(f"Token count: {result.token_count}")
    logger.info(f"Original token count: {result.original_token_count}")
    logger.info(f"Token savings: {result.token_savings}")
    logger.info(f"Stability score: {result.stability_score}")
    
    # Get token savings statistics
    stats = prompt_manager.calculate_token_savings()
    
    logger.info("-" * 50)
    logger.info("Token Savings Statistics:")
    logger.info(f"Total prompts: {stats['total_prompts']}")
    logger.info(f"Total token savings: {stats['total_token_savings']}")
    logger.info(f"Average savings percentage: {stats['average_savings_percent']:.2f}%")
    logger.info(f"Average stability score: {stats['average_stability_score']:.2f}")


if __name__ == "__main__":
    main()