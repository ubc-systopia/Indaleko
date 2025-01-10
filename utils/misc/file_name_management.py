'''
This module provides utility functions for managing file names in Indaleko.

Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
import os
import platform
import sys

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
import utils.misc.timestamp_management
from constants.values import IndalekoConstants
# pylint: enable=wrong-import-position

indaleko_file_name_prefix = IndalekoConstants.default_prefix

def generate_final_name(args : list, **kwargs) -> str:
    '''
    This is a helper function for generate_file_name, which throws
    a pylint error as having "too many branches".  An explicit args list
    threw a "too many arguments" error, so this is a compromise - send in a
    list, and then unpack it manually. Why this is better is a mystery of
    the faith.
    '''
    prefix = args[0]
    target_platform = args[1]
    service = args[2]
    ts = args[3]
    suffix = args[4]
    max_len = args[5]
    name = prefix
    if '-' in prefix:
        raise ValueError('prefix must not contain a hyphen')
    if '-' in suffix:
        raise ValueError('suffix must not contain a hyphen')
    if target_platform: # platform is optional
        name += f'-plt={target_platform}'
    name += f'-svc={service}'
    ic(kwargs)
    for key, value in kwargs.items():
        assert isinstance(value, str), f'value must be a string: {key, value}'
        if '-' in key:
            raise ValueError(f'key must not contain a hyphen: {key, value}')
        name += f'-{key}={value}'
    if ts is not None:
        name += ts
    name += f'.{suffix}'
    if len(name) > max_len:
        raise ValueError('file name is too long' + '\n' + name + '\n' + str(len(name)))
    return name

def generate_file_name(**kwargs) -> str:
    f'''
    Given a key/value store of labels and values, this generates a file
    name in a common format.
    Special labels:
        * prefix: string to prepend to the file name (default is {indaleko_file_name_prefix})
        * platform: identifies the platform from which the data originated (default is {platform.system()})
        * service: identifies the service that generated the data (collector,
            recorder, etc.) (no default)
        * timestamp: timestamp to use in the file name (default is the current time)
        * suffix: string to append to the file name (default is jsonl)
    '''
    max_len = 255
    prefix = indaleko_file_name_prefix
    suffix = 'jsonl'
    if 'max_len' in kwargs:
        max_len = kwargs['max_len']
        if isinstance(max_len, str):
            max_len = int(max_len)
        if not isinstance(max_len, int):
            raise ValueError('max_len must be an integer')
        del kwargs['max_len']
    if 'platform' not in kwargs:
        target_platform = None
    else:
        target_platform = kwargs['platform']
        del kwargs['platform']
    if 'service' not in kwargs:
        raise ValueError('service must be specified')
    service = kwargs['service']
    del kwargs['service']
    ts = utils.misc.timestamp_management.generate_iso_timestamp_for_file()
    if 'timestamp' in kwargs:
        if kwargs['timestamp'] is not None:
            ts = utils.misc.timestamp_management.generate_iso_timestamp_for_file(kwargs['timestamp'])
        else:
            ts = None
        del kwargs['timestamp']
    if 'prefix' in kwargs:
        prefix = kwargs['prefix']
        del kwargs['prefix']
    if 'suffix' in kwargs:
        suffix = kwargs['suffix']
        del kwargs['suffix']
    if suffix.startswith('.'):
        suffix = suffix[1:] # avoid ".." for suffix
    if target_platform and '-' in target_platform:
        raise ValueError(f'platform must not contain a hyphen (platform={target_platform})')
    if '-' in service:
        raise ValueError(f'service must not contain a hyphen (service={service})')

    return generate_final_name(
        [prefix,
        target_platform,
        service,
        ts,
        suffix,
        max_len],
        **kwargs)

def extract_keys_from_file_name(file_name : str) -> dict:
    '''
    Given a file name, extract the keys and values from the file name,
    then validate that fields we expect are present.
    '''
    def parse_file_name(file_name: str) -> dict:
        """
        Helper function to parse a file name into a dictionary of keys and values.
        """
        # Extract the base file name (without extension) and split by '-'
        base_file_name, file_suffix = os.path.splitext(os.path.basename(file_name))
        fields = base_file_name.split('-')
        data = {
            'suffix': file_suffix.lstrip('.')
        }

        # Parse prefix
        prefix = fields.pop(0)
        next = None
        while fields and '=' not in fields[0]:
            next = fields.pop(0)
            prefix += '-' + next
        data['prefix'] = prefix
        # now let's parse through the key/value pairs
        while fields:
            next = fields.pop(0)
            if '=' not in next:
                raise ValueError(f"Invalid key-value pair format: {next}")
            key, value = next.split('=', 1)
            # now let's see if there's more to append to the value
            while fields and not '=' in fields[0]:
                value += '-' + fields.pop(0)
            data[key] = value
        return data
    data = parse_file_name(file_name)
    assert 'svc' in data, f'service field must be present in file name ({file_name})'
    if 'ts' in data:
        data['timestamp'] = utils.misc.timestamp_management.extract_iso_timestamp_from_file_timestamp(data['ts'])
        del data['ts']
    return data

def find_candidate_files(input_strings : list[str], directory : str) -> list[tuple[str,str]]:
    '''Given a directory location, find a list of candidate files that match
    the input strings.'''

    def get_unique_identifier(file_name, all_files):
        """
        Generate a unique identifier for a file by finding the shortest
        unique substring from a list of candidate files.
        """
        for i in range(1, len(file_name) + 1):
            for j in range(len(file_name) - i + 1):
                substring = file_name[j:j+i]
                if sum(substring in f for f in all_files) == 1:
                    return substring
        return file_name

    all_files = os.listdir(directory)
    matched_files = []

    for file in all_files:
        matched_files.append((file, get_unique_identifier(file, all_files)))

    if len(input_strings) == 0:
        return matched_files

    candidates = matched_files[:]

    for input_string in input_strings:
        updated_candidates = []
        for candidate, unique_id in candidates:
            if input_string in candidate:
                updated_candidates.append((candidate, unique_id))
        candidates = updated_candidates

    if len(candidates) > 0:
        return candidates
    return []

def print_candidate_files(candidates : list[tuple[str,str]]) -> None:
    '''Print the candidate files in a nice format.'''
    print(candidates)
    if len(candidates) == 0:
        print('No candidate files found')
        return
    unique_id_label = 'Unique identifier'
    unique_id_label_length = len(unique_id_label)
    max_unique_id_length = unique_id_label_length
    for file, unique_id in candidates:
        if len(unique_id) > max_unique_id_length:
            max_unique_id_length = len(unique_id)
    print('Unique identifier', (max_unique_id_length-len('Unique identifier')) * ' ', 'File name')
    for file, unique_id in candidates:
        print(f'{unique_id.strip()} {(max_unique_id_length-len(unique_id))*" "} {file}')
