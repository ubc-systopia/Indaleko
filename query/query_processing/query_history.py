'''
This module defines the base data model for LLM connectors.

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
'''
from datetime import datetime, timezone
import json
import os
import sys
from textwrap import dedent

from typing import List, Dict, Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoRecordDataModel, IndalekoSourceIdentifierDataModel
from data_models.query_history import IndalekoQueryHistoryDataModel
from query.history.data_models.query_history import QueryHistoryData  # noqa: E402
from db import IndalekoDBConfig, IndalekoDBCollections  # noqa: E402
from utils.misc.data_management import encode_binary_data  # noqa: E402
# pylint: enable=wrong-import-position


class QueryHistory:
    """
    Manages the history of user queries and their results.
    """

    query_history_uuid_str = "9d13e4b4-de50-4a7d-878a-932c54f346ec"
    query_history_version = "2025.02.17.01"
    query_history_description = dedent("""Captured query history for Indaleko.""")

    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
        '''Set up the query history'''
        self.db_config = db_config
        self.query_history_collection = self.db_config.db.collection(
            IndalekoDBCollections.Indaleko_Query_History_Collection
        )

    def add(self, query_history: QueryHistoryData) -> None:
        """
        Add a query and its results to the history.

        Args:
            kwargs: Keyword arguments for the query history data model

        Note: this is a preliminary implementation.
        """
        query_history = IndalekoQueryHistoryDataModel(
            Record=IndalekoRecordDataModel(
                SourceIdentifier=IndalekoSourceIdentifierDataModel(
                    Identifier=self.query_history_uuid_str,
                    Version=self.query_history_version,
                    Description=self.query_history_description,
                ),
                Timestamp=datetime.now(timezone.utc),
                Data=encode_binary_data(
                    bytes(
                        query_history.model_dump_json(
                            exclude_none=True,
                            exclude_unset=True
                        ),
                        'utf-8'
                    )
                ),
            ),
            QueryHistory=query_history
        )
        doc = json.loads(query_history.model_dump_json())
        self.query_history_collection.insert(doc)

    def get_recent_queries(self, n: int = 5) -> List[QueryHistoryData]:
        """
        Get the n most recent queries.

        Args:
            n (int): Number of recent queries to retrieve

        Returns:
            List[str]: List of recent queries
        """
        return [
            IndalekoQueryHistoryDataModel(**doc).QueryHistory
            for doc in self.query_history_collection.find(
                {},
                sort=[('Record.Timestamp', -1)],
                limit=n
            )
        ]

    def get_last_query(self) -> QueryHistoryData:
        """
        Get the most recent query and its results.

        Returns:
            Dict[str, Any]: The last query and its results, or None if history is empty
        """
        return self.get_recent_queries(1)[0] if self.query_history_collection.count() > 0 else None

    def clear(self) -> None:
        """
        Clear the query history.
        """
        self.history.clear()

    def get_full_history(self) -> List[Dict[str, Any]]:
        """
        Get the full query history.

        Returns:
            List[Dict[str, Any]]: The full query history
        """
        raise NotImplementedError("This method is not yet implemented")
        # This is going to require an iterator, most likely.

    def find_similar_queries(self, query: str) -> List[Dict[str, Any]]:
        """
        Find queries in the history that are similar to the given query.

        Args:
            query (str): The query to compare against

        Returns:
            List[Dict[str, Any]]: Similar queries and their results
        """
        # Implement similarity comparison logic
        # This is a placeholder implementation
        raise NotImplementedError("This method is not yet implemented")
