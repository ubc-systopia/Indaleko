"""
The purpose of this package is to define the core data types used in Indaleko.

Indaleko is a Unified Private Index (UPI) service that enables the indexing of
storage content (e.g., files, databases, etc.) in a way that extracts useful
metadata and then uses it for creating a rich index service that can be used in
a variety of ways, including improving search results, enabling development of
non-traditional data visualizations, and mining relationships between objects to
enable new insights.

Indaleko is not a storage engine.  Rather, it is a metadata service that relies
upon storage engines to provide the data to be indexed.  The storage engines can
be local (e.g., a local file system,) remote (e.g., a cloud storage service,) or
even non-traditional (e.g., applications that provide access to data in some
way, such as Discord, Teams, Slack, etc.)

Indaleko uses three distinct classes of metadata to enable its functionality:

* Storage metadata - this is the metadata that is provided by the storage
  services
* Semantic metadata - this is the metadata that is extracted from the objects,
  either by the storage service or by semantic transducers that act on the files
  when it is available on the local device(s).
* Activity context - this is metadata that captures information about how the
  file was used, such as when it was accessed, by what application, as well as
  ambient information, such as the location of the device, the person with whom
  the user was interacting, ambient conditions (e.g., temperature, humidity, the
  music the user is listening to, etc.) and even external events (e.g., current
  news, weather, etc.)

To do this, Indaleko stores information of various types in databases.  One of
the purposes of this package is to encapsulate the data types used in the system
as well as the schemas used to validate the data.

The general architecture of Indaleko attempts to be flexible, while still
capturing essential metadata that is used as part of the indexing functionality.
Thus, to that end, we define both a generic schema and in some cases a flexible
set of properties that can be extracted and stored.  Since this is a prototype
system, we have strived to "keep it simple" yet focus on allowing us to explore
a broad range of storage systems, semantic transducers, and activity data sources.

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
import uuid
import datetime
from IndalekoObjectSchema import IndalekoObjectSchema
from IndalekoServicesSchema import IndalekoServicesSchema
from IndalekoRelationshipSchema import IndalekoRelationshipSchema
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema

class Indaleko:
    '''This class defines constants used by Indaleko.'''
    default_data_dir = './data'
    default_config_dir = './config'
    default_log_dir = './logs'

    Indaleko_Objects = 'Objects'
    Indaleko_Relationships = 'Relationships'
    Indaleko_Services = 'Services'
    Indaleko_MachineConfig = 'MachineConfig'

    Collections = {
        Indaleko_Objects: {
            'schema' : IndalekoObjectSchema.get_schema(),
            'edge' : False,
            'indices' : {
                'URI' : {
                    'fields' : ['URI'],
                    'unique' : True,
                    'type' : 'persistent'
                },
                'file identity' : {
                    'fields' : ['ObjectIdentifier'],
                    'unique' : True,
                    'type' : 'persistent'
                },
                'local identity' : {
                    # Question: should this be combined with other info to allow uniqueness?
                    'fields' : ['LocalIdentifier'],
                    'unique' : False,
                    'type' : 'persistent'
                },
            },
        },
        Indaleko_Relationships : {
            'schema' : IndalekoRelationshipSchema.get_schema(),
            'edge' : True,
            'indices' : {
                'relationship' : {
                    'fields' : ['relationship'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'vertex1' : {
                    'fields' : ['object1'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'vertex2' : {
                    'fields' : ['object2'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'edge' : {
                    'fields' : ['object1', 'object2'],
                    'unique' : False,
                    'type' : 'persistent'
                },
            }
        },
        Indaleko_Services : {
            'schema' : IndalekoServicesSchema.get_schema(),
            'edge' : False,
            'indices' : {
                'identifier' : {
                    'fields' : ['Name'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            },
        },
        Indaleko_MachineConfig : {
            'schema' : IndalekoMachineConfigSchema.get_schema(),
            'edge' : False,
            'indices' : { },
        }
    }

    @staticmethod
    def validate_uuid_string(uuid_string : str) -> bool:
        """Given a string, verify that it is in fact a valid uuid."""
        if not isinstance(uuid_string, str):
            print(f'uuid is not a string it is a {type(uuid)}')
            return False
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            print('uuid is not valid')
            return False

    @staticmethod
    def validate_iso_timestamp(source : str) -> bool:
        """Given a string, ensure it is a valid ISO timestamp."""
        valid = True
        if not isinstance(source, str):
            valid = False
        else:
            try:
                datetime.datetime.fromisoformat(source)
            except ValueError:
                valid = False
        return valid


def main():
    """Test code for Indaleko.py"""
    print('At the present time, there is no test code in Indaleko.py')

if __name__ == "__main__":
    main()
