"""
Script to load the generated metadata onto the db and run Indaleko query 
Author: Pearl Park

"""


import os, shutil, sys, json

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from IndalekoIngesterManagement import IndalekoIngesterManagement


def main():
    dataset_path = "data_generator/sample_dataset.jsonl"
    with open(dataset_path, 'r') as dataset_path:
        # Load the JSON data
        data = json.load(dataset_path)
    ingester = IndalekoIngesterManagement(service_name = "indaleko_ingester", service_id = 1)
    ingester.build_load_string(collection='Objects', file=data)


if __name__ == '__main__':
    main()
