# LLM Connectors for Indaleko

This document describes the LLM connector system for Indaleko, which allows using different language models with the query assistant interface.

## Available Connectors

Currently, the following connectors are available:

- **OpenAI**: Uses OpenAI's API (GPT-4, GPT-3.5, etc.)
- **Gemma**: Uses Google's Gemma model running locally via LM Studio
- **Random**: Randomly selects one of the available connectors on startup

## Configuration

LLM connectors can be configured through command-line arguments or via a configuration file.

### Command-line Configuration

When running the assistant CLI, you can specify the connector and model to use:

```bash
# Use OpenAI (default)
python -m query.assistants.cli --llm openai --model gpt-4o

# Use local Gemma via LM Studio
python -m query.assistants.cli --llm gemma --model Gemma

# Randomly select a connector
python -m query.assistants.cli --llm random
```

### Configuration File

Create or edit the file `config/llm-config.ini` to set default values:

```ini
[llm]
connector_type = openai
comment = Available types: openai, gemma, random

[openai]
model = gpt-4o
max_tokens = 8000

[gemma]
base_url = http://localhost:1234/v1
model = Gemma
max_tokens = 4096
```

## Running Local Models with LM Studio

To use the Gemma connector, you need to have LM Studio running with the API server enabled.

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Download a compatible model (e.g., Gemma)
3. Start the model and enable the API server (port 1234 by default)
4. Run the Indaleko CLI with the `--llm gemma` option

## Testing the Connectors

You can use the test script to verify that the connectors are working:

```bash
# Test the Gemma connector
python test_gemma_connector.py --llm gemma

# Test OpenAI connector
python test_gemma_connector.py --llm openai

# Test with a specific prompt
python test_gemma_connector.py --llm gemma --prompt "What is a unified personal index?"
```

## Implementing New Connectors

To add a new LLM connector:

1. Create a new file in `query/utils/llm_connector/your_connector.py`
2. Implement a class that inherits from `IndalekoLLMBase`
3. Implement all required methods
4. Register the connector in `LLMConnectorFactory._registered_connectors`

See the `GemmaConnector` class for an example implementation.

## Architecture

The LLM connector system uses the following components:

- **IndalekoLLMBase**: Abstract base class that defines the interface for all LLM connectors
- **LLMConnectorFactory**: Factory class that creates connector instances based on configuration
- **Specific Connectors**: Implementation classes that provide the actual integration with LLMs

The system is designed to be extensible, allowing new connectors to be added without modifying existing code.

## Considerations for Production Deployment

When deploying to production, consider these aspects:

- **Security**: Ensure API keys and model access are properly secured
- **Performance**: Local models may have different latency and throughput characteristics than cloud APIs
- **Quotas**: Consider usage limits when using APIs
- **Fallbacks**: Implement fallback mechanisms if a connector fails

## Future Enhancements

Planned future enhancements include:

- **Ensemble Mode**: Use multiple LLMs in parallel and aggregate responses
- **Model Selection**: Dynamically select models based on query characteristics
- **Output Validation**: Add improved validation for response formats across models
- **Context Handling**: Optimize context window usage for different models