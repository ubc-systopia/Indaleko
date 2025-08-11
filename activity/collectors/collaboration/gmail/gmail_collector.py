"""
gmail_collector.py.

This collector retrieves email metadata from Gmail using the Gmail API.
Following the Collector/Recorder pattern, it only collects raw data
without normalization or database operations.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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
"""

import json
import logging
import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import HttpError, build
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.collaboration_base import CollaborationCollector
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoServiceManager
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from utils.misc.directory_management import indaleko_default_config_dir


# pylint: enable=wrong-import-position


class IndalekoGmailCollector(CollaborationCollector):
    """Gmail email metadata collector for Indaleko."""

    gmail_platform = "Gmail"
    gmail_collector_name = "gmail_collector"

    indaleko_gmail_collector_uuid = "a7f3d2e1-8b4c-4d5e-9f6a-2c3b4d5e6f7a"
    indaleko_gmail_collector_service_name = "Gmail Email Collector"
    indaleko_gmail_collector_service_description = "Collects email metadata from Gmail for Indaleko."
    indaleko_gmail_collector_service_version = "1.0"
    indaleko_gmail_collector_service_type = IndalekoServiceManager.service_type_activity_collector

    # Gmail API scopes - we only request read-only access to metadata
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.metadata",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]

    # Fields to retrieve for each message
    MESSAGE_FORMAT = "metadata"  # We use metadata format to avoid downloading full message bodies
    MESSAGE_METADATA_HEADERS = [
        "From",
        "To",
        "Cc",
        "Bcc",
        "Subject",
        "Date",
        "Message-ID",
        "In-Reply-To",
        "References",
        "List-ID",
        "List-Unsubscribe",
        "Return-Path",
    ]

    gmail_config_file = "gmail_config.json"
    gmail_token_file = "gmail_token.json"

    indaleko_gmail_collector_service = {
        "uuid": indaleko_gmail_collector_uuid,
        "name": indaleko_gmail_collector_service_name,
        "description": indaleko_gmail_collector_service_description,
        "version": indaleko_gmail_collector_service_version,
        "type": indaleko_gmail_collector_service_type,
    }

    def __init__(self, **kwargs) -> None:
        """Initialize the Gmail collector."""
        self.email = None
        self.config_dir = kwargs.get("config_dir", indaleko_default_config_dir)
        self.gmail_config_file = os.path.join(
            self.config_dir,
            IndalekoGmailCollector.gmail_config_file,
        )
        assert os.path.exists(
            self.gmail_config_file,
        ), f"No Gmail config file found at {self.gmail_config_file}"
        self.gmail_token_file = os.path.join(
            self.config_dir,
            IndalekoGmailCollector.gmail_token_file,
        )
        self.gmail_config = None
        self.load_gmail_config()
        self.gmail_credentials = None
        self.load_gmail_credentials()

        # Counters for statistics
        self.message_count = 0
        self.thread_count = 0
        self.label_count = 0
        self.error_count = 0

        super().__init__()

    def load_gmail_config(self) -> "IndalekoGmailCollector":
        """Load the Gmail OAuth configuration."""
        with open(self.gmail_config_file) as f:
            self.gmail_config = json.load(f)
        return self

    def load_gmail_credentials(self) -> "IndalekoGmailCollector":
        """Load or refresh Gmail credentials."""
        if os.path.exists(self.gmail_token_file):
            logging.debug("Loading Gmail credentials from %s", self.gmail_token_file)
            self.gmail_credentials = Credentials.from_authorized_user_file(
                self.gmail_token_file,
                IndalekoGmailCollector.SCOPES,
            )
        if not self.gmail_credentials or not self.gmail_credentials.valid:
            query_user = True
            if self.gmail_credentials and self.gmail_credentials.expired and self.gmail_credentials.refresh_token:
                try:
                    self.gmail_credentials.refresh(Request())
                    query_user = False
                except RefreshError as error:
                    logging.exception("Error refreshing credentials: %s", error)
            if query_user:
                self.query_user_for_credentials()
            if self.gmail_credentials and self.gmail_credentials.valid:
                self.store_gmail_credentials()
            else:
                logging.error("Unable to get valid credentials")
                ic("Unable to get valid credentials, terminating")
                sys.exit(-1)
        return self

    def store_gmail_credentials(self) -> "IndalekoGmailCollector":
        """Store the Gmail credentials to disk."""
        assert self.gmail_credentials is not None, "No credentials to store"
        with open(self.gmail_token_file, "w") as f:
            f.write(self.gmail_credentials.to_json())
        return self

    def query_user_for_credentials(self) -> "IndalekoGmailCollector":
        """Query the user for Gmail credentials via OAuth flow."""
        flow = InstalledAppFlow.from_client_config(
            self.gmail_config,
            IndalekoGmailCollector.SCOPES,
        )
        self.gmail_credentials = flow.run_local_server(port=0)
        return self

    def get_email(self) -> str:
        """Get the email address associated with the credentials."""
        if self.email is None:
            service = build("gmail", "v1", credentials=self.gmail_credentials)
            try:
                profile = service.users().getProfile(userId="me").execute()
                self.email = profile.get("emailAddress", "unknown@gmail.com")
            except HttpError as error:
                logging.exception("Error fetching email address: %s", error)
                self.email = "unknown@gmail.com"
        return self.email

    def get_labels(self) -> list[dict[str, Any]]:
        """Retrieve all labels/folders from Gmail."""
        service = build("gmail", "v1", credentials=self.gmail_credentials)
        try:
            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            self.label_count = len(labels)
            return labels
        except HttpError as error:
            logging.exception("Error fetching labels: %s", error)
            self.error_count += 1
            return []

    def build_message_metadata(self, message: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from a Gmail message."""
        metadata = {
            "id": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
            "snippet": message.get("snippet"),
            "historyId": message.get("historyId"),
            "internalDate": message.get("internalDate"),
            "sizeEstimate": message.get("sizeEstimate"),
            "raw": message.get("raw"),  # Only present if format='raw' was requested
        }

        # Extract headers if present
        if "payload" in message and "headers" in message["payload"]:
            headers = {}
            for header in message["payload"]["headers"]:
                if header["name"] in self.MESSAGE_METADATA_HEADERS:
                    headers[header["name"]] = header["value"]
            metadata["headers"] = headers

        # Extract parts information (attachments, etc.) if present
        if "payload" in message and "parts" in message["payload"]:
            parts_info = []
            for part in message["payload"]["parts"]:
                part_info = {
                    "partId": part.get("partId"),
                    "mimeType": part.get("mimeType"),
                    "filename": part.get("filename"),
                    "body_size": part.get("body", {}).get("size", 0),
                }
                if part.get("filename"):  # This is an attachment
                    part_info["isAttachment"] = True
                parts_info.append(part_info)
            metadata["parts"] = parts_info

        # Add collection timestamp
        metadata["collected_at"] = datetime.now(UTC).isoformat()

        return metadata

    def collect_messages(self, query: str = "", max_results: int | None = None) -> list[dict[str, Any]]:
        """
        Collect email messages from Gmail.

        Args:
            query: Gmail search query (e.g., "is:unread", "from:someone@example.com")
            max_results: Maximum number of messages to retrieve

        Returns:
            List of message metadata dictionaries
        """
        if self.gmail_credentials is None:
            self.load_gmail_credentials()

        service = build("gmail", "v1", credentials=self.gmail_credentials)
        messages = []
        page_token = None

        try:
            while True:
                # List messages matching the query
                if query:
                    results = (
                        service.users()
                        .messages()
                        .list(
                            userId="me",
                            q=query,
                            pageToken=page_token,
                            maxResults=min(500, max_results) if max_results else 500,
                        )
                        .execute()
                    )
                else:
                    results = (
                        service.users()
                        .messages()
                        .list(
                            userId="me",
                            pageToken=page_token,
                            maxResults=min(500, max_results) if max_results else 500,
                        )
                        .execute()
                    )

                message_refs = results.get("messages", [])

                # Fetch full metadata for each message
                for msg_ref in message_refs:
                    try:
                        msg = (
                            service.users()
                            .messages()
                            .get(
                                userId="me",
                                id=msg_ref["id"],
                                format=self.MESSAGE_FORMAT,
                                metadataHeaders=self.MESSAGE_METADATA_HEADERS,
                            )
                            .execute()
                        )

                        metadata = self.build_message_metadata(msg)
                        messages.append(metadata)
                        self.message_count += 1

                        if max_results and len(messages) >= max_results:
                            return messages

                    except HttpError as error:
                        if error.resp.status == 401:
                            # Token expired, refresh and retry
                            self.load_gmail_credentials()
                            self.error_count += 1
                            continue
                        logging.exception("Error fetching message %s: %s", msg_ref["id"], error)
                        self.error_count += 1

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as error:
            logging.exception("Error listing messages: %s", error)
            self.error_count += 1

        return messages

    def collect_threads(self, query: str = "", max_results: int | None = None) -> list[dict[str, Any]]:
        """
        Collect email threads (conversations) from Gmail.

        Args:
            query: Gmail search query
            max_results: Maximum number of threads to retrieve

        Returns:
            List of thread metadata dictionaries
        """
        if self.gmail_credentials is None:
            self.load_gmail_credentials()

        service = build("gmail", "v1", credentials=self.gmail_credentials)
        threads = []
        page_token = None

        try:
            while True:
                # List threads matching the query
                if query:
                    results = (
                        service.users()
                        .threads()
                        .list(
                            userId="me",
                            q=query,
                            pageToken=page_token,
                            maxResults=min(500, max_results) if max_results else 500,
                        )
                        .execute()
                    )
                else:
                    results = (
                        service.users()
                        .threads()
                        .list(
                            userId="me",
                            pageToken=page_token,
                            maxResults=min(500, max_results) if max_results else 500,
                        )
                        .execute()
                    )

                thread_refs = results.get("threads", [])

                # Fetch full thread data
                for thread_ref in thread_refs:
                    try:
                        thread = (
                            service.users()
                            .threads()
                            .get(
                                userId="me",
                                id=thread_ref["id"],
                                format=self.MESSAGE_FORMAT,
                                metadataHeaders=self.MESSAGE_METADATA_HEADERS,
                            )
                            .execute()
                        )

                        thread_metadata = {
                            "id": thread.get("id"),
                            "historyId": thread.get("historyId"),
                            "message_count": len(thread.get("messages", [])),
                            "messages": [self.build_message_metadata(msg) for msg in thread.get("messages", [])],
                            "collected_at": datetime.now(UTC).isoformat(),
                        }

                        threads.append(thread_metadata)
                        self.thread_count += 1

                        if max_results and len(threads) >= max_results:
                            return threads

                    except HttpError as error:
                        if error.resp.status == 401:
                            # Token expired, refresh and retry
                            self.load_gmail_credentials()
                            self.error_count += 1
                            continue
                        logging.exception("Error fetching thread %s: %s", thread_ref["id"], error)
                        self.error_count += 1

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as error:
            logging.exception("Error listing threads: %s", error)
            self.error_count += 1

        return threads

    def collect(self, mode: str = "messages", query: str = "", max_results: int | None = None) -> dict[str, Any]:
        """
        Main collection method - retrieves Gmail data.

        Args:
            mode: "messages", "threads", or "all"
            query: Gmail search query
            max_results: Maximum number of items to retrieve

        Returns:
            Dictionary containing collected data and metadata
        """
        collection_data = {
            "platform": self.gmail_platform,
            "collector": self.gmail_collector_name,
            "version": self.indaleko_gmail_collector_service_version,
            "email": self.get_email(),
            "collected_at": datetime.now(UTC).isoformat(),
            "query": query,
            "mode": mode,
        }

        # Collect labels
        collection_data["labels"] = self.get_labels()

        # Collect based on mode
        if mode in {"messages", "all"}:
            collection_data["messages"] = self.collect_messages(query, max_results)

        if mode in {"threads", "all"}:
            collection_data["threads"] = self.collect_threads(query, max_results)

        # Add statistics
        collection_data["statistics"] = {
            "message_count": self.message_count,
            "thread_count": self.thread_count,
            "label_count": self.label_count,
            "error_count": self.error_count,
        }

        return collection_data

    def write_data_to_file(self, data: dict[str, Any], output_file: str) -> None:
        """Write collected data to a JSON file."""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("Data written to %s", output_file)

    def get_counts(self) -> dict[str, int]:
        """Return collection statistics."""
        return {
            "messages": self.message_count,
            "threads": self.thread_count,
            "labels": self.label_count,
            "errors": self.error_count,
        }

    # CollaborationCollector abstract method implementations
    def get_collector_name(self) -> str:
        return self.gmail_collector_name

    def get_provider_id(self) -> UUID:
        return UUID(self.indaleko_gmail_collector_uuid)

    def get_description(self) -> str:
        return self.indaleko_gmail_collector_service_description


def local_run(keys: dict[str, str]) -> dict | None:
    """Run the Gmail collector."""
    args = keys["args"]
    cli = keys["cli"]
    config_data = cli.get_config_data()
    debug = hasattr(args, "debug") and args.debug
    if debug:
        ic(args)
        ic(config_data)

    output_file_name = str(Path(args.datadir) / args.outputfile)

    def collect(collector: IndalekoGmailCollector) -> None:
        """Local implementation of collect."""
        mode = getattr(args, "mode", "messages")
        query = getattr(args, "query", "")
        max_results = getattr(args, "max_results", None)

        data = collector.collect(mode=mode, query=query, max_results=max_results)
        collector.write_data_to_file(data, output_file_name)

    def extract_counters(**kwargs):
        """Local implementation of extract_counters."""
        collector = kwargs.get("collector")
        if collector:
            return collector.get_counts()
        return {}

    collector = IndalekoGmailCollector(config_dir=args.configdir)
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        collect,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.get_provider_id(),
            Version=collector.indaleko_gmail_collector_service_version,
            Description=collector.get_description(),
        ),
        description=collector.get_description(),
        MachineIdentifier=None,
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=output_file_name,
        collector=collector,
    )

    if args.performance_db or args.performance_file:
        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_file = str(Path(args.datadir) / config_data["PerformanceDataFile"])
            perf_recorder.add_data_to_file(perf_file, perf_data)
            if debug:
                ic("Performance data written to ", config_data["PerformanceDataFile"])
        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            if debug:
                ic("Performance data written to the database")

    return perf_data


def main() -> None:
    """Gmail collector main entry point."""
    from utils.cli.base import IndalekoBaseCLI, IndalekoCLIRunner

    cli_data = {
        "name": "Gmail Email Collector",
        "description": "Collects email metadata from Gmail",
        "epilog": "Retrieves email metadata without downloading full message bodies",
        "arguments": [
            {
                "name": "--mode",
                "type": str,
                "default": "messages",
                "choices": ["messages", "threads", "all"],
                "help": "Collection mode: messages, threads, or all",
            },
            {
                "name": "--query",
                "type": str,
                "default": "",
                "help": "Gmail search query (e.g., 'is:unread', 'from:someone@example.com')",
            },
            {
                "name": "--max-results",
                "type": int,
                "help": "Maximum number of items to retrieve",
            },
            {
                "name": "--configdir",
                "type": str,
                "default": str(indaleko_default_config_dir),
                "help": "Configuration directory path",
            },
            {
                "name": "--datadir",
                "type": str,
                "default": "./data",
                "help": "Output data directory",
            },
            {
                "name": "--outputfile",
                "type": str,
                "default": f"gmail-collector-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
                "help": "Output file name",
            },
            {
                "name": "--performance-file",
                "action": "store_true",
                "help": "Write performance data to file",
            },
            {
                "name": "--performance-db",
                "action": "store_true",
                "help": "Write performance data to database",
            },
            {
                "name": "--debug",
                "action": "store_true",
                "help": "Enable debug output",
            },
        ],
    }

    runner = IndalekoCLIRunner(
        cli_data=cli_data,
        handler_mixin=None,
        features=IndalekoBaseCLI.cli_features(),
        Run=local_run,
    )
    runner.run()


if __name__ == "__main__":
    main()
