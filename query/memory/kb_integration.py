"""
Knowledge Base integration with Query CLI.

This module connects the Knowledge Base Updating functionality with the
query command-line interface.

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
import logging
from typing import Any, Dict, List, Optional

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
try:
    from archivist.kb_cli_integration import KnowledgeBaseCliIntegration
    from archivist.kb_integration import ArchivistKnowledgeIntegration
    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False

from utils.cli.base import IndalekoBaseCLI
# pylint: enable=wrong-import-position


def initialize_kb_for_cli(cli_instance: IndalekoBaseCLI) -> Optional[KnowledgeBaseCliIntegration]:
    """
    Initialize the Knowledge Base integration for the Query CLI.
    
    Args:
        cli_instance: The CLI instance to integrate with
        
    Returns:
        KnowledgeBaseCliIntegration instance if available, None otherwise
    """
    if not HAS_KNOWLEDGE_BASE:
        logging.warning("Knowledge Base features are not available")
        return None
    
    try:
        # Create integration
        kb_integration = KnowledgeBaseCliIntegration(cli_instance)
        
        # Store integration in CLI instance
        cli_instance.kb_integration = kb_integration
        
        # Log success
        logging.info("Knowledge Base integration initialized successfully")
        
        return kb_integration
    except Exception as e:
        logging.error(f"Failed to initialize Knowledge Base integration: {str(e)}")
        return None


def enhance_query_with_kb(cli_instance: IndalekoBaseCLI, query_text: str, 
                        intent: str = "", 
                        entities: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enhance a query using the Knowledge Base if available.
    
    Args:
        cli_instance: The CLI instance
        query_text: The original query text
        intent: The query intent (if known)
        entities: Entities extracted from the query
        
    Returns:
        Enhanced query information or original query if KB not available
    """
    # Return original query if KB not available
    if not HAS_KNOWLEDGE_BASE or not hasattr(cli_instance, "kb_integration"):
        return {
            "original_query": query_text,
            "enhanced_query": query_text,
            "intent": intent,
            "entities": entities or [],
            "enhancements_applied": False
        }
    
    try:
        # Enhance query using KB
        enhanced = cli_instance.kb_integration.enhance_query(
            query_text=query_text,
            intent=intent,
            extracted_entities=entities or []
        )
        
        return enhanced
    except Exception as e:
        logging.error(f"Error enhancing query with Knowledge Base: {str(e)}")
        return {
            "original_query": query_text,
            "enhanced_query": query_text,
            "intent": intent,
            "entities": entities or [],
            "enhancements_applied": False
        }


def record_query_results(cli_instance: IndalekoBaseCLI, query_text: str, 
                       result_info: Dict[str, Any],
                       intent: str = "",
                       entities: List[Dict[str, Any]] = None) -> None:
    """
    Record query results for learning if KB is available.
    
    Args:
        cli_instance: The CLI instance
        query_text: The original query text
        result_info: Information about query results
        intent: The query intent (if known)
        entities: Entities extracted from the query
    """
    # Do nothing if KB not available
    if not HAS_KNOWLEDGE_BASE or not hasattr(cli_instance, "kb_integration"):
        return
    
    try:
        # Record results using KB
        cli_instance.kb_integration.record_query_results(
            query_text=query_text,
            result_info=result_info,
            query_intent=intent,
            entities=entities or []
        )
    except Exception as e:
        logging.error(f"Error recording query results with Knowledge Base: {str(e)}")


def add_kb_arguments(parser) -> None:
    """
    Add Knowledge Base arguments to a command-line parser.
    
    Args:
        parser: The argument parser to add arguments to
    """
    kb_group = parser.add_argument_group("Knowledge Base")
    kb_group.add_argument(
        "--kb", "--knowledge-base",
        action="store_true",
        help="Enable Knowledge Base features"
    )
    kb_group.add_argument(
        "--kb-confidence",
        type=float,
        default=0.7,
        help="Minimum confidence threshold for knowledge patterns (0-1)"
    )