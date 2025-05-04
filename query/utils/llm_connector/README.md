# LLM Connector System for Indaleko

This directory contains the LLM connector system for Indaleko, which provides a unified interface for interacting with different language model providers.

## Available Connectors

- `OpenAIConnector`: Connects to OpenAI's API (GPT-4, GPT-4o, etc.)
- `GemmaConnector`: Connects to Google's Gemma models via LM Studio

## Configuration

The system supports a unified configuration approach through the `llm-keys.ini` file in the `config/` directory. This file contains:

1. The default LLM provider to use
2. An optional list of enabled providers (if not specified, all configured providers are enabled)
3. API keys and model configurations for each provider

Example configuration:
```ini
[llm]
default_provider = openai
enabled_providers = openai,anthropic,gemma

[openai]
api_key = sk-your-openai-key
model = gpt-4o

[anthropic]
api_key = sk-your-anthropic-key
model = claude-3-sonnet-20240229

[gemma]
api_base = http://localhost:1234/v1
model = gemma
```

### Dynamic Provider Discovery

The system automatically discovers providers from the configuration file. Each section (except `[llm]`) is treated as a potential provider. The system will:

1. Look for implemented connector classes for each provider in the config
2. Attempt to dynamically load connectors from `provider_name_connector.py` files
3. Only enable providers that have both an implementation and are included in the `enabled_providers` list (if specified)

This means you can add a new provider simply by:
1. Creating its connector implementation
2. Adding a section in the config file

No code changes are needed in the factory class itself.

## Adding a New Connector

To add a new LLM provider, follow these steps:

1. Create a new file `your_provider_connector.py`
2. Implement the `IndalekoLLMBase` interface
3. Register the connector in `factory.py`

### Example Implementation

```python
from query.utils.llm_connector.llm_base import IndalekoLLMBase

class YourProviderConnector(IndalekoLLMBase):
    """Connector for YourProvider's LLM API."""

    llm_name = "YourProvider"

    def __init__(self, **kwargs):
        """Initialize the connector with API key, model, etc."""
        self.api_key = kwargs.get("api_key")
        self.model = kwargs.get("model", "default-model")
        # Initialize client or other setup

    def get_llm_name(self) -> str:
        """Return the name of the LLM provider."""
        return self.llm_name

    def generate_text(self, prompt, **kwargs):
        """Generate text from a prompt."""
        # Your implementation here

    def answer_question(self, context, question, schema):
        """Answer a question based on context with structured response."""
        # Your implementation here

    # Implement other required methods
```

### Registering the Connector

In `factory.py`, add your connector to the `_registered_connectors` dictionary:

```python
from query.utils.llm_connector.your_provider_connector import YourProviderConnector

class LLMConnectorFactory:
    """Factory for creating LLM connectors."""

    # Dictionary of registered connector types
    _registered_connectors = {
        "openai": OpenAIConnector,
        "gemma": GemmaConnector,
        "your_provider": YourProviderConnector,  # Add your connector here
    }
```

## Using LLM Connectors

### From Code

```python
from query.utils.llm_connector.factory import LLMConnectorFactory

# Create a connector
connector = LLMConnectorFactory.create_connector(
    connector_type="your_provider",
    api_key="your-api-key",
    model="your-model"
)

# Use the connector
response = connector.generate_text("Hello, world!")
```

### From CLI

The query CLI supports selecting the LLM provider:

```bash
python -m query.cli --llm-provider your_provider
```

## Testing

To test a specific connector:

```bash
python test_llm_integration.py --connector your_provider
```

## Contributing

When adding a new connector, ensure:

1. All methods from `IndalekoLLMBase` are implemented
2. Proper error handling is in place
3. The connector is properly registered in the factory
4. API key loading works correctly
5. Tests are created to verify functionality
