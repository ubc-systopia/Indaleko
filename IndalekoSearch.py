'''
This module is used to provide a simple conversational interface for the
Indaleko search tool.

Project Indaleko
Copyright (C) 2024 Tony Mason

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
import argparse
import configparser
import os

from datetime import datetime
from icecream import ic

from IndalekoDBConfig import IndalekoDBConfig
from IndalekoSchema import IndalekoSchema

from search.interface.cli import CLI
from search.query_processing.nl_parser import NLParser
from search.query_processing.query_translator.aql_translator import AQLTranslator
from search.query_processing.query_history import QueryHistory
from search.search_execution.query_executor.aql_executor import AQLExecutor
from search.result_analysis.metadata_analyzer import MetadataAnalyzer
from search.result_analysis.facet_generator import FacetGenerator
from search.result_analysis.result_ranker import ResultRanker
from search.utils.llm_connector.openai_connector import OpenAIConnector
from search.utils.logging_service import LoggingService
class IndalekoSearch():
    '''
    This is a class object for performing specific searches in the Indaleko database.
    '''

    def __init__(self, **kwargs):
        '''Initialize a new instance of the IndalekoSearch class object.'''
        for key, value in kwargs.items():
            setattr(self, key, value)
        if not hasattr(self, 'db_config'):
            self.db_config = IndalekoDBConfig()
        schema_table = IndalekoSchema.build_from_db()
        if hasattr(schema_table, 'schema'):
            self.db_info = schema_table.schema
        else:
            raise ValueError("Schema table not found")
        self.interface = CLI()
        self.nl_parser = NLParser()
        self.query_translator = AQLTranslator()
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()
        self.metadata_analyzer = MetadataAnalyzer()
        self.facet_generator = FacetGenerator()
        self.result_ranker = ResultRanker()
        self.openai_key = self.get_api_key()
        self.llm_connector = OpenAIConnector(api_key=self.openai_key)

        ic('IndalekoSearch initialized, Database connection instantiated.')


    @staticmethod
    def get_api_key(api_key_file : str = 'config/openai-key.ini') -> str:
        '''Get the API key from the config file'''
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

    @staticmethod
    def time_operation(operation, **kwargs) -> datetime:
        '''Given a function, return the time and results of the operation'''
        ic(type(operation))
        start_time = datetime.now()
        results = operation(**kwargs)
        end_time = datetime.now()
        operation_time = end_time - start_time
        return str(operation_time), results


    def run(self, logging_service : LoggingService = None) -> None:
        '''Main function for the search tool.'''
        while True:
            # Get query from user
            user_query_time, user_query = self.time_operation(self.interface.get_query)
            ic(f"User query: {user_query}")
            ic(f"Query time: {user_query_time}")

            # Log the query
            # self.logging_service.log_query(user_query)

            # Process the query
            parse_query_time, parsed_query = self.time_operation(self.nl_parser.parse, query=user_query, schema=self.db_info)
            ic(f"Parsed query: {parsed_query}")
            ic(f"Parse time: {parse_query_time}")
            translate_query_time, translated_query = \
                self.time_operation(self.query_translator.translate, parsed_query=parsed_query, llm_connector=self.llm_connector)
            ic(f"Translated query: {translated_query}")
            ic(f"Translation time: {translate_query_time}")
            # Execute the query
            execute_time, raw_results = self.time_operation(
                self.query_executor.execute,
                query=translated_query,
                data_connector=self.db_config
            )
            #ic(f"Raw results: {raw_results}")
            ic(f"Execution time: {execute_time}")

            # Analyze and refine results
            analyzed_results = self.metadata_analyzer.analyze(raw_results)
            facets = self.facet_generator.generate(analyzed_results)
            ranked_results = self.result_ranker.rank(analyzed_results)

            # Display results to user
            self.interface.display_results(ranked_results, facets)

            # Update query history
            self.query_history.add(user_query, ranked_results)

            # Check if user wants to continue
            if not self.interface.continue_session():
                break



def main() -> None:
    '''Main function for the IndalekoSearch module.'''
    parser = argparse.ArgumentParser(description='Indaleko Search Tool')
    args = parser.parse_args()
    search_tool = IndalekoSearch(args=args)
    search_tool.run()

if __name__ == '__main__':
    main()
