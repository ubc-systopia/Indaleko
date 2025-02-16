"""
This module provides a CLI based interface for querying Indaleko.

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

import configparser
import os
import sys

from icecream import ic
from typing import Union, Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.query_history import QueryHistory
from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.metadata_analyzer import MetadataAnalyzer
from query.result_analysis.result_ranker import ResultRanker
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.utils.llm_connector.openai_connector import OpenAIConnector
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
# pylint: enable=wrong-import-position


class IndalekoQueryCLI(IndalekoBaseCLI):
    '''This class represents the base class for Indaleko Queries.'''

    service_name = 'IndalekoQueryCLI'

    def __init__(self):
        '''Create an instance of the IndalekoQueryCLI class.'''
        cli_data = IndalekoBaseCliDataModel()
        handler_mixin = IndalekoBaseCLI.default_handler_mixin
        features = IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            output=False,
            offline=False,
            logging=False,
            performance=False,
            platform=False,
        )
        super().__init__(
            cli_data=cli_data,
            handler_mixin=handler_mixin,
            features=features
        )
        config_data = self.get_config_data()
        config_file_path = os.path.join(config_data['ConfigDirectory'], config_data['DBConfigFile'])
        self.db_config = IndalekoDBConfig(config_file=config_file_path)
        self.collections_metadata = IndalekoDBCollectionsMetadata(self.db_config)
        self.openai_key = self.get_api_key()
        self.llm_connector = OpenAIConnector(api_key=self.openai_key)
        self.nl_parser = NLParser(
            llm_connector=self.llm_connector,
            collections_metadata=self.collections_metadata
        )
        self.query_translator = AQLTranslator(self.collections_metadata)
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()
        self.metadata_analyzer = MetadataAnalyzer()
        self.facet_generator = FacetGenerator()
        self.result_ranker = ResultRanker()
        self.prompt = 'Indaleko Search> '
        self.schema = self.build_schema_table()

    def get_api_key(self, api_key_file: Union[str, None] = None) -> str:
        '''Get the API key from the config file'''
        if api_key_file is None:
            api_key_file = os.path.join(self.config_data['ConfigDirectory'], 'openai-key.ini')
        assert os.path.exists(api_key_file), \
            f"API key file ({api_key_file}) not found"
        config = configparser.ConfigParser()
        config.read(api_key_file, encoding='utf-8-sig')
        openai_key = config['openai']['api_key']
        if openai_key is None:
            raise ValueError("OpenAI API key not found in config file")
        if openai_key[0] == '"' or openai_key[0] == "'":
            openai_key = openai_key[1:]
        if openai_key[-1] == '"' or openai_key[-1] == "'":
            openai_key = openai_key[:-1]
        return openai_key

    def run(self):
        while True:
            # Need UPI information about the database
            #

            # Get query from user
            user_query = self.get_query()

            # Log the query
            # self.logging_service.log_query(user_query)

            # Process the query
            parsed_query = self.nl_parser.parse(query=user_query)
            ic(parsed_query)
            exit(0)
            translated_query = self.query_translator.translate(
                parsed_query,
                selected_md_attributes=None,
                additional_notes=None,
                n_truth=1,
                llm_connector=self.llm_connector,
            )

            # Execute the query
            raw_results = self.query_executor.execute(translated_query, self.db_config)

            # Analyze and refine results
            analyzed_results = self.metadata_analyzer.analyze(raw_results)
            facets = self.facet_generator.generate(analyzed_results)
            ranked_results = self.result_ranker.rank(analyzed_results)

            # Display results to user
            self.display_results(ranked_results, facets)

            # Update query history
            self.query_history.add(user_query, ranked_results)

            # Check if user wants to continue
            if not self.continue_session():
                break

        # self.logging_service.log_session_end()

    def get_query(self) -> str:
        '''Get a query from the user.'''
        return input(self.prompt).strip()

    def display_results(self, results: list[dict[str, Any]], facets: list[str]) -> None:
        """
        Displays the search results and suggested facets to the user.

        Args:
            results (List[Dict[str, Any]]): The ranked search results
            facets (List[str]): Suggested facets for query refinement
        """
        if not results:
            print("No results found.")
            return

        print("\nSearch Results:")
        ic(len(results))
        if len(results) < 10:
            for i, result in enumerate(results, 1):
                doc = result['original']['result']
                ic(doc['Record']['Attributes']['Path'])

        if facets:
            print("Suggested refinements:")
            for facet in facets:
                print(f"- {facet}")

    def continue_session(self) -> bool:
        '''Check if the user wants to continue the session.'''
        return input('Do you want to continue? [Y/N] ').strip().lower() in ['y', 'yes']

    def build_schema_table(self):
        '''Build the schema table.'''
        schema = {}
        for collection in self.db_config.db.collections():
            name = collection['name']
            if name.startswith('_'):
                continue
            doc = self.db_config.db.collection(name)
            properties = doc.properties()
            schema[name] = properties['schema']
        return schema


def main():
    '''A CLI based query tool for Indaleko.'''
    ic('Starting Indaleko Query CLI')
    cli = IndalekoQueryCLI()
    cli.run()


if __name__ == '__main__':
    main()
