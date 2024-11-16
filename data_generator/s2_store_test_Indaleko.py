"""
Script to load the generated metadata onto the db and run Indaleko query 
Author: Pearl Park

"""
import os, shutil, sys, json, subprocess
from arango import ArangoClient

from icecream import ic


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from IndalekoCollections import IndalekoCollections
from IndalekoDBConfig import IndalekoDBConfig


# adds each metadata into the specified collection
def add_records_to_collection(collections: IndalekoCollections, collection_name: str, records: list) -> None:
    for record in records:
        ic(record)
        collections.get_collection(collection_name).insert(record)
        print(f'Inserted {record} into {collection_name}')
    
# convert the json file to a list of metadata 
def convert_json_file(json_file: list):
    with open(json_file, 'r') as file:
        print("here")
        dataset = json.load(file)
    return dataset


#delete the Indaleko objects from the collection:
def delete_records_from_collection(collections: IndalekoCollections, collection_name: str) -> None:
    collections.get_collection(collection_name).delete_collection("Object")



def main():
    collections = IndalekoCollections()
    records = "/Users/pearl/Indaleko_updated/Indaleko/data/data.json"
    dataset = convert_json_file(records)
    add_records_to_collection(collections, "Object", dataset)
    #delete_records_from_collection(collections, "Object")


if __name__ == '__main__':
    main()
