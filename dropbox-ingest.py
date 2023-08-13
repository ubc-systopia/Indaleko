import os
import json
import argparse
import dropbox


def get_dropbox_credentials(file: str = 'data/dropbox-token.json'):
    # Note: this should be converted to use the OAuth2 work flow that Dropbox
    # prefers, but for testing this works with a hard coded token
    assert os.path.exists(file), 'File {} does not exist, aborting'.format(file)
    data = json.load(open(file, 'rt'))
    return data['token']


def convert_to_serializable(data):
    if isinstance(data, (int, float, str, bool, type(None))):
        return data
    elif isinstance(data, list):
        return [convert_to_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_to_serializable(value) for key, value in data.items()}
    else:
        # If data is an object with __dict__, convert it to a dictionary and recursively process
        if hasattr(data, '__dict__'):
            return convert_to_serializable(data.__dict__)
        # If data is not serializable, skip it for now
        return None

def get_dropbox_metadata():
    access_token = get_dropbox_credentials()
    dbx = dropbox.Dropbox(access_token)
    try:
        metadata_list = []
        cursor = None
        while True:
            result = dbx.files_list_folder('', recursive=True)
            result = dbx.files_list_folder_continue(
                cursor) if cursor else dbx.files_list_folder('', recursive=True)
            for entry in result.entries:
                captured_entry = {}
                for key in dir(entry):
                    if key.startswith('_'):
                        continue
                    value = convert_to_serializable(getattr(entry, key))
                    if value is not None and (isinstance(value, (bool, int, float)) or len(value) != 0):
                        captured_entry[key] = value
                metadata_list.append(captured_entry)
            if not result.has_more:
                break
            cursor = result.cursor
    except dropbox.exceptions.ApiError as e:
        print(f"Error enumerating folder, exception {e}")
    return metadata_list

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='data/dropbox-data.json',
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
    dropbox_contents = get_dropbox_metadata()
    with open(args.output, 'wt') as output_file:
        json.dump(dropbox_contents, output_file, indent=4)


if __name__ == "__main__":
    main()
