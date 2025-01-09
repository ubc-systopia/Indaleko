'''
Script to run the metadata generator tool
Author: Pearl Park

required files: /data_generator/dg_config.json /config/openai-key.ini

'''

import os, shutil, sys
import argparse
import configparser
import json 
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_generator.s1_metadata_generator import Dataset_Generator
from data_generator.s2_store_test_Indaleko import MetadataStorer
from data_generator.s3_translate_query import QueryExtractor
from data_generator.s4_get_precision_and_recall import ResultCalculator
from IndalekoSearch import IndalekoSearch
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoSchema import IndalekoSchema

from IndalekoCollections import IndalekoCollections
from query.utils.logging_service import LoggingService
from query import CLI, NLParser, AQLTranslator, QueryHistory, AQLExecutor, MetadataAnalyzer, FacetGenerator, ResultRanker, OpenAIConnector, LoggingService
from data_generator.s5_log_result import ResultLogger

class Validator():
    '''This is the class for performing the validation for Indaleko'''
    def __init__(self) -> None:
        self.config = self.get_config_file()
        self.logger = ResultLogger()

        self.db_config = IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config['database']['database'],reset = True)
        self.db_config.collections = IndalekoCollections()
        schema_table = IndalekoSchema.build_from_db()

        if hasattr(schema_table, 'schema'):
            self.db_info = schema_table.schema
        else:
            raise ValueError("Schema table not found")

        self.query_extractor = QueryExtractor()
        self.data_generator = Dataset_Generator(self.config)
        self.data_storer = MetadataStorer()
        self.result_calculator = ResultCalculator()
        self.search_tool = IndalekoSearch()
        self.openai_key = self.search_tool.get_api_key()

        self.llm_connector = OpenAIConnector(api_key=self.openai_key)

        self.nl_parser = NLParser()
        self.query_translator = AQLTranslator()
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()
        self.result_dictionary = {}

    # parse the configuration file 
    def parse_config_json(self, config_path):
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config

    # get the config file in the form of a dictionary 
    def get_config_file(self) -> dict:
        config_file = 'data_generator/dg_config.json'
        assert os.path.exists(config_file), f'Config file path "{config_file}" not found'
        config = self.parse_config_json(config_file)
        return config
    
    def add_result(self, key: str, value:str):
        self.result_dictionary[key] = value

    # this is the main run function for the metadata generator 
    def run(self) -> None:
        query = self.config["query"]
        n_truth_md = self.config["n_matching_queries"]
        n_total_md = self.config["n_metadata_records"]

        self.logger.log_config(self.config)
        self.add_result("query", query)
        self.add_result("n_total_truth", n_truth_md)
        self.add_result("n_metadata", n_total_md)

        # extract the query from the config file into a dictionary
        self.logger.log_process("extracting query from config...")
        selected_md_attributes = self.query_extractor.extract(query = query, llm_connector = self.llm_connector)

        # selected_md_attributes = {
        #                             "Posix": {
        #                                 "file.name": {
        #                                     "extension": ".pdf"
        #                                 }
        #                             }, "Activity" :{},
        #                             "Semantic":{}
        #                         }
        self.data_generator.set_selected_md_attributes(selected_md_attributes)

        self.logger.log_query(query, selected_md_attributes)
        # generate the metadata dataset

        # self.logger.log_process("generating record and activity metadata...")
        generation_time, results = self.search_tool.time_operation(self.data_generator.generate_metadata_dataset)
        all_records_md, all_activity_md = results[0], results[1]
        ic(f"Generation time: {generation_time}")
        self.logger.log_process_result("metadata_generation_time", generation_time)
        

        # # # store the metadata dataset
        self.logger.log_process("storing record metadata...")
        record_storage_time = self.search_tool.time_operation(self.data_storer.add_records_to_collection, collections=self.db_config.collections, collection_name="Objects", records=all_records_md)
        ic(f"Storing time for record metadata: {record_storage_time}")
        self.logger.log_process_result("record_storage_time", generation_time)


        activity_storage_time = self.search_tool.time_operation(self.data_storer.add_ac_to_collection, collections=self.db_config.collections, collection_name="ActivityContext", records=all_activity_md)
        self.logger.log_process("storing activity context...")
        ic(f"Storing time for activity metadata: {activity_storage_time}")
        self.logger.log_process_result("stored activity context", generation_time)

        # run indaleko search 
        # adapted from IndalekoSearch.py
        #parser has yet to be implemented
        parse_query_time, parsed_query = self.search_tool.time_operation(self.nl_parser.parse, query=query, schema=self.db_info)
        self.logger.log_process("parsing query...")
        ic(f"Parsed query: {parsed_query}")
        ic(f"Parse time: {parse_query_time}")

        self.logger.log_process_result("parsed_query", parse_query_time, parsed_query)

        self.logger.log_process("translating query to aql...")
        translate_query_time, translated_query = \
            self.search_tool.time_operation(self.query_translator.translate, parsed_query=parsed_query, llm_connector=self.llm_connector)
       
        ic(f"Translated query: {translated_query}")
        ic(f"Translation time: {translate_query_time}")
        self.logger.log_process_result("translated_aql", translate_query_time, translated_query)

        # translated_query = 'FOR obj IN Objects FILTER obj.PosixFileAttributes != null AND obj.Record.Timestamp >= DATE_SUBTRACT(DATE_TRUNC(DATE_NOW(), "day"), 1, "day") AND obj.Record.Timestamp < DATE_TRUNC(DATE_NOW(), "day") AND obj.Label != null AND CONTAINS(obj.Label, "essay", true) AND LIKE(obj.URI, "%.pdf") RETURN obj'
        # translated_query = 'FOR obj IN Objects FILTER obj.Label LIKE "%.pdf" AND DATE_ISO8601(obj.Record.Attributes.st_birthtime * 1000) >= DATE_SUBTRACT(DATE_NOW(), 1, "day") AND DATE_ISO8601(obj.Record.Attributes.st_birthtime * 1000) < DATE_NOW() RETURN obj'
        # translated_query = 'FOR obj IN Objects FILTER obj.Record.Attributes.Name LIKE "%.pdf" RETURN obj'

        # Execute the query
        self.logger.log_process("running search with translated aql query...")
        execute_time, raw_results = self.search_tool.time_operation(
            self.query_executor.execute,
            query=translated_query,
            data_connector=self.db_config
        )

        ic(self.db_config.db.aql.execute(translated_query))
        result = self.db_config.db.aql.execute(translated_query)
        ic(self.query_executor.format_results(result))


        self.logger.log_result(query, len(raw_results), execute_time)

        ic(f"Raw results: {raw_results}")
        self.logger.log_process("calculating precision and recall")
        ic(f"Execution time: {execute_time}")
        
        calculation_time, calculation_result = self.search_tool.time_operation(self.result_calculator.run, raw_results=raw_results, theoretical_truth_n=n_truth_md)
        precision = calculation_result[0]
        recall = calculation_result[1]

        self.logger.log_process_result("calculated precision and recall", calculation_time, f"precision: {precision}, recall: {recall}")

        self.add_result("actual_n_total_truth", 0)
        self.add_result("actual_n_metadata", len(raw_results))
        self.add_result("precision", precision)
        self.add_result("recall", recall)
        

        ic(selected_md_attributes)


def main() -> None:
    '''Main function for the validator tool'''
    validator_tool = Validator()
    # with open('./data_generator/db_info.txt', 'w') as f:
    #     # Write the value of db_info to the file
    #     f.write(str(validator_tool.db_info))
    total_epoch, no_output = validator_tool.search_tool.time_operation(validator_tool.run)
    ic(total_epoch)
    validator_tool.logger.log_final_result(total_epoch, validator_tool.result_dictionary)
    

if __name__ == '__main__':
    main()
