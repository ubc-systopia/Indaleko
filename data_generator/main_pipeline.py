"""
Main script to run the validation tool
Author: Pearl Park
required files: /data_generator/dg_config.json /config/openai-key.ini
"""

import os, shutil, sys
import configparser
import json
from icecream import ic
from datetime import datetime

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_generator.scripts.s1_metadata_generator import Dataset_Generator
from data_generator.scripts.s2_store_test_Indaleko import MetadataStorer
from data_generator.scripts.s3_translate_query import QueryExtractor
from data_generator.scripts.s4_translate_AQL import AQLQueryConverter
from data_generator.scripts.s5_get_precision_and_recall import ResultCalculator
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections
from query import NLParser, QueryHistory, AQLExecutor, OpenAIConnector
from data_generator.scripts.s6_log_result import ResultLogger
from pathlib import Path
from typing import Dict, Any


class Validator:
    """
    This is the class for performing the validation for Indaleko
    """

    def __init__(self) -> None:
        self.file_path = "./data_generator/results/"
        self.stored_file_path = self.file_path + "stored_metadata/"
        api_path = "./config/openai-key.ini"

        path = Path(self.file_path)
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

        metadata_path = Path(self.stored_file_path)
        metadata_path.mkdir(parents=True, exist_ok=True)

        self.config = self.get_config_file("data_generator/config/dg_config.json")
        self.logger = ResultLogger(result_path=self.file_path)

        self.db_config = IndalekoDBConfig()
        self.db_config.setup_database(
            self.db_config.config["database"]["database"], reset=True
        )
        self.db_config.collections = IndalekoCollections()

        self.query_extractor = QueryExtractor()
        self.data_generator = Dataset_Generator(self.config)
        self.data_storer = MetadataStorer()
        self.result_calculator = ResultCalculator()

        self.openai_key = self.get_api_key(api_path)
        self.llm_connector = OpenAIConnector(api_key=self.openai_key)
        self.nl_parser = NLParser()
        self.query_translator = AQLQueryConverter()
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()

        self.result_dictionary = {}
        self.schema = self.read_json("data_generator/config/schema.json")

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
        assert os.path.exists(api_key_file), f"API key file ({api_key_file}) not found"
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
            Dict[str]: The config file
        """
        assert os.path.exists(
            config_path
        ), f'Config file path "{config_path}" not found'
        with open(config_path, "r") as file:
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

    def run(self) -> None:
        """
        Run function for the validator tool
        """
        query = self.config["query"]
        n_truth_md = self.config["n_matching_queries"]
        n_total_md = self.config["n_metadata_records"]
        dynamic_activity_providers = {}

        self.logger.log_config(self.config)
        self.add_result_to_dict("query", query)
        self.add_result_to_dict("n_total_truth", n_truth_md)
        self.add_result_to_dict("n_metadata", n_total_md)

        # EXTRACT QUERY FROM CONFIG FILE:
        self.logger.log_process("extracting query from config...")
        selected_md_attributes = self.query_extractor.extract(
            query=query, llm_connector=self.llm_connector
        )

        self.logger.log_process_result("selected_md_attributes", selected_md_attributes)
        self.add_result_to_dict("selected_md_attributes", selected_md_attributes)

        # GENERATE METADATA DATASET:
        selected_md_attributes = self.data_generator.preprocess_dictionary_timestamps(
            selected_md_attributes, False
        )
        self.logger.log_process("generating record and activity metadata...")
        generation_time, results = self.time_operation(
            self.data_generator.generate_metadata_dataset,
            selected_md_attributes=selected_md_attributes,
        )

        (
            all_records_md,
            all_geo_activity_md,
            all_temp_activity_md,
            all_music_activity_md,
            all_machine_config_md,
            all_semantics_md,
            stats,
        ) = results

        # save the resulting dataset to a json file for future reference
        self.data_generator.write_json(
            all_records_md, self.stored_file_path + "all_records.json"
        )
        self.data_generator.write_json(
            all_geo_activity_md, self.stored_file_path + "all_geo_activity.json"
        )
        self.data_generator.write_json(
            all_music_activity_md, self.stored_file_path + "all_music_activity.json"
        )
        self.data_generator.write_json(
            all_temp_activity_md, self.stored_file_path + "all_temp_activity.json"
        )
        self.data_generator.write_json(
            all_machine_config_md, self.stored_file_path + "all_machine_config.json"
        )
        self.data_generator.write_json(
            all_semantics_md, self.stored_file_path + "all_semantics_config.json"
        )

        self.logger.log_process_result("metadata_generation_time", generation_time)
        self.add_result_to_dict("metadata_stats", stats)

        # STORE METADATA INTO DATABASE:
        self.logger.log_process("storing record metadata...")
        record_storage_time = self.time_operation(
            self.data_storer.add_records_to_collection,
            collections=self.db_config.collections,
            collection_name="Objects",
            records=all_records_md,
        )
        ic(f"Storing time for record metadata: {record_storage_time}")
        self.logger.log_process_result("stored record:", record_storage_time[0])

        geo_registrator, geo_collection = self.data_storer.register_activity_provider(
            "Geographical Location Collector"
        )
        dynamic_activity_providers["GeoActivity"] = (
            geo_registrator.get_activity_collection_name()
        )

        geo_activity_storage_time = self.time_operation(
            self.data_storer.add_records_with_activity_provider,
            collection=geo_collection,
            activity_contexts=all_geo_activity_md,
        )
        self.logger.log_process("storing geo activity context...")
        ic(
            f"Storing time for geographical location activity metadata: {geo_activity_storage_time}"
        )
        self.logger.log_process_result(
            "stored geo activity context:", geo_activity_storage_time[0]
        )

        music_registrator, music_collection = (
            self.data_storer.register_activity_provider("Music Collector")
        )
        dynamic_activity_providers["MusicActivity"] = (
            music_registrator.get_activity_collection_name()
        )

        music_activity_storage_time = self.time_operation(
            self.data_storer.add_records_with_activity_provider,
            collection=music_collection,
            activity_contexts=all_music_activity_md,
        )
        self.logger.log_process("storing music activity context...")
        ic(f"Storing time for music activity metadata: {music_activity_storage_time}")
        self.logger.log_process_result(
            "stored music activity context:", music_activity_storage_time[0]
        )

        temp_registrator, temp_collection = self.data_storer.register_activity_provider(
            "Temperature Collector"
        )
        dynamic_activity_providers["TempActivity"] = (
            temp_registrator.get_activity_collection_name()
        )

        temp_activity_storage_time = self.time_operation(
            self.data_storer.add_records_with_activity_provider,
            collection=temp_collection,
            activity_contexts=all_temp_activity_md,
        )
        self.logger.log_process("storing music activity context...")
        ic(f"Storing time for music activity metadata: {temp_activity_storage_time}")
        self.logger.log_process_result(
            "stored music activity context:", temp_activity_storage_time[0]
        )

        # self.logger.log_process("storing semantics metadata...")
        # semantics_storage_time = self.time_operation(self.data_storer.add_records_to_collection, collections=self.db_config.collections, collection_name="Unstructured", records=all_machine_config_md, key_required = True)
        # ic(f"Storing time for semantics metadata: {semantics_storage_time}")
        # self.logger.log_process_result("stored semantics metadata:", semantics_storage_time[0])

        self.logger.log_process("storing machine config metadata...")
        machine_config_storage_time = self.time_operation(
            self.data_storer.add_records_to_collection,
            collections=self.db_config.collections,
            collection_name="MachineConfig",
            records=all_machine_config_md,
            key_required=True,
        )
        ic(f"Storing time for machine config metadata: {machine_config_storage_time}")
        self.logger.log_process_result(
            "stored machine config:", machine_config_storage_time[0]
        )

        # PARSE QUERY
        # Adapted from IndalekoSearch.py
        # NOTE: parser hasn't yet been implemented so takes the query + schema and puts in dictionary format
        parse_query_time, parsed_query = self.time_operation(
            self.nl_parser.parse, query=query, schema=self.schema
        )
        self.logger.log_process("parsing query...")
        ic(f"Parse time: {parse_query_time}")
        self.logger.log_process_result("parsed_query", parse_query_time)

        # PREPARE AQL TRANSLATION:
        self.logger.log_process("preparing aql translation...")
        # retrieve the geo coordinates for the AQL translator:
        geo_coordinates = str(self.data_generator.geo_activity_generator.saved_geo_loc)
        self.add_result_to_dict("geo_coord", geo_coordinates)

        # convert the time to posix timestamps for consistent AQL translation results:
        converted_selected_md_attributes = (
            self.data_generator.preprocess_dictionary_timestamps(
                selected_md_attributes, True
            )
        )
        self.logger.log_process("translating query to aql...")
        self.logger.log_process_result(
            "converted_selected_md_attributes", converted_selected_md_attributes
        )
        self.add_result_to_dict(
            "converted_selected_md_attributes", converted_selected_md_attributes
        )

        # GENERATE AQL TRANSLATION:
        translate_query_time, translated_query = self.time_operation(
            self.query_translator.translate,
            parsed_query=parsed_query,
            selected_md_attributes=converted_selected_md_attributes,
            dynamic_activity_providers=dynamic_activity_providers,
            additional_notes=geo_coordinates,
            n_truth=n_truth_md,
            llm_connector=self.llm_connector,
        )
        self.logger.log_process_result(
            "translated_aql", translate_query_time, translated_query
        )

        self.add_result_to_dict("aql_query", translated_query)

        # RUN INDALEKO SEARCH
        self.logger.log_process("running search with translated aql query...")
        execute_time, raw_results = self.time_operation(
            self.query_executor.execute,
            query=translated_query,
            data_connector=self.db_config,
        )
        self.logger.log_process_result("Indaleko search completed", execute_time)

        # CALCULATE PRECISION AND RECALL
        self.logger.log_process("calculating precision and recall")
        calculation_time, calculation_result = self.time_operation(
            self.result_calculator.run,
            raw_results=raw_results,
            theoretical_truth_n=n_truth_md,
        )
        n_actual_truth_md, precision, recall = (
            calculation_result[0],
            calculation_result[1],
            calculation_result[2],
        )
        self.logger.log_process_result(
            "calculated precision and recall",
            calculation_time,
            f"precision: {precision}, recall: {recall}",
        )

        self.add_result_to_dict("uuid_returned", self.result_calculator.selected_uuid)
        self.add_result_to_dict("actual_n_total_truth", n_actual_truth_md)
        self.add_result_to_dict("actual_n_metadata", len(raw_results))
        self.add_result_to_dict("precision", precision)
        self.add_result_to_dict("recall", recall)
        self.logger.log_process("precision and recall calculated")
        self.logger.log_process(
            "DONE -- please check /data_generator/results/validator_result.log for the full results"
        )
        self.save_as_json("Indaleko_search_result", raw_results)

    def read_json(self, json_path):
        with open(json_path, "r") as file:
            data = json.load(file)
        return data

    def save_as_json(self, title, result_dict):
        with open(self.file_path + title + ".json", "w") as file:
            json.dump(result_dict, file, indent=4)


def main() -> None:
    """Main function for the validator tool"""
    validator_tool = Validator()
    total_epoch = validator_tool.time_operation(validator_tool.run)
    validator_tool.logger.log_final_result(
        total_epoch[0], validator_tool.result_dictionary
    )


if __name__ == "__main__":
    main()
