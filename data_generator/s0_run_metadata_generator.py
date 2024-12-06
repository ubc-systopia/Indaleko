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
from datetime import datetime

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
from db.db_config import IndalekoDBConfig
from deprecated.IndalekoSchema import IndalekoSchema

from db.i_collections import IndalekoCollections
from query import NLParser, AQLTranslator, QueryHistory, AQLExecutor, OpenAIConnector
from data_generator.s5_log_result import ResultLogger
from pathlib import Path



class Validator():
    '''This is the class for performing the validation for Indaleko'''
    def __init__(self) -> None:
        self.file_path = "./data_generator/results/"
        api_path = './config/openai-key.ini'
        path = Path(self.file_path)
        if path.exists():
            shutil.rmtree(path)

        path.mkdir(parents=True, exist_ok=True)

        self.config = self.get_config_file('data_generator/dg_config.json')
        self.logger = ResultLogger(result_path=self.file_path )
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
        self.openai_key = self.get_api_key(api_path)

        self.llm_connector = OpenAIConnector(api_key=self.openai_key)
        self.nl_parser = NLParser()
        self.query_translator = AQLTranslator()
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()
        self.result_dictionary = {}
        self.schema = self.read_json('data_generator/schema.json')
    
    def time_operation(self, operation, **kwargs) -> datetime:
        '''Given a function, return the time and results of the operation'''
        ic(type(operation))
        start_time = datetime.now()
        results = operation(**kwargs)
        end_time = datetime.now()
        operation_time = end_time - start_time
        return str(operation_time), results

    def get_api_key(self, api_key_file) -> str:
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

    # parse the configuration file 
    def parse_config_json(self, config_path):
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config

    # get the config file in the form of a dictionary 
    def get_config_file(self, config_file) -> dict:
        assert os.path.exists(config_file), f'Config file path "{config_file}" not found'
        config = self.parse_config_json(config_file)
        return config
    
    def add_result_to_dict(self, key: str, value:str):
        '''
        adds the results to the result dictionary
        '''
        self.result_dictionary[key] = value


    # this is the main run function for the metadata generator 
    def run(self) -> None:
        query = self.config["query"]
        n_truth_md = self.config["n_matching_queries"]
        n_total_md = self.config["n_metadata_records"]

        self.logger.log_config(self.config)
        self.add_result_to_dict("query", query)
        self.add_result_to_dict("n_total_truth", n_truth_md)
        self.add_result_to_dict("n_metadata", n_total_md)

        # extract the query from the config file into a dictionary
        self.logger.log_process("extracting query from config...")
        selected_md_attributes = self.query_extractor.extract(query = query, llm_connector = self.llm_connector)
        #selected_md_attributes = {'Posix': {'timestamps': {'specific': {'modified': {'starttime': '2019-10-31T00:00:00', 'endtime': '2019-11-13T23:59:59', 'command': 'range'}}}}, 'Semantic': {}, "Activity": {"geo_location": {"location": "Vancouver","command": "within", 'km':8}}}

        self.add_result_to_dict("selected_md_attributes", selected_md_attributes)

        #generate the metadata dataset
        self.data_generator.set_selected_md_attributes(selected_md_attributes)
        self.logger.log_query(query, selected_md_attributes)

        self.logger.log_process("generating record and activity metadata...")
        generation_time, results = self.time_operation(self.data_generator.generate_metadata_dataset)
        all_records_md, all_activity_md, all_machine_config_md, stats = results[0], results[1], results[2], results[3]
        ic(f"Generation time: {generation_time}")
        self.logger.log_process_result("metadata_generation_time", generation_time)
        self.add_result_to_dict("metadata_stats", stats)
        

        # # # store the metadata dataset
        self.logger.log_process("storing record metadata...")
        record_storage_time = self.time_operation(self.data_storer.add_records_to_collection, collections=self.db_config.collections, collection_name="Objects", records=all_records_md)
        ic(f"Storing time for record metadata: {record_storage_time}")
        self.logger.log_process_result("stored record:", record_storage_time)


        activity_storage_time = self.time_operation(self.data_storer.add_to_collection_key, collections=self.db_config.collections, collection_name="ActivityContext", records=all_activity_md)
        self.logger.log_process("storing activity context...")
        ic(f"Storing time for activity metadata: {activity_storage_time}")
        self.logger.log_process_result("stored activity context:", activity_storage_time)

        # # # store the machine config metadata dataset
        self.logger.log_process("storing machine config metadata...")
        machine_config_storage_time = self.time_operation(self.data_storer.add_to_collection_key, collections=self.db_config.collections, collection_name="MachineConfig", records=all_machine_config_md)
        ic(f"Storing time for machine config metadata: {machine_config_storage_time}")
        self.logger.log_process_result("stored machine config:", machine_config_storage_time)


        # run indaleko search 
        # adapted from IndalekoSearch.py
        # parser has yet to be implemented
        parse_query_time, parsed_query = self.time_operation(self.nl_parser.parse, query=query, schema=self.schema)
        self.logger.log_process("parsing query...")
        ic(f"Parse time: {parse_query_time}")

        self.logger.log_process_result("parsed_query", parse_query_time)

        self.logger.log_process("translating query to aql...")

        geo_coordinates = str(self.data_generator.saved_geo_loc)
        ic(geo_coordinates)
        translate_query_time, translated_query = self.time_operation(self.query_translator.translate, parsed_query=parsed_query, selected_md_attributes=selected_md_attributes, additional_notes=geo_coordinates, llm_connector=self.llm_connector)
       
        ic(f"Translated query: {translated_query}")
        ic(f"Translation time: {translate_query_time}")
        self.logger.log_process_result("translated_aql", translate_query_time, translated_query)
        
        #working queries:
        # translated_query = 'FOR obj IN Objects FILTER obj.PosixFileAttributes != null AND obj.Record.Timestamp >= DATE_SUBTRACT(DATE_TRUNC(DATE_NOW(), "day"), 1, "day") AND obj.Record.Timestamp < DATE_TRUNC(DATE_NOW(), "day") AND obj.Label != null AND CONTAINS(obj.Label, "essay", true) AND LIKE(obj.URI, "%.pdf") RETURN obj'
        # translated_query = 'FOR obj IN Objects FILTER obj.Label LIKE "%.pdf" AND DATE_ISO8601(obj.Record.Attributes.st_birthtime * 1000) >= DATE_SUBTRACT(DATE_NOW(), 1, "day") AND DATE_ISO8601(obj.Record.Attributes.st_birthtime * 1000) < DATE_NOW() RETURN obj'
        # translated_query = 'FOR obj IN Objects FILTER obj.Record.Attributes.Name LIKE "%.pdf" RETURN obj'
        # translated_query = "FOR context IN ActivityContext FILTER context.SemanticAttributes[*].Identifier.Label == 'Longitude' AND context.SemanticAttributes[*].Data == 140 AND context.SemanticAttributes[*].Identifier.Label == 'Latitude' AND context.SemanticAttributes[*].Data == 49.99 AND context.Timestamp >= '2019-01-13T00:00:00' AND context.Timestamp <= '2019-10-31T00:00:00' RETURN context"
        # translated_query ="FOR record IN ActivityContext FILTER TO_NUMBER(record.Record.Attributes.st_mtime) >= 1547395200 && TO_NUMBER(record.Record.Attributes.st_mtime) <= 1572480000 RETURN record"
        #translated_query="FOR record IN ActivityContext FOR loc IN record.SemanticAttributes FILTER loc.Identifier.Label == 'Longitude' && TO_NUMBER(loc.Data) == -123.113952 RETURN record"
        #translated_query = "FOR record IN ActivityContext FILTER TO_NUMBER(record.Record.Attributes.st_mtime) >= 1572643200 && TO_NUMBER(record.Record.Attributes.st_mtime) <= 1573670399 FILTER (FOR attr IN record.SemanticAttributes FILTER attr.Identifier.Label == 'Longitude' && TO_NUMBER(attr.Data) == -123.113952 RETURN attr)[0] != null FILTER (FOR attr IN record.SemanticAttributes FILTER attr.Identifier.Label == 'Latitude' && TO_NUMBER(attr.Data) == 49.2608724 RETURN attr)[0] != null RETURN record"
        #translated_query = "FOR record IN ActivityContext FILTER TO_NUMBER(record.Record.Attributes.st_mtime) >= 1572566400 AND TO_NUMBER(record.Record.Attributes.st_mtime) <= 1573689599 LET longitude = FIRST(FOR attr IN record.SemanticAttributes FILTER attr.Identifier.Label == 'Longitude' RETURN attr.Data) LET latitude = FIRST(FOR attr IN record.SemanticAttributes FILTER attr.Identifier.Label == 'Latitude' RETURN attr.Data) FILTER longitude >= -123.113952 - 0.072 && longitude <= -123.113952 + 0.072 FILTER latitude >= 49.2608724 - 0.072 && latitude <= 49.2608724 + 0.072 RETURN record"
        self.add_result_to_dict("aql_query", translated_query)

        
        # Execute the query
        self.logger.log_process("running search with translated aql query...")
        execute_time, raw_results = self.time_operation(
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
        
        calculation_time, calculation_result = self.time_operation(self.result_calculator.run, raw_results=raw_results, theoretical_truth_n=n_truth_md)
        precision = calculation_result[0]
        recall = calculation_result[1]

        self.logger.log_process_result("calculated precision and recall", calculation_time, f"precision: {precision}, recall: {recall}")
        self.add_result_to_dict("uuid_returned", self.result_calculator.selected_uuid)
        self.add_result_to_dict("actual_n_total_truth", 0)
        self.add_result_to_dict("actual_n_metadata", len(raw_results))
        self.add_result_to_dict("precision", precision)
        self.add_result_to_dict("recall", recall)

        self.save_as_json("returned_metadata", self.result_calculator.selected_metadata)
        self.save_as_json("Indaleko_search_result", raw_results)
        

        ic(selected_md_attributes)

    def read_json(self, json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
        return data


    def save_as_json(self, title, result_dict):
        with open(self.file_path  + title +'.json', 'w') as file:
            json.dump(result_dict, file, indent=4)

def main() -> None:
    '''Main function for the validator tool'''
    validator_tool = Validator()

    total_epoch, no_output = validator_tool.time_operation(validator_tool.run)
    validator_tool.logger.log_final_result(total_epoch, validator_tool.result_dictionary)
    

if __name__ == '__main__':
    main()
