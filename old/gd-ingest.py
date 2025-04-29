import logging
import os

import IndalekoIngest
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleDriveIngest(IndalekoIngest.IndalekoIngest):
    """This is the ingestor for Google Drive."""

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

    def __init__(self):
        super().__init__()
        self.gdrive_creds = None
        self.email = None

    def _get_output_file(self) -> str:
        """This method returns the output file name"""
        return f"{self.data_dir}/gdrive-{self.get_email()}-{self.timestamp}.json".replace(
            " ",
            "_",
        ).replace(":", "-")

    def main(self):
        """Set up the specific features for this ingestor"""
        self.parser.add_argument(
            "--creds",
            type=str,
            default=f"{self.config_dir}/gdrive-credentials.json",
            help="Name of the credentials file",
        )
        self.parser.add_argument(
            "--token",
            type=str,
            default=f"{self.config_dir}/gdrive-token.json",
            help="Where the temporary token should be stored",
        )
        super().main()
        # at this point we can authenticate and get the e-mail address to use.
        if self.args.output is None:
            if self.gdrive_creds is None:
                self._get_credentials()
            self.args.output = f"{self.data_dir}/gdrive-{self.get_email()}-{self.timestamp}.json".replace(
                " ",
                "_",
            ).replace(
                ":",
                "-",
            )

    def get_metadata(self):
        """This method extracts the metadata from the Google Drive API"""
        if self.gdrive_creds is None:
            self._get_credentials()
        page_token = None
        field_to_use = "nextPageToken, files({})".format(
            ", ".join(GoogleDriveIngest.FILE_METADATA_FIELDS),
        )
        self.metadata = []
        service = None

        while True:
            if service is None:
                service = build("drive", "v3", credentials=self.gdrive_creds)
            try:
                results = service.files().list(fields=field_to_use, pageToken=page_token).execute()
            except HttpError as error:
                # this should handle a token expiration by refreshing it
                if error.resp.status == 401:
                    self._get_credentials()
                    continue
                else:
                    raise error
            self.metadata.extend(results.get("files", []))
            page_token = results.get("nextPageToken", None)
            if not page_token:
                break
        return self.metadata

    def _get_credentials(self) -> None:
        """This method obtains credentials if we have them stored, fetches new
        ones if we don't, and refreshes the token upon expiration. The token is
        stored in the given file.
        """
        if os.path.exists(self.args.token):
            self.gdrive_creds = Credentials.from_authorized_user_file(
                self.args.token,
                GoogleDriveIngest.SCOPES,
            )
        if not self.gdrive_creds or not self.gdrive_creds.valid:
            if self.gdrive_creds and self.gdrive_creds.expired and self.gdrive_creds.refresh_token:
                self.gdrive_creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.args.creds,
                    GoogleDriveIngest.SCOPES,
                )
                self.gdrive_creds = flow.run_local_server(port=0, prompt="consent")
            with open(self.args.token, "w") as token:
                token.write(self.gdrive_creds.to_json())

    def get_email(self) -> str:
        """This method returns the email address associated with the
        credentials
        """
        if self.email is None:
            service = build("people", "v1", credentials=self.gdrive_creds)
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


if __name__ == "__main__":
    ingestor = GoogleDriveIngest()
    ingestor.main()
