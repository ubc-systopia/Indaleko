"""
Test the enhanced system prompt to validate View usage in the EnhancedAQLTranslator.

This script prints out the system prompt from the EnhancedAQLTranslator
to verify that it includes the necessary instructions for using
ArangoDB Views for text search operations.
"""

import os
import sys

# Set up environment variables
current_path = os.path.dirname(os.path.abspath(__file__))
os.environ["INDALEKO_ROOT"] = current_path
if current_path not in sys.path:
    sys.path.insert(0, current_path)

# Add the src directory to the path
src_path = os.path.join(current_path, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

print("Python path:", sys.path)


# Extract the content of the system prompt from the EnhancedAQLTranslator
def extract_translator_prompt():
    """Extract the system prompt from the EnhancedAQLTranslator file."""
    try:
        translator_file = os.path.join(
            current_path,
            "query",
            "query_processing",
            "query_translator",
            "enhanced_aql_translator.py",
        )

        print(f"Looking for enhanced translator file at: {translator_file}")

        if not os.path.exists(translator_file):
            raise ValueError(f"Enhanced translator file not found: {translator_file}")

        # Read the file content
        with open(translator_file, encoding="utf-8") as f:
            content = f.read()

        # Extract the system prompt
        start_marker = 'system_prompt = f"""'
        end_marker = '"""'

        start_idx = content.find(start_marker)
        if start_idx == -1:
            raise ValueError("Start marker not found in file")

        # Find the end marker after the start marker
        start_idx += len(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if end_idx == -1:
            raise ValueError("End marker not found after start marker")

        # Extract the prompt template
        prompt_template = content[start_idx:end_idx]

        return prompt_template

    except Exception as e:
        print(f"Error extracting enhanced translator prompt: {e!s}")
        import traceback

        traceback.print_exc()
        return None


# Main function
def main():
    """Main entry point for the script."""
    try:
        # Extract the translator prompt
        prompt_template = extract_translator_prompt()

        if prompt_template:
            print("\n=== Enhanced AQL Translator System Prompt ===\n")
            print(prompt_template)

            # Check if the prompt mentions views and search analyzer
            view_mentioned = "view" in prompt_template.lower()
            search_analyzer_mentioned = "search analyzer" in prompt_template.lower()
            objectstextview_mentioned = "objectstextview" in prompt_template.lower()
            text_search_examples = prompt_template.lower().count(
                "for doc in objectstextview",
            )
            bm25_mentioned = "bm25" in prompt_template.lower()

            print("\n=== Analysis ===\n")
            print(f"View mentioned: {'Yes' if view_mentioned else 'No'}")
            print(
                f"SEARCH ANALYZER mentioned: {'Yes' if search_analyzer_mentioned else 'No'}",
            )
            print(
                f"ObjectsTextView mentioned: {'Yes' if objectstextview_mentioned else 'No'}",
            )
            print(f"Number of text search examples: {text_search_examples}")
            print(f"BM25 mentioned: {'Yes' if bm25_mentioned else 'No'}")

            # Check for specific sections on ArangoDB Views
            views_section = "arangodb views for text search" in prompt_template.lower()
            view_mapping = "collection to view mapping" in prompt_template.lower()

            print(f"Has ArangoDB Views section: {'Yes' if views_section else 'No'}")
            print(f"Has collection-to-view mapping: {'Yes' if view_mapping else 'No'}")

    except Exception as e:
        print(f"Error in main: {e!s}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
