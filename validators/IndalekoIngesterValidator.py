import argparse
import configparser
import os
from arango import ArangoClient
from arango import DefaultHTTPClient
import arango
from dbconfig import DBConfig
import json

class Validator:
    # (?) contains: 3d4b772d-b4b0-4203-a410-ecac5dc6dafa
    # contained by: cde81295-f171-45be-8607-8100f4611430
    queries = {
        "count": """RETURN LENGTH(FOR doc IN {collection_name} FILTER doc.{field}=={value} RETURN 1)""",
        "group_by_count" : """FOR doc IN Objects COLLECT st_mode = doc.Record.Attributes.st_mode WITH COUNT INTO count RETURN { 'st_mode': st_mode, 'count': count }""",

        "relationships": """FOR obj IN Objects FILTER obj.URI == '{parent_uri}' RETURN {{'uri': obj.URI, '_id': obj._id}}""",

        "k_hop_contains": """FOR v, e IN {min_depth}..{max_depth} OUTBOUND "{parent_uri}" Relationships FILTER e.Relationship == "3d4b772d-b4b0-4203-a410-ecac5dc6dafa" RETURN v""",
        "k_hop_contained_by": """FOR v, e IN {min_depth}..{max_depth} OUTBOUND "{parent_uri}" Relationships FILTER e.Relationship == "cde81295-f171-45be-8607-8100f4611430" RETURN v"""
    }

    TIMEOUT_SEC=4*60 # request timeout

    def __init__(self, config_path: str, json_path: str):
        assert os.path.isfile(config_path), f'Err: no config path at this file: {config_path}'
        assert os.path.isfile(json_path), f"Err: no json file at this path: {json_path}"

        self.json_path = json_path

        config_parser = configparser.ConfigParser()
        config_parser.read(config_path)

        # make sure we have the database section
        assert 'database' in config_parser, f"couldn't find 'database' section in the config file"
        self.db_config = DBConfig(config_parser['database'])

        # filled when called with db_connect
        self.db_client = None
        self.db = None

    def db_connect(self) -> bool:
        url = f"http://{self.db_config.get_host()}:{self.db_config.get_port()}"
        client = ArangoClient(hosts=url, request_timeout=self.TIMEOUT_SEC)

        # Connect to the target database
        try:
            db = client.db(self.db_config.get_db(), username=self.db_config.get_user_name(
            ), password=self.db_config.get_user_password())

            self.db = db
            self.db_client = client
        except Exception as e:
            print(f"error connecting to the databse, got={e}")
            return False
        return True

    def generate_objects_from_json_file(self):
        with open(self.json_path, 'r') as file:
            for line in file:
                try:
                    # Attempt to load each line as a JSON object
                    obj = json.loads(line)
                    yield obj
                except json.JSONDecodeError as e:
                    print('Err parsing the input json file; got=', e)
                    yield None
    def validate(self):
        st_mode_dict = None

        def __build_st_mode_dict():
            nonlocal st_mode_dict
            try:
                results = self.db.aql.execute(Validator.queries['group_by_count'])
                st_mode_dict = {doc['st_mode']: doc['count'] for doc in results}
            except arango.AQLQueryExecuteError as e:
                print(f'could not group the st_mode field; got={e}')
                return
            print('Total st_mode=', len(st_mode_dict))
            
            

        total_misses=0
        total=0
        for line_num, validation_obj in enumerate(self.generate_objects_from_json_file()):
            if not validation_obj:
                continue
            try:
                total+=1
                match validation_obj['type']:
                    case 'count':
                        if not st_mode_dict: __build_st_mode_dict()

                        count = st_mode_dict[validation_obj['value']]

                        # Compare the query result with the given count field
                        if count == validation_obj['count']:
                            print(f"Matching count for field '{
                                validation_obj['value']}' in '{self.db.db_name}', count={validation_obj['count']}")
                        else:
                            print(f"Mismatching count for field '{validation_obj['value']}' in {
                                self.db.db_name}: Expected {validation_obj['count']}, Got {count}")
                    case 'contains':
                        # escape the spaces
                        validation_obj['parent_uri'] = validation_obj['parent_uri'].replace(r"'", r"\'")

                        # find the parent_uri object
                        find_parent_query = Validator.queries['relationships'].format(
                            parent_uri= validation_obj['parent_uri']
                            )

                        parent_obj = [obj for obj in self.db.aql.execute(find_parent_query)]
                        if not len(parent_obj):
                            print(f'[CONTAINS] SKIPPED VALIATION: couldn\'t find the parent obj for {validation_obj['parent_uri']}')
                            continue
                        parent_obj=parent_obj.pop()

                        find_1hop_neighbors= Validator.queries['k_hop_contains'].format(
                            min_depth=1,
                            max_depth=1,
                            parent_uri=parent_obj["_id"]
                        )
                        neighbors_cursor=self.db.aql.execute(find_1hop_neighbors)
                        results = [document['URI'] for document in neighbors_cursor if document]

                        if len(results) != len(validation_obj['children_uri']):
                            print(f'CONTAINS[MISS]: skipped : {validation_obj['parent_uri']}')
                            total_misses+=1
                    case 'contained_by':
                        # escape the spaces
                        validation_obj['child_uri'] = validation_obj['child_uri'].replace(' ', r'\ ')

                        find_parent_query = Validator.queries['relationships'].format(
                            parent_uri= validation_obj['child_uri']
                            )

                        parent_obj = [obj for obj in self.db.aql.execute(find_parent_query)]
                        if not len(parent_obj):
                            print(f'[CONTAINED_BY] SKIPPED VALIDATION: couldn\'t find the parent obj for {validation_obj['child_uri']}')
                            continue
                        parent_obj=parent_obj.pop()

                        find_1hop_contained_by =Validator.queries['k_hop_contained_by'].format(
                            min_depth=1,
                            max_depth=1,
                            parent_uri=parent_obj['_id']
                        )

                        parents_cursor=self.db.aql.execute(find_1hop_contained_by)
                        results = [document['URI'] for document in parents_cursor if document]

                        if len(results) != len(validation_obj['parent_uris']):
                            print(f'CONTAINED_BY[MISS]: skipped: {validation_obj['child_uri']}')
                            total_misses+=1

            except (arango.exceptions.AQLQueryExecuteError, StopIteration) as e:
                print('{:-^10} Error at line {}'.format("", line_num))
                print(f"Error querying and comparing in {self.db.db_name} for {validation_obj['parent_uri']}: Exception Type: {type(e)}, Exception: {e}")
                find_parent_query and print(find_parent_query)
                find_1hop_neighbors and print(find_1hop_neighbors)
                find_1hop_contained_by and print(find_1hop_contained_by)

        if not total:
            print('Total processed is 0. Either the input is empty or all entries are not valid')
        if total_misses not in (0, 1, 2):
            print('Total misses has to be among 0, 1 and 2.')
        print('{:*^10} DONE'.format(''))


def main():
    print('{:-^10} Validating Ingestion'.format(''))
    parser = argparse.ArgumentParser('Ingester Validator')
    parser.add_argument('-f', '--file', dest='json_file_path', required=True)
    parser.add_argument('-c', '--config', dest='config_path', required=False)

    args = parser.parse_args()
    config_path = args.config_path if args.config_path else None
    if config_path:
        assert os.path.exists(config_path) and os.path.isfile(
            config_path), f"Err: config file doesn't exist or is not a file; path={config_path}"
    json_path = args.json_file_path

    # extract indaleko credentials
    validator = Validator(config_path=config_path, json_path=json_path)
    assert validator.db_connect()

    validator.validate()


if __name__ == '__main__':
    main()
