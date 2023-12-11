import argparse
from typing import Any
import uuid
import json
import datetime

'''
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
'''

class IndalekoObject:
    '''
    This defines the information that makes up an Indaleko Object (the
    things we store in the index)
    '''
    Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema#",
        "$id" : "https://activitycontext.work/schema/indaleko-object.json",
        "title": "Indaleko Object Schema",
        "description": "Schema for the JSON representation of an Indaleko Object, which is used for indexing storage content.",
        "type": "object",
        "rule" : {
            "type" : "object",
            "properties" : {
                "Label" : {
                    "type" : "string",
                    "description" : "The object label (like a file name)."
                },
                "URI" : {
                    "type" : "string",
                    "description" : "The URI of the object."
                },
                "ObjectIdentifier" : {
                    "type" : "string",
                    "description" : "The object identifier (UUID).",
                    "format" : "uuid",
                },
                "LocalIdentifier": {
                    "type" : "string",
                    "description" : "The local identifier used by the storage system to find this, such as a UUID or inode number."
                },
                "Timestamps" : {
                    "type" : "array",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" : "UUID representing the semantic meaning of this timestamp.",
                            "format": "uuid",
                        },
                        "Value" : {
                            "type" : "string",
                            "description" : "Timestamp in ISO date and time format.",
                            "format" : "date-time",
                        },
                    },
                    "required" : [
                        "Label",
                        "Value"
                    ],
                    "description" : "List of timestamps with UUID-based semantic meanings associated with this object."
                },
                "Size" : {
                    "type" : "integer",
                    "description" : "Size of the object in bytes."
                },
                "RawData" : {
                    "type" : "string",
                    "description" : "Raw data captured for this object.",
                    "contentEncoding" : "base64",
                    "contentMediaType" : "application/octet-stream",
                },
                "SemanticAttributes" : {
                    "type" : "array",
                    "description" : "Semantic attributes associated with this object.",
                    "properties" : {
                        "UUID" : {
                            "type" : "string",
                            "description" : "The UUID for this attribute.",
                            "format" : "uuid",
                        },
                        "Data" : {
                            "type" : "string",
                            "description" : "The data associated with this attribute.",
                        },
                    },
                    "required" : [
                        "UUID",
                        "Data"
                    ]
                }
            },
            "required" : [
                "URI",
                "ObjectIdentifier",
                "Timestamps",
                "Size",
            ]
        }
    }

class IndalekoRelationship:
    '''
    This schema defines the fields that are required as part of identifying
    relationships between objects.
    '''
    Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema#",
        "$id" : "https://activitycontext.work/schema/indaleko-relationship.json",
        "title" : "Indaleko Relationship Schema",
        "description" : "Schema for the JSON representation of an Indaleko Relationship, which is used for identifying related objects.",
        "type" : "object",
        "rule" : {
            "properties" : {
                "object1" : {
                    "type" : "string",
                    "format" : "uuid",
                    "description" : "The Indaleko UUID for the first object in the relationship.",
                },
                "object2" : {
                    "type" : "string",
                    "format" : "uuid",
                    "description" : "The Indaleko UUID for the second object in the relationship.",
                },
                "relationship" : {
                    "type" : "string",
                    "description" : "The UUID specifying the specific relationship between the two objects.",
                    "format" : "uuid",
                },
                "metadata" :  {
                    "type" : "array",
                    "items" : {
                        "type" : "object",
                        "properties" : {
                            "UUID" : {
                                "type" : "string",
                                "format" : "uuid",
                                "description" : "The UUID for this metadata.",
                            },
                            "Data" : {
                                "type" : "string",
                                "description" : "The data associated with this metadata.",
                            },
                        },
                        "required" : ["UUID", "Data"],
                    },
                    "description" : "Optional metadata associated with this relationship.",
                },
            },
            "required" : ["object1", "object2" , "relationship"],
        },
    }

