'''
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.

Project Indaleko
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

from dataclasses import dataclass
from uuid import UUID
from apischema.graphql import graphql_schema
from graphql import print_schema

from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel

class IndalekoSourceDataModel(IndalekoRecordDataModel):
    '''Defines the data model for source data (e.g., where the data came from)'''

    @dataclass
    class SourceData(IndalekoDataModel.SourceIdentifier):
        '''Defines the data model for source data.'''

    @staticmethod
    def get_source_data(uuid : UUID) -> 'IndalekoSourceDataModel.SourceData':
        '''Lookup the source data'''
        return IndalekoSourceDataModel.SourceData(
            Identifier=uuid,
            Version='1.0',
            Description='This is a test record'
        )


    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the IndalekoDataModel'''
        return [IndalekoSourceDataModel.get_source_data]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the IndalekoDataModel'''
        return [IndalekoSourceDataModel.SourceData]

def main():
    '''Test code for the IndalekoDataModel class'''
    print("This is the IndalekoDataModel module")
    print('graphql schema:')
    print(print_schema(graphql_schema(query=IndalekoSourceDataModel.get_queries(),
                                      types=IndalekoSourceDataModel.get_types())))

if __name__ == "__main__":
    main()
