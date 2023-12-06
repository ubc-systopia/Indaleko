import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import argparse

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
FILE_METADATA_FIELDS = [
    'kind',
    'driveId',
    'fileExtension',
    'md5Checksum',
    'viewedByMe',
    'mimeType',
    'exportLinks',
    'parents',
    'thumbnailLink',
    'shared',
    'headRevisionId',
    'webViewLink',
    'webContentLink',
    'size',
    'spaces',
    'id',
    'name',
    'description',
    'starred',
    'trashed',
    'explicitlyTrashed',
    'createdTime',
    'modifiedTime',
    'modifiedByMeTime',
    'viewedByMeTime',
    'sharedWithMeTime',
    'quotaBytesUsed',
    'version',
    'originalFilename',
    'ownedByMe',
    'fullFileExtension',
    'properties',
    'appProperties',
    'capabilities',
    'hasAugmentedPermissions',
    'trashingUser',
    'thumbnailVersion',
    'modifiedByMe',
    'imageMediaMetadata',
    'videoMediaMetadata',
    'shortcutDetails',
    'contentRestrictions',
    'resourceKey',
    'linkShareMetadata',
    'labelInfo',
    'sha1Checksum',
    'sha256Checksum'
]
FILE_METADATA_FIELDS_NEW = [
    'kind',
    'driveId',
    'fileExtension',
    'md5Checksum',
    'viewedByMe',
    'mimeType',
    'exportLinks',
    'parents[]',
    'thumbnailLink',
    'shared',
    'headRevisionId',
    'webViewLink',
    'webContentLink',
    'size',
    'spaces[]',
    'id',
    'name',
    'description',
    'starred',
    'trashed',
    'explicitlyTrashed',
    'createdTime',
    'modifiedTime',
    'modifiedByMeTime',
    'viewedByMeTime',
    'sharedWithMeTime',
    'quotaBytesUsed',
    'version',
    'originalFileName',
    'ownedByMe',
    'fullFileExtension',
    'properties',
    'appProperties',
    'capabilities',
    'hasAugmentedPermissions',
    'trashingUser',
    'thumbnailVersion',
    'modifiedByMe',
    'imageMediaMetadata',
    'videoMediaMetadata',
    'shortcutDetails',
    'contentRestrictions[]',
    'resourceKey',
    'linkSharedMetadata',
    'labelInfo',
    'sha1Checksum',
    'sha256Checksum'
]


def get_gdrive_credentials(file: str = 'data/gdrive-token.json'):
    creds = None
    if os.path.exists(file):
        creds = Credentials.from_authorized_user_file(file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'data/gdrive-credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(file, 'w') as token:
            token.write(creds.to_json())
    return creds


def get_drive_metadata():
    creds = get_gdrive_credentials()
    service = build('drive', 'v3', credentials=creds)
    metadata_list = []
    page_token=None
    field_to_use = 'nextPageToken, files({})'.format(', '.join(FILE_METADATA_FIELDS))

    while True:
        # fields="nextPageToken, files(kind, driveId, fileExtension, md5Checksum, parents, webViewLink, id, name, description, mimeType, size, createdTime, modifiedTime, quotaBytesUsed, version, sha1Checksum, sha256Checksum)"
        results = service.files().list(fields=field_to_use, pageToken=page_token).execute()
        metadata_list = metadata_list + results.get('files', [])
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return metadata_list

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='data/google-drive-data.json',
                        help='Name and location of where to save the fetched metadata')
    parser.add_argument('--host', type=str,
                        help='URL to use for ArangoDB (overrides config file)')
    parser.add_argument('--port', type=int,
                        help='Port number to use (overrides config file)')
    parser.add_argument('--user', type=str,
                        help='user name (overrides config file)')
    parser.add_argument('--password', type=str,
                        help='user password (overrides config file)')
    parser.add_argument('--database', type=str,
                        help='Name of the database to use (overrides config file)')
    parser.add_argument('--reset', action='store_true',
                        default=False, help='Clean database before running')
    args = parser.parse_args()
    gdrive_contents = get_drive_metadata()
    with open(args.output, 'wt') as output_file:
        json.dump(gdrive_contents, output_file, indent=4)

if __name__ == "__main__":
    main()
