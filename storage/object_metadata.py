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
from textwrap import dedent

# from typing import Any

# from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel
from db import IndalekoDBCollections
from storage.i_object import IndalekoObject
from utils import IndalekoSingleton
# pylint: enable=wrong-import-position


class ObjectCollectionMetadata(IndalekoSingleton):
    '''This class provides a basic (default) implementation of the object collection metadata.'''

    @staticmethod
    def get_timestamp_map() -> str:
        return json.dumps({
            IndalekoObject.CREATION_TIMESTAMP: "Creation Timestamp",
            IndalekoObject.MODIFICATION_TIMESTAMP: "Modification Timestamp",
            IndalekoObject.ACCESS_TIMESTAMP: "Access Timestamp",
            IndalekoObject.CHANGE_TIMESTAMP: "Change Timestamp"
        }, indent=4)

    default_metadata = IndalekoCollectionMetadataDataModel(
        key=IndalekoDBCollections.Indaleko_Object_Collection,
        Description=dedent(
            f'''
            ## Object Collection Overview
            An **object** in Indaleko refers to a **storage object** - typically a **file** or **directory**.

            ### Purpose
            - Objects in this collection have **normalized metadata**, providing a **consistent** view
              across different storage systems.
            - This normalization ensures that **queries behave predictably**, regardless of where the file is stored.

            ### Storage System Considerations
            - The metadata structure abstracts over **POSIX and Windows file systems**.
            - While most metadata fields exist across all storage types, **some fields are optional** depending
              on the storage provider.
            - Indaleko records **unique identifiers for files** (`ObjectIdentifier`) to provide **fast lookups**.

            ### Query Guidelines (See Below)
            - **When searching by file name, always use the `Label` field**.
            - **When retrieving a specific object, use `ObjectIdentifier` (equivalent to `_key` in ArangoDB).**

            ### Timestamps
            - The Timestamps field entries are maintained in ISO8601 format with a timezone specifier.
            - The currently defined timestamp UUIDs, along with their meaning are:
            ```json
            {get_timestamp_map()}
            ```
            '''
            ),
        QueryGuidelines=[
            dedent(
                '''
                ## Query Guidelines
                - **Primary Key**: `ObjectIdentifier` uniquely identifies each object and is
                  equivalent to `_key` in ArangoDB.
                - **Filename Search**: Use `Label` for file name lookups.

                **Full-Text Search Fields** (e.g., `CamelCaseTokenizedName`, `SnakeCaseTokenizedName`,
                `NgramTokenizedName`) **should NOT be used** in standard queries. These exist for
                potential future enhancements but are currently unindexed.
                '''
            ),
            dedent(
                """
                The URI field is meant to serve as a uniform resource identifier for an object.  However
                not all storage systems provide globally accessible URIs:
                   - For local storage, this is typically a file:// URI, and must be used relative to the
                     machine containing the data.
                   - For cloud storage, this is typically a cloud storage URI
                """
            ),
            dedent(
                'The Label field corresponds to the name that has been applied to the object in the underlying '
                'storage system.'
                'It is case preserved, though for case-insensitive systems this will not be relevant.'
                'When asked to find a file by name, title, label, etc., this is the field to use. '
                'It should always be indexed.'
            ),
            dedent(
                'The Timestamps field is a list of timestamps associated with the object. '
                'The label associated with the timestamp '
                'is a UUID, the definitions of which should be provided to you separately. '
                'These timestamps are maintained in ISO8601 '
                'format, with ArangoDB having a strict requirement they have a time zone specifier.'
            ),
            dedent(
                'The SemanticAttributes field is a list of descriptive elements that provide semantic labels '
                'to the normalized storage data associated with the file.  Presently, this mostly consists '
                'of metadata typically found in POSIX compliant systems, which are not likely to be used as '
                'part of a search unless the user explicitly requests it. '
            ),
            dedent(
                'The Size field is the size of the object in bytes.  This field is optional, as not all storage '
                'services provide this information.  For directories, this value may, or may not be valid, depending '
                'on the storage service.  For files, this value should be assumed accurate.'
            ),
            dedent(
                'The LocalIdentifier field is the identifier used by the storage system to reference the object. '
                'For POSIX compliant systems, this is typically the inode number.  This field is optional, '
                'as not all storage services provide this information.'
            ),
            dedent(
                """
                The **Volume** field is the volume associated with the object.  This field is optional, as
                cloud storage services do not have the volume concept, and thus far the extraction of this
                information is only implemented for Windows systems.  For Windows systems this information
                is important because it ensures that drive letters retain their original meaning, while the
                URI works regardless of any change to drive letters.
                """
            ),
            dedent(
                'The PosixFileAttributes field is the POSIX file attributes associated with the object. '
                'It is represented by strings representing the S_IF* values.  This field is optional, '
                'but frequently present. '
                'One common use of this field is to identify directories, as storage recorders attempt '
                'to normalize S_IFDIR from '
                'different storage systems into a common value.'
            ),
            dedent(
                'The WindowsFileAttributes field is the Windows file attributes associated with the object. '
                'This field is optional, but present for Windows local storage recorders.  It could be used '
                'to identify Windows specific attributes, such as reparse points, etc.'
            ),
            dedent(
                'CamelCaseTokenizedName is a field that is generated by the system to provide a '
                'tokenized variant of the '
                'name of the file object.  While not presently used, the goal of this field is '
                'to allow full text style searches '
                'to be performed on the name of the object. This field should be ignored for purposes '
                'of query generation.'
            ),
            dedent(
                'SnakeCaseTokenizedName is a field that is generated by the system to provide a '
                'tokenized variant of the name of the file object.  While not presently used, the '
                'goal of this field is to allow full text style searches to be performed on the name '
                'of the object. This field should be ignored for purposes of query generation.'
            ),
            dedent(
                'NgramTokenizedName is a field that is generated by the system to provide a tokenized '
                'variant of the name of the file object.  While not presently used, the goal of this field '
                'is to allow full text style searches to be performed on the name of the object. This field '
                'should be ignored for purposes of query generation.'
            ),
            dedent(
                'SpaceTokenizedName is a field that is generated by the system to provide a tokenized '
                'variant of the name of the file object.  While not presently used, the goal of this field '
                'is to allow full text style searches to be performed on the name of the object. This field '
                'should be ignored for purposes of query generation.'
            ),
            dedent(
                """
                ### Example: Retrieve File by Object Identifier
                ```json
                {
                """
                f"""
                    "FOR obj IN {IndalekoDBCollections.Indaleko_Object_Collection}
                    FILTER obj.ObjectIdentifier == '123e4567-e89b-12d3-a456-426614174000'
                    RETURN obj"
                """
                """
                }
                ```
                ### Example: Search for File by Name
                ```json
                {
                """
                f"""
                    "FOR obj IN {IndalekoDBCollections.Indaleko_Object_Collection}
                    FILTER obj.Label == 'report.pdf'
                    RETURN obj"
                """
                """}
                ```
                """
                ),
        ],
        Schema=IndalekoDBCollections.Collections[IndalekoDBCollections.Indaleko_Object_Collection]['schema']
    )


def main():
    '''Main entry point for the module.'''
    metadata = ObjectCollectionMetadata()
    print(metadata.default_metadata.model_dump_json(indent=4))
    # print(metadata.default_metadata.Description)


if __name__ == '__main__':
    main()
