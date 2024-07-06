'''
This module defines the common database schema for Activity Data.

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
'''
'''
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.

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
'''
from datetime import datetime
from graphql import print_schema
from uuid import UUID
from typing import Annotated, List
from dataclasses import dataclass
from apischema.graphql import graphql_schema
from apischema.metadata import required


from IndalekoDataModel import IndalekoDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoActivityContextDataModel(IndalekoRecordDataModel):
    '''This is the data model for the Indaleko activity context.'''
    @dataclass
    class ActivityContext:

        ActivityContextIdentifier : Annotated[
            IndalekoDataModel.IndalekoUUID,
            required
        ]

        ActivityType: Annotated[
            IndalekoDataModel.IndalekoUUID,
            required
        ]

        Timestamps : List[IndalekoDataModel.Timestamp]

    @staticmethod
    def get_activity_context() -> 'IndalekoActivityContextDataModel.ActivityContext':
        '''Return an activity context.'''
        indaleko_activity_context = IndalekoActivityContextDataModel.ActivityContext(
            ActivityContextIdentifier=IndalekoDataModel.IndalekoUUID(
                UUID=UUID('00000000-0000-0000-0000-000000000000'),
                Label='Activity Context Identifier'
            ),
            ActivityType=IndalekoDataModel.IndalekoUUID(
                UUID=UUID('00000000-0000-0000-0000-000000000000'),
                Label='Activity Type Identifier'),
            Timestamps=[IndalekoDataModel.Timestamp(
                Label=UUID('00000000-0000-0000-0000-000000000000'),
                Value=datetime.now())
            ]
        )
        return indaleko_activity_context

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the schema.'''
        return [IndalekoActivityContextDataModel.get_activity_context]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the schema.'''
        return [IndalekoActivityContextDataModel.ActivityContext]

def main():
    '''Test code for IndalekoObjectDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(
        query=IndalekoActivityContextDataModel.get_queries(),
        types=IndalekoActivityContextDataModel.get_types()))
    )

if __name__ == '__main__':
    main()
