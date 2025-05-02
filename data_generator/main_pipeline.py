"""
Main script to run the validation tool.

Required files:
    1) /config/openai-key.ini
"""
import configparser
import copy
import json
import os
import shutil
import sys

from datetime import datetime
from pathlib import Path
from typing import Any

import click

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_generator.scripts.s1_metadata_generator import Dataset_Generator, MetadataResults
from data_generator.scripts.s2_store_metadata import MetadataStorer
from data_generator.scripts.s3_translate_query import QueryExtractor
from data_generator.scripts.s4_translate_AQL import AQLQueryConverter
from data_generator.scripts.s5_get_precision_and_recall import ResultCalculator, Results
from data_generator.scripts.s6_log_result import ResultLogger
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.query_processing.nl_parser import NLParser
from query.utils.llm_connector.openai_connector import OpenAIConnector
from query.cli import IndalekoQueryCLI


# pylint: enable=wrong-import-position

class DataGenerator:
    """This is the main class to run the data generator."""

    def __init__(self) -> None:
        # Set paths:
        self.base_path = Path(current_path)
        self.file_path = self.base_path / "data_generator" / "results"
        self.stored_file_path = self.file_path / "stored_metadata"
        self.config_path = self.base_path / "data_generator" / "config"
        api_path = self.base_path / "config" / "openai-key.ini"

        # Remove and recreate results directory
        if self.file_path.exists():
            shutil.rmtree(self.file_path)
        self.file_path.mkdir(parents=True, exist_ok=True)

        # Ensure stored_metadata directory exists
        self.stored_file_path.mkdir(parents=True, exist_ok=True)

        # Read config files
        self.config = self.get_config_file(self.config_path / "dg_config.json")
        self.logger = ResultLogger(result_path=self.file_path)
        
        # Initialize the database config with proper connection
        self.db_config = IndalekoDBConfig()
        
        # Make sure the database is accessible before proceeding
        self.db_config.start()
        
        # Check if database is properly connected
        assert self.db_config._arangodb is not None, "Database connection failed"
        
        # Setup the database if needed
        self.db_config.setup_database(self.db_config.config["database"]["database"])

        # Initialize different modules required
        self.db_config.collections = IndalekoCollections()
        self.query_extractor = QueryExtractor()
        self.data_generator = Dataset_Generator(self.config)
        self.data_storer = MetadataStorer()
        self.result_calculator = ResultCalculator()

        self.openai_key = self.get_api_key(api_path)

        self.llm_connector = OpenAIConnector(api_key=self.openai_key)
        self.query_executor = AQLExecutor()
        self.collections_md = IndalekoDBCollectionsMetadata()
        self.cli = IndalekoQueryCLI()


        self.dynamic_activity_providers = {}
        self.result_dictionary = {}

    def time_operation(self, operation, **kwargs) -> tuple[str, Any]:
        """
        Given a function, return the time and results of the operation
        Args:
            operation (Any): The function or operation to time
            **kwargs (Any): The arguments required to run the function
        Returns:
            tuple[str, Any]: The operation time and any outputs returned.
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
            str: The API key.
        """
        assert os.path.exists(api_key_file), \
            f"API key file ({api_key_file}) not found"
        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")
        openai_key = config["openai"]["api_key"]
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
            Dict[str]: The config file.
        """
        assert os.path.exists(config_path), f'Config file path "{config_path}" not found'
        with open(config_path) as file:
            return json.load(file)

    def add_result_to_dict(self, key: str, value: str) -> None:
        """
        Adds the results to the result dictionary
        Args:
            key (str): The key to add to the dictionary
            value (str): The value to add to the dictionary.
        """
        self.result_dictionary[key] = value

    def run(self, non_interactive=False, create_dictionary=False, use_existing_dictionary=False, 
             generate_query=False, use_existing_query=False) -> None:
        """
        Run function for the validator tool.
        
        Args:
            non_interactive: Whether to run in non-interactive mode
            create_dictionary: Create a new dictionary in non-interactive mode
            use_existing_dictionary: Use existing dictionary in non-interactive mode
            generate_query: Generate a new AQL query in non-interactive mode
            use_existing_query: Use existing AQL query in non-interactive mode
        """
        self.process_config()

        query = self.config["query"]
        self.add_result_to_dict("query", query)

        original_data_number = self.get_files_collections()
        self.add_result_to_dict("db_number", original_data_number)

        # GENERATE DICTIONARY FOR GENERATOR:
        if non_interactive:
            if create_dictionary:
                intial_selection = 1
            elif use_existing_dictionary:
                intial_selection = 0
            else:
                # Default to creating a new dictionary in non-interactive mode
                intial_selection = 1
        else:
            intial_selection = click.prompt("Type (1) to create a new dictionary or (0) to use existing", type=int)
        
        if intial_selection == 1:
            selected_md_attributes = self.generate_dictionary(query, non_interactive)
        elif intial_selection == 0:
            try:
                selected_md_attributes = self.read_json(self.config_path / "dictionary.json")
            except FileNotFoundError:
                self.logger.log_process("Dictionary file not found. Creating a new one.")
                selected_md_attributes = self.generate_dictionary(query, non_interactive)
        else:
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
        self.query_translator = AQLQueryConverter(self.collections_md)

        if non_interactive:
            if generate_query:
                translate_query = 1
            elif use_existing_query:
                translate_query = 0
            else:
                # Default to generating a new query in non-interactive mode
                translate_query = 1
        else:
            translate_query = click.prompt("Ready for AQL generation. Type (1) to generate a new AQL or (0) to use existing.", type=int)
        
        if translate_query == 0:
            try:
                aql = self.read_aql(self.config_path / aql_text)
            except FileNotFoundError:
                self.logger.log_process("AQL file not found. Generating a new one.")
                aql = self.generate_query(translated_query)
        elif translate_query == 1:
            aql = self.generate_query(translated_query)
        else:
            sys.exit()

        self.write_as_json(self.config_path, query_info, translated_query)
        self.write_as_aql(self.config_path, aql_text, aql)

        # ENSURES THAT AQL FORMAT IS IN CORRECT SYNTAX:
        is_valid_query = False

        while(not is_valid_query):
            try:
                # ASK FOR AQL QUERY REVIEW:
                if non_interactive:
                    aql_selection = 1  # Auto-continue in non-interactive mode
                else:
                    aql_selection = click.prompt(
                        "Please review the AQL_query.aql file and query_info.json and make any necessary changes. \
                        \n Type (1) to continue, or any number to exit",
                        type=int)

                if aql_selection != 1:
                    sys.exit()

                final_query = self.read_aql(self.config_path / aql_text)

                # RUN INDALEKO SEARCH
                raw_results = self.run_search(final_query)
                is_valid_query = True
                self.add_result_to_dict("aql_query", final_query)

            except Exception as e:
                if non_interactive:
                    # In non-interactive mode, log the error and exit
                    self.logger.log_process(f"Error executing query: {e}")
                    return
                self.logger.log_process(e)

        self.add_result_to_dict("metadata_number", len(raw_results))

        updated_data_number = self.get_files_collections()
        self.add_result_to_dict("db_number_update", updated_data_number)

        # CALCULATE PRECISION, RECALL AND OTHER STATISTICS
        self.generate_stats(raw_results)
        self.write_as_json(self.file_path, "Indaleko_search_result.json", raw_results)

    def generate_query(self, query_attributes: dict[str, Any]) -> str:
        """Generate the AQL query:"""
        # Create a dictionary with the parameters instead of passing them individually
        translate_input = {
            "selected_md_attributes": query_attributes["converted_selected_md_attributes"],
            "collections": query_attributes["providers"],
            "geo_coordinates": query_attributes["geo_coords"],
            "n_truth": self.expected_truth_number,
            "llm_connector": self.llm_connector
        }
        
        translate_query_time, translated_query = self.time_operation(
            self.query_translator.translate,
            input_data=translate_input)
        self.logger.log_process_result("translated_aql", translate_query_time, translated_query)
        return translated_query

    def generate_dictionary(self, query:str, non_interactive=False):
        """
        Generate the dictionary from scratch.
        
        Args:
            query: The natural language query to process
            non_interactive: Whether to run in non-interactive mode
        """
        json_name = "dictionary.json"
        self.logger.log_process("building dictionary...")
        self.nl_parser = NLParser(self.collections_md, self.llm_connector)

        # Get relevant NER data for geolocation:
        ner_metadata = self.nl_parser._extract_entities(query)
        entities = self.cli.map_entities(ner_metadata)
        dictionary_generation_time, selected_md_attributes = self.time_operation(
            self.query_extractor.extract,
            query = query,
            named_entities = entities,
            llm_connector = self.llm_connector,
        )
        self.logger.log_process_result("translated_query", dictionary_generation_time, selected_md_attributes)
        self.write_as_json(self.config_path, json_name, selected_md_attributes)

        if non_interactive:
            # Automatically continue in non-interactive mode
            dictionary_selection = 1
        else:
            dictionary_selection = click.prompt("Dictionary ready for evaluation, please type 1 to continue, otherwise type 0 to exit", type=int)
        
        if dictionary_selection != 1:
            sys.exit()
        return self.read_json(self.config_path / json_name)

    def process_config(self) -> None:
        """Process the config file:"""
        self.expected_truth_number = self.config["n_matching_queries"]
        self.n_total_md = self.config["n_metadata_records"]

        self.logger.log_config(self.config)
        self.add_result_to_dict("n_total_truth", self.expected_truth_number)
        self.add_result_to_dict("n_metadata", self.n_total_md)

    def _store_general_metadata(self, collection_name, data, key_required = True) -> None:
        """Helper function to store general metadata like for objects, semantic, machineconfig."""
        self.logger.log_process(f"storing {collection_name} metadata...")
        record_storage_time = self.time_operation(self.data_storer.add_records_to_collection,
                                                    collections=self.db_config.collections,
                                                    collection_name=collection_name,
                                                    records=data,
                                                    key_required = key_required)
        ic(f"Storing time for record metadata: {record_storage_time}")
        self.logger.log_process_result(f"stored {collection_name} :", record_storage_time[0])

    def _store_activity_metadata(self, collection_name, data) -> None:
        """Helper function to store activity metadata like for music, temperature and geographical location."""
        registrator, collection = self.data_storer.register_activity_provider(collection_name + " Collector")
        # Use the collection name directly instead of calling get_activity_collection_name
        self.dynamic_activity_providers[collection_name] = collection.name

        storage_time = self.time_operation(self.data_storer.add_records_with_activity_provider, collection=collection, activity_contexts=data)
        self.logger.log_process(f"storing {collection_name} activity context...")
        ic(f"Storing time for {collection_name} activity metadata: {storage_time}")
        self.logger.log_process_result(f"stored {collection_name} data:", storage_time[0])

    def store_all_metadata(self, results_obj: MetadataResults) -> None:
        """Store all metadata in their appropriate collections withing the DB:"""
        self._store_general_metadata("Objects", results_obj.all_records_md)
        self._store_general_metadata("MachineConfig", results_obj.all_machine_config_md)
        self._store_general_metadata("SemanticData", results_obj.all_semantics_md)

        self._store_activity_metadata("GeoActivity", results_obj.all_geo_activity_md)
        self._store_activity_metadata("MusicActivity", results_obj.all_music_activity_md)
        self._store_activity_metadata("TempActivity", results_obj.all_temp_activity_md)

    def generate_dataset(self, selected_md_attributes):
        """Generate the metadata dataset:"""
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
        """Prepare for the AQL translation:"""
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


    def generate_stats(self, raw_results: dict[str,Any]) -> None:
        """Generates necessary stats:"""
        self.logger.log_process("calculating precision and recall")
        calculation_time, calculation_result = self.time_operation(self.result_calculator.run,
                                                                    truth_list = self.data_generator.truth_list,
                                                                    filler_list = self.data_generator.filler_list,
                                                                    raw_results = raw_results,
                                                                    expected_truth_number = self.expected_truth_number)
        results: Results = calculation_result
        self.add_result_to_dict("results", results)
        self.logger.log_process("precision and recall calculated")
        self.logger.log_process_result("calculated precision and recall", calculation_time, f"precision: {results.precision}, recall: {results.recall}")

    def run_search(self, query: str):
        """Run Indaleko Search:"""
        self.logger.log_process("running search with translated aql query...")
        execute_time, raw_results = self.time_operation(
            self.query_executor.execute,
            query=query,
            data_connector=self.db_config,
        )
        self.logger.log_process_result("Indaleko search completed", execute_time)
        return raw_results

    def get_files_collections(self):
        """Get the count for data already stored in the DB:"""
        total = 0
        for collection in self.db_config.db.collections():
            name = collection["name"]
            collection_count = self.db_config.db.aql.execute(f"""
                RETURN COLLECTION_COUNT('{name}')
            """).next()
            total += collection_count
        return total

    def read_aql(self, aql_path):
        """Read AQL with path specified:"""
        with open(aql_path) as f:
            return f.read()

    def read_json(self, json_path):
        """Read JSON with path specified:"""
        with open(json_path) as file:
            return json.load(file)

    def write_as_aql(self, path, title, aql_query) -> None:
        """Write AQL with path specified:"""
        with open(path / title, "w") as file:
            file.write(aql_query)

    def write_as_json(self, path, title, result_dict) -> None:
        """Write JSON with path specified:"""
        with open(path / title, "w") as file:
            json.dump(result_dict, file, indent=4)

def main() -> None:
    """Main function for the validator tool."""
    import argparse
    
    # Create command-line argument parser
    parser = argparse.ArgumentParser(description="Indaleko Data Generator for Testing")
    parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode")
    parser.add_argument("--create-dictionary", action="store_true", help="Create a new dictionary in non-interactive mode")
    parser.add_argument("--use-existing-dictionary", action="store_true", help="Use existing dictionary in non-interactive mode")
    parser.add_argument("--generate-query", action="store_true", help="Generate a new AQL query in non-interactive mode")
    parser.add_argument("--use-existing-query", action="store_true", help="Use existing AQL query in non-interactive mode")
    
    args = parser.parse_args()
    
    # Initialize the data generator
    validator_tool = DataGenerator()
    
    # Pass the command-line arguments to the run method
    total_epoch = validator_tool.time_operation(
        validator_tool.run,
        non_interactive=args.non_interactive,
        create_dictionary=args.create_dictionary,
        use_existing_dictionary=args.use_existing_dictionary,
        generate_query=args.generate_query,
        use_existing_query=args.use_existing_query
    )
    
    validator_tool.logger.log_final_result(total_epoch[0], validator_tool.result_dictionary)



if __name__ == "__main__":
    main()