class IndalekoSource:
        '''This schema defines the fields that are required as part of this
        metadata.  Additional (optional) metadata can be included.'''
        Schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/source.json",
            "title": "Data source schema",
            "description": "This schema describes information about the sources of metadata within the Indaleko system.",
            "type": "object",
            "rule" : {
                "properties": {
                    "identifier": {
                        "description": "This is the UUID of the given source for this metadata.",
                        "type": "string",
                        "format": "uuid"
                    },
                    "version": {
                        "description": "This is the version of the source provider. Versioning allows evolution of the data generated by the source.",
                        "type": "string",
                    },
                },
                "required": ["identifier", "version"]
            }
        }


        def __init__(self, identifier : uuid.UUID, version : str, description : str) -> None:
            '''The identifier is a UUID, the version is a string, and the
            description is freeform text describing this source.'''
            ### Start with the public fields
            if not isinstance(identifier, uuid.UUID):
                raise TypeError('identifier must be a UUID')
            self.__identifier = identifier
            if type(version) is not str:
                raise TypeError('version must be a string')
            self.__version = version
            ## now we have internal fields that are not part of the stored data type
            if type(description) is not str and type(description) is not None:
                raise TypeError('description must be a string or None')
            self.__description = description
            self.__db_key = datetime.datetime.utcnow() # preserve date this was created

            def to_dict(self) -> dict:
                return {
                    'SourceIdentifier': str(self.__identifier),
                    'Version': self.__version,
                }

            def __str__(self) -> str:
                return json.dumps(self.to_dict())


        def set_db_key(self, db_key : str) -> 'IndalekoSource':
            self.__db_key = db_key
            return self


        def get_db_key(self) -> str:
            return self.__db_key


        def to_dict(self) -> dict:
            return {
                'SourceIdentifier': str(self.__identifier),
                'Version': self.__version,
            }


        def get_source_identifier(self) -> uuid.UUID:
            return self.__identifier


        def get_version(self) -> str:
            return self.__version


        def get_description(self) -> str:
            return self.__description


        def to_dict(self) -> dict:
            return {
                'SourceIdentifier': str(self.__identifier),
                'Version': self.__version,
                'Description': self.__description,
                'DBKey': self.__db_key,
            }


        def __str__(self) -> str:
            return json.dumps(self.to_dict())


        def get_schema(self) -> str:
            return json.dumps(self.Schema, indent=4)


class IndalekoRecord:
    '''This defines the format of a "record" within Indaleko'''

    keyword_map = (
        ('__raw_data__', 'Data'),
        ('__attributes__', 'Attributes'),
        ('__source__', 'Source'),
    )

    def __init__(self, raw_data : bytes, attributes : dict, source : IndalekoSource) -> None:
        self.__raw_data__ = raw_data
        self.__attributes__ = attributes
        self.__source__ = source

    def to_json(self):
        tmp = {}
        for field, keyword in self.keyword_map:
            if hasattr(self, field):
                tmp[keyword] = self.__dict__[field]
        return json.dumps(tmp, indent=4)





