import json
import uuid
import os, sys
if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from db.i_collections import IndalekoCollections
from db.collection import IndalekoCollection

from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.record import IndalekoRecordDataModel
from datetime import datetime

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

    def register_activity_provider(self, collector_type: str, version:str = '1.0.0') -> IndalekoCollection:
        """
        initializes a activity provider registerer for the specifitied collector
        Args: 
            collection
        """
        identifier = uuid.uuid4()
        activity_data_registrar = IndalekoActivityDataRegistrationService()

        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=identifier,
            Version=version,
            Description=collector_type
        )

        record_kwargs = {
            'Identifier' : str(identifier),
            'Version' : version,
            'Description' : collector_type,
            'Record' : IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(),
                Attributes={},
                Data=''
            )
        }
        _, collection = activity_data_registrar.register_provider(**record_kwargs)
        return activity_data_registrar, collection

    def add_records_with_activity_provider(self, collection: IndalekoCollection, activity_contexts: dict) -> None:
        """
        initializes a activity provider registerer for the specifitied collector
        Args: 
            collection
        """
        for activity in activity_contexts:
            collection.insert(activity)
            

# convert the json file to a list of metadata 
def convert_json_file(json_file: str) -> dict:
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

    # records = "/Indaleko/data_generator/results/all_records.json"
    # record_dataset = convert_json_file(records)
    # storer.add_records_to_collection(collections, "Objects", record_dataset)
    current_path = os.path.dirname(os.path.abspath(__file__))
    print(current_path)

    activities = "./data_generator/results/test_temp_records.json"
    activity_dataset = convert_json_file(activities)
    storer.add_records_to_collection(collections, "TempActivityContext", activity_dataset)

    # machine_config = "/Indaleko/data_generator/results/all_machine_config.json"
    # machine_config_dg = convert_json_file(machine_config)
    # storer.add_ac_to_collection(collections, "MachineConfig", machine_config_dg)

if __name__ == '__main__':
    main()
