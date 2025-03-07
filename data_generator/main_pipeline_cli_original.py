'''
Main script to run the validation tool
Author: Pearl Park
required files: /data_generator/dg_config.json /config/openai-key.ini
'''
import os, shutil, sys
import configparser
import json 
from icecream import ic
from datetime import datetime, timezone
import argparse

import copy
import click
if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_models.location_data_model import BaseLocationDataModel
from data_models.named_entity import IndalekoNamedEntityDataModel, NamedEntityCollection, example_entities, IndalekoNamedEntityType
from db.i_collections import IndalekoDBCollections
from query.cli import IndalekoQueryCLI
from data_generator.scripts.s1_metadata_generator import Dataset_Generator
from data_generator.scripts.s2_store_test_Indaleko import MetadataStorer
from data_generator.scripts.s3_translate_query import QueryExtractor
from data_generator.scripts.s4_translate_AQL import AQLQueryConverter
from data_generator.scripts.s5_get_precision_and_recall import ResultCalculator
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections
from query import NLParser, AQLExecutor, OpenAIConnector
from data_generator.scripts.s6_log_result import ResultLogger
from pathlib import Path
from typing import Any
import subprocess
from collections import namedtuple
from data_generator.scripts.s5_get_precision_and_recall import Results

MetadataResults = namedtuple('MetadataResults', [
    'all_records_md', 'all_geo_activity_md', 'all_temp_activity_md', 
    'all_music_activity_md', 'all_machine_config_md', 'all_semantics_md', 'stats'
])

from db.db_collection_metadata import IndalekoDBCollectionsMetadata

