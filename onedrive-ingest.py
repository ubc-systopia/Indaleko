import argparse
import json
import os
import msal
import requests
import logging
import sys

class MicrosoftGraphCredentials:

    def __init__(self, config: str = 'data/msgraph-parameters.json', cache_file: str = 'data/msgraph-cache.bin'):
        self.config = json.load(open(config, 'rt'))
        self.cache_file = cache_file
        self.__load_cache__()
        # Note: this will prompt for credentials, if needed
        self.app = msal.PublicClientApplication(self.config['client_id'],
                                                authority=self.config['authority'],
                                                token_cache=self.cache)
        self.__get_token__()


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
            return choice


    def __get_token__(self):
        if hasattr(self, 'token') and self.token is not None:
            return self.token
        self.token = None
        result = None
        accounts = self.app.get_accounts()
        logging.info(f'{len(accounts)} account(s) exist in cache, hopefully with tokens.  Checking.')
        chosen_account = -1
        if len(accounts) > 0:
            chosen_account = self.__choose_account__()
            print(f'Choice is {chosen_account}')
            if chosen_account >= 0:
                result = self.app.acquire_token_silent(self.config['scope'], account=accounts[chosen_account])
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


def get_onedrive_metadata_recursive(cred: MicrosoftGraphCredentials, folder_id=None):
    headers = {
        'Authorization': f'Bearer {cred.get_token()}'
    }
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
            endpoint = None

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
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
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
    print(args)
    # TODO: need to rework this config stuff.  Microsoft's SDK has its own
    # magical stuff so it will be easier to use their expected format than
    # try to fit it into the JSON format.
    graphcreds = MicrosoftGraphCredentials()
    metadata = get_onedrive_metadata_recursive(graphcreds)
    print(len(metadata))

if __name__ == '__main__':
    main()
