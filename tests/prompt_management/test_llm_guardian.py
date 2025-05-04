"""Tests for LLMGuardian class."""

import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock

from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian,
    PromptVariable,
    RequestMode,
    VerificationLevel,
)
from query.utils.prompt_management.guardian.prompt_guardian import VerificationResult


class TestLLMGuardian(unittest.TestCase):
    """Test cases for the LLMGuardian class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_prompt_manager = MagicMock()
        self.mock_prompt_guardian = MagicMock()

        # Mock the prompt evaluation result
        self.mock_evaluation_result = MagicMock()
        self.mock_evaluation_result.prompt = "This is a test prompt"
        self.mock_evaluation_result.token_count = 10
        self.mock_evaluation_result.is_optimized = True
        self.mock_prompt_manager.create_prompt.return_value = self.mock_evaluation_result

        # Mock the verification result
        self.mock_verification_result = MagicMock(spec=VerificationResult)
        self.mock_verification_result.passed = True
        self.mock_verification_result.warnings = []
        self.mock_verification_result.violations = []
        self.mock_verification_result.timestamp = datetime.now(UTC)
        self.mock_prompt_guardian.verify_prompt.return_value = self.mock_verification_result
        self.mock_prompt_guardian.process_prompt.return_value = "This is a test prompt"

        # Mock LLM connectors
        self.mock_openai_connector = MagicMock()
        self.mock_anthropic_connector = MagicMock()
        self.mock_gemma_connector = MagicMock()

        self.mock_openai_connector.get_completion.return_value = (
            "Test completion from OpenAI",
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        self.mock_anthropic_connector.get_completion.return_value = (
            "Test completion from Anthropic",
            {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
        )

        # Create instance with mocks
        self.guardian = LLMGuardian(
            db=self.mock_db,
            prompt_manager=self.mock_prompt_manager,
            prompt_guardian=self.mock_prompt_guardian,
            openai_connector=self.mock_openai_connector,
            anthropic_connector=self.mock_anthropic_connector,
            gemma_connector=self.mock_gemma_connector,
        )

    def test_initialization(self):
        """Test that LLMGuardian initializes correctly."""
        self.assertEqual(self.guardian.default_provider, "openai")
        self.assertEqual(self.guardian.verification_level, VerificationLevel.STANDARD)
        self.assertEqual(self.guardian.request_mode, RequestMode.WARN)

    def test_get_completion_from_template(self):
        """Test getting completion from a template."""
        variables = [PromptVariable(name="test", value="value")]

        completion, metadata = self.guardian.get_completion_from_template(
            template_id="test_template",
            variables=variables,
            provider="openai",
        )

        # Verify correct methods were called
        self.mock_prompt_manager.create_prompt.assert_called_once_with(
            template_id="test_template",
            variables=variables,
            optimize=True,
            evaluate_stability=True,
        )

        self.mock_prompt_guardian.verify_prompt.assert_called_once()
        self.mock_openai_connector.get_completion.assert_called_once()

        # Verify correct results
        self.assertEqual(completion, "Test completion from OpenAI")
        self.assertEqual(metadata["provider"], "openai")
        self.assertEqual(metadata["token_usage"]["prompt_tokens"], 10)
        self.assertEqual(metadata["token_usage"]["completion_tokens"], 5)
        self.assertEqual(metadata["token_usage"]["total_tokens"], 15)
        self.assertTrue(metadata["verification_passed"])

    def test_get_completion_raw(self):
        """Test getting completion from a raw prompt."""
        completion, metadata = self.guardian.get_completion_raw(prompt="Raw test prompt", provider="anthropic")

        # Verify correct methods were called
        self.mock_prompt_guardian.verify_prompt.assert_called_once_with(
            "Raw test prompt",
            level=VerificationLevel.STANDARD,
            user_id=None,
        )
        self.mock_anthropic_connector.get_completion.assert_called_once()

        # Verify correct results
        self.assertEqual(completion, "Test completion from Anthropic")
        self.assertEqual(metadata["provider"], "anthropic")
        self.assertEqual(metadata["token_usage"]["prompt_tokens"], 12)
        self.assertEqual(metadata["token_usage"]["completion_tokens"], 6)
        self.assertEqual(metadata["token_usage"]["total_tokens"], 18)

    def test_verification_failure(self):
        """Test behavior when prompt verification fails."""
        # Set verification to fail
        self.mock_verification_result.passed = False
        self.mock_verification_result.warnings = ["Suspicious content"]
        self.mock_prompt_guardian.process_prompt.return_value = None

        completion, metadata = self.guardian.get_completion_from_template(
            template_id="test_template",
            variables=[],
            provider="openai",
            mode=RequestMode.SAFE,
        )

        # Verify no completion was called
        self.mock_openai_connector.get_completion.assert_not_called()

        # Verify correct results
        self.assertIsNone(completion)
        self.assertFalse(metadata["verification_passed"])
        self.assertEqual(metadata["warnings"], ["Suspicious content"])

    def test_force_mode(self):
        """Test force mode bypasses verification failures."""
        # Set verification to fail but process_prompt to pass due to FORCE mode
        self.mock_verification_result.passed = False
        self.mock_verification_result.violations = ["Security violation"]

        # Despite failing verification, process_prompt returns prompt in FORCE mode
        self.mock_prompt_guardian.process_prompt.return_value = "This is a test prompt"

        completion, metadata = self.guardian.get_completion_from_template(
            template_id="test_template",
            variables=[],
            provider="openai",
            mode=RequestMode.FORCE,
        )

        # Verify completion was still called despite verification failure
        self.mock_openai_connector.get_completion.assert_called_once()

        # Verify correct results
        self.assertEqual(completion, "Test completion from OpenAI")
        self.assertFalse(metadata["verification_passed"])
        self.assertEqual(metadata["violations"], ["Security violation"])

    def test_provider_fallback(self):
        """Test fallback between providers."""
        # Make OpenAI connector fail
        self.mock_openai_connector.get_completion.side_effect = Exception("API Error")

        completion, metadata = self.guardian.get_completion_from_template(
            template_id="test_template",
            variables=[],
            provider="openai",
            fallback=True,
        )

        # Verify both connectors were called (OpenAI failed, fell back to Anthropic)
        self.mock_openai_connector.get_completion.assert_called_once()
        self.mock_anthropic_connector.get_completion.assert_called_once()

        # Verify correct results from fallback provider
        self.assertEqual(completion, "Test completion from Anthropic")
        self.assertEqual(metadata["provider"], "anthropic")
        self.assertEqual(metadata["original_provider"], "openai")
        self.assertTrue(metadata["used_fallback"])

    def test_token_usage_tracking(self):
        """Test token usage is tracked correctly."""
        # Call a few completions to generate usage data
        self.guardian.get_completion_raw("Test 1", provider="openai")
        self.guardian.get_completion_raw("Test 2", provider="anthropic")
        self.guardian.get_completion_raw("Test 3", provider="openai")

        # Verify token usage is logged to the database
        self.assertEqual(self.mock_db.insert_document.call_count, 3)

        # Test get_token_usage method
        # Mock the database response for token usage query
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = [
            {"provider": "openai", "model": "gpt-4", "prompt_tokens": 20, "completion_tokens": 10},
            {"provider": "anthropic", "model": "claude-3", "prompt_tokens": 12, "completion_tokens": 6},
        ]
        self.mock_db.aql.execute.return_value = mock_cursor

        usage = self.guardian.get_token_usage(
            provider="all",
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC),
        )

        # Verify correct aggregated usage
        self.assertEqual(usage.total_prompt_tokens, 32)
        self.assertEqual(usage.total_completion_tokens, 16)
        self.assertEqual(usage.total_tokens, 48)
        self.assertEqual(len(usage.by_provider), 2)

    def test_custom_model_parameters(self):
        """Test passing custom model parameters."""
        model_params = {"temperature": 0.7, "max_tokens": 500, "top_p": 0.9}

        self.guardian.get_completion_raw(prompt="Test with params", provider="openai", model_params=model_params)

        # Verify parameters were passed correctly
        call_args = self.mock_openai_connector.get_completion.call_args[1]
        for param, value in model_params.items():
            self.assertEqual(call_args[param], value)


if __name__ == "__main__":
    unittest.main()
