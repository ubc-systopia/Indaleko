"""ExecutorBase class for query execution in a data pipeline."""
import os
import sys

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from query.utils.llm_connector.llm_base import LLMBase
from data_models.query_history import IndalekoQueryHistoryDataModel

# pylint: enable=wrong-import-position

T = TypeVar("T", bound="IndalekoQueryHistoryDataModel")

class ExecutorBase(ABC):
    """Abstract base class for query executors."""

    @staticmethod
    @abstractmethod
    def execute(
        query: str,
        data_connector: LLMBase,
        **kwargs: dict,
    ) -> list[dict[str, Any]]:
        """
        Execute the query using the provided data connector.

        Args:
            query (str): The query to execute
            data_connector (Any): The connector to the data source
            kwargs (dict): Additional arguments for the execution

        Returns:
            list[dict[str, Any]]: The query results
        """

    @abstractmethod
    def validate_query(self, query: str) -> bool:
        """
        Validate the query before execution.

        Args:
            query (str): The query to validate

        Returns:
            bool: True if the query is valid, False otherwise
        """

    @abstractmethod
    def format_results(self, raw_results: Any) -> list[dict[str, Any]]:
        """
        Format the raw query results into a standardized format.

        Args:
            raw_results (Any): The raw results from the query execution

        Returns:
            List[Dict[str, Any]]: The formatted results
        """
