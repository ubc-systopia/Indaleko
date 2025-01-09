import argparse
import json
import os
import msal
import requests
import logging
import sys
import datetime

class MicrosoftGraphCredentials:

    def __init__(self, config: str = 'config/msgraph-parameters.json', cache_file: str = 'data/msgraph-cache.bin'):
        self.__chosen_account__ = -1
        self.config = json.load(open(config, 'rt'))
        self.cache_file = cache_file
        self.__load_cache__()
        self.__output_file_name__ = None
        # Note: this will prompt for credentials, if needed
        self.app = msal.PublicClientApplication(self.config['client_id'],
                                                authority=self.config['authority'],
                                                token_cache=self.cache
                                                )
        self.__get_token__()

    def __get_chosen_account__(self) -> int:
        if self.__chosen_account__ < 0:
            self.__chosen_account__ = self.__choose_account__()
        return self.__chosen_account__

    def reset_chosen_account(self) -> 'MicrosoftGraphCredentials':
        self.__chosen_account__ = -1
        return self

    def __load_cache__(self):
        if hasattr(self, 'cache'):
            return
        self.cache = msal.SerializableTokenCache()
        if os.path.exists(self.cache_file):
            logging.info('Cache file exists, deserializing')
            self.cache.deserialize(open(self.cache_file, 'r').read())
            logging.info(f'Loaded cache: {self.cache}')
        return self


    def __choose_account__(self) -> int:
        if self.__chosen_account__ >= 0:
            return self.__chosen_account__
        accounts = self.app.get_accounts()
        if accounts:
            choice = -1
            while choice == -1:
                print('Pick the account to use:')
                index = 1
                for a in accounts:
                    print(f'{index} {a["username"]}')
                    index = index + 1
                print(f'{index} Use a different account (login)')
                try:
                    choice = int(input())
                    if choice == index:  # Use a different account
                        choice = -1
                        break  # done
                    choice = choice - 1
                except ValueError:
                    choice = -1
            if choice >= 0:
                self.__chosen_account__ = choice
        return self.__chosen_account__

    def get_account_name(self):
        if self.__output_file_name__ is None:
            assert self.__get_chosen_account__() >= 0, 'No account chosen'
            accounts = self.app.get_accounts()
            if accounts:
                self.__output_file_name__ = accounts[self.__get_chosen_account__()].get("username")
        return self.__output_file_name__

    def get_output_file_name(self):
        return f'data/microsoft-onedrive-data-{self.get_account_name()}-{datetime.datetime.now(datetime.UTC)}-data.json'.replace(' ', '_').replace(':', '-')

    def __get_token__(self):
        if hasattr(self, 'token') and self.token is not None:
            return self.token
        self.token = None
        result = None
        accounts = self.app.get_accounts()
        logging.info(f'{len(accounts)} account(s) exist in cache, hopefully with tokens.  Checking.')
        if self.__chosen_account__ < 0 and len(accounts) > 0:
                self.chosen_account = self.__choose_account__()
        if self.__chosen_account__ >= 0:
            result = self.app.acquire_token_silent(self.config['scope'], account=accounts[self.__chosen_account__])
        if result is None:
            logging.info('Suitable token not found in cache. Request from user.')
            flow = self.app.initiate_device_flow(scopes=self.config['scope'])
            if 'user_code' not in flow:
                raise ValueError(f'Failed to create device flow. Err: {json.dumps(flow,indent=4)}')
            print(flow['message'])
            sys.stdout.flush()
            result = self.app.acquire_token_by_device_flow(flow)
        if 'access_token' not in result:
            print(result.get('error'))
            print(result.get('error_description'))
            print(result.get('correlation_id'))
            self.token = None
        else:
            self.token = result['access_token']
        return self.token

    def __save_cache__(self):
        if hasattr(self, 'cache') and getattr(self, 'cache') is not None:
            print(type(self.cache))
            open(self.cache_file, 'w').write(self.cache.serialize())

    def __del__(self):
        if hasattr(self, 'cache') and self.cache is not None and self.cache.has_state_changed:
            self.__save_cache__()

    def get_token(self):
        return self.__get_token__()

    def clear_token(self) -> 'MicrosoftGraphCredentials':
        '''Use this to clear a stale or invalid token.'''
        self.token = None
        return self

def get_onedrive_metadata_recursive(cred: MicrosoftGraphCredentials, folder_id=None):

    def get_headers():
        return {
            'Authorization': f'Bearer {cred.get_token()}'
        }
    headers = get_headers()
    metadata_list = []

    if folder_id is None:
        endpoint = 'https://graph.microsoft.com/v1.0/me/drive/root/children'
    else:
        endpoint = f'https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children'

    while endpoint:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data['value']:
                metadata_list.append(item)
                if item.get('folder'):
                    # Recursively fetch metadata for subfolder
                    subfolder_id = item['id']
                    metadata_list.extend(
                        get_onedrive_metadata_recursive(cred, subfolder_id))
            endpoint = data.get('@odata.nextLink')
        else:
            print(f"Error: {response.status_code} - {response.text}")
            if 401 == response.status_code: # seems to indicate a stale token
                cred.clear_token()
                headers = get_headers()
            # try again
    return metadata_list


'''
def get_onedrive_metadata(cred: MicrosoftGraphCredentials):
    headers = {
        'Authorization': f'Bearer {cred.get_token()}'
    }
    metadata_list = []

    endpoint = 'https://graph.microsoft.com/v1.0/me/drive/root/children'
    while endpoint:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data['value']:
                metadata_list.append(item)
            endpoint = data.get('@odata.nextLink')
        else:
            print(f"Error: {response.status_code} - {response.text}")
            endpoint = None
    return metadata_list
'''

def main():
    # First, let's figure out the name we're using
    graphcreds = MicrosoftGraphCredentials()
    # Now parse the arguments
    logging_levels = sorted(set([l for l in logging.getLevelNamesMapping()]))
    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel', type=int, default=logging.WARNING, choices=logging_levels,
                        help='Logging level to use (lower number = more logging)')
    parser.add_argument('--output', type=str, default=graphcreds.get_output_file_name(),
                        help='Name and location of where to save the fetched metadata')
    parser.add_argument('--config', type=str, default='msgraph-config.json',
                        help='Name and location from whence to retrieve the Microsoft Graph Config info')
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
    print("args:", args)
    start = datetime.datetime.now(datetime.UTC)
    metadata = get_onedrive_metadata_recursive(graphcreds)
    end = datetime.datetime.now(datetime.UTC)
    if len(metadata) > 0:
        with open(args.output, 'wt') as output_file:
            json.dump(metadata, output_file, indent=4)
        print(f'Saved {len(metadata)} records to {args.output} in {end-start} seconds ({(end-start)/len(metadata)} seconds per record)')

if __name__ == '__main__':
    main()
