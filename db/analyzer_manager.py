"""
This module provides utilities for managing ArangoDB analyzers for Indaleko.

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

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Any, Optional, Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig
# We'll import the CLI base class later in a separate module

# pylint: enable=wrong-import-position


class IndalekoAnalyzerManager:
    """
    Manages ArangoDB analyzers for Indaleko.

    This class provides functionality to create, list, and manage custom
    text analyzers in ArangoDB that improve file name search capabilities.
    """

    # Default analyzer definitions
    CAMEL_CASE_ANALYZER = "Indaleko::indaleko_camel_case"
    SNAKE_CASE_ANALYZER = "Indaleko::indaleko_snake_case"
    FILENAME_ANALYZER = "Indaleko::indaleko_filename"

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """
        Initialize the analyzer manager.

        Args:
            db_config: Database configuration object. If None, a new one is created.
        """
        self.db_config = db_config if db_config is not None else IndalekoDBConfig()
        self.db_config.start()

    @staticmethod
    def build_arangosh_command_string(db_config: IndalekoDBConfig,
                                      script_file: str = "",
                                      use_root: bool = False) -> str:
        """
        Build the arangosh command for executing JavaScript files.

        Args:
            db_config: The database configuration object
            script_file: Path to a JavaScript file to execute
            use_root: Whether to use the root account instead of the standard user account

        Returns:
            The arangosh command as a string
        """
        command = "arangosh"

        # Add connection details
        command += f" --server.database {db_config.get_database_name()}"

        # Use root account if requested (for operations requiring admin privileges)
        if use_root:
            command += f" --server.username {db_config.get_root_name()}"
            command += f" --server.password {db_config.get_root_password()}"
        else:
            command += f" --server.username {db_config.get_user_name()}"
            command += f" --server.password {db_config.get_user_password()}"

        # Handle SSL if needed
        if db_config.get_ssl_state():
            command += " --ssl.protocol 5"
            endpoint = f"ssl://{db_config.get_hostname()}:{db_config.get_port()}"
        else:
            endpoint = f"tcp://{db_config.get_hostname()}:{db_config.get_port()}"

        command += f" --server.endpoint {endpoint}"

        # Add script file if provided
        if script_file:
            command += f" --javascript.execute {script_file}"

        return command

    def build_arangosh_command(self, script_file: str = "") -> str:
        """
        Build the arangosh command for executing JavaScript files for this instance.

        Args:
            script_file: Path to a JavaScript file to execute

        Returns:
            The arangosh command as a string
        """
        # Analyzer creation typically requires admin privileges
        return self.build_arangosh_command_string(
            self.db_config,
            script_file,
            use_root=True  # Use root account since analyzer creation requires admin privileges
        )

    def execute_arangosh_script(self, script_content: str) -> tuple[bool, str]:
        """
        Execute the provided JavaScript code using arangosh.

        Args:
            script_content: JavaScript code to execute

        Returns:
            Tuple of (success, output)
        """
        # Create a temporary file for the script
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False, mode='w') as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(script_content)

        try:
            # Execute the script using arangosh
            command = self.build_arangosh_command(temp_file_path)
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Check the result
            success = result.returncode == 0
            output = result.stdout

            if not success:
                output += f"\nError: {result.stderr}"
                logging.error("Arangosh execution failed: %s", result.stderr)

            return success, output

        finally:
            # Remove the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def execute_arangosh_command(self, command: str) -> tuple[bool, str]:
        """
        Execute a single arangosh command.

        Args:
            command: JavaScript command to execute

        Returns:
            Tuple of (success, output)
        """
        script = f"try {{ {command} }} catch (err) {{ print('Error: ' + err); }}"
        return self.execute_arangosh_script(script)

    def list_analyzers(self) -> List[Dict[str, Any]]:
        """
        List all analyzers in the database.

        Returns:
            List of analyzer dictionaries
        """
        script = """
        try {
            var analyzers = require("@arangodb/analyzers").toArray();
            analyzers.forEach(function(analyzer) {
                var properties = JSON.stringify(analyzer.properties(), null, 2);
                print(JSON.stringify({
                    name: analyzer.name(),
                    type: analyzer.type(),
                    properties: properties
                }));
            });
        } catch (err) {
            print("Error: " + err);
        }
        """

        success, output = self.execute_arangosh_script(script)
        if not success:
            logging.error("Failed to list analyzers: %s", output)
            return []

        analyzers = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    import json
                    analyzer = json.loads(line)
                    analyzers.append(analyzer)
                except json.JSONDecodeError:
                    continue

        return analyzers

    def analyzer_exists(self, analyzer_name: str) -> bool:
        """
        Check if an analyzer with the given name exists.

        Args:
            analyzer_name: Name of the analyzer to check

        Returns:
            True if the analyzer exists, False otherwise
        """
        script = f"""
        try {{
            var analyzer = require("@arangodb/analyzers").analyzer('{analyzer_name}');
            if (analyzer) {{
                print("Exists: true");
            }}
        }} catch (err) {{
            print("Exists: false");
        }}
        """

        success, output = self.execute_arangosh_script(script)
        return success and "Exists: true" in output

    def create_camel_case_analyzer(self) -> bool:
        """
        Create the CamelCase analyzer.

        Returns:
            True if successful, False otherwise
        """
        if self.analyzer_exists(self.CAMEL_CASE_ANALYZER):
            logging.info("CamelCase analyzer already exists")
            return True

        script = f"""
        var analyzers = require("@arangodb/analyzers");
        try {{
            analyzers.save("{self.CAMEL_CASE_ANALYZER}", "pipeline", {{
                pipeline: [
                    // Split on camelCase boundaries
                    {{
                        type: "delimiter",
                        properties: {{
                            delimiter: "",
                            regexp: true,
                            pattern: "(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
                        }}
                    }},
                    // Normalize to lowercase
                    {{
                        type: "norm",
                        properties: {{
                            locale: "en",
                            case: "lower"
                        }}
                    }}
                ]
            }});
            print("Successfully created CamelCase analyzer");
        }} catch (err) {{
            print("Failed to create CamelCase analyzer: " + err);
        }}
        """

        success, output = self.execute_arangosh_script(script)
        if success and "Successfully created CamelCase analyzer" in output:
            logging.info("Successfully created CamelCase analyzer")
            return True
        else:
            logging.error("Failed to create CamelCase analyzer: %s", output)
            return False

    def create_snake_case_analyzer(self) -> bool:
        """
        Create the snake_case analyzer.

        Returns:
            True if successful, False otherwise
        """
        if self.analyzer_exists(self.SNAKE_CASE_ANALYZER):
            logging.info("snake_case analyzer already exists")
            return True

        script = f"""
        var analyzers = require("@arangodb/analyzers");
        try {{
            analyzers.save("{self.SNAKE_CASE_ANALYZER}", "pipeline", {{
                pipeline: [
                    // Split on underscores
                    {{
                        type: "delimiter",
                        properties: {{
                            delimiter: "_"
                        }}
                    }},
                    // Normalize to lowercase
                    {{
                        type: "norm",
                        properties: {{
                            locale: "en",
                            case: "lower"
                        }}
                    }}
                ]
            }});
            print("Successfully created snake_case analyzer");
        }} catch (err) {{
            print("Failed to create snake_case analyzer: " + err);
        }}
        """

        success, output = self.execute_arangosh_script(script)
        if success and "Successfully created snake_case analyzer" in output:
            logging.info("Successfully created snake_case analyzer")
            return True
        else:
            logging.error("Failed to create snake_case analyzer: %s", output)
            return False

    def create_filename_analyzer(self) -> bool:
        """
        Create the filename analyzer.

        Returns:
            True if successful, False otherwise
        """
        if self.analyzer_exists(self.FILENAME_ANALYZER):
            logging.info("filename analyzer already exists")
            return True

        script = f"""
        var analyzers = require("@arangodb/analyzers");
        try {{
            analyzers.save("{self.FILENAME_ANALYZER}", "pipeline", {{
                pipeline: [
                    // Extract extension first
                    {{
                        type: "delimiter",
                        properties: {{
                            delimiter: ".",
                            reverse: true,
                            max: 1
                        }}
                    }},
                    // Then split on various separators (hyphens, underscores, spaces, percent-encoded chars)
                    {{
                        type: "delimiter",
                        properties: {{
                            delimiter: "",
                            regexp: true,
                            pattern: "[-_\\\\s%]+"
                        }}
                    }},
                    // Split CamelCase
                    {{
                        type: "delimiter",
                        properties: {{
                            delimiter: "",
                            regexp: true,
                            pattern: "(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
                        }}
                    }},
                    // Normalize to lowercase
                    {{
                        type: "norm",
                        properties: {{
                            locale: "en",
                            case: "lower"
                        }}
                    }}
                ]
            }});
            print("Successfully created filename analyzer");
        }} catch (err) {{
            print("Failed to create filename analyzer: " + err);
        }}
        """

        success, output = self.execute_arangosh_script(script)
        if success and "Successfully created filename analyzer" in output:
            logging.info("Successfully created filename analyzer")
            return True
        else:
            logging.error("Failed to create filename analyzer: %s", output)
            return False

    def create_all_analyzers(self) -> Dict[str, bool]:
        """
        Create all custom analyzers.

        Returns:
            Dictionary of analyzer names to success status
        """
        results = {}
        results[self.CAMEL_CASE_ANALYZER] = self.create_camel_case_analyzer()
        results[self.SNAKE_CASE_ANALYZER] = self.create_snake_case_analyzer()
        results[self.FILENAME_ANALYZER] = self.create_filename_analyzer()
        return results

    def delete_analyzer(self, analyzer_name: str) -> bool:
        """
        Delete an analyzer.

        Args:
            analyzer_name: Name of the analyzer to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.analyzer_exists(analyzer_name):
            logging.info("Analyzer %s does not exist", analyzer_name)
            return True

        script = f"""
        try {{
            require("@arangodb/analyzers").remove('{analyzer_name}');
            print("Successfully deleted analyzer {analyzer_name}");
            return true;
        }} catch (err) {{
            print("Failed to delete analyzer {analyzer_name}: " + err);
            return false;
        }}
        """

        success, output = self.execute_arangosh_script(script)
        if success and f"Successfully deleted analyzer {analyzer_name}" in output:
            logging.info("Successfully deleted analyzer %s", analyzer_name)
            return True
        else:
            logging.error("Failed to delete analyzer %s: %s", analyzer_name, output)
            return False

    def test_analyzer(self, analyzer_name: str, test_string: str) -> tuple[bool, List[str]]:
        """
        Test an analyzer on a string.

        Args:
            analyzer_name: Name of the analyzer to test
            test_string: String to analyze

        Returns:
            Tuple of (success, tokens)
        """
        if not self.analyzer_exists(analyzer_name):
            logging.error("Analyzer %s does not exist", analyzer_name)
            return False, []

        script = f"""
        try {{
            var result = db._query(
                "RETURN TOKENS(@text, @analyzer)",
                {{ text: '{test_string}', analyzer: '{analyzer_name}' }}
            ).toArray()[0];
            print("Tokens: " + JSON.stringify(result));
        }} catch (err) {{
            print("Failed to test analyzer {analyzer_name}: " + err);
        }}
        """

        success, output = self.execute_arangosh_script(script)
        tokens = []

        if success:
            # Extract tokens from the output
            for line in output.splitlines():
                if line.startswith("Tokens: "):
                    try:
                        import json
                        tokens = json.loads(line[8:])
                        break
                    except json.JSONDecodeError:
                        pass
            return True, tokens
        else:
            logging.error("Failed to test analyzer %s: %s", analyzer_name, output)
            return False, []


