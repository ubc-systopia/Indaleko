import logging
from typing import Dict, Any
import json
from datetime import datetime


class ResultLogger:
    """
    A service for logging the result of the metadata generator.
    adapted from LoggingServicce from logging_service.py
    """

    def __init__(self, log_file: str = "data_generator_results.log"):
        """
        Initialize the logging service.

        Args:
            log_file (str): The name of the log file
            level (int): loging level set to info as default
        """
        def __init__(self):
            pass

        self.process_logger = logging.getLogger("Process Logger")
        self.process_logger.setLevel(logging.INFO)
        process_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setFormatter(process_formatter)
        self.process_logger.addHandler(file_handler)
        
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(query_formatter)
        # self.logger.addHandler(console_handler)
    
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
        self.process_logger.info(json.dumps(log_data))

    def log_process(self, description: str):
        self.process_logger.info(description)

    def log_final_result(self, total_epoch:str, results: dict):
        self.process_logger.info("FINAL RESULT:")
        self.process_logger.info(f" Total epoch: {total_epoch}")
        self.process_logger.info(f" Total truth metadata queried: {results['n_total_truth']}")
        self.process_logger.info(f" Total metadata queried: {results['n_metadata']}")
        self.process_logger.info(f" Query: {results['query']}")
        self.process_logger.info(f" Actual truth metadata found: {results['actual_n_total_truth']}")
        self.process_logger.info(f" Actual number of metadata returned: {results['actual_n_metadata']}")     
        self.process_logger.info(f" Precision: {results['precision']}")
        self.process_logger.info(f" Recall: {results['recall']}")

        
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

        self.process_logger.info(json.dumps(log_data))


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
        self.process_logger.info(json.dumps(log_data))

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
        self.process_logger.info(json.dumps(log_data))
