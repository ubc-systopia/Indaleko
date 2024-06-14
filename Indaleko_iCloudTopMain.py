'''
This script will index files in the opening directory of iCloud drive.
It will not go into the sub-directories (folders) of iCloud.
Mainly a proof of concept that one is able to login and access file information. 
Furthermore, make sure logging is done for all the steps.
'''
from Indaleko_iCloudSecureCreds import authenticate
from Indaleko_iCloudTopLevel import index_to_json

def main():
    try:
        api = authenticate()
        print("Authentication Successful")
        index_to_json(api)
        print("Metadata indexing completed.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()