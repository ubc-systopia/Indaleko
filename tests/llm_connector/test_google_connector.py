"""
Tests for the Google connector with prompt management integration.

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
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the root directory to sys.path
current_path = Path(__file__).parent.resolve()
while not (Path(current_path) / "Indaleko.py").exists():
    current_path = Path(current_path).parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

# Now we can import the modules we need
from query.utils.llm_connector.google_connector import GoogleConnector


class TestGoogleConnector(unittest.TestCase):
    """
    Tests for the GoogleConnector class with prompt management integration.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Mock genai.Client
        self.mock_genai_patcher = patch("query.utils.llm_connector.google_connector.genai")
        self.mock_genai = self.mock_genai_patcher.start()
        self.mock_client = MagicMock()
        self.mock_genai.Client.return_value = self.mock_client

        # Mock types
        self.mock_types_patcher = patch("query.utils.llm_connector.google_connector.types")
        self.mock_types = self.mock_types_patcher.start()

        # Mock LLMGuardian
        self.mock_guardian_patcher = patch("query.utils.llm_connector.google_connector.LLMGuardian")
        self.mock_guardian_class = self.mock_guardian_patcher.start()
        self.mock_guardian = MagicMock()
        self.mock_guardian_class.return_value = self.mock_guardian

        # Create a test instance without guardian first
        self.google = GoogleConnector(
            model="gemini-2.0-flash",
            api_key="test-api-key",
            use_guardian=False,
        )

        # Then create one with guardian
        self.google_with_guardian = GoogleConnector(
            model="gemini-2.0-flash",
            api_key="test-api-key",
            use_guardian=True,
            verification_level="STANDARD",
            request_mode="WARN",
        )

        # Mock response for Google GenAI API calls
        self.mock_response = MagicMock()
        self.mock_response.text = '{"test": "response"}'
        self.mock_client.models.generate_content.return_value = self.mock_response

    def tearDown(self):
        """Tear down test fixtures."""
        self.mock_genai_patcher.stop()
        self.mock_types_patcher.stop()
        self.mock_guardian_patcher.stop()

    def test_init_without_guardian(self):
        """Test initialization without LLMGuardian."""
        self.assertEqual(self.google.model, "gemini-2.0-flash")
        self.assertEqual(self.google.api_key, "test-api-key")
        self.assertFalse(self.google.use_guardian)
        self.assertIsNone(self.google.guardian)

    def test_init_with_guardian(self):
        """Test initialization with LLMGuardian."""
        self.assertEqual(self.google_with_guardian.model, "gemini-2.0-flash")
        self.assertTrue(self.google_with_guardian.use_guardian)
        self.assertEqual(self.google_with_guardian.guardian, self.mock_guardian)
        self.mock_guardian_class.assert_called_once()

    def test_get_llm_name(self):
        """Test get_llm_name method."""
        self.assertEqual(self.google.get_llm_name(), "Gemini")

    def test_count_tokens(self):
        """Test token counting method."""
        # Since we may not have tiktoken, test the fallback method
        self.google.tokenizer = None
        count = self.google._count_tokens("This is a test sentence with more than 4 characters.")
        self.assertEqual(count, 14)  # 56 chars / 4 = 14 tokens (approx)

    def test_extract_json_from_content(self):
        """Test extracting JSON from response content."""
        # Test valid JSON
        valid_json = '{"key": "value", "number": 42}'
        result = self.google._extract_json_from_content(valid_json)
        self.assertEqual(result, {"key": "value", "number": 42})

        # Test invalid JSON
        invalid_json = "This is not JSON"
        result = self.google._extract_json_from_content(invalid_json)
        self.assertTrue(result["error"])
        self.assertIn("No valid JSON found", result["error_message"])

    def test_generate_query_without_guardian(self):
        """Test generate_query method without guardian."""
        # Setup test prompt
        prompt = {
            "system": "You are a helpful assistant.",
            "user": "Translate 'find my documents' to AQL",
        }

        # Set up mock response
        self.mock_response.text = '{"query": "find my documents", "translated_query": "FOR doc IN documents RETURN doc", "explanation": "Test", "error": false}'

        # Call method
        result = self.google.generate_query(prompt)

        # Verify result
        self.assertFalse(result.error)
        self.assertEqual(result.query, "find my documents")
        self.assertEqual(result.translated_query, "FOR doc IN documents RETURN doc")

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_generate_query_with_guardian(self):
        """Test generate_query method with guardian."""
        # Setup test prompt
        prompt = {
            "system": "You are a helpful assistant.",
            "user": "Translate 'find my documents' to AQL",
        }

        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            '{"query": "find my documents", "translated_query": "FOR doc IN documents RETURN doc", "explanation": "Guardian Test", "error": false}',
            {"verification": {"allowed": True}},
        )

        # Call method
        result = self.google_with_guardian.generate_query(prompt)

        # Verify result
        self.assertFalse(result.error)
        self.assertEqual(result.query, "find my documents")
        self.assertEqual(result.translated_query, "FOR doc IN documents RETURN doc")
        self.assertEqual(result.explanation, "Guardian Test")

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_generate_query_guardian_blocked(self):
        """Test generate_query when guardian blocks the request."""
        # Setup test prompt
        prompt = {
            "system": "You are a helpful assistant.",
            "user": "Translate 'find my documents' to AQL",
        }

        # Mock guardian blocking response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            None,
            {"block_reason": "Security violation detected", "verification": {"allowed": False}},
        )

        # Call method
        result = self.google_with_guardian.generate_query(prompt)

        # Verify result shows blocked status
        self.assertTrue(result.error)
        self.assertEqual(result.error_message, "Security violation detected")
        self.assertIn("blocked by LLMGuardian", result.explanation)

    def test_get_completion_without_guardian(self):
        """Test get_completion method without guardian."""
        # Set up mock response
        self.mock_response.text = "This is a test response."

        # Call method
        completion, metadata = self.google.get_completion(
            system_prompt="You are a helpful assistant.",
            user_prompt="Tell me about Indaleko.",
        )

        # Verify result
        self.assertEqual(completion, "This is a test response.")
        self.assertEqual(metadata["provider"], "google")
        self.assertEqual(metadata["model"], "gemini-2.0-flash")
        self.assertFalse(metadata.get("guardian_used", False))

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_get_completion_with_guardian(self):
        """Test get_completion method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            "This is a guardian response.",
            {
                "verification": {"allowed": True},
                "token_metrics": {"token_count": 10, "token_savings": 5},
                "total_time_ms": 120,
            },
        )

        # Call method
        completion, metadata = self.google_with_guardian.get_completion(
            system_prompt="You are a helpful assistant.",
            user_prompt="Tell me about Indaleko.",
        )

        # Verify result
        self.assertEqual(completion, "This is a guardian response.")
        self.assertEqual(metadata["provider"], "google")
        self.assertEqual(metadata["model"], "gemini-2.0-flash")
        self.assertTrue(metadata["guardian_used"])
        self.assertEqual(metadata["token_metrics"]["token_count"], 10)

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_summarize_text_without_guardian(self):
        """Test summarize_text method without guardian."""
        # Set up mock response
        self.mock_response.text = "This is a summary."

        # Call method
        result = self.google.summarize_text("This is a long text that needs to be summarized.")

        # Verify result
        self.assertEqual(result, "This is a summary.")

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_summarize_text_with_guardian(self):
        """Test summarize_text method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            "This is a guardian summary.",
            {"verification": {"allowed": True}},
        )

        # Call method
        result = self.google_with_guardian.summarize_text("This is a long text that needs to be summarized.")

        # Verify result
        self.assertEqual(result, "This is a guardian summary.")

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_extract_keywords_without_guardian(self):
        """Test extract_keywords method without guardian."""
        # Set up mock response
        self.mock_response.text = "keyword1, keyword2, keyword3"

        # Call method
        result = self.google.extract_keywords("This is text containing keywords.")

        # Verify result
        self.assertEqual(result, ["keyword1", "keyword2", "keyword3"])

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_extract_keywords_with_guardian(self):
        """Test extract_keywords method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            "guardian_keyword1, guardian_keyword2, guardian_keyword3",
            {"verification": {"allowed": True}},
        )

        # Call method
        result = self.google_with_guardian.extract_keywords("This is text containing keywords.")

        # Verify result
        self.assertEqual(result, ["guardian_keyword1", "guardian_keyword2", "guardian_keyword3"])

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_classify_text_without_guardian(self):
        """Test classify_text method without guardian."""
        # Set up mock response
        self.mock_response.text = "Technology"

        # Call method
        result = self.google.classify_text("This is about AI.", ["Technology", "Science", "Art"])

        # Verify result
        self.assertEqual(result, "Technology")

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_classify_text_with_guardian(self):
        """Test classify_text method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = ("Science", {"verification": {"allowed": True}})

        # Call method
        result = self.google_with_guardian.classify_text("This is about AI.", ["Technology", "Science", "Art"])

        # Verify result
        self.assertEqual(result, "Science")

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_answer_question_without_guardian(self):
        """Test answer_question method without guardian."""
        # Set up mock response
        self.mock_response.text = '{"answer": "Test answer", "confidence": 0.9}'

        # Call method
        result = self.google.answer_question(
            context="This is context.",
            question="What is this about?",
            schema={"type": "object", "properties": {"answer": {"type": "string"}, "confidence": {"type": "number"}}},
        )

        # Verify result
        self.assertEqual(result["answer"], "Test answer")
        self.assertEqual(result["confidence"], 0.9)

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_answer_question_with_guardian(self):
        """Test answer_question method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            '{"answer": "Guardian answer", "confidence": 0.95}',
            {"verification": {"allowed": True}},
        )

        # Call method
        result = self.google_with_guardian.answer_question(
            context="This is context.",
            question="What is this about?",
            schema={"type": "object", "properties": {"answer": {"type": "string"}, "confidence": {"type": "number"}}},
        )

        # Verify result
        self.assertEqual(result["answer"], "Guardian answer")
        self.assertEqual(result["confidence"], 0.95)

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_generate_text_without_guardian(self):
        """Test generate_text method without guardian."""
        # Set up mock response
        self.mock_response.text = "Generated text response."

        # Call method
        result = self.google.generate_text("Generate some text about AI.")

        # Verify result
        self.assertEqual(result, "Generated text response.")

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_generate_text_with_guardian(self):
        """Test generate_text method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            "Guardian generated text about AI.",
            {"verification": {"allowed": True}},
        )

        # Call method
        result = self.google_with_guardian.generate_text("Generate some text about AI.")

        # Verify result
        self.assertEqual(result, "Guardian generated text about AI.")

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()

    def test_extract_semantic_attributes_without_guardian(self):
        """Test extract_semantic_attributes method without guardian."""
        # Set up mock response
        self.mock_response.text = '{"entities": ["Google", "AI"], "keywords": ["system", "database"]}'

        # Call method
        result = self.google.extract_semantic_attributes("This is text about Google's AI.")

        # Verify result
        self.assertEqual(result["entities"], ["Google", "AI"])
        self.assertEqual(result["keywords"], ["system", "database"])

        # Verify API was called correctly
        self.mock_client.models.generate_content.assert_called_once()

    def test_extract_semantic_attributes_with_guardian(self):
        """Test extract_semantic_attributes method with guardian."""
        # Mock guardian response
        self.mock_guardian.get_completion_from_prompt.return_value = (
            '{"entities": ["Guardian", "Google"], "keywords": ["security", "verification"]}',
            {"verification": {"allowed": True}},
        )

        # Call method
        result = self.google_with_guardian.extract_semantic_attributes("This is text about Google's AI.")

        # Verify result
        self.assertEqual(result["entities"], ["Guardian", "Google"])
        self.assertEqual(result["keywords"], ["security", "verification"])

        # Verify guardian was called correctly
        self.mock_guardian.get_completion_from_prompt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
