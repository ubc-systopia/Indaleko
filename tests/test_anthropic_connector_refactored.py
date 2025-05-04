"""
Tests for refactored Anthropic connector.

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

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Make sure we can import from root directory
current_path = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
    current_path = os.path.dirname(current_path)
sys.path.append(current_path)
os.environ["INDALEKO_ROOT"] = current_path

# pylint: disable=wrong-import-position
from query.utils.llm_connector.anthropic_connector_refactored import AnthropicConnector
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian


class TestAnthropicConnectorRefactored(unittest.TestCase):
    """Test cases for the refactored Anthropic connector with prompt management integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the Anthropic client
        self.mock_anthropic_client = MagicMock()
        self.mock_message = MagicMock()

        # Mock the content response
        mock_text = MagicMock()
        mock_text.text = json.dumps(
            {
                "query": "test query",
                "translated_query": "test translated query",
                "confidence": 0.9,
            },
        )

        # Set up the mock message response
        self.mock_message.content = [mock_text]
        self.mock_anthropic_client.messages.create.return_value = self.mock_message

        # Mock the Guardian
        self.mock_guardian = MagicMock(spec=LLMGuardian)
        self.mock_guardian_result = ("Test completion", {"status": "success"})
        self.mock_guardian.get_completion_from_prompt.return_value = self.mock_guardian_result
        self.mock_guardian.get_completion_from_template.return_value = self.mock_guardian_result

        # Create the connector with the mock Anthropic client
        with (
            patch("anthropic.Anthropic", return_value=self.mock_anthropic_client),
            patch("query.utils.prompt_management.guardian.llm_guardian.LLMGuardian", return_value=self.mock_guardian),
        ):
            self.connector_with_guardian = AnthropicConnector(
                api_key="test_api_key",
                model="claude-3-sonnet-20240229",
                use_guardian=True,
                verification_level="STANDARD",
                request_mode="WARN",
            )

            self.connector_without_guardian = AnthropicConnector(
                api_key="test_api_key",
                model="claude-3-sonnet-20240229",
                use_guardian=False,
            )

    def test_initialization_with_guardian(self):
        """Test initialization with LLMGuardian."""
        self.assertTrue(self.connector_with_guardian.use_guardian)
        self.assertIsNotNone(self.connector_with_guardian.guardian)
        self.assertEqual(self.connector_with_guardian.model, "claude-3-sonnet-20240229")

    def test_initialization_without_guardian(self):
        """Test initialization without LLMGuardian."""
        self.assertFalse(self.connector_without_guardian.use_guardian)
        self.assertIsNone(self.connector_without_guardian.guardian)
        self.assertEqual(self.connector_without_guardian.model, "claude-3-sonnet-20240229")

    def test_get_llm_name(self):
        """Test get_llm_name method."""
        self.assertEqual(self.connector_with_guardian.get_llm_name(), "Claude")
        self.assertEqual(self.connector_without_guardian.get_llm_name(), "Claude")

    def test_extract_json_from_content(self):
        """Test _extract_json_from_content method."""
        # Test with valid JSON
        valid_json = '{"key": "value", "number": 42}'
        result = self.connector_with_guardian._extract_json_from_content(valid_json)
        self.assertEqual(result, {"key": "value", "number": 42})

        # Test with JSON embedded in text
        embedded_json = 'Some text before {"key": "value"} and some text after'
        result = self.connector_with_guardian._extract_json_from_content(embedded_json)
        self.assertEqual(result, {"key": "value"})

        # Test with invalid JSON
        invalid_json = "Not a JSON at all"
        result = self.connector_with_guardian._extract_json_from_content(invalid_json)
        self.assertTrue("error" in result)
        self.assertTrue("error_message" in result)

    def test_generate_query_with_guardian(self):
        """Test generate_query with LLMGuardian."""
        # Create a test prompt
        prompt = {
            "system": "You are a helpful assistant.",
            "user": "Translate this query: hello world",
        }

        # Mock the guardian's completion
        self.mock_guardian.get_completion_from_prompt.return_value = (
            json.dumps(
                {
                    "query": "hello world",
                    "translated_query": "SELECT * FROM world WHERE greeting = 'hello'",
                    "confidence": 0.95,
                },
            ),
            {"status": "success"},
        )

        # Call the method
        result = self.connector_with_guardian.generate_query(prompt)

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(result.query, "hello world")
        self.assertEqual(result.translated_query, "SELECT * FROM world WHERE greeting = 'hello'")
        self.assertEqual(result.confidence, 0.95)

    def test_generate_query_without_guardian(self):
        """Test generate_query without LLMGuardian."""
        # Create a test prompt
        prompt = {
            "system": "You are a helpful assistant.",
            "user": "Translate this query: hello world",
        }

        # Mock the Anthropic response
        mock_text = MagicMock()
        mock_text.text = json.dumps(
            {
                "query": "hello world",
                "translated_query": "SELECT * FROM world WHERE greeting = 'hello'",
                "confidence": 0.95,
            },
        )
        self.mock_message.content = [mock_text]

        # Call the method
        result = self.connector_without_guardian.generate_query(prompt)

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result
        self.assertEqual(result.query, "hello world")
        self.assertEqual(result.translated_query, "SELECT * FROM world WHERE greeting = 'hello'")
        self.assertEqual(result.confidence, 0.95)

    def test_summarize_text_with_guardian(self):
        """Test summarize_text with LLMGuardian."""
        # Call the method
        self.connector_with_guardian.summarize_text("This is a test text to summarize.")

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_summarize_text_without_guardian(self):
        """Test summarize_text without LLMGuardian."""
        # Call the method
        self.connector_without_guardian.summarize_text("This is a test text to summarize.")

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

    def test_extract_keywords_with_guardian(self):
        """Test extract_keywords with LLMGuardian."""
        # Set up the mock response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            "keyword1, keyword2, keyword3",
            {"status": "success"},
        )

        # Call the method
        result = self.connector_with_guardian.extract_keywords("Test text for keyword extraction")

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(result, ["keyword1", "keyword2", "keyword3"])

    def test_extract_keywords_without_guardian(self):
        """Test extract_keywords without LLMGuardian."""
        # Set up the mock response
        mock_text = MagicMock()
        mock_text.text = "keyword1, keyword2, keyword3"
        self.mock_message.content = [mock_text]

        # Call the method
        result = self.connector_without_guardian.extract_keywords("Test text for keyword extraction")

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result
        self.assertEqual(result, ["keyword1", "keyword2", "keyword3"])

    def test_classify_text_with_guardian(self):
        """Test classify_text with LLMGuardian."""
        # Set up the mock response
        self.mock_guardian.get_completion_from_prompt.return_value = ("Category A", {"status": "success"})

        # Call the method
        result = self.connector_with_guardian.classify_text(
            "Test text for classification",
            ["Category A", "Category B", "Category C"],
        )

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(result, "Category A")

    def test_classify_text_without_guardian(self):
        """Test classify_text without LLMGuardian."""
        # Set up the mock response
        mock_text = MagicMock()
        mock_text.text = "Category B"
        self.mock_message.content = [mock_text]

        # Call the method
        result = self.connector_without_guardian.classify_text(
            "Test text for classification",
            ["Category A", "Category B", "Category C"],
        )

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result
        self.assertEqual(result, "Category B")

    def test_answer_question_with_guardian(self):
        """Test answer_question with LLMGuardian."""
        # Set up the mock response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            json.dumps({"answer": "This is the answer to your question."}),
            {"status": "success"},
        )

        # Create a schema
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

        # Call the method
        result = self.connector_with_guardian.answer_question(
            "This is the context for the question.",
            "What is the question?",
            schema,
        )

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(result, {"answer": "This is the answer to your question."})

    def test_answer_question_without_guardian(self):
        """Test answer_question without LLMGuardian."""
        # Create a schema
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

        # Set up the mock response
        mock_text = MagicMock()
        mock_text.text = json.dumps({"answer": "This is the answer to your question."})
        self.mock_message.content = [mock_text]

        # Call the method
        result = self.connector_without_guardian.answer_question(
            "This is the context for the question.",
            "What is the question?",
            schema,
        )

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result
        self.assertEqual(result, {"answer": "This is the answer to your question."})

    def test_get_completion(self):
        """Test get_completion method."""
        # Test with guardian
        completion, metadata = self.connector_with_guardian.get_completion(
            system_prompt="You are a helpful assistant.",
            user_prompt="Tell me a joke.",
        )

        # Check that guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(completion, "Test completion")
        self.assertEqual(metadata["status"], "success")

        # Reset mock
        self.mock_guardian.get_completion_from_prompt.reset_mock()

        # Test without guardian
        # Set up the mock response
        mock_text = MagicMock()
        mock_text.text = "This is a joke about prompt management."
        self.mock_message.content = [mock_text]

        # Add mock usage
        self.mock_message.usage = MagicMock(input_tokens=20, output_tokens=10)

        # Call the method
        completion, metadata = self.connector_without_guardian.get_completion(
            system_prompt="You are a helpful assistant.",
            user_prompt="Tell me a joke.",
        )

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result
        self.assertEqual(completion, "This is a joke about prompt management.")
        self.assertEqual(metadata["provider"], "anthropic")
        self.assertEqual(metadata["tokens"]["prompt"], 20)
        self.assertEqual(metadata["tokens"]["completion"], 10)

    def test_generate_text_with_guardian(self):
        """Test generate_text with LLMGuardian."""
        # Set up the mock response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            "This is the generated text.",
            {"status": "success"},
        )

        # Call the method
        result = self.connector_with_guardian.generate_text("Generate some text.")

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(result, "This is the generated text.")

    def test_generate_text_without_guardian(self):
        """Test generate_text without LLMGuardian."""
        # Set up the mock response
        mock_text = MagicMock()
        mock_text.text = "This is the generated text."
        self.mock_message.content = [mock_text]

        # Call the method
        result = self.connector_without_guardian.generate_text("Generate some text.")

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result
        self.assertEqual(result, "This is the generated text.")

    def test_extract_semantic_attributes_with_guardian(self):
        """Test extract_semantic_attributes with LLMGuardian."""
        # Set up the mock response
        mock_attributes = {
            "entities": ["entity1", "entity2"],
            "keywords": ["keyword1", "keyword2"],
            "sentiment": {"label": "positive", "score": 0.8},
            "topics": ["topic1", "topic2"],
        }

        self.mock_guardian.get_completion_from_prompt.return_value = (
            json.dumps(mock_attributes),
            {"status": "success"},
        )

        # Call the method
        result = self.connector_with_guardian.extract_semantic_attributes("Test text for semantic attribute extraction")

        # Check that the guardian was called
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

        # Check the result
        self.assertEqual(result, mock_attributes)

    def test_extract_semantic_attributes_without_guardian(self):
        """Test extract_semantic_attributes without LLMGuardian."""
        # Set up the mock response
        mock_attributes = {
            "entities": ["entity1", "entity2"],
            "keywords": ["keyword1", "keyword2"],
            "sentiment": {"label": "positive", "score": 0.8},
            "topics": ["topic1", "topic2"],
        }

        mock_text = MagicMock()
        mock_text.text = json.dumps(mock_attributes)
        self.mock_message.content = [mock_text]

        # Call the method
        result = self.connector_without_guardian.extract_semantic_attributes(
            "Test text for semantic attribute extraction",
        )

        # Check that Anthropic client was called directly
        self.mock_anthropic_client.messages.create.assert_called_once()

        # Check the result structure
        self.assertEqual(set(result.keys()), set(mock_attributes.keys()))


if __name__ == "__main__":
    unittest.main()
