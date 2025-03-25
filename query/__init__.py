"""initializtion logic for the Indaleko query library"""

import os
import importlib
import sys

# from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# probably should add some exports here.
# pylint: disable=wrong-import-position
from query.interface.cli import CLI
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.query_history import QueryHistory
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.result_analysis.metadata_analyzer import MetadataAnalyzer
from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.result_ranker import ResultRanker
from query.utils.llm_connector.openai_connector import OpenAIConnector
from query.utils.logging_service import LoggingService

# pylint: enable=wrong-import-position


__version__ = "0.1.0"

__all__ = [
    "CLI",
    "NLParser",
    "AQLTranslator",
    "QueryHistory",
    "AQLExecutor",
    "MetadataAnalyzer",
    "FacetGenerator",
    "ResultRanker",
    "OpenAIConnector",
    "LoggingService",
]
