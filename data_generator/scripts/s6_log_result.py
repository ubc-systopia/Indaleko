import json
import logging

from datetime import datetime
from logging import Logger


class ResultLogger:
    """
    A service for logging the result of the metadata generator.
    Adapted from LoggingService from logging_service.py
    """

    def __init__(self, result_path: str) -> None:
        """
        Initialize the logging service.

        Args:
            result_path (str): The path to the results
            level (int): loging level set to info as default
        """
        progress_formatting = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        result_formatting = "%(message)s"

        self.progress_logger = self.create_logger(
            result_path + "validator_progress.log",
            "ProgressLogger",
            progress_formatting,
        )
        self.result_logger = self.create_logger(
            result_path + "validator_result.log",
            "ResultLogger",
            result_formatting,
        )

    def create_logger(self, log_file, logger_name, formatting) -> Logger:
        """
        Creates a new logger instance
        Args:
            log_file (str): the name of the logger file
            logger_name (str): the name of the logger
            formatting (str): the formatting type for the specific logger
        Returns: Logger: logger object
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setLevel(logging.INFO)

        file_formatter = logging.Formatter(formatting)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def log_config(self, config: dict) -> None:
        """
        Progress Logger: Logs the contents of a given config file
        Args:
            config(dict) : the given config file
        """
        log_data = {
            "event": "user_config",
            "n_truth_attributes": config["n_matching_queries"],
            "n_total_metadata": config["n_metadata_records"],
            "timestamp": datetime.now().isoformat(),
        }
        self.progress_logger.info(json.dumps(log_data))

    def log_process(self, description: str) -> None:
        """
        Progress Logger: Logs current process in validator_progress.log
        Args:
            description(str) : the description of the process that is occurring
        """
        self.progress_logger.info(description)

    def log_process_result(self, description: str, epoch: str, results=None) -> None:
        """
        Progress Logger: Logs general processes occuring
        Args:
            description(str) : the description of the process
            epoch(str) : the epoch time for the process
        """
        log_data = {"event": description, "epoch": epoch}

        if results != None:
            log_data["results"] = results

        self.progress_logger.info(json.dumps(log_data))

    def log_final_result(self, total_epoch: str, results: dict):
        """
        Result Logger: Logs a summary results including
        the query, extracted features, aql query, total epoch, number of truth files queried, total number of metadata queried,
        total files returned by Indaleko
        and precision and recall calculations
        Args:
            config(dict) :
                total epoch (str) : the total epoch taken for the entire validation process
                results (dict) : a dictionary consisting of all requires elements to create the summary
        """
        self.result_logger.info("SUMMARY OF RESULT:")
        self.result_logger.info(f" Total Metadata Queried: {results['n_metadata']}")
        self.result_logger.info(
            f" Total Truth Metadata Queried: {results['n_total_truth']}",
        )
        self.result_logger.info(
            "--------------------------------------------------------------------------------------------",
        )
        self.result_logger.info("LLM Results:")
        self.result_logger.info(f" Original Query: {results['query']}")
        self.result_logger.info(
            f" Truth File Attributes:\n{json.dumps(results['selected_md_attributes'], indent=4)}",
        )
        # self.result_logger.info(f" Converted Truth File Attributes:\n{json.dumps(results['converted_selected_md_attributes'], indent=4)}")
        self.result_logger.info(f" Geographical Coordinates: {results['geo_coord']}")
        self.result_logger.info(f" AQL Query:\n{results['aql_query']}")
        self.result_logger.info(
            "--------------------------------------------------------------------------------------------",
        )
        self.result_logger.info("Metadata Generation:")
        self.result_logger.info(
            f" Truth Files Made: {results['metadata_stats']['truth']}",
        )
        self.result_logger.info(
            f" Filler Files Made: {results['metadata_stats']['filler']}",
        )
        self.result_logger.info(
            f" Of the Filler Files, Truth-like Filler Files: {results['metadata_stats']['truth-like']}",
        )
        self.result_logger.info(
            "--------------------------------------------------------------------------------------------",
        )
        self.result_logger.info("Indaleko Results:")
        self.result_logger.info(
            f" Actual Metadata Returned: {results['actual_n_metadata']}",
        )
        self.result_logger.info(
            f" Actual Truth Metadata Returned: {results['actual_n_total_truth']}",
        )
        self.result_logger.info(
            f" UUID of Indaleko Objects Returned: {results['uuid_returned']}",
        )
        self.result_logger.info(
            "--------------------------------------------------------------------------------------------",
        )
        self.result_logger.info("Summary Stats:")
        self.result_logger.info(f" Total epoch: {total_epoch}")
        self.result_logger.info(f" Precision: {results['precision']}")
        self.result_logger.info(f" Recall: {results['recall']}")
