import json
import uuid
from db.i_collections import IndalekoCollections

'''
MetadataStorer for moving the metadata dataset onto the Indaleko DB
'''
class MetadataStorer():
    """
    A service for storing the metadata created
    """
    def __init__(self) -> None:
        """
        Initialize the metadata storer service.
        """
        pass

    def delete_records_from_collection(self, collections: IndalekoCollections, collection_name: str) -> None:
        """
        Deletes the records from the specified collection in IndalekoCollections
        Args: 
            collections (IndalekoCollections): the Indaldeko Collection to delete records from
            collection_name (str): the name of the collection
        """
        collections.get_collection(collection_name).delete_collection(collection_name)

    def add_records_to_collection(self, collections: IndalekoCollections, collection_name: str, records: list, key_required=False) -> None:
        """
        Adds each metadata into the specified collection
        Args: 
            collections (IndalekoCollections): the Indaldeko Collection to delete records from
            collection_name (str): the name of the collection
            records (list) : list of Records to store into the collection
        """
        for record in records:
            if key_required:
                record['_key'] = str(uuid.uuid4())
            collections.get_collection(collection_name).insert(record)
            print(f'Inserted {record} into {collection_name}')

# convert the json file to a list of metadata 
def convert_json_file(json_file: list) -> dict:
    """
    Testing purposes: convert json to dictionary
    """
    with open(json_file, 'r') as file:
        print("here")
        dataset = json.load(file)
    return dataset


def main():
    collections = IndalekoCollections()
    storer = MetadataStorer()

    records = "/Indaleko/data_generator/results/all_records.json"
    record_dataset = convert_json_file(records)
    storer.add_records_to_collection(collections, "Objects", record_dataset)

    activities = "/Indaleko/data_generator/results/all_activity.json"
    activity_dataset = convert_json_file(activities)
    storer.add_ac_to_collection(collections, "ActivityContext", activity_dataset)

    machine_config = "/Indaleko/data_generator/results/all_machine_config.json"
    machine_config_dg = convert_json_file(machine_config)
    storer.add_ac_to_collection(collections, "MachineConfig", machine_config_dg)

if __name__ == '__main__':
    main()
