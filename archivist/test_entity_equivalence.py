"""
Test script for entity equivalence functionality.

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
"""

import argparse
import os
import sys


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from archivist.entity_equivalence import EntityEquivalenceManager
from data_models.named_entity import IndalekoNamedEntityType
from db.db_collections import IndalekoDBCollections


# pylint: enable=wrong-import-position


def reset_collections():
    """Reset the entity equivalence collections for testing."""
    from db.i_collections import IndalekoCollections

    # Get collection names from central registry
    nodes_collection_name = IndalekoDBCollections.Indaleko_Entity_Equivalence_Node_Collection
    relations_collection_name = IndalekoDBCollections.Indaleko_Entity_Equivalence_Relation_Collection
    groups_collection_name = IndalekoDBCollections.Indaleko_Entity_Equivalence_Group_Collection

    # Use central collections management
    nodes_collection = IndalekoCollections.get_collection(nodes_collection_name)
    relations_collection = IndalekoCollections.get_collection(relations_collection_name)
    groups_collection = IndalekoCollections.get_collection(groups_collection_name)

    # Truncate the collections
    nodes_collection._arangodb_collection.truncate()

    relations_collection._arangodb_collection.truncate()

    groups_collection._arangodb_collection.truncate()


def test_entity_creation():
    """Test creating entity equivalence nodes."""

    # Initialize manager
    manager = EntityEquivalenceManager()

    # Create entities
    entity1 = manager.add_entity_reference(
        name="Elizabeth Jones",
        entity_type=IndalekoNamedEntityType.person,
        canonical=True,
        source="test",
        context="Full name",
    )

    entity2 = manager.add_entity_reference(
        name="Beth",
        entity_type=IndalekoNamedEntityType.person,
        source="test",
        context="Nickname",
    )


    # Verify data
    assert entity1.name == "Elizabeth Jones"
    assert entity1.canonical is True
    assert entity2.name == "Beth"
    assert entity2.canonical is False

    return entity1, entity2


def test_entity_merging(entity1, entity2):
    """Test merging entity equivalence nodes."""

    # Initialize manager
    manager = EntityEquivalenceManager()

    # Merge entities
    manager.merge_entities(
        entity2.entity_id,
        entity1.entity_id,
        relation_type="nickname",
        confidence=0.9,
    )


    # Verify canonical reference
    canonical = manager.get_canonical_reference(entity2.entity_id)

    assert canonical is not None
    assert canonical.entity_id == entity1.entity_id
    assert canonical.name == "Elizabeth Jones"

    # Verify all references
    all_refs = manager.get_all_references(entity1.entity_id)
    ref_names = [ref.name for ref in all_refs]

    assert len(all_refs) == 2
    assert "Elizabeth Jones" in ref_names
    assert "Beth" in ref_names

    return entity1, entity2


def test_entity_graph(entity1):
    """Test generating entity graphs."""

    # Initialize manager
    manager = EntityEquivalenceManager()

    # Get entity graph
    graph = manager.get_entity_graph(entity1.entity_id)


    # Print graph structure
    for _node in graph["nodes"]:
        pass

    for _edge in graph["edges"]:
        pass

    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1



def test_multiple_equivalence_classes():
    """Test handling multiple equivalence classes."""

    # Initialize manager
    manager = EntityEquivalenceManager()

    # Person entities
    person1 = manager.add_entity_reference(
        name="John Smith",
        entity_type=IndalekoNamedEntityType.person,
        canonical=True,
    )

    person2 = manager.add_entity_reference(
        name="Johnny",
        entity_type=IndalekoNamedEntityType.person,
    )

    # Location entities
    location1 = manager.add_entity_reference(
        name="New York City",
        entity_type=IndalekoNamedEntityType.location,
        canonical=True,
    )

    location2 = manager.add_entity_reference(
        name="NYC",
        entity_type=IndalekoNamedEntityType.location,
    )

    # Merge within each class
    manager.merge_entities(person2.entity_id, person1.entity_id, "nickname")
    manager.merge_entities(location2.entity_id, location1.entity_id, "abbreviation")

    # Get all groups
    groups = manager.list_entity_groups()

    for group in groups:
        [m["name"] for m in group["members"]]

    # Verify groups are separate
    person_group = None
    location_group = None

    for group in groups:
        if group["canonical"]["name"] == "John Smith":
            person_group = group
        elif group["canonical"]["name"] == "New York City":
            location_group = group

    assert person_group is not None
    assert location_group is not None
    assert len(person_group["members"]) == 2
    assert len(location_group["members"]) == 2

    # Verify canonical references
    p_canonical = manager.get_canonical_reference(person2.entity_id)
    l_canonical = manager.get_canonical_reference(location2.entity_id)

    assert p_canonical.name == "John Smith"
    assert l_canonical.name == "New York City"



def test_statistics():
    """Test entity equivalence statistics."""

    # Initialize manager
    manager = EntityEquivalenceManager()

    # Get statistics
    stats = manager.get_stats()


    assert stats["node_count"] >= 4
    assert stats["group_count"] >= 2
    assert stats["relation_count"] >= 2



def run_all_tests():
    """Run all entity equivalence tests."""

    # Reset collections for clean test
    reset_collections()

    # Run tests
    entity1, entity2 = test_entity_creation()
    entity1, entity2 = test_entity_merging(entity1, entity2)
    test_entity_graph(entity1)
    test_multiple_equivalence_classes()
    test_statistics()



def main():
    """Main function for running entity equivalence tests."""
    parser = argparse.ArgumentParser(
        description="Test entity equivalence functionality",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset equivalence collections",
    )
    parser.add_argument("--create", action="store_true", help="Test entity creation")
    parser.add_argument("--merge", action="store_true", help="Test entity merging")
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Test entity graph generation",
    )
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Test multiple equivalence classes",
    )
    parser.add_argument("--stats", action="store_true", help="Test statistics")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    if args.reset:
        reset_collections()

    if args.all:
        run_all_tests()
        return

    if args.create:
        entity1, entity2 = test_entity_creation()

    if args.merge:
        if "entity1" not in locals():
            entity1, entity2 = test_entity_creation()
        test_entity_merging(entity1, entity2)

    if args.graph:
        if "entity1" not in locals():
            entity1, entity2 = test_entity_creation()
            test_entity_merging(entity1, entity2)
        test_entity_graph(entity1)

    if args.multi:
        test_multiple_equivalence_classes()

    if args.stats:
        test_statistics()

    if not any(
        [
            args.reset,
            args.create,
            args.merge,
            args.graph,
            args.multi,
            args.stats,
            args.all,
        ],
    ):
        parser.print_help()


if __name__ == "__main__":
    main()