# CLI functionality has been moved to analyzer_manager_cli.py
# This avoids the circular dependency while preserving inheritance


def main():
    """Main entry point for the analyzer manager CLI."""
    try:
        # Import CLI from the separate module to avoid circular dependency
        from db.analyzer_manager_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"Error importing analyzer_manager_cli: {e}")
        print("The CLI functionality has been moved to analyzer_manager_cli.py")
        # Fallback to direct analyzer creation
        if "--direct" in sys.argv:
            print("Executing analyzer creation directly...")
            execute_analyzer_creation()
        else:
            print("Please use python -m db.analyzer_manager_cli to access the CLI")
            print("Or use --direct to create analyzers directly")


def create_custom_analyzers(db_config: Optional[IndalekoDBConfig] = None) -> Dict[str, bool]:
    """
    Utility function to create all custom analyzers.
    This can be called directly without creating an instance of IndalekoAnalyzerManager.

    Args:
        db_config: Optional database configuration. If None, a new one is created.

    Returns:
        Dictionary with analyzer names as keys and success status as values
    """
    analyzer_manager = IndalekoAnalyzerManager(db_config)
    return analyzer_manager.create_all_analyzers()


def execute_analyzer_creation(db_config: Optional[IndalekoDBConfig] = None) -> bool:
    """
    Run the custom analyzer creation directly using arangosh.
    This is a simple wrapper function that executes the arangosh command to create analyzers.

    Args:
        db_config: Optional database configuration. If None, a new one is created.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the command
        command = get_arangosh_command(db_config)

        # Execute the command
        logging.info(f"Executing analyzer creation command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check result
        if result.returncode == 0:
            logging.info("Custom analyzers created successfully")
            # Check if analyzers were actually created by looking at stdout
            for line in result.stdout.splitlines():
                if "Created" in line and "analyzer" in line:
                    logging.info(line.strip())
            return True
        else:
            logging.error(f"Failed to create custom analyzers: {result.stderr}")
            return False

    except Exception as e:
        logging.error(f"Error executing analyzer creation: {e}")
        return False


def create_custom_analyzers_script() -> str:
    """
    Generate a script that can be executed directly to create custom analyzers.
    This is useful for creating a standalone script that can be run from the command line.

    Returns:
        A string containing the arangosh script to create analyzers
    """
    # Load the create_analyzers.js file
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "create_analyzers.js")

    if not os.path.exists(script_path):
        logging.error(f"Analyzer script file not found: {script_path}")
        return ""

    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    # Return the script content for execution
    return script_content


def get_arangosh_command(db_config: Optional[IndalekoDBConfig] = None) -> str:
    """
    Get the arangosh command to execute the analyzer creation script.

    Args:
        db_config: Optional database configuration. If None, a new one is created.

    Returns:
        The arangosh command string to create analyzers
    """
    if db_config is None:
        db_config = IndalekoDBConfig()

    # Get the script file path
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "create_analyzers.js")

    # Build the command
    return IndalekoAnalyzerManager.build_arangosh_command_string(
        db_config,
        script_file=script_path,
        use_root=True  # Use root account since analyzer creation requires admin privileges
    )


if __name__ == "__main__":
    main()