class Indaleko:
    '''This is the python implementation of the Indaleko data format.'''


    class Source:
        '''This schema defines the fields that are required as part of this
        metadata.  Additional (optional) metadata can be included.'''
        Schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/source.json",
            "title": "Data source schema",
            "description": "This schema describes information about the sources of metadata within the Indaleko system.",
            "type": "object",
            "properties": {
                "identifier": {
                    "description": "This is the UUID of the given source for this metadata.",
                    "type": "string",
                    "format": "uuid"
                },
                "version": {
                    "description": "This is the version of the source provider. Versioning allows evolution of the data generated by the source.",
                    "type": "string",
                },
            },
            "required": ["identifier", "version"]
        }


        def __init__(self, identifier : uuid.UUID, version : str, description : str) -> None:
            '''The identifier is a UUID, the version is a string, and the
            description is freeform text describing this source.'''
            ### Start with the public fields
            if not isinstance(identifier, uuid.UUID):
                raise TypeError('identifier must be a UUID')
            self.__identifier = identifier
            if type(version) is not str:
                raise TypeError('version must be a string')
            self.__version = version
            ## now we have internal fields that are not part of the stored data type
            if type(description) is not str and type(description) is not None:
                raise TypeError('description must be a string or None')
            self.__description = description
            self.__db_key = datetime.datetime.utcnow() # preserve date this was created

            def to_dict(self) -> dict:
                return {
                    'SourceIdentifier': str(self.__identifier),
                    'Version': self.__version,
                }

            def __str__(self) -> str:
                return json.dumps(self.to_dict())


        def set_db_key(self, db_key : str) -> 'Source':
            self.__db_key = db_key
            return self


        def get_db_key(self) -> str:
            return self.__db_key


        def to_dict(self) -> dict:
            return {
                'SourceIdentifier': str(self.__identifier),
                'Version': self.__version,
            }


        def get_source_identifer(self) -> uuid.UUID:
            return self.__identifier


        def get_version(self) -> str:
            return self.__version


        def get_description(self) -> str:
            return self.__description


        def to_dict(self) -> dict:
            return {
                'SourceIdentifier': str(self.__identifier),
                'Version': self.__version,
                'Description': self.__description,
                'DBKey': self.__db_key,
            }


        def __str__(self) -> str:
            return json.dumps(self.to_dict())


        def get_schema(self) -> str:
            return json.dumps(self.Schema, indent=4)



    class Record:

        Schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://fsgeek.ca/indaleko/schema/record.json",
            "title": "Indaleko Record Schema",
            "description": "Schema for the JSON representation of an abstract record within Indaleko.",

            "type": "object",
            "properties": {
                "Source Identifier": { "$ref" : "schema/source.json" },
                "Timestamp": {
                    "type" : "string",
                    "description" : "The timestamp of when this record was created.",
                    "format" : "date-time",
                },
                "Attributes" : {
                    "type" : "object",
                    "description" : "The attributes extracted from the source data.",
                },
                "Data" : {
                    "type" : "string",
                    "description" : "The raw (uninterpreted) data from the source.",
                }
            },
            "required": ["Source Identifier", "Timestamp", "Attributes", "Data"]
        }


        def __init__(self, source : 'Indaleko.Source', attributes : dict, data : bytes):
            '''A record captures data gathered from an identified source,
            specific attributes extracted from the source data, and the original
            data.  The idea behind this is to permit sources to vary over time
            (versioning), with specific information converted to a common
            language (the attributes) and the original data preserved for future
            processing.  The fields can either be persistent (e.g., what is
            stored/loaded from the database) or transient (e.g., what is useful
            at runtime, such as for debugging.)'''
            if not isinstance(source, Indaleko.Source):
                raise TypeError('source must be a Source')
            self.__source = source
            if not isinstance(attributes, dict):
                raise TypeError('attributes must be a dict')
            self.__attributes = attributes
            if not isinstance(data, bytes):
                raise TypeError('data must be bytes')
            self.__data = data
            self.__timestamp = datetime.datetime.utcnow()


        def get_source(self) -> 'Source':
            return self.__source


        def get_attributes(self) -> dict:
            return self.__attributes


        def get_data(self) -> bytes:
            return self.__data

        def to_dict(self) -> dict:
            return {
                'Source': self.__source.to_dict(),
                'Attributes': self.__attributes,
                'Data': self.__data,
                'Timestamp': self.__timestamp,
            }

    class Machine:
        '''This class is intended to capture information about the specific
        machine where the data is being collected.  This becomes important when
        we have multiple machines collecting data, and we want to be able to
        identify information relative to the machine that collected it.  For
        example, a file URL isn't really useful by itself, since the file
        moniker does not properly identify how to retrieve the file. This isn't
        an issue with cloud services.'''

        def __init__(self, hostname : str, ip_address : str, mac_address : str, description : str) -> None:
            pass



    def __init__(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()
    print(args)


if __name__ == "__main__":
    main()
