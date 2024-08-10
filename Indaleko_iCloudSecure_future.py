'''
This simple bit of code records MUCH more information in the log file. Trying to correct the current version of
iCloudSecureCreds log file output is not productive atm. As there are no issues in getting it to run 2024-06-24
But if errors pop up and it's unclear this is essential as it is my only remaining file that records the level 
of detail I want the iCloudSecureCreds to originally do
'''


import os
import keyring
from pyicloud import PyiCloudService
import logging
from datetime import datetime
from getpass import getpass

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
log_filename = datetime.now().strftime('logs/%Y%m%d-%H%M%S-iCloudLoginLog.log')
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(message)s')

def store_credentials(username, password):
    keyring.set_password('iCloud', username, password)
    logging.debug(f"Stored credentials for {username}")

def get_stored_usernames():
    usernames = keyring.get_password('iCloud', 'usernames')
    return usernames.split(',') if usernames else []

def update_stored_usernames(username):
    usernames = get_stored_usernames()
    if username not in usernames:
        usernames.append(username)
        keyring.set_password('iCloud', 'usernames', ','.join(usernames))
    return usernames

def list_all_entries(service_name):
    logging.debug(f"Listing all entries for service '{service_name}':")
    stored_usernames = get_stored_usernames()
    for stored_username in stored_usernames:
        logging.debug(f"Username: {stored_username}")

def get_icloud_credentials():
    list_all_entries('iCloud')
    stored_usernames = get_stored_usernames()
    logging.debug(f"Retrieved stored usernames: {stored_usernames}")

    if stored_usernames:
        print("Stored usernames:")
        for stored_username in stored_usernames:
            print(f"- {stored_username}")

    username = input("Enter your iCloud username (or press Enter to select from the list above): ").strip()
    if not username and stored_usernames:
        if len(stored_usernames) == 1:
            username = stored_usernames[0]
        else:
            username = input("Please select a username from the list above: ").strip()

    password = keyring.get_password('iCloud', username)
    if not password:
        password = getpass("Enter your iCloud password: ")
        store_credentials(username, password)
        logging.debug(f"Existing stored usernames before update: {stored_usernames}")
        update_stored_usernames(username)
        logging.debug(f"Stored usernames after updating: {get_stored_usernames()}")

    return username, password

def authenticate():
    username, password = get_icloud_credentials()
    api = PyiCloudService(username, password)
    
    if api.requires_2fa:
        code = input("Enter the code you received on one of your approved devices: ")
        result = api.validate_2fa_code(code)
        if not result:
            raise ValueError("Failed to verify security code")
        if not api.is_trusted_session:
            api.trust_session()
    return api

# Now you can call the authenticate function in your main script
if __name__ == "__main__":
    api = authenticate()
    print("Authentication successful.")