import inspect
import os
import sys
from pathlib import Path

# Adjust path for Indaleko imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from query.utils.llm_connector.anthropic_connector import AnthropicConnector
from query.utils.llm_connector.factory import LLMConnectorFactory


def main():
    print("--- Testing LLM Factory and AnthropicConnector ---")

    # Check factory
    factory = LLMConnectorFactory
    print(f"Available connectors: {factory.get_available_connectors()}")

    # Create connector
    connector = factory.create_connector(connector_type="anthropic")
    print(f"Created connector: {connector.__class__.__name__}")

    # Check if stream parameter exists in the refactored connector
    if isinstance(connector, AnthropicConnector):
        print("Checking AnthropicConnector.get_completion parameters:")
        sig = inspect.signature(connector.get_completion)
        print(f"Parameters: {list(sig.parameters.keys())}")

        # Check if it has stream parameter
        has_stream = "stream" in dir(connector.client.messages.create)
        print(f"Has stream parameter in client.messages.create: {has_stream}")

        # Check get_completion method implementation
        if hasattr(connector, "get_completion"):
            print(f"get_completion method source location: {inspect.getfile(connector.get_completion)}")

            # Call get_completion with stream=False explicitly
            try:
                print("Testing get_completion with explicit stream=False...")
                result = connector.get_completion(
                    context="Test context",
                    question="Test question",
                    schema={"type": "string"},
                )
                print(f"get_completion result type: {type(result)}")
            except Exception as e:
                print(f"Error calling get_completion: {e}")


if __name__ == "__main__":
    main()