class Validator():
    """
    This is the class for performing the validation for Indaleko
    """
    def __init__(self, args) -> None:
        self.file_path = "./data_generator/results/"
        self.stored_file_path = self.file_path + "stored_metadata/"
        self.config_path =  './data_generator/config/'
        api_path = './config/openai-key.ini'

        path = Path(self.file_path)
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

        metadata_path = Path(self.stored_file_path)
        metadata_path.mkdir(parents=True, exist_ok=True)

        self.config = self.get_config_file(self.config_path + 'dg_config.json')
        self.db_schema = self.read_json(self.config_path + 'schema.json')
        self.logger = ResultLogger(result_path=self.file_path)
        self.db_config = IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config['database']['database'])

        if not args.no_reset:
            try:
                subprocess.run(["python3", "./db/db_config.py", "reset"], check=True)
                subprocess.run(["python3", "./platforms/mac/machine_config.py", "--add"], check=True)
                subprocess.run(["python3", "./storage/recorders/local/mac/recorder.py", "--arangoimport"], check=True)
            except subprocess.CalledProcessError as e:
                raise e

        self.db_config.collections = IndalekoCollections()
        self.query_extractor = QueryExtractor()
        self.data_generator = Dataset_Generator(self.config)
        self.data_storer = MetadataStorer()
        self.result_calculator = ResultCalculator()

        self.openai_key = self.get_api_key(api_path)
        self.llm_connector = OpenAIConnector(api_key=self.openai_key)
        self.query_executor = AQLExecutor()
        self.insert_ner_metadata_test()
        self.collections_md = IndalekoDBCollectionsMetadata()
        self.cli = IndalekoQueryCLI()


        self.dynamic_activity_providers = {}
        self.result_dictionary = {}
        # self.schema = self.read_json('data_generator/config/schema.json')
    
    def time_operation(self, operation, **kwargs) -> tuple[str, Any]:
        """
        Given a function, return the time and results of the operation
        Args:
            operation (Any): The function or operation to time
            **kwargs (Any): The arguments required to run the function
        Returns:
            tuple[str, Any]: The operation time and any outputs returned 
        """
        start_time = datetime.now()
        results = operation(**kwargs)
        end_time = datetime.now()
        operation_time = end_time - start_time
        return str(operation_time), results

    def get_api_key(self, api_key_file: str) -> str:
        """
        Given the path to an API key file in the config dir, return the api key
        Args:
            api_key_file (str): The path to the api key file
        Returns:
            str: The API key
        """
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

    def get_config_file(self, config_path) -> dict[str]:
        """
        Given the path to a config file, parse the configuration file in the form of a dictionary
        Args:
            config_path (str): The path to the config file
        Returns:
            Dict[str]: The config file
        """
        assert os.path.exists(config_path), f'Config file path "{config_path}" not found'
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config
    
    def add_result_to_dict(self, key: str, value: str) -> None:
        """
        Adds the results to the result dictionary
        Args:
            key (str): The key to add to the dictionary
            value (str): The value to add to the dictionary
        """
        self.result_dictionary[key] = value
    
    def insert_ner_metadata_test(self) -> None:
        ner_example = IndalekoNamedEntityDataModel(
        name="Paris",
        category=IndalekoNamedEntityType.location,
        description="Capital of France",
        gis_location=BaseLocationDataModel(
            source='defined',
            timestamp=datetime.now(timezone.utc),
            latitude=48.8566,
            longitude=2.3522,
            )
        )
        ner_example = [json.loads(ner_example.json())]
        self._store_general_metadata("NamedEntities", ner_example, key_required = False)

    def run(self) -> None:
        """
        Run function for the validator tool
        """        
        self.process_config()

        query = self.config["query"]
        self.add_result_to_dict("query", query)

        original_data_number = self.get_files_collections()
        self.add_result_to_dict("db_number", original_data_number)
       
        # GENERATE DICTIONARY FOR GENERATOR:   
        intial_selection = click.prompt("Create new dictionary (1) or use existing (0)", type=int)
        if intial_selection == 1:
            selected_md_attributes = self.generate_dictionary(query)

        elif intial_selection == 0:
            selected_md_attributes = self.read_json(self.config_path + "dictionary.json")  
        else:
            print("Invalid input. Exiting.")
            sys.exit()

        self.add_result_to_dict("selected_md_attributes", selected_md_attributes)

        # GENERATE METADATA DATASET:   
        copy_selected_md = copy.deepcopy(selected_md_attributes)
        results_obj = self.generate_dataset(copy_selected_md)

        # STORE ALL METADATA DATASET:
        self.store_all_metadata(results_obj)

        #PREPARE FOR QUERY GENERATION:
        translated_query = self.prepare_query_generation(copy_selected_md)

        # GENERATE/SUBMIT AQL QUERY:
        query_info = "query_info.json"
        aql_text = "AQL_query.aql"
        self.query_translator = AQLQueryConverter(self.db_schema, self.collections_md)

        translate_query = click.prompt("Ready for AQL generation, please (1) to generate a new AQL or (0) to use existing", type=int)
        if translate_query == 0:
            aql = self.read_aql(self.config_path + aql_text)
            
        elif translate_query == 1:
            aql = self.generate_query(translated_query)
        
        self.write_as_json(self.config_path, query_info, translated_query)
        self.write_as_aql(self.config_path, aql_text, aql)

        # ASK FOR AQL QUERY REVIEW:
        aql_selection = click.prompt(
            "Please review the AQL_query.aql file and query_info.json and make any necessary changes. \
            \n Type (1) to continue, or any number to exit", 
            type=int)

        if aql_selection != 1:
            sys.exit()
        
        final_query = self.read_aql(self.config_path + aql_text)
        self.add_result_to_dict("aql_query", final_query)

        # RUN INDALEKO SEARCH
        raw_results = self.run_search(final_query)
        self.add_result_to_dict("metadata_number", len(raw_results)) 

        updated_data_number = self.get_files_collections()
        self.add_result_to_dict("db_number_update", updated_data_number)

        # CALCULATE PRECISION, RECALL AND OTHER STATISTICS
        self.generate_stats(raw_results)
        self.write_as_json(self.file_path, "Indaleko_search_result.json", raw_results)
        self.logger.log_process("DONE -- please check /data_generator/results/validator_result.log for the full results")
    
    def generate_query(self, query_attributes: dict[str, Any]) -> str:
        """
        Generate the AQL query:
        """
        translate_query_time, translated_query = self.time_operation(
            self.query_translator.translate, 
            selected_md_attributes=query_attributes["converted_selected_md_attributes"], 
            collections=query_attributes["providers"],
            geo_coordinates=query_attributes["geo_coords"], 
            n_truth = self.n_truth_md,
            llm_connector=self.llm_connector)
        self.logger.log_process_result("translated_aql", translate_query_time, translated_query)
        return translated_query

    def generate_dictionary(self, query:str):
        """
        Generate the dictionary from scratch
        """
        json_name = "dictionary.json"
        self.logger.log_process("building dictionary...")
        self.nl_parser = NLParser(self.llm_connector, self.collections_md)
        ner_metadata = self.nl_parser._extract_entities(query)
        entities = self.cli.map_entities(ner_metadata)

        selected_md_attributes = self.query_extractor.extract(query = query, named_entities = entities, llm_connector = self.llm_connector)
        self.logger.log_process_result("selected_md_attributes", selected_md_attributes)
        self.write_as_json(self.config_path, json_name, selected_md_attributes)
        dictionary_selection = click.prompt("Dictionary ready for evaluation, please type 1 to continue, otherwise type 0 to exit", type=int)
        if dictionary_selection != 1:
            sys.exit()
        selected_md_attributes = self.read_json(self.config_path + json_name)    
        return selected_md_attributes

    def process_config(self):
        """
        Process the config file:
        """
        self.n_truth_md = self.config["n_matching_queries"]
        self.n_total_md = self.config["n_metadata_records"]

        self.logger.log_config(self.config)
        self.add_result_to_dict("n_total_truth", self.n_truth_md)
        self.add_result_to_dict("n_metadata", self.n_total_md)

    def _store_general_metadata(self, collection_name, data, key_required = True):
        """
        Helper function to store general metadata like for objects, semantic, machineconfig
        """
        self.logger.log_process(f"storing {collection_name} metadata...")
        record_storage_time = self.time_operation(self.data_storer.add_records_to_collection, 
                                                    collections=self.db_config.collections, 
                                                    collection_name=collection_name, 
                                                    records=data, 
                                                    key_required = key_required)
        ic(f"Storing time for record metadata: {record_storage_time}")
        self.logger.log_process_result(f"stored {collection_name} :", record_storage_time[0])

    def _store_activity_metadata(self, collection_name, data):
        """
        Helper function to store activity metadata like for music, temperature and geographical location
        """
        registrator, collection = self.data_storer.register_activity_provider(collection_name + " Collector")
        self.dynamic_activity_providers[collection_name]=registrator.get_activity_collection_name()

        storage_time = self.time_operation(self.data_storer.add_records_with_activity_provider, collection=collection, activity_contexts=data)
        self.logger.log_process(f"storing {collection_name} activity context...")
        ic(f"Storing time for {collection_name} activity metadata: {storage_time}")
        self.logger.log_process_result(f"stored {collection_name} data:", storage_time[0])

    def store_all_metadata(self, results_obj: MetadataResults):
        """
        Store all metadata in their appropriate collections withing the DB:
        """
        self._store_general_metadata("Objects", results_obj.all_records_md)
        self._store_general_metadata("MachineConfig", results_obj.all_machine_config_md)
        self._store_general_metadata("SemanticData", results_obj.all_semantics_md)

        self._store_activity_metadata("GeoActivity", results_obj.all_geo_activity_md)
        self._store_activity_metadata("MusicActivity", results_obj.all_music_activity_md)
        self._store_activity_metadata("TempActivity", results_obj.all_temp_activity_md)

    def generate_dataset(self, selected_md_attributes):
        """
        Generate the metadata dataset:
        """
        self.logger.log_process("generating record and activity metadata...")
        generation_time, results = self.time_operation(self.data_generator.generate_metadata_dataset, 
                                                        selected_md_attributes=selected_md_attributes,
                                                        save_files = True,
                                                        path = self.stored_file_path)
        self.logger.log_process_result("metadata_generation_time", generation_time)
        results_obj = MetadataResults(*results)
        self.add_result_to_dict("metadata_stats", results_obj.stats)

        return results_obj

    def prepare_query_generation(self, copy_selected_md):
        """
        Prepare for the AQL translation:
        """
        translated_query = {}

        self.logger.log_process("preparing AQL translation...")
        self.collections_md = IndalekoDBCollectionsMetadata(self.db_config)
        self.nl_parser = NLParser(self.llm_connector, self.collections_md)

        # Retrieve the geo coordinates for the AQL translator:
        translated_query["geo_coords"] = str(self.data_generator.geo_activity_generator.get_saved_geolocation())
        self.add_result_to_dict("geo_coords", translated_query["geo_coords"])
       
        # Save dynamic providers:
        translated_query["providers"] = self.dynamic_activity_providers

        # Convert the time to posix timestamps for consistent AQL translation results:
        self.data_generator.posix_generator.preprocess_dictionary_timestamps(True)
        copy_selected_md["Posix"] = self.data_generator.posix_generator.selected_md
        translated_query["converted_selected_md_attributes"] = copy_selected_md

        self.logger.log_process("translating query to aql...")
        self.logger.log_process_result("converted_selected_md_attributes", translated_query["converted_selected_md_attributes"])
        self.add_result_to_dict("converted_selected_md_attributes", translated_query["converted_selected_md_attributes"])
       
        return translated_query


    def generate_stats(self, raw_results: dict[str,Any]):
        """
        Generates necessary stats:
        """
        self.logger.log_process("calculating precision and recall")
        calculation_time, calculation_result = self.time_operation(self.result_calculator.run, 
                                                                    truth_list = self.data_generator.truth_list, 
                                                                    filler_list = self.data_generator.filler_list, 
                                                                    raw_results = raw_results, 
                                                                    n_truth_md = self.n_truth_md)
        results: Results = calculation_result
        self.add_result_to_dict("results", results)
        # self.add_result_to_dict("uuid_returned", results.returned_uuid)
        self.logger.log_process("precision and recall calculated")
        self.logger.log_process_result("calculated precision and recall", calculation_time, f"precision: {results.precision}, recall: {results.recall}")
    
    def run_search(self, query: str):
        """
        Run Indaleko Search:
        """
        self.logger.log_process("running search with translated aql query...")
        execute_time, raw_results = self.time_operation(
            self.query_executor.execute,
            query=query,
            data_connector=self.db_config
        )
        self.logger.log_process_result("Indaleko search completed", execute_time)
        return raw_results

    def get_files_collections(self): 
        """
        Get the count for data already stored in the DB:
        """
        total = 0
        for collection in self.db_config.db.collections():
            name = collection["name"]
            ic(name)
            collection_count = self.db_config.db.aql.execute(f"""
                RETURN COLLECTION_COUNT('{name}')
            """).next()
            ic(collection_count)
            total += collection_count
        return total

    def read_aql(self, aql_path):
        """
        Read AQL with path specified:
        """
        with open(aql_path, "r") as f:
            return f.read()
    
    def read_json(self, json_path):
        """
        Read JSON with path specified:
        """
        with open(json_path, 'r') as file:
            data = json.load(file)
        return data

    def write_as_aql(self, path, title, aql_query):
        """
        Write AQL with path specified:
        """
        with open(path+title, "w") as file:
            file.write(aql_query)

    def write_as_json(self, path, title, result_dict):
        """
        Write JSON with path specified:
        """
        with open(path + title, 'w') as file:
            json.dump(result_dict, file, indent=4)

def main() -> None:
    '''Main function for the validator tool'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--no_reset',
                        '-nr',
                        help='Prevents resetting of the database', action='store_true')
    args = parser.parse_args()

    validator_tool = Validator(args)
    total_epoch = validator_tool.time_operation(validator_tool.run)
    validator_tool.logger.log_final_result(total_epoch[0], validator_tool.result_dictionary)
    
    

if __name__ == '__main__':
    main()
