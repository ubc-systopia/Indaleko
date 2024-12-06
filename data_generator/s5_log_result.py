import logging
from typing import Dict, Any
import json
from datetime import datetime


class ResultLogger:
    """
    A service for logging the result of the metadata generator.
    adapted from LoggingServicce from logging_service.py
    """

    def __init__(self, result_path: str):
        """
        Initialize the logging service.

        Args:
            result_path (str): The path to the results
            level (int): loging level set to info as default
        """
        progress_formatting = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        result_formatting = '%(message)s'

        self.progress_logger = self.create_logger(result_path + "validator_progress.log", "ProgressLogger", progress_formatting)
        self.result_logger = self.create_logger(result_path + "validator_result.log", "ResultLogger", result_formatting)
        
       
        
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(query_formatter)
        # self.logger.addHandler(console_handler)
    def create_logger(self, log_file, logger_name, formatting):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file, mode = 'w')
        file_handler.setLevel(logging.INFO)

        file_formatter = logging.Formatter(formatting)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def log_config(self, config: dict):
        '''
        log a config file 
        Args: config(dict) : the config file received

        '''
        log_data = {
            "event": "user_config",
            "n_truth_attributes": config["n_matching_queries"],
            "n_total_metadata": config["n_metadata_records"],
            "timestamp": datetime.now().isoformat()
        }
        self.progress_logger.info(json.dumps(log_data))

    def log_process(self, description: str):
        self.progress_logger.info(description)

    def log_final_result(self, total_epoch:str, results: dict):
        '''
        logs final results including the query, 
            extracted features, aql query, total epoch, 
            number of truth files queried, 
            total number of metadata queried, 
            number of total files returned by Indaleko, 
            actual number of truth files from the number returned 

        Args: config(dict) : total epoch (str), results (dict)
        '''
        self.result_logger.info("SUMMARY OF RESULT:")
        self.result_logger.info(f" Total Metadata Queried: {results['n_metadata']}")
        self.result_logger.info(f" Total Truth Metadata Queried: {results['n_total_truth']}")
        self.result_logger.info("--------------------------------------------------------------------------------------------")
        self.result_logger.info("LLM Results:")
        self.result_logger.info(f" Original Query: {results['query']}")
        self.result_logger.info(f" Extracted Features: {results['selected_md_attributes']}")
        self.result_logger.info(f" AQL Query: {results['aql_query']}")
        self.result_logger.info("--------------------------------------------------------------------------------------------")
        self.result_logger.info("Metadata Generation:")
        self.result_logger.info(f" Truth Files Made: {results['metadata_stats']['truth']}")
        self.result_logger.info(f" Filler Files Made: {results['metadata_stats']['filler']}")
        self.result_logger.info(f" Of the Filler Files, Truth-like Filler Files: {results['metadata_stats']['truth-like']}")
        self.result_logger.info("--------------------------------------------------------------------------------------------")
        self.result_logger.info("Indaleko Results:")
        self.result_logger.info(f" Actual Metadata Returned: {results['actual_n_metadata']}")     
        self.result_logger.info(f" Actual Truth Metadata Returned: {results['actual_n_total_truth']}")
        self.result_logger.info(f" UUID of Indaleko Objects Returned: {results['uuid_returned']}")
        self.result_logger.info("--------------------------------------------------------------------------------------------")
        self.result_logger.info("Summary Stats:")
        self.result_logger.info(f" Total epoch: {total_epoch}")
        self.result_logger.info(f" Precision: {results['precision']}")
        self.result_logger.info(f" Recall: {results['recall']}")
        

        
    def log_process_result(self, description:str, epoch:str, results=None):
        '''
        log general processes occuring 
        Args: config(dict) : the config file received

        '''

        log_data = {
            "event": description,
            "epoch": epoch
        }

        if results != None:
            log_data["results"] = results

        self.progress_logger.info(json.dumps(log_data))


    def log_query(self, query: str, metadata: Dict[str, Any] = None):
        """
        Log a user query.

        Args:
            query (str): The user's query
            metadata (Dict[str, Any], optional): Additional metadata about the query
        """
        log_data = {
            "event": "user_query",
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            log_data.update(metadata)
        self.progress_logger.info(json.dumps(log_data))

    def log_result(self, query: str, num_results: int, execution_time: float):
        """
        Log the results of a query.

        Args:
            query (str): The query that was executed
            num_results (int): The number of results returned
            execution_time (float): The time taken to execute the query
        """
        log_data = {
            "event": "query_result",
            "query": query,
            "num_results": num_results,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        self.progress_logger.info(json.dumps(log_data))
