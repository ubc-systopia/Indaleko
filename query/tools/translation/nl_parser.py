"""
Natural language parser tool for Indaleko.

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
from typing import Any, Dict, List, Optional

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.tools.base import BaseTool, ToolDefinition, ToolInput, ToolOutput, ToolParameter
from query.query_processing.nl_parser import NLParser
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db import IndalekoDBConfig
from query.utils.llm_connector.openai_connector import OpenAIConnector


class NLParserTool(BaseTool):
    """Tool for parsing natural language queries into structured formats."""
    
    def __init__(self):
        """Initialize the NL parser tool."""
        super().__init__()
        self._llm_connector = None
        self._nl_parser = None
        self._collections_metadata = None
    
    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name="nl_parser",
            description="Parses natural language queries into structured representations with intent and entities.",
            parameters=[
                ToolParameter(
                    name="query",
                    description="The natural language query to parse",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="db_config_path",
                    description="Path to the database configuration file",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="api_key_path",
                    description="Path to the OpenAI API key file",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="model",
                    description="The OpenAI model to use",
                    type="string",
                    required=False,
                    default="gpt-4o-mini"
                )
            ],
            returns={
                "intent": "The detected intent of the query",
                "entities": "Entities extracted from the query",
                "categories": "Relevant database categories for the query",
                "raw_result": "The raw parser result"
            },
            examples=[
                {
                    "parameters": {
                        "query": "Show me documents with report in the title"
                    },
                    "returns": {
                        "intent": "search",
                        "entities": [{"name": "report", "type": "keyword"}],
                        "categories": ["Objects"]
                    }
                }
            ]
        )
    
    def _initialize_parser(self, db_config_path: Optional[str] = None, api_key_path: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the NL parser and related components.
        
        Args:
            db_config_path (Optional[str]): Path to the database configuration file.
            api_key_path (Optional[str]): Path to the OpenAI API key file.
            model (str): The OpenAI model to use.
        """
        # Load database configuration
        if db_config_path is None:
            config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
            db_config_path = os.path.join(config_dir, "indaleko-db-config.ini")
        
        # Load OpenAI API key
        if api_key_path is None:
            config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
            api_key_path = os.path.join(config_dir, "openai-key.ini")
        
        # Initialize DB config
        self._db_config = IndalekoDBConfig(config_file=db_config_path)
        
        # Initialize collections metadata
        self._collections_metadata = IndalekoDBCollectionsMetadata(self._db_config)
        
        # Initialize OpenAI connector
        openai_key = self._get_api_key(api_key_path)
        self._llm_connector = OpenAIConnector(
            api_key=openai_key,
            model=model
        )
        
        # Initialize NL parser
        self._nl_parser = NLParser(
            llm_connector=self._llm_connector,
            collections_metadata=self._collections_metadata
        )
    
    def _get_api_key(self, api_key_file: str) -> str:
        """
        Get the API key from the config file.
        
        Args:
            api_key_file (str): Path to the API key file.
            
        Returns:
            str: The API key.
            
        Raises:
            ValueError: If the API key file is not found or the key is not present.
        """
        import configparser
        
        if not os.path.exists(api_key_file):
            raise ValueError(f"API key file not found: {api_key_file}")
        
        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")
        
        if "openai" not in config or "api_key" not in config["openai"]:
            raise ValueError("OpenAI API key not found in config file")
        
        openai_key = config["openai"]["api_key"]
        
        # Clean up the key if it has quotes
        if openai_key[0] in ["'", '"'] and openai_key[-1] in ["'", '"']:
            openai_key = openai_key[1:-1]
        
        return openai_key
    
    def execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Execute the NL parser tool.
        
        Args:
            input_data (ToolInput): The input data for the tool.
            
        Returns:
            ToolOutput: The result of the tool execution.
        """
        # Extract parameters
        query = input_data.parameters["query"]
        db_config_path = input_data.parameters.get("db_config_path")
        api_key_path = input_data.parameters.get("api_key_path")
        model = input_data.parameters.get("model", "gpt-4o-mini")
        
        # Initialize parser if needed
        if self._nl_parser is None:
            self._initialize_parser(db_config_path, api_key_path, model)
        
        ic(f"Parsing query: {query}")
        
        # Parse the query
        try:
            parsed_result = self._nl_parser.parse(query=query)
            
            # Extract key information
            intent = parsed_result.Intent.intent
            
            # Create entity list
            entities = []
            for entity in parsed_result.Entities.entities:
                entities.append({
                    "name": entity.name,
                    "type": entity.category if hasattr(entity, "category") else "unknown",
                    "value": entity.value if hasattr(entity, "value") else entity.name
                })
            
            # Extract categories
            categories = []
            if hasattr(parsed_result.Categories, "category_map"):
                for category in parsed_result.Categories.category_map:
                    categories.append({
                        "name": category.collection,
                        "relevance": category.relevance
                    })
            
            # Return the result
            return ToolOutput(
                tool_name=self.definition.name,
                success=True,
                result={
                    "intent": intent,
                    "entities": entities,
                    "categories": categories,
                    "raw_result": parsed_result.model_dump(mode="json")
                },
                elapsed_time=0.0  # Will be filled by wrapper
            )
            
        except Exception as e:
            ic(f"Error parsing query: {e}")
            return ToolOutput(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                elapsed_time=0.0  # Will be filled by wrapper
            )