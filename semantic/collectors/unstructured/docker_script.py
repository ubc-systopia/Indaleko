import sys
import os
import json

# to fix import issues
sys.path.append("")

from unstructured.partition.auto import partition # type: ignore
from unstructured.staging.base import elements_to_dicts # type: ignore


input_file_path = sys.argv[1]
output_file_path = sys.argv[2]

with open(input_file_path, 'r') as input, open(output_file_path, 'w') as output:
    for line in input:
        file_object = json.loads(line.strip())
        elements = partition(file_object['URI'])
        elements_json = elements_to_dicts(elements)
        output.write(json.dumps({'ObjectIdentifier': file_object['ObjectIdentifier'],
                                'URI': file_object['URI'],
                                'Unstructured': elements_json}) + '\n')