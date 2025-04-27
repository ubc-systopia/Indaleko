"""
g_drive.py

This script is used to scan the files in the Google Drive folder of Indaleko.
It will create a JSONL file with the metadata of the files in the Dropbox
folder.
The JSONL file will be used by the google drive recorder to load data into
the database.

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
from pathlib import Path
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
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoServiceManager
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from storage.collectors.base import BaseStorageCollector
from storage.collectors.cloud.cloud_base import BaseCloudStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from utils.misc.directory_management import indaleko_default_config_dir

# pylint: enable=wrong-import-position


class IndalekoGDriveCloudStorageCollector(BaseCloudStorageCollector):
    gdrive_platform = "GoogleDrive"
    gdrive_collector_name = "collector"

    indaleko_gdrive_collector_uuid = "74c82969-6bbb-4450-97f5-44d65c65e133"
    indaleko_gdrive_collector_service_name = "Google Drive Indexer"
    indaleko_gdrive_collector_service_description = "Indexes the Google Drive folder for Indaleko."
    indaleko_gdrive_collector_service_version = "1.0"
    indaleko_gdrive_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    collector_data = IndalekoStorageCollectorDataModel(
        PlatformName=gdrive_platform,
        ServiceRegistrationName=indaleko_gdrive_collector_service_name,
        ServiceFileName=gdrive_collector_name,
        ServiceUUID=UUID(indaleko_gdrive_collector_uuid),
        ServiceVersion=indaleko_gdrive_collector_service_version,
        ServiceDescription=indaleko_gdrive_collector_service_description,
    )

    SCOPES = [
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    FILE_METADATA_FIELDS = [
        "kind",
        "driveId",
        "fileExtension",
        "md5Checksum",
        "viewedByMe",
        "mimeType",
        "exportLinks",
        "parents",
        "thumbnailLink",
        "shared",
        "headRevisionId",
        "webViewLink",
        "webContentLink",
        "size",
        "spaces",
        "id",
        "name",
        "description",
        "starred",
        "trashed",
        "explicitlyTrashed",
        "createdTime",
        "modifiedTime",
        "modifiedByMeTime",
        "viewedByMeTime",
        "sharedWithMeTime",
        "quotaBytesUsed",
        "version",
        "originalFilename",
        "ownedByMe",
        "fullFileExtension",
        "properties",
        "appProperties",
        "capabilities",
        "hasAugmentedPermissions",
        "trashingUser",
        "thumbnailVersion",
        "modifiedByMe",
        "imageMediaMetadata",
        "videoMediaMetadata",
        "shortcutDetails",
        "contentRestrictions",
        "resourceKey",
        "linkShareMetadata",
        "labelInfo",
        "sha1Checksum",
        "sha256Checksum",
    ]

    gdrive_config_file = "gdrive_config.json"
    gdrive_token_file = "gdrive_token.json"

    indaleko_gdrive_collector_service = {
        "uuid": indaleko_gdrive_collector_uuid,
        "name": indaleko_gdrive_collector_service_name,
        "description": indaleko_gdrive_collector_service_description,
        "version": indaleko_gdrive_collector_service_version,
        "type": indaleko_gdrive_collector_service_type,
    }

    def __init__(self, **kwargs):
        self.email = None
        self.config_dir = kwargs.get("config_dir", indaleko_default_config_dir)
        self.gdrive_config_file = os.path.join(
            self.config_dir,
            IndalekoGDriveCloudStorageCollector.gdrive_config_file,
        )
        assert os.path.exists(
            self.gdrive_config_file,
        ), f"No GDrive config file found at {self.gdrive_config_file}"
        self.gdrive_token_file = os.path.join(
            self.config_dir,
            IndalekoGDriveCloudStorageCollector.gdrive_token_file,
        )
        self.gdrive_config = None
        self.load_gdrive_config()
        self.gdrive_credentials = None
        self.load_gdrive_credentials()
        if "platform" not in kwargs:
            kwargs["platform"] = IndalekoGDriveCloudStorageCollector.gdrive_platform
        if "collector_data" not in kwargs:
            kwargs["collector_data"] = IndalekoGDriveCloudStorageCollector.collector_data
        super().__init__(
            **kwargs,
            collector_name=IndalekoGDriveCloudStorageCollector.gdrive_collector_name,
            **IndalekoGDriveCloudStorageCollector.indaleko_gdrive_collector_service,
        )

    def load_gdrive_config(self) -> "IndalekoGDriveCloudStorageCollector":
        """This method loads the GDrive configuration"""
        with open(self.gdrive_config_file) as f:
            self.gdrive_config = json.load(f)
        return self

    def load_gdrive_credentials(self) -> "IndalekoGDriveCloudStorageCollector":
        """This method gets the GDrive credentials"""
        if os.path.exists(self.gdrive_token_file):
            logging.debug("Loading GDrive credentials from %s", self.gdrive_token_file)
            self.gdrive_credentials = Credentials.from_authorized_user_file(
                self.gdrive_token_file,
                IndalekoGDriveCloudStorageCollector.SCOPES,
            )
        if not self.gdrive_credentials or not self.gdrive_credentials.valid:
            query_user = True
            if self.gdrive_credentials and self.gdrive_credentials.expired and self.gdrive_credentials.refresh_token:
                try:
                    self.gdrive_credentials.refresh(Request())
                    query_user = False
                except RefreshError as error:
                    logging.exception("Error refreshing credentials: %s", error)
            if query_user:
                self.query_user_for_credentials()
            if self.gdrive_credentials and self.gdrive_credentials.valid:
                self.store_gdrive_credentials()
            else:
                logging.error("Unable to get valid credentials")
                ic("Unable to get valid credentials, terminating")
                exit(-1)
        return self

    def store_gdrive_credentials(self) -> "IndalekoGDriveCloudStorageCollector":
        """This method stores the credentials"""
        assert self.gdrive_credentials is not None, "No credentials to store"
        with open(self.gdrive_token_file, "w") as f:
            f.write(self.gdrive_credentials.to_json())
        return self

    def query_user_for_credentials(self) -> "IndalekoGDriveCloudStorageCollector":
        """This method queries the user for credentials"""
        flow = InstalledAppFlow.from_client_config(
            self.gdrive_config,
            IndalekoGDriveCloudStorageCollector.SCOPES,
        )
        self.gdrive_credentials = flow.run_local_server(port=0)
        return self

    def get_email(self) -> str:
        """This method returns the email address associated with the
        credentials
        """
        if self.email is None:
            service = build("people", "v1", credentials=self.gdrive_credentials)
            results = service.people().get(resourceName="people/me", personFields="emailAddresses").execute()
            email = "dummy@dummy.com"
            if "emailAddresses" not in results:
                logging.warning("No email addresses found in %s", results)
            else:
                if len(results["emailAddresses"]) > 1:
                    logging.info("More than one email address found in %s", results)
                email = results["emailAddresses"][0]["value"]
            self.email = email
        return self.email

    def build_stat_dict(self, entry: dict) -> dict:
        """This builds the stat dict for the entry"""
        return entry

    def fetch_root_metadata(self) -> dict:
        """Fetch metadata for the root directory"""
        service = build("drive", "v3", credentials=self.gdrive_credentials)
        try:
            root_metadata = service.files().get(fileId="root", fields=",".join(self.FILE_METADATA_FIELDS)).execute()
            return self.build_stat_dict(root_metadata)
        except HttpError as error:
            logging.exception("Error fetching root metadata: %s", error)
            ic("Error fetching root metadata: ", error)
            return {}

    def collect(self, recursive=True) -> list:
        """
        This method indexes Google Drive.
        """
        if self.gdrive_credentials is None:
            self.load_gdrive_credentials()
        page_token = None
        field_to_use = "nextPageToken, files({})".format(
            ", ".join(IndalekoGDriveCloudStorageCollector.FILE_METADATA_FIELDS),
        )
        metadata_list = []
        service = None

        # Fetch the metadata for the root directory
        root_metadata = self.fetch_root_metadata()
        if root_metadata:
            metadata_list.append(root_metadata)
            self.dir_count += 1
        else:
            ic("Root metadata fetching failed. Aborting.")
            exit(0)

        while True:
            if service is None:
                service = build("drive", "v3", credentials=self.gdrive_credentials)
            try:
                results = service.files().list(fields=field_to_use, pageToken=page_token).execute()
            except HttpError as error:
                # this should handle a token expiration by refreshing it
                if error.resp.status == 401:
                    self.load_gdrive_credentials()
                    self.error_count += 1
                    continue
                else:
                    raise error
            for entry in results.get("files", []):
                metadata = self.build_stat_dict(entry)
                metadata_list.append(metadata)
                mimetype = metadata.get("mimeType")
                if mimetype == "application/vnd.google-apps.folder":
                    self.dir_count += 1
                else:
                    self.file_count += 1
            page_token = results.get("nextPageToken", None)
            if not page_token:
                break
        self.data = metadata_list
        return metadata_list

    @staticmethod
    def find_collector_files(
        search_dir: str,
        prefix: str = BaseCloudStorageCollector.default_file_prefix,
        suffix: str = BaseCloudStorageCollector.default_file_suffix,
    ) -> list:
        """This function finds the files to ingest:
        search_dir: path to the search directory
        prefix: prefix of the file to ingest
        suffix: suffix of the file to ingest (default is .json)
        """
        prospects = BaseStorageCollector.find_collector_files(
            search_dir,
            prefix,
            suffix,
        )
        return [f for f in prospects if IndalekoGDriveCloudStorageCollector.gdrive_platform in f]

    class gdrive_collector_mixin(BaseCloudStorageCollector.cloud_collector_mixin):
        """This is the mixin for the Google Drive collector"""

        @staticmethod
        def generate_output_file_name(keys: dict[str, str]) -> str:
            """Generate the output file name"""
            if not keys.get("UserId"):
                collector = IndalekoGDriveCloudStorageCollector(
                    config_dir=keys["ConfigDirectory"],
                )
                keys["UserId"] = collector.get_email()
            return BaseCloudStorageCollector.cloud_collector_mixin.generate_output_file_name(
                keys,
            )

    cli_handler_mixin = gdrive_collector_mixin


@staticmethod
def local_run(keys: dict[str, str]) -> dict | None:
    """Run the collector"""
    args = keys["args"]
    cli = keys["cli"]
    config_data = cli.get_config_data()
    debug = hasattr(args, "debug") and args.debug
    if debug:
        ic(args)
        ic(config_data)
    kwargs = {"timestamp": config_data["Timestamp"], "offline": args.offline}
    output_file_name = str(Path(args.datadir) / args.outputfile)

    def collect(collector: IndalekoGDriveCloudStorageCollector):
        """Local implementation of collect"""
        data = collector.collect(not args.norecurse)
        output_file = output_file_name
        collector.write_data_to_file(data, output_file)

    def extract_counters(**kwargs):
        """Local implementation of extract_counters"""
        collector = kwargs.get("collector")
        if collector:
            return ic(collector.get_counts())
        else:
            return {}

    collector = IndalekoGDriveCloudStorageCollector(**kwargs)
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        collect,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.service_identifier,
            Version=collector.service_version,
            Description=collector.service_description,
        ),
        description=collector.service_description,
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


def main() -> None:
    """Google Drive collector main"""
    BaseCloudStorageCollector.cloud_collector_runner(
        IndalekoGDriveCloudStorageCollector,
    )


if __name__ == "__main__":
    main()
