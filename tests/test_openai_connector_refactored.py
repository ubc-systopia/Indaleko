"""
Tests for refactored OpenAI connector.

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
from query.utils.llm_connector.openai_connector_refactored import OpenAIConnector
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian


class TestOpenAIConnectorRefactored(unittest.TestCase):
    """Test cases for the refactored OpenAI connector with prompt management integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the OpenAI client
        self.mock_openai_client = MagicMock()
        self.mock_openai_parse = MagicMock()
        self.mock_openai_client.beta.chat.completions.parse = self.mock_openai_parse

        # Mock the content response
        mock_content = {
            "query": "test query",
            "translated_query": "test translated query",
            "confidence": 0.9,
        }

        # Mock the completion response
        self.mock_completion = MagicMock()
        self.mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_content)))]

        # Set the return value for the mock parse method
        self.mock_openai_parse.return_value = self.mock_completion

        # Mock the Guardian
        self.mock_guardian = MagicMock(spec=LLMGuardian)
        self.mock_guardian_result = ("Test completion", {"status": "success"})
        self.mock_guardian.get_completion_from_prompt.return_value = self.mock_guardian_result
        self.mock_guardian.get_completion_from_template.return_value = self.mock_guardian_result

        # Create the connector with the mock OpenAI client
        with (
            patch("openai.OpenAI", return_value=self.mock_openai_client),
            patch("query.utils.prompt_management.guardian.llm_guardian.LLMGuardian", return_value=self.mock_guardian),
        ):
            self.connector_with_guardian = OpenAIConnector(
                api_key="test_api_key",
                model="gpt-4o",
                use_guardian=True,
                verification_level="STANDARD",
                request_mode="WARN",
            )

            self.connector_without_guardian = OpenAIConnector(
                api_key="test_api_key",
                model="gpt-4o",
                use_guardian=False,
            )

    def test_initialization_with_guardian(self):
        """Test initialization with LLMGuardian."""
        self.assertTrue(self.connector_with_guardian.use_guardian)
        self.assertIsNotNone(self.connector_with_guardian.guardian)
        self.assertEqual(self.connector_with_guardian.model, "gpt-4o")

    def test_initialization_without_guardian(self):
        """Test initialization without LLMGuardian."""
        self.assertFalse(self.connector_without_guardian.use_guardian)
        self.assertIsNone(self.connector_without_guardian.guardian)
        self.assertEqual(self.connector_without_guardian.model, "gpt-4o")

    def test_get_llm_name(self):
        """Test get_llm_name method."""
        self.assertEqual(self.connector_with_guardian.get_llm_name(), "OpenAI")
        self.assertEqual(self.connector_without_guardian.get_llm_name(), "OpenAI")

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

        # Call the method
        result = self.connector_without_guardian.generate_query(prompt)

        # Check that OpenAI client was called directly
        self.mock_openai_parse.assert_called_once()

        # Check the result structure (actual content is from the mock)
        self.assertTrue(hasattr(result, "query"))
        self.assertTrue(hasattr(result, "translated_query"))
        self.assertTrue(hasattr(result, "confidence"))

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

        # Check that OpenAI client was called directly
        self.mock_openai_parse.assert_called_once()

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
        # Set up the mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = "keyword1, keyword2, keyword3"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        self.mock_openai_client.chat.completions.create.return_value = mock_response

        # Call the method
        result = self.connector_without_guardian.extract_keywords("Test text for keyword extraction")

        # Check that OpenAI client was called directly
        self.mock_openai_client.chat.completions.create.assert_called_once()

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
        # Set up the mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = "Category B"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        self.mock_openai_client.chat.completions.create.return_value = mock_response

        # Call the method
        result = self.connector_without_guardian.classify_text(
            "Test text for classification",
            ["Category A", "Category B", "Category C"],
        )

        # Check that OpenAI client was called directly
        self.mock_openai_client.chat.completions.create.assert_called_once()

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

        # Set up the mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = {"answer": "This is the answer to your question."}
        mock_choice = MagicMock()
        mock_choice.message = mock_message

        self.mock_completion.choices[0].message.content = {"answer": "This is the answer to your question."}

        # Call the method
        result = self.connector_without_guardian.answer_question(
            "This is the context for the question.",
            "What is the question?",
            schema,
        )

        # Check that OpenAI client was called directly
        self.mock_openai_parse.assert_called_once()

        # The result is what the mock returns, which we just pass through
        self.assertEqual(result, {"answer": "This is the answer to your question."})

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
        # Set up the mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = "This is the generated text."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        self.mock_openai_client.chat.completions.create.return_value = mock_response

        # Call the method
        result = self.connector_without_guardian.generate_text("Generate some text.")

        # Check that OpenAI client was called directly
        self.mock_openai_client.chat.completions.create.assert_called_once()

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
        # Set up the mock OpenAI response
        mock_attributes = {
            "entities": ["entity1", "entity2"],
            "keywords": ["keyword1", "keyword2"],
            "sentiment": {"label": "positive", "score": 0.8},
            "topics": ["topic1", "topic2"],
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_attributes)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        self.mock_openai_client.chat.completions.create.return_value = mock_response

        # Call the method
        result = self.connector_without_guardian.extract_semantic_attributes(
            "Test text for semantic attribute extraction",
        )

        # Check that OpenAI client was called directly
        self.mock_openai_client.chat.completions.create.assert_called_once()

        # Check the result structure
        self.assertEqual(set(result.keys()), set(mock_attributes.keys()))


if __name__ == "__main__":
    unittest.main()
