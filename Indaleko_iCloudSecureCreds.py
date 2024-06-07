import os
import keyring
from pyicloud import PyiCloudService

def get_icloud_credentials():
    username = os.getenv('ICLOUD_USERNAME')
    password = keyring.get_password('iCloud', username)
    if not password:
        raise ValueError("Password not found in keyring for the given username.")
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