'''
This script will index files of iCloud drive.
Mainly a proof of concept that one is able to login and access file information. 
Furthermore, made sure logging is done for all the steps.
'''
from Indaleko_iCloudSecureCreds import authenticate
from Indaleko_iCloudFullLevel import index_to_jsonl

def main():
    try:
        api = authenticate()
        print("Authentication Successful")
        index_to_jsonl(api)
        print("Metadata indexing completed.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()