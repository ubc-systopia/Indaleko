import os
import keyring
from pyicloud import PyiCloudService
import logging
from datetime import datetime
from getpass import getpass

def setup_logging():
    logger = logging.getLogger('iCloudAuthLogger')
    logger.setLevel(logging.DEBUG)
    if not os.path.exists('logs'):
        os.makedirs('logs')
    log_filename = datetime.now().strftime('logs/%Y%m%d-%H%M%S-iCloudLoginLog.log')
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(file_handler)
    
    # Enable DEBUG logging for third-party libraries
    logging.getLogger('pyicloud').setLevel(logging.DEBUG)
    logging.getLogger('requests').setLevel(logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.DEBUG)
    
    return logger

auth_logger = setup_logging()

def store_credentials(username, password):
    keyring.set_password('iCloud', username, password)
    auth_logger.debug(f"Stored credentials for {username}")

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
    auth_logger.debug(f"Listing all entries for service '{service_name}':")
    stored_usernames = get_stored_usernames()
    for stored_username in stored_usernames:
        auth_logger.debug(f"Username: {stored_username}")

def get_icloud_credentials():
    list_all_entries('iCloud')
    stored_usernames = get_stored_usernames()
    auth_logger.debug(f"Retrieved stored usernames: {stored_usernames}")

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
        auth_logger.debug(f"Existing stored usernames before update: {stored_usernames}")
        update_stored_usernames(username)
        auth_logger.debug(f"Stored usernames after updating: {get_stored_usernames()}")

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

# This module should not run any main code