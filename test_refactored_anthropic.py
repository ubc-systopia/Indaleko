#!/usr/bin/env python
"""
Test script for the refactored Anthropic connector with prompt management integration.

This script runs a simple test to verify that the refactored Anthropic connector works
correctly with the prompt management system.

Usage:
    python test_refactored_anthropic.py
"""

import logging
import os
import sys

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()

# Make sure we can import from root directory
current_path = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
    current_path = os.path.dirname(current_path)
if current_path not in sys.path:
    sys.path.append(current_path)
os.environ["INDALEKO_ROOT"] = current_path

# Import the required modules
try:
    from query.utils.llm_connector.anthropic_connector_refactored import (
        AnthropicConnector,
    )
    from query.utils.llm_connector.factory_updated import LLMFactory
    from query.utils.prompt_management.guardian.llm_guardian import (
        RequestMode,
        VerificationLevel,
    )
    from query.utils.prompt_management.prompt_manager import PromptVariable
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


def load_api_key() -> str | None:
    """
    Load the Anthropic API key from the config file.

    Returns:
        Optional[str]: The API key or None if not found
    """
    # Try to load from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key

    # Try to load from config file
    config_dir = os.path.join(current_path, "config")
    key_path = os.path.join(config_dir, "llm-keys.ini")

    if not os.path.exists(key_path):
        logger.error(f"Config file not found: {key_path}")
        return None

    # Parse the config file
    import configparser

    config = configparser.ConfigParser()

    try:
        config.read(key_path)

        # Check if Anthropic section exists
        if "anthropic" in config and "api_key" in config["anthropic"]:
            api_key = config["anthropic"]["api_key"]

            # Clean up quotes if present
            if api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
                api_key = api_key[1:-1]

            return api_key

        logger.error("No Anthropic API key found in config file")
        return None
    except Exception as e:
        logger.error(f"Failed to load API key: {e}")
        return None


def test_direct_connector():
    """Test the refactored Anthropic connector directly."""
    logger.info("Testing refactored Anthropic connector directly")

    # Load API key
    api_key = load_api_key()
    if not api_key:
        logger.error("Failed to load Anthropic API key")
        return False

    # Create connector with LLMGuardian
    logger.info("Creating connector with LLMGuardian")
    connector_with_guardian = AnthropicConnector(
        api_key=api_key,
        model="claude-3-sonnet-20240229",
        use_guardian=True,
        verification_level="STANDARD",
        request_mode="WARN",
    )

    # Create connector without LLMGuardian
    logger.info("Creating connector without LLMGuardian")
    connector_without_guardian = AnthropicConnector(
        api_key=api_key,
        model="claude-3-sonnet-20240229",
        use_guardian=False,
    )

    # Test generating text with guardian
    logger.info("Testing text generation with LLMGuardian")
    try:
        with_guardian_result = connector_with_guardian.generate_text(
            prompt="Write a haiku about prompt management systems.",
            max_tokens=100,
            temperature=0.7,
        )
        logger.info(f"With guardian result: {with_guardian_result}")
    except Exception as e:
        logger.error(f"Failed to generate text with guardian: {e}")
        return False

    # Test generating text without guardian
    logger.info("Testing text generation without LLMGuardian")
    try:
        without_guardian_result = connector_without_guardian.generate_text(
            prompt="Write a haiku about prompt management systems.",
            max_tokens=100,
            temperature=0.7,
        )
        logger.info(f"Without guardian result: {without_guardian_result}")
    except Exception as e:
        logger.error(f"Failed to generate text without guardian: {e}")
        return False

    return True


def test_factory_integration():
    """Test the LLMFactory integration with the refactored connector."""
    logger.info("Testing LLMFactory integration")

    # Load API key
    api_key = load_api_key()
    if not api_key:
        logger.error("Failed to load Anthropic API key")
        return False

    # Create LLM interface for Anthropic
    logger.info("Creating LLM interface for Anthropic with guardian")
    try:
        llm_with_guardian = LLMFactory.get_llm(
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            use_guardian=True,
            verification_level="STANDARD",
            request_mode="WARN",
        )
    except Exception as e:
        logger.error(f"Failed to create LLM interface with guardian: {e}")
        return False

    # Create LLM interface for Anthropic without guardian
    logger.info("Creating LLM interface for Anthropic without guardian")
    try:
        llm_without_guardian = LLMFactory.get_llm(
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            use_guardian=False,
        )
    except Exception as e:
        logger.error(f"Failed to create LLM interface without guardian: {e}")
        return False

    # Test completion with guardian
    logger.info("Testing completion with LLMGuardian")
    try:
        with_guardian_result, metadata = llm_with_guardian.get_completion(
            user_prompt="What are the benefits of prompt management systems?",
            temperature=0.7,
        )
        logger.info(f"With guardian result: {with_guardian_result}")
        logger.info(f"With guardian metadata: {metadata}")
    except Exception as e:
        logger.error(f"Failed to get completion with guardian: {e}")
        return False

    # Test completion without guardian
    logger.info("Testing completion without LLMGuardian")
    try:
        without_guardian_result, metadata = llm_without_guardian.get_completion(
            user_prompt="What are the benefits of prompt management systems?",
            temperature=0.7,
        )
        logger.info(f"Without guardian result: {without_guardian_result}")
        logger.info(f"Without guardian metadata: {metadata}")
    except Exception as e:
        logger.error(f"Failed to get completion without guardian: {e}")
        return False

    return True


def main() -> int:
    """Run the test script."""
    logger.info("Starting refactored Anthropic connector test")

    success = True

    # Test direct connector
    if not test_direct_connector():
        logger.error("Direct connector test failed")
        success = False

    # Test factory integration
    if not test_factory_integration():
        logger.error("Factory integration test failed")
        success = False

    if success:
        logger.info("All tests passed!")
        return 0
    else:
        logger.error("One or more tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
