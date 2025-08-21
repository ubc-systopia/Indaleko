import json
import logging

from datetime import datetime
from typing import Any


class LoggingService:
    """A service for logging various events and metrics in the system."""

    def __init__(self, log_file: str = "upi_log.log", level: int = logging.INFO) -> None:
        """
        Initialize the logging service.

        Args:
            log_file (str): The name of the log file
            level (int): The logging level (e.g., logging.INFO, logging.DEBUG)
        """
        self.logger = logging.getLogger("UPILogger")
        self.logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def log_query(self, query: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Log a user query.

        Args:
            query (str): The user's query
            metadata (Dict[str, Any], optional): Additional metadata about the query
        """
        log_data = {
            "event": "user_query",
            "query": query,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            log_data.update(metadata)
        self.logger.info(json.dumps(log_data))

    def log_result(self, query: str, num_results: int, execution_time: float) -> None:
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
            "timestamp": datetime.now().isoformat(),
        }
        self.logger.info(json.dumps(log_data))

    def log_error(self, error_message: str, error_type: str, stack_trace: str | None = None) -> None:
        """
        Log an error that occurred in the system.

        Args:
            error_message (str): The error message
            error_type (str): The type of error
            stack_trace (str, optional): The stack trace of the error
        """
        log_data = {
            "event": "error",
            "error_message": error_message,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat(),
        }
        if stack_trace:
            log_data["stack_trace"] = stack_trace
        self.logger.error(json.dumps(log_data))

    def log_system_metric(self, metric_name: str, metric_value: Any) -> None:
        """
        Log a system metric.

        Args:
            metric_name (str): The name of the metric
            metric_value (Any): The value of the metric
        """
        log_data = {
            "event": "system_metric",
            "metric_name": metric_name,
            "metric_value": metric_value,
            "timestamp": datetime.now().isoformat(),
        }
        self.logger.info(json.dumps(log_data))

    def log_user_action(self, action: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Log a user action.

        Args:
            action (str): The action performed by the user
            metadata (Dict[str, Any], optional): Additional metadata about the action
        """
        log_data = {
            "event": "user_action",
            "action": action,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            log_data.update(metadata)
        self.logger.info(json.dumps(log_data))
