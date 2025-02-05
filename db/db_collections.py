'''
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
import json
import os
import sys

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import \
    IndalekoActivityDataRegistrationDataModel, \
    IndalekoIdentityDomainDataModel, \
    IndalekoObjectDataModel, \
    IndalekoMachineConfigDataModel, \
    IndalekoRelationshipDataModel, \
    IndalekoServiceDataModel, \
    IndalekoUserDataModel
from activity import IndalekoActivityDataModel
# pylint: enable=wrong-import-position


class IndalekoDBCollections:
    '''Defines the set of well-known collections used by Indaleko.'''

    Indaleko_Object_Collection = 'Objects'
    Indaleko_Relationship_Collection = 'Relationships'
    Indaleko_Service_Collection = 'Services'
    Indaleko_MachineConfig_Collection = 'MachineConfig'
    Indaleko_ActivityDataProvider_Collection = 'ActivityDataProviders'
    Indaleko_ActivityContext_Collection = 'ActivityContext'
    Indaleko_MusicActivityContext_Collection = 'MusicActivityContext'
    Indaleko_TempActivityContext_Collection = 'TempActivityContext'
    Indaleko_GeoActivityContext_Collection = 'GeoActivityContext'

    Indaleko_Identity_Domain_Collection = 'IdentityDomains'
    Indaleko_User_Collection = 'Users'
    Indaleko_User_Relationship_Collection = 'UserRelationships'
    Indaleko_Performance_Data_Collection = 'PerformanceData'
    Indaleko_Query_History_collection = "QueryHistory"

    Collections = {
        Indaleko_Object_Collection: {
            'schema': IndalekoObjectDataModel.get_arangodb_schema(),
            'edge': False,
            'indices': {
                'URI': {
                    'fields': ['URI'],
                    'unique': True,
                    'type': 'persistent'
                },
                'file identity': {
                    'fields': ['ObjectIdentifier'],
                    'unique': True,
                    'type': 'persistent'
                },
                'local identity': {
                    # Question: should this be combined with other info to allow uniqueness?
                    'fields': ['LocalIdentifier'],
                    'unique': False,
                    'type': 'persistent'
                },
            },
        },
        Indaleko_Relationship_Collection: {
            'schema': IndalekoRelationshipDataModel.get_arangodb_schema(),
            'edge': True,
            'indices': {
                'relationship': {
                    'fields': ['relationship'],
                    'unique': False,
                    'type': 'persistent'
                },
                'vertex1': {
                    'fields': ['object1'],
                    'unique': False,
                    'type': 'persistent'
                },
                'vertex2': {
                    'fields': ['object2'],
                    'unique': False,
                    'type': 'persistent'
                },
                'edge': {
                    'fields': ['object1', 'object2'],
                    'unique': False,
                    'type': 'persistent'
                },
            }
        },
        Indaleko_Service_Collection: {
            'schema': IndalekoServiceDataModel.get_arangodb_schema(),
            'edge': False,
            'indices': {
                'identifier': {
                    'fields': ['Name'],
                    'unique': True,
                    'type': 'persistent'
                },
            },
        },
        Indaleko_MachineConfig_Collection: {
            'schema': IndalekoMachineConfigDataModel.get_arangodb_schema(),
            'edge': False,
            'indices': {
            },
        },
        Indaleko_ActivityDataProvider_Collection: {
            'schema':  IndalekoActivityDataRegistrationDataModel.get_arangodb_schema(),
            'edge': False,
            'indices': {
            },
        },
        Indaleko_ActivityContext_Collection : {
            'schema' : IndalekoActivityDataModel.get_arangodb_schema(),
            'edge' : False,
            'indices' : {},
        },
        Indaleko_MusicActivityContext_Collection : {
            'schema' : IndalekoActivityDataModel.get_arangodb_schema(),
            'edge' : False,
            'indices' : {},
        },
        Indaleko_GeoActivityContext_Collection : {
            'schema' : IndalekoActivityDataModel.get_arangodb_schema(),
            'edge' : False,
            'indices' : {},
        },Indaleko_TempActivityContext_Collection : {
            'schema' : IndalekoActivityDataModel.get_arangodb_schema(),
            'edge' : False,
            'indices' : {},
        },
        Indaleko_Identity_Domain_Collection: {
            'schema': IndalekoIdentityDomainDataModel.get_arangodb_schema(),
            'edge': False,
            'indices': {
            }
        },
        Indaleko_User_Collection:  {
            'schema': IndalekoUserDataModel.get_arangodb_schema(),
            'edge': False,
            'indices': {
                'identifier': {
                    'fields': ['Identifier'],
                    'unique': True,
                    'type': 'persistent'
                },
            },
        },
        # Indaleko_User_Relationship_Collection:  'This needs to be tied into NER work'
        Indaleko_Performance_Data_Collection:  {
            'schema': None,
            'edge': False,
            'indices': {
            }
        },
        Indaleko_Query_History_collection: {
            'schema': None,
            'edge': False,
            'indices': {
            }
        }
    }


def main():
    '''Main entry point for the script.'''
    ic('Indaleko Database Collections')
    for collection in IndalekoDBCollections.Collections:
        ic(f'Collection: {collection}')
        for key, value in IndalekoDBCollections.Collections[collection].items():
            if 'schema' == key:
                schema = json.dumps(value, indent=4)
                print(f'Schema: {schema}')
            else:
                ic(f'  {key}: {value}')
        print('\n')


if __name__ == '__main__':
    main()
