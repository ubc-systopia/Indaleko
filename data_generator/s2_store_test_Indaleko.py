"""
Script to load the generated metadata onto the db and run Indaleko query
Author: Pearl Park

"""
import os, shutil, sys, json, subprocess
from arango import ArangoClient
from pydantic import ValidationError
import uuid

from icecream import ic
if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_models.i_object import IndalekoObjectDataModel
from IndalekoCollections import IndalekoCollections
from IndalekoDBConfig import IndalekoDBConfig

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


'''
MetadataStorer for moving the metadata dataset onto the Indaleko DB
'''
class MetadataStorer():
    def __init__(self) -> None:
        pass

    #delete the Indaleko objects from the collection:
    def delete_records_from_collection(self, collections: IndalekoCollections, collection_name: str) -> None:
        collections.get_collection(collection_name).delete_collection(collection_name)

    # adds each metadata into the specified collection
    def add_records_to_collection(self, collections: IndalekoCollections, collection_name: str, records: list) -> None:
        for record in records:
            collections.get_collection(collection_name).insert(record)
            print(f'Inserted {record} into {collection_name}')

    # add each activity context to the specified collection
    def add_ac_to_collection(self, collections: IndalekoCollections, collection_name: str, records: list) -> None:
        for record in records:
            record['_key'] = str(uuid.uuid4())
            ic(record)
            collections.get_collection(collection_name).insert(record)
            print(f'Inserted {record} into {collection_name}')


    # convert the json file to a list of metadata
    def convert_json_file(self, json_file: list):
        with open(json_file, 'r') as file:
            print("here")
            dataset = json.load(file)
        return dataset
    #test the data model to see if in the right form
    # test with any of the following variables: target, truth_like_filler, filler
    def test_data_model(self, model, dataModel):
        try:
            model_test = dataModel(**model)
            print("Valid input passed:", model_test)
        except ValidationError as e:
            print("Validation error for valid input:", e)



def main():
    collections = IndalekoCollections()
    storer = MetadataStorer()
    # records = "/Users/pearl/Indaleko_updated/Indaleko/data/all_records.json"
    # record_dataset = storer.convert_json_file(records)
    # storer.add_records_to_collection(collections, "Object", record_dataset)

    activities = "/Users/pearl/Indaleko_updated/Indaleko/data/all_activity.json"
    activity_dataset = storer.convert_json_file(activities)
    storer.add_ac_to_collection(collections, "ActivityContext", activity_dataset)
    #delete_records_from_collection(collections, "ActivityContext")
    # machine_config = "/Users/pearl/Indaleko_updated/Indaleko/config/macos-hardware-info-47582870-5694-0536-0078-6547569242582024-11-11T16:47:18.350318.json"
    # machine_config_dg = convert_json_file(machine_config)
    # add_records_to_collection(collections, "MachineConfig", machine_config_dg)


    #delete_records_from_collection(collections, "Object")


if __name__ == '__main__':
    main()
