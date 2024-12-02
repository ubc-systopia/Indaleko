"""
This module provides the front-end interface for using an AI agent
to search the Indaleko Personal Index service.

Project Indaleko
Copyright (C) 2024 Tony Mason

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
"""

from openai import OpenAI

from enum import Enum

from Indaleko import Indaleko

class IndalekoAISearch:
    '''This class provides the front-end interface for using an AI agent'''

    default_url = 'http://localhost:1234/v1'
    default_api_key = 'lm-studio'
    default_categories = []

    class Collection(str, Enum):
        Objects = Indaleko.Indaleko_Object_Collection
        Relationships = Indaleko.Indaleko_Relationship_Collection
        Machines = 'MachineConfig'

    class object_columns(str, Enum):
        uri = 'URI'
        label = 'Label'
        object_identifier = 'ObjectIdentifier'
        size = 'Size'
        timestamps = 'Timestamps'

    class relationship_columns(str, Enum):
        object1 = 'Object1'
        object2 = 'Object2'
        relationship_type = 'Relationship'

    class machineconfig_columns(str, Enum):
        machine_name = 'MachineName'
        machine_type = 'MachineType'
        machine_config = 'MachineConfig'

    def __init__(self, **kwargs):
        '''Initialize the AI agent'''
        self.base_url = kwargs.get('base_url', IndalekoAISearch.default_url)
        self.api_key = kwargs.get('api_key', IndalekoAISearch.default_api_key)
        self.categories = kwargs.get('categories', [])
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)


def main():
    '''Main entry point for the program'''
    ai_agent = IndalekoAISearch(base_url="http://localhost:1234/v1", api_key="lm-studio")
    print(ai_agent.client)

if __name__ == '__main__':
    main()
