

import os

from icecream import ic

from Indaleko import Indaleko

objects = [x for x in os.listdir('data') if 'collection=Objects' in x and x.endswith('.jsonl')]
print(objects)
relationships = [x for x in os.listdir('data') if 'collection=Relationships' in x and x.endswith('.jsonl')]
print(relationships)


def generate_import_command(collection : str, file_name : str, dir_name : str = '.') -> str:
    cmd = 'arangoimport'
    cmd += f' -collection {collection}'
    cmd += ' --create-collection false'
    cmd += ' --server.username uiRXxRxF'
    cmd += ' --server.password jDrcwy9VcAhhSmt'
    cmd += ' --server.endpoint http+tcp:localahost:8529'
    cmd += ' --server.database Indaleko'
    cmd += f' {dir_name}/{file_name}'
    return cmd

for obj in objects:
    # keys = Indaleko.extract_keys_from_file_name(obj)
    #ic(keys)
    ic(generate_import_command('Objects', obj, 'data'))

#for rel in relationships:
#    keys = Indaleko.extract_keys_from_file_name(rel)
#    ic(keys)
