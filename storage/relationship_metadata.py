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
from storage.i_relationship import IndalekoRelationship
from utils import IndalekoSingleton
# pylint: enable=wrong-import-position


class RelationshipCollectionMetadata(IndalekoSingleton):
    '''This class provides a basic (default) implementation of the relationship collection metadata.'''

    default_metadata = IndalekoCollectionMetadataDataModel(
        key=IndalekoDBCollections.Indaleko_Relationship_Collection,
        Description=dedent(
            'In Indaleko, a relationship represents a connection between two data elements. '
            'For example, a file residing in a directory forms a contains relationship. '
            'Relationships are stored as edges in ArangoDB, which are inherently uni-directional. '
            'To account for this, Indaleko defines paired relationships when needed, such as '
            "'contains' (A → B) and 'contained by' (B → A)."
            'A relationship in Indaleko represents a connection between two data '
            'elements. A classic example is a file residing in a directory. '
            'The contents of this collection are logically edges in the ArangoDB model. '
            'Edges in ArangoDB are uni-directional, which is why in many cases you will see '
            'two definitions, such as "contains" and "contained by". '
            'A relationship consists of a pair of vertices (documents) which include '
            'the specification of the '
            'collection that contains them, and a UUID that defines the meaning '
            'of the relationship.  '
            'Indaleko dynamically constructs a complete list of UUID labels and '
            'their meanings. If this list is missing or incomplete, this is an Indaleko '
            'data issue, not your issue. Please report any missing UUID meanings '
            'as feedback for the maintainers. '
            'Relationships may be one-to-one, one-to-many, or many-to-many depending '
            'on the specific relationship. You should account for this when constructing queries. '
            'Given that these relationships form a graph, it is likely there will be '
            'cycles in the graph. '
            'However, you do not need to consider that in your AQL construction as this is a prototype '
            'and we can address that in future versions, if necessary. '
            'Currently, the relationship definitions are storage-focused.  In your consideration of the '
            'human queries, feedback on adding additional relationships will be appreciated. '
        ),
        QueryGuidelines=[
            dedent(
                'One example of a common relationship is the "contains" relationship, which is used to indicate that '
                'an object is logically contained inside another object, like a file (or directory) contained inside a '
                'directory. The UUID for this relationship is '
                f'{IndalekoRelationship.RelationshipType.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR}. '
            ),
            dedent(
                'Another example of a relationship, albeit uncommon, is the "contained by" relationship, which is used '
                'to indicate that an object is logically contained by another object, like a file being '
                '"contained by" a directory. '
                'This relationship permits finding all of the locations from which a given object is referenced. '
                'The UUID for this relationship is '
                f'{IndalekoRelationship.RelationshipType.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR}. '
            ),
            dedent(
                'Many local storage systems have a concept of a volume, which in turn is made '
                'up of part of one device, or '
                'constructed from storage across multiple devices.  The "volume" relationship '
                'is used to indicate that an '
                'object is part of a volume.  The UUID for these  relationships are '
                f'{IndalekoRelationship.RelationshipType.VOLUME_CONTAINS_RELATIONSHIP_UUID_STR}, which indicates '
                'that the volume "contains" the object, and '
                f'{IndalekoRelationship.RelationshipType.CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR}, which indicates '
                'that the object is "contained by" the volume. '
            ),
            dedent(
                'Objects may be associated with a specific machine, and there may be relationships between objects and '
                'the containing machine.  This can be useful when a user, having found a reference to the object they '
                'want, wants to know which of their devices contains the object.  The UUID for these relationships are '
                f'{IndalekoRelationship.RelationshipType.MACHINE_CONTAINS_RELATIONSHIP_UUID_STR}, which indicates that '
                'the machine "contains" the object, and '
                f'{IndalekoRelationship.RelationshipType.CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR}, which indicates '
                'that the object is "contained by" the machine. '
            ),
            dedent(
                'The Indaleko system is designed to allow extensibility, so that new relationships can be added as '
                'they are found to be useful.  In evaluating queries, you should suggest relationships that, '
                'in your opinion, would be useful to have. '
            ),
        ],
        Schema=IndalekoDBCollections.Collections[IndalekoDBCollections.Indaleko_Relationship_Collection]['schema']
    )


def main():
    '''Main entry point for the module.'''
    metadata = RelationshipCollectionMetadata()
    print(metadata.default_metadata.model_dump_json(indent=4))


if __name__ == '__main__':
    main()
