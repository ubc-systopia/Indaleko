"""
Test script for ArangoDB View usage in query translation.

This script tests whether the enhanced AQL translator correctly uses ArangoDB Views
for text search operations.
"""

import os
import sys


# Set up environment variables and path
current_path = os.path.dirname(os.path.abspath(__file__))
if current_path not in sys.path:
    sys.path.insert(0, current_path)

os.environ["INDALEKO_ROOT"] = current_path


def main():
    """Main entry point for the script."""
    try:
        # Import necessary components
        from data_models.named_entity import (
            IndalekoNamedEntityDataModel,
            NamedEntityCollection,
        )
        from db.db_collection_metadata import IndalekoDBCollectionsMetadata
        from db.db_config import IndalekoDBConfig
        from query.query_processing.data_models.query_input import StructuredQuery
        from query.query_processing.data_models.translator_input import TranslatorInput
        from query.query_processing.query_translator.aql_translator import AQLTranslator
        from query.utils.llm_connector.openai_connector import OpenAIConnector

        print("Imports succeeded")

        # Load API key
        api_key = load_api_key()
        print("API key loaded successfully")

        # Initialize DB config
        db_config = IndalekoDBConfig(
            config_file=os.path.join(current_path, "config", "indaleko-db-config.ini"),
        )
        print("DB config loaded successfully")

        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)
        print("Collections metadata loaded successfully")

        # Initialize OpenAI connector
        llm_connector = OpenAIConnector(api_key=api_key, model="gpt-4o-mini")
        print("LLM connector initialized")

        # Initialize AQL translator
        translator = AQLTranslator(collections_metadata)
        print("AQL translator initialized")

        # Test queries
        test_queries = [
            "Show me files with test in the name",
            "Find documents about Indaleko",
            "Search for PDF files with report in the title",
        ]

        # Process each query
        for query_text in test_queries:
            print(f"\nProcessing query: {query_text}")

            # Create entities for the query
            if "test" in query_text.lower():
                entities = [
                    IndalekoNamedEntityDataModel(
                        name="test",
                        category="keyword",
                        description="test",
                    ),
                ]
            elif "indaleko" in query_text.lower():
                entities = [
                    IndalekoNamedEntityDataModel(
                        name="indaleko",
                        category="keyword",
                        description="indaleko",
                    ),
                ]
            else:
                entities = [
                    IndalekoNamedEntityDataModel(
                        name="pdf",
                        category="file_extension",
                        description="pdf",
                    ),
                    IndalekoNamedEntityDataModel(
                        name="report",
                        category="keyword",
                        description="report",
                    ),
                ]

            entity_collection = NamedEntityCollection(entities=entities)

            # Create structured query
            structured_query = StructuredQuery(
                original_query=query_text,
                intent="search",
                entities=entity_collection,
            )

            # Create translator input
            translator_input = TranslatorInput(
                Query=structured_query,
                Connector=llm_connector,
            )

            # Translate query
            result = translator.translate(translator_input)

            # Print results
            print(f"AQL Query: {result.aql_query}")
            print(f"Bind Variables: {result.bind_vars}")
            print(f"Confidence: {result.confidence}")

            # Check if the query is using a view
            is_using_view = "ObjectsTextView" in result.aql_query and "SEARCH ANALYZER" in result.aql_query

            view_status = "✅ Using view" if is_using_view else "❌ Not using view"
            print(f"View Usage: {view_status}")

    except Exception as e:
        print(f"Error: {e!s}")
        import traceback

        traceback.print_exc()


def load_api_key() -> str:
    """Load the OpenAI API key from config file."""
    import configparser

    config_file = os.path.join(current_path, "config", "openai-key.ini")
    if not os.path.exists(config_file):
        raise ValueError(f"API key file not found: {config_file}")

    config = configparser.ConfigParser()
    config.read(config_file, encoding="utf-8-sig")

    if "openai" not in config or "api_key" not in config["openai"]:
        raise ValueError("OpenAI API key not found in config file")

    openai_key = config["openai"]["api_key"]

    # Clean up the key if it has quotes
    if openai_key[0] in ["'", '"'] and openai_key[-1] in ["'", '"']:
        openai_key = openai_key[1:-1]

    return openai_key


if __name__ == "__main__":
    main()
