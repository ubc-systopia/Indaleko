"""
Tests for the PromptManager class.

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
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from query.utils.prompt_management.data_models.base import PromptTemplate, PromptTemplateType
from query.utils.prompt_management.prompt_manager import (
    PromptManager, PromptVariable, PromptEvaluationResult
)


class TestPromptManager(unittest.TestCase):
    """Tests for the PromptManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the database and AyniGuard
        self.mock_db = MagicMock()
        self.mock_ayni_guard = MagicMock()
        self.mock_schema_manager = MagicMock()
        
        # Set up the prompt manager with mocks
        self.prompt_manager = PromptManager(
            db_instance=self.mock_db,
            ayni_guard=self.mock_ayni_guard,
            schema_manager=self.mock_schema_manager,
        )
        
        # Set up a simple token estimator for testing
        self.prompt_manager._token_estimator = lambda text: len(text.split())

    def test_normalize_whitespace(self):
        """Test the _normalize_whitespace method."""
        # Input with various whitespace issues
        input_text = """
        This is a test     with lots of   spaces
        
        
        And multiple newlines   
            And indentation
        """
        
        expected = "This is a test with lots of spaces\n\nAnd multiple newlines\nAnd indentation"
        
        result = self.prompt_manager._normalize_whitespace(input_text)
        self.assertEqual(result, expected)

    def test_bind_variables(self):
        """Test the _bind_variables method."""
        # Template with variables
        template = "Hello, $name! Your favorite color is $color."
        
        # Variables to bind
        variables = [
            PromptVariable(name="name", value="Alice", required=True),
            PromptVariable(name="color", value="blue", required=True),
        ]
        
        expected = "Hello, Alice! Your favorite color is blue."
        
        result = self.prompt_manager._bind_variables(template, variables)
        self.assertEqual(result, expected)

    def test_bind_variables_missing_required(self):
        """Test the _bind_variables method with missing required variables."""
        # Template with variables
        template = "Hello, $name! Your favorite color is $color."
        
        # Variables to bind - missing color
        variables = [
            PromptVariable(name="name", value="Alice", required=True),
        ]
        
        # Missing required variable should raise ValueError
        with self.assertRaises(ValueError):
            self.prompt_manager._bind_variables(template, variables)

    def test_create_prompt_simple(self):
        """Test creating a prompt from a simple template."""
        # Mock get_template to return a simple template
        template = PromptTemplate(
            name="Test Template",
            template_type=PromptTemplateType.SIMPLE,
            template_text="Hello, $name! Your task is to $task.",
            description="A test template",
        )
        self.prompt_manager.get_template = MagicMock(return_value=template)
        
        # Mock AyniGuard evaluate to return a mock result
        self.mock_ayni_guard.evaluate.return_value = MagicMock(
            composite_score=0.95,
            details={"test": "details"},
        )
        self.mock_ayni_guard.compute_prompt_hash.return_value = "test_hash"
        
        # Variables to bind
        variables = [
            PromptVariable(name="name", value="Alice", required=True),
            PromptVariable(name="task", value="solve this problem", required=True),
        ]
        
        # Create the prompt
        result = self.prompt_manager.create_prompt(
            template_id="test_template",
            variables=variables,
            optimize=True,
            evaluate_stability=True,
        )
        
        # Assertions
        self.assertEqual(result.prompt, "Hello, Alice! Your task is to solve this problem.")
        self.assertEqual(result.token_count, 9)  # Based on our simple word-based estimator
        self.assertGreater(result.original_token_count, 0)
        self.assertEqual(result.stability_score, 0.95)
        self.assertEqual(result.prompt_hash, "test_hash")

    def test_create_prompt_layered(self):
        """Test creating a prompt from a layered template."""
        # Mock get_template to return a layered template
        layered_template_text = json.dumps([
            {
                "type": "immutable_context",
                "content": "You are an AI assistant. You help with $task.",
                "order": 1,
            },
            {
                "type": "hard_constraints",
                "content": "Always be polite. Never use offensive language.",
                "order": 2,
            },
            {
                "type": "soft_preferences",
                "content": "Try to keep responses under $max_words words.",
                "order": 3,
            },
            {
                "type": "trust_contract",
                "content": "I will provide clear instructions, you will provide helpful responses.",
                "order": 4,
            },
        ])
        
        template = PromptTemplate(
            name="Layered Test Template",
            template_type=PromptTemplateType.LAYERED,
            template_text=layered_template_text,
            description="A test layered template",
        )
        self.prompt_manager.get_template = MagicMock(return_value=template)
        
        # Mock AyniGuard evaluate to return a mock result
        self.mock_ayni_guard.evaluate.return_value = MagicMock(
            composite_score=0.95,
            details={"test": "details"},
        )
        self.mock_ayni_guard.compute_prompt_hash.return_value = "test_hash"
        
        # Variables to bind
        variables = [
            PromptVariable(name="task", value="coding", required=True),
            PromptVariable(name="max_words", value="100", required=True),
        ]
        
        # Create the prompt
        result = self.prompt_manager.create_prompt(
            template_id="layered_template",
            variables=variables,
            optimize=True,
            evaluate_stability=True,
        )
        
        # Expected output
        expected = (
            "# Context\n"
            "You are an AI assistant. You help with coding.\n\n"
            "# Requirements\n"
            "Always be polite. Never use offensive language.\n\n"
            "# Preferences\n"
            "Try to keep responses under 100 words.\n\n"
            "# Agreement\n"
            "I will provide clear instructions, you will provide helpful responses."
        )
        
        # Assertions
        self.assertEqual(result.prompt, expected)
        # Our simple estimator counts words
        expected_token_count = len(expected.split())
        self.assertEqual(result.token_count, expected_token_count)
        self.assertEqual(result.stability_score, 0.95)
        self.assertEqual(result.prompt_hash, "test_hash")

    def test_calculate_token_savings(self):
        """Test calculating token savings statistics."""
        # Mock get_metrics to return some test metrics
        self.prompt_manager.get_metrics = MagicMock(return_value=[
            {
                "token_savings": 10,
                "original_token_count": 100,
                "token_count": 90,
                "stability_score": 0.95,
            },
            {
                "token_savings": 20,
                "original_token_count": 200,
                "token_count": 180,
                "stability_score": 0.90,
            },
        ])
        
        # Calculate token savings
        result = self.prompt_manager.calculate_token_savings()
        
        # Assertions
        self.assertEqual(result["total_prompts"], 2)
        self.assertEqual(result["total_token_savings"], 30)
        self.assertEqual(result["total_tokens_before"], 300)
        self.assertEqual(result["total_tokens_after"], 270)
        self.assertEqual(result["average_savings_percent"], 10.0)  # (30/300) * 100
        self.assertEqual(result["average_stability_score"], 0.925)  # (0.95 + 0.90) / 2


if __name__ == "__main__":
    unittest.main()