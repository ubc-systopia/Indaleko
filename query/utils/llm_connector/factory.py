"""
LLM Connector Factory for the Indaleko system.

This module provides a factory for creating various LLM connectors.

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

import configparser
import os
import random
import sys
from pathlib import Path

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.utils.llm_connector.gemma_connector import GemmaConnector
from query.utils.llm_connector.llm_base import IndalekoLLMBase
from query.utils.llm_connector.openai_connector import OpenAIConnector

# pylint: enable=wrong-import-position


class LLMConnectorFactory:
    """Factory for creating LLM connectors."""

    # Dictionary of registered connector types
    _registered_connectors = {
        "openai": OpenAIConnector,
        "gemma": GemmaConnector,
        # Register OpenAI-compatible providers
        "deepseek": OpenAIConnector,  # Uses OpenAI-compatible API
        "grok": OpenAIConnector,  # Uses OpenAI-compatible API
    }

    @classmethod
    def register_connector(cls, name: str, connector_class: type) -> None:
        """
        Register a new connector type.

        Args:
            name (str): The name of the connector
            connector_class (type): The connector class
        """
        cls._registered_connectors[name.lower()] = connector_class

    @classmethod
    def get_available_connectors(cls) -> list[str]:
        """
        Get list of available connector types.

        Returns:
            list[str]: Names of available connector types
        """
        # First make sure we've loaded any connectors from config
        try:
            cls._load_connector_config()
        except Exception as e:
            ic(f"Error loading connector config: {e}")

        return list(cls._registered_connectors.keys())

    @classmethod
    def create_connector(
        cls,
        connector_type: str = None,
        config_path: str = None,
        api_key: str = None,
        **kwargs,
    ) -> IndalekoLLMBase:
        """
        Create a connector instance based on type.

        Args:
            connector_type (str, optional): The type of connector to create.
                If None, will be loaded from config.
            config_path (str, optional): Path to config file.
                If None, will use default paths.
            api_key (str, optional): API key to use. If provided, overrides
                any key from the config file.
            **kwargs: Additional arguments to pass to the connector constructor.

        Returns:
            IndalekoLLMBase: The created connector instance.

        Raises:
            ValueError: If the connector type is not registered.
        """
        # If connector_type is not provided, load from config
        if connector_type is None:
            connector_type, config = cls._load_connector_config(config_path)
            kwargs.update(config)
        else:
            # If connector_type is provided but not config, still load config
            # for that specific provider
            _, config = cls._load_connector_config(config_path)
            # If the connector has config, use it
            if connector_type.lower() in config:
                kwargs.update(config[connector_type.lower()])

        # Convert to lowercase for case-insensitive lookup
        connector_type = connector_type.lower()

        # Special case for "random" - randomly select a connector
        if connector_type == "random":
            connector_type = random.choice(cls.get_available_connectors())  # noqa: S311
            ic(f"Randomly selected connector: {connector_type}")

        # Check if the connector type is registered
        if connector_type not in cls._registered_connectors:
            raise ValueError(
                f"Connector type '{connector_type}' not registered. "
                f"Available types: {', '.join(cls._registered_connectors.keys())}",
            )

        # Handle API key
        if api_key is not None:
            # Explicitly provided API key takes precedence
            kwargs["api_key"] = api_key
        elif "api_key" not in kwargs and connector_type != "gemma":  # Gemma doesn't need an API key
            try:
                # Try loading from config if needed
                keys_config_path = Path(os.environ.get("INDALEKO_ROOT")) / "config" / "llm-keys.ini"
                if os.path.exists(keys_config_path):
                    keys_config = configparser.ConfigParser()
                    keys_config.read(keys_config_path, encoding="utf-8-sig")
                    if connector_type in keys_config and "api_key" in keys_config[connector_type]:
                        api_key = keys_config[connector_type]["api_key"]
                        # Clean up quotes if present
                        if api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
                            api_key = api_key[1:-1]
                        kwargs["api_key"] = api_key
                        ic(f"Loaded API key for {connector_type} from llm-keys.ini")
                elif connector_type == "openai":
                    api_key = cls._load_openai_api_key()
                    kwargs["api_key"] = api_key
                    ic("Loaded OpenAI API key from legacy openai-key.ini")
            except Exception as e:
                ic(f"Error loading API key for {connector_type}: {e}")
                if connector_type != "gemma":  # Gemma doesn't require API key
                    ic(f"Warning: No API key provided for {connector_type}")

        # Create the connector instance
        connector_class = cls._registered_connectors[connector_type]

        return connector_class(**kwargs)

    @classmethod
    def _load_connector_config(
        cls,
        config_path: str | None = None,
    ) -> tuple[str, dict]:
        """
        Load connector configuration from a file.

        Args:
            config_path (Optional[str]): Path to the config file.
                If None, will use default paths.

        Returns:
            tuple[str, dict]: The connector type and configuration.
        """
        # Default config paths
        if config_path is None:
            config_dir = Path(os.environ.get("INDALEKO_ROOT")) / "config"
            keys_path = config_dir / "llm-keys.ini"
            if os.path.exists(keys_path):
                config_path = keys_path
            else:
                # Fall back to legacy config file
                config_path = config_dir / "llm-config.ini"

        # Create default config if not exists
        if not os.path.exists(config_path):
            cls._create_default_config(config_path)

        # Load config
        config = configparser.ConfigParser()
        config.read(config_path, encoding="utf-8-sig")

        # Get connector type
        connector_type = config.get("llm", "default_provider", fallback="openai")

        # Dynamically discover available providers from config sections
        # Filter out the 'llm' section which is for general settings
        config_providers = [section for section in config.sections() if section.lower() != "llm"]

        # Update enabled providers based on config
        if "llm" in config and "enabled_providers" in config["llm"]:
            # If enabled_providers is specified, filter the providers list
            enabled_providers_str = config.get("llm", "enabled_providers")
            enabled_providers = [p.strip() for p in enabled_providers_str.split(",")]
            config_providers = [p for p in config_providers if p.lower() in [ep.lower() for ep in enabled_providers]]

        ic(f"Providers found in config: {config_providers}")

        # Register any implemented providers that are in the config
        for provider in config_providers:
            provider_lower = provider.lower()
            # Check if we have an implementation for this provider
            if provider_lower in cls._registered_connectors:
                ic(f"Provider {provider} is implemented and configured")
            else:
                # Check for dynamically loadable connectors (for custom additions)
                try:
                    # Try to dynamically import the connector class
                    module_name = f"query.utils.llm_connector.{provider_lower}_connector"
                    class_name = f"{provider.capitalize()}Connector"

                    # Try to import the module
                    import importlib

                    try:
                        module = importlib.import_module(module_name)
                        connector_class = getattr(module, class_name)
                        # Register the connector
                        cls._registered_connectors[provider_lower] = connector_class
                        ic(f"Dynamically registered LLM provider: {provider}")
                    except (ImportError, AttributeError) as e:
                        ic(f"Provider {provider} is configured but not implemented: {e}")
                except Exception as e:
                    ic(f"Error loading provider {provider}: {e}")

        # Get connector-specific config
        connector_config = {}
        if connector_type in config:
            connector_config = dict(config[connector_type])

            # Special handling for API key
            if "api_key" in connector_config:
                # Check if API key is empty - try environment variable
                api_key = connector_config["api_key"]

                # Remove quotes if present
                if api_key and api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
                    api_key = api_key[1:-1]

                # If API key is empty, try environment variables
                if not api_key:
                    # Try provider-specific environment variable first
                    env_var = f"{connector_type.upper()}_API_KEY"
                    api_key = os.environ.get(env_var)

                    if not api_key:
                        # Try generic INDALEKO_API_KEY_{PROVIDER} format
                        env_var = f"INDALEKO_API_KEY_{connector_type.upper()}"
                        api_key = os.environ.get(env_var)

                # Update the config with the key from environment if found
                if api_key:
                    connector_config["api_key"] = api_key
                    ic(f"Using API key for {connector_type} from environment variable")

        return connector_type, connector_config

    @classmethod
    def _create_default_config(cls, config_path: str) -> None:
        """
        Create a default LLM configuration file.

        Args:
            config_path (str): Path to the config file.
        """
        config = configparser.ConfigParser()

        # Check if this is the unified keys file
        if "llm-keys" in config_path:
            config["llm"] = {
                "default_provider": "openai",
                "enabled_providers": "openai,anthropic,gemma,deepseek,grok",
            }

            config["openai"] = {
                "api_key": "your_openai_api_key_here",
                "model": "gpt-4o",
                "max_tokens": "8000",
            }

            config["anthropic"] = {
                "api_key": "your_anthropic_api_key_here",
                "model": "claude-3-sonnet-20240229",
                "max_tokens": "100000",
            }

            config["gemma"] = {
                "api_base": "http://localhost:1234/v1",
                "model": "gemma",
                "max_tokens": "4096",
            }

            config["deepseek"] = {
                "api_key": "your_deepseek_api_key_here",
                "api_base": "https://api.deepseek.com/v1",
                "model": "deepseek-llm",
                "max_tokens": "8192",
            }

            config["grok"] = {
                "api_key": "your_grok_api_key_here",
                "api_base": "https://api.grok.x/v1",
                "model": "grok-1",
                "max_tokens": "8192",
            }
        else:
            # Legacy config file
            config["llm"] = {
                "connector_type": "openai",
                "comment": "Available types: openai, anthropic, gemma, deepseek, grok, random",
            }

            config["openai"] = {
                "model": "gpt-4o",
                "max_tokens": "8000",
            }

            config["gemma"] = {
                "base_url": "http://localhost:1234/v1",
                "model": "Gemma",
                "max_tokens": "4096",
            }

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Write the config file
        with open(config_path, "w") as f:
            config.write(f)

    @classmethod
    def _load_openai_api_key(cls) -> str:
        """
        Load the OpenAI API key from the config file.

        Returns:
            str: The API key.
        """
        config_dir = Path(os.environ.get("INDALEKO_ROOT")) / "config"
        api_key_file = config_dir / "openai-key.ini"
        if not os.path.exists(api_key_file):
            raise ValueError(
                f"OpenAI API key file not found at {api_key_file}. "
                "Please create it with [openai] section and api_key value.",
            )

        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")

        if not config.has_section("openai") or not config.has_option("openai", "api_key"):
            raise ValueError(
                f"OpenAI API key not found in {api_key_file}. " "Please add [openai] section with api_key value.",
            )

        api_key = config["openai"]["api_key"]

        # Clean up quotes if present
        if api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
            api_key = api_key[1:-1]

        return api_key
