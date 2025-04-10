"""
AQL translator tool for Indaleko.

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
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.data_models.query_input import StructuredQuery
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db import IndalekoDBConfig
from query.utils.llm_connector.openai_connector import OpenAIConnector


class AQLTranslatorTool(BaseTool):
    """Tool for translating structured queries to AQL."""
    
    def __init__(self):
        """Initialize the AQL translator tool."""
        super().__init__()
        self._translator = None
        self._llm_connector = None
        self._collections_metadata = None
    
    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name="aql_translator",
            description="Translates structured queries into AQL.",
            parameters=[
                ToolParameter(
                    name="structured_query",
                    description="The structured query to translate",
                    type="object",
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
                "aql_query": "The translated AQL query",
                "bind_vars": "Bind variables for the query",
                "raw_result": "The raw translator result"
            },
            examples=[
                {
                    "parameters": {
                        "structured_query": {
                            "original_query": "Show me documents with report in the title",
                            "intent": "search",
                            "entities": [{"name": "report", "type": "keyword", "value": "report"}]
                        }
                    },
                    "returns": {
                        "aql_query": "FOR doc IN Objects FILTER LIKE(doc.Record.Attributes.Label, '%report%') RETURN doc",
                        "bind_vars": {}
                    }
                }
            ]
        )
    
    def _initialize_translator(self, db_config_path: Optional[str] = None, api_key_path: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the AQL translator and related components.
        
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
        
        # Initialize AQL translator
        self._translator = AQLTranslator(self._collections_metadata)
    
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
        Execute the AQL translator tool.
        
        Args:
            input_data (ToolInput): The input data for the tool.
            
        Returns:
            ToolOutput: The result of the tool execution.
        """
        # Extract parameters
        structured_query_data = input_data.parameters["structured_query"]
        db_config_path = input_data.parameters.get("db_config_path")
        api_key_path = input_data.parameters.get("api_key_path")
        model = input_data.parameters.get("model", "gpt-4o-mini")
        
        # Initialize translator if needed
        if self._translator is None:
            self._initialize_translator(db_config_path, api_key_path, model)
        
        try:
            # Convert raw structured query to StructuredQuery object
            original_query = structured_query_data.get("original_query", "")
            intent = structured_query_data.get("intent", "search")
            entities = structured_query_data.get("entities", {})
            
            # Get collection metadata and indices if available
            db_info = structured_query_data.get("db_info", [])
            db_indices = structured_query_data.get("db_indices", {})
            
            # Process entities to ensure they are in the correct format
            # If entities is already a NamedEntityCollection object, use it directly
            if hasattr(entities, "entities") and isinstance(entities.entities, list):
                # It's already a NamedEntityCollection or similar object
                processed_entities = entities
            else:
                # Convert from dict or list format
                from data_models.named_entity import NamedEntityCollection, IndalekoNamedEntityDataModel, IndalekoNamedEntityType
                
                # If it's a dict with an 'entities' key, extract the entities
                if isinstance(entities, dict) and "entities" in entities:
                    entity_list = entities["entities"]
                elif isinstance(entities, list):
                    entity_list = entities
                else:
                    entity_list = []
                
                # Process each entity to ensure it has required fields
                processed_entity_list = []
                for entity in entity_list:
                    # If it's already an IndalekoNamedEntityDataModel, use it directly
                    if hasattr(entity, "name") and hasattr(entity, "category"):
                        processed_entity_list.append(entity)
                    else:
                        # Otherwise, convert from dict
                        if isinstance(entity, dict) and "name" in entity:
                            # Try to convert entity type to valid enum value
                            entity_type = entity.get("type", "item")
                            try:
                                entity_category = IndalekoNamedEntityType(entity_type.lower())
                            except ValueError:
                                entity_category = IndalekoNamedEntityType.item
                                
                            processed_entity_list.append(IndalekoNamedEntityDataModel(
                                name=entity["name"],
                                category=entity_category,
                                description=entity.get("value", entity["name"])
                            ))
                
                # Create a NamedEntityCollection
                processed_entities = NamedEntityCollection(entities=processed_entity_list)
            
            structured_query = StructuredQuery(
                original_query=original_query,
                intent=intent,
                entities=processed_entities,
                db_info=db_info if db_info else [],  # Ensure db_info is a list
                db_indices=db_indices if db_indices else {}  # Ensure db_indices is a dict
            )
            
            # Create translator input
            translator_input = TranslatorInput(
                Query=structured_query,
                Connector=self._llm_connector
            )
            
            ic(f"Translating query: {original_query}")
            
            # Translate the query
            translated_output = self._translator.translate(translator_input)
            
            # Return the result
            return ToolOutput(
                tool_name=self.definition.name,
                success=True,
                result={
                    "aql_query": translated_output.aql_query,
                    "bind_vars": translated_output.bind_vars,
                    "raw_result": translated_output.model_dump(mode="json")
                },
                elapsed_time=0.0  # Will be filled by wrapper
            )
            
        except Exception as e:
            ic(f"Error translating query: {e}")
            return ToolOutput(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                elapsed_time=0.0  # Will be filled by wrapper
            )