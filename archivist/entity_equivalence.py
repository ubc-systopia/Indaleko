"""
Entity equivalence class implementation for Indaleko.

This module provides functionality for managing entity equivalence classes,
allowing the system to recognize different references to the same entity.

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

import os
import sys
from datetime import UTC, datetime
from uuid import UUID, uuid4

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.named_entity import IndalekoNamedEntityType
from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from utils.misc.named_entity import IndalekoNamedEntity
from utils.misc.string_similarity import jaro_winkler_similarity

# pylint: enable=wrong-import-position


class EntityEquivalenceNode(IndalekoBaseModel):
    """
    Represents a node in the entity equivalence graph.
    Each node corresponds to a specific form of an entity reference.
    """

    entity_id: UUID
    name: str
    entity_type: IndalekoNamedEntityType
    canonical: bool = False  # Is this the primary name for the entity?
    source: str | None = None  # Where this reference was found
    context: str | None = None  # Additional context about this reference
    timestamp: datetime = datetime.now(UTC)

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "entity_id": "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                "name": "Beth",
                "entity_type": IndalekoNamedEntityType.person,
                "canonical": False,
                "source": "conversation",
                "context": "mentioned as a colleague",
            },
        }


class EntityEquivalenceRelation(IndalekoBaseModel):
    """
    Represents a relation between two entity nodes in the equivalence graph.
    """

    source_id: UUID  # ID of the source entity
    target_id: UUID  # ID of the target entity
    relation_type: str  # The type of relation (alias, nickname, etc.)
    confidence: float = 1.0  # Confidence score (0-1)
    evidence: str | None = None  # Evidence supporting this relation
    timestamp: datetime = datetime.now(UTC)

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "source_id": "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                "target_id": "a81b3522-c394-40b0-a82c-a9d7fa1f7e02",
                "relation_type": "nickname",
                "confidence": 0.95,
                "evidence": "User referred to Elizabeth as Beth in conversation",
            },
        }


class EntityEquivalenceGroup(IndalekoBaseModel):
    """
    Represents a group of equivalent entity references.
    """

    group_id: UUID = uuid4()
    canonical_id: UUID  # The ID of the canonical entity reference
    entity_type: IndalekoNamedEntityType
    members: list[UUID] = []  # List of entity reference IDs in this group

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "group_id": "a81b3522-c394-40b0-a82c-a9d7fa1f7e03",
                "canonical_id": "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                "entity_type": IndalekoNamedEntityType.person,
                "members": [
                    "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                    "a81b3522-c394-40b0-a82c-a9d7fa1f7e02",
                ],
            },
        }


class EntityEquivalenceManager:
    """
    Manages entity equivalence classes in Indaleko.

    This class is responsible for:
    1. Maintaining equivalence relationships between entity references
    2. Identifying potential equivalences using string similarity and context
    3. Resolving entity references to their canonical forms
    4. Managing the persistence of equivalence data
    """

    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
        """
        Initialize the entity equivalence manager.

        Args:
            db_config: Database configuration
        """
        self.db_config = db_config
        self.entity_manager = IndalekoNamedEntity(db_config)

        # Ensure necessary collections exist
        self._setup_collections()

        # Cache for nodes and relations
        self._nodes_cache: dict[UUID, EntityEquivalenceNode] = {}
        self._groups_cache: dict[UUID, EntityEquivalenceGroup] = {}
        self._relations_cache: dict[str, EntityEquivalenceRelation] = {}

        # Load existing data
        self._load_data()

    def _setup_collections(self):
        """Set up the necessary collections in the database."""
        from db.i_collections import IndalekoCollections

        # Get collection names from central registry
        nodes_collection_name = (
            IndalekoDBCollections.Indaleko_Entity_Equivalence_Node_Collection
        )
        relations_collection_name = (
            IndalekoDBCollections.Indaleko_Entity_Equivalence_Relation_Collection
        )
        groups_collection_name = (
            IndalekoDBCollections.Indaleko_Entity_Equivalence_Group_Collection
        )

        # Use the central IndalekoCollections to get or create collections
        nodes_collection = IndalekoCollections.get_collection(nodes_collection_name)
        relations_collection = IndalekoCollections.get_collection(
            relations_collection_name,
        )
        groups_collection = IndalekoCollections.get_collection(groups_collection_name)

        # Store the collection references
        self.nodes_collection = nodes_collection._arangodb_collection
        self.relations_collection = relations_collection._arangodb_collection
        self.groups_collection = groups_collection._arangodb_collection

    def _load_data(self):
        """Load existing entity equivalence data from the database."""
        # Load nodes
        cursor = self.nodes_collection.all()
        while cursor.has_more():
            doc = cursor.next()
            node = EntityEquivalenceNode(**doc)
            self._nodes_cache[node.entity_id] = node

        # Load groups
        cursor = self.groups_collection.all()
        while cursor.has_more():
            doc = cursor.next()
            group = EntityEquivalenceGroup(**doc)
            self._groups_cache[group.group_id] = group

        # Load relations
        cursor = self.relations_collection.all()
        while cursor.has_more():
            doc = cursor.next()
            relation = EntityEquivalenceRelation(**doc)
            relation_key = f"{relation.source_id}_{relation.target_id}"
            self._relations_cache[relation_key] = relation

    def add_entity_reference(
        self,
        name: str,
        entity_type: IndalekoNamedEntityType,
        canonical: bool = False,
        source: str | None = None,
        context: str | None = None,
    ) -> EntityEquivalenceNode:
        """
        Add a new entity reference to the system.

        Args:
            name: The name or reference text
            entity_type: The type of entity
            canonical: Whether this is a canonical (primary) reference
            source: Where this reference was found
            context: Additional context about this reference

        Returns:
            The created entity reference node
        """
        # Create a new node
        node = EntityEquivalenceNode(
            entity_id=uuid4(),
            name=name,
            entity_type=entity_type,
            canonical=canonical,
            source=source,
            context=context,
        )

        # Insert into database
        node_doc = node.serialize()
        self.nodes_collection.insert(node_doc)

        # Add to cache
        self._nodes_cache[node.entity_id] = node

        # If this is a canonical reference, create a new group for it
        if canonical:
            group = EntityEquivalenceGroup(
                canonical_id=node.entity_id,
                entity_type=entity_type,
                members=[node.entity_id],
            )

            # Insert into database
            group_doc = group.serialize()
            self.groups_collection.insert(group_doc)

            # Add to cache
            self._groups_cache[group.group_id] = group

        # Check for potential matches with existing nodes
        self._find_potential_matches(node)

        return node

    def _find_potential_matches(
        self, node: EntityEquivalenceNode, similarity_threshold: float = 0.85,
    ) -> list[tuple[UUID, float]]:
        """
        Find potential matching entities for a given node.

        Args:
            node: The entity node to find matches for
            similarity_threshold: Minimum similarity score to consider a match

        Returns:
            List of (entity_id, similarity_score) tuples for potential matches
        """
        matches = []

        # Check against all existing nodes of the same type
        for existing_id, existing_node in self._nodes_cache.items():
            # Skip if not the same entity type
            if existing_node.entity_type != node.entity_type:
                continue

            # Skip self-comparison
            if existing_id == node.entity_id:
                continue

            # Compute similarity
            similarity = jaro_winkler_similarity(
                node.name.lower(), existing_node.name.lower(),
            )

            # If similarity is above threshold, add to matches
            if similarity >= similarity_threshold:
                matches.append((existing_id, similarity))

                # Suggest relation if high confidence
                if similarity >= 0.9:
                    self._suggest_relation(node.entity_id, existing_id, similarity)

        # Sort matches by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _suggest_relation(
        self, source_id: UUID, target_id: UUID, confidence: float,
    ) -> None:
        """
        Suggest a potential relation between two entity references.

        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            confidence: Confidence score for the relation
        """
        # Determine the target node and its group
        target_node = self._nodes_cache.get(target_id)
        if not target_node:
            return

        # Find the group for the target
        target_group = None
        for group in self._groups_cache.values():
            if target_id in group.members:
                target_group = group
                break

        # If target has a group but source doesn't, add source to target's group
        if target_group:
            # Check if source is already in a group
            source_in_group = False
            for group in self._groups_cache.values():
                if source_id in group.members:
                    source_in_group = True
                    break

            if not source_in_group:
                # Add relation
                self.add_relation(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type="similar_name",
                    confidence=confidence,
                    evidence=f"String similarity: {confidence:.2f}",
                )

                # Add to group
                target_group.members.append(source_id)
                self.groups_collection.update(
                    {"group_id": str(target_group.group_id)},
                    {"$set": {"members": [str(m) for m in target_group.members]}},
                )
                self._groups_cache[target_group.group_id] = target_group

    def add_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
        confidence: float = 1.0,
        evidence: str | None = None,
    ) -> EntityEquivalenceRelation:
        """
        Add a relation between two entity references.

        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            relation_type: The type of relation (e.g., "nickname", "alias")
            confidence: Confidence score for the relation
            evidence: Evidence supporting this relation

        Returns:
            The created relation object
        """
        # Create relation
        relation = EntityEquivalenceRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
            evidence=evidence,
        )

        # Insert into database
        relation_doc = relation.serialize()
        self.relations_collection.insert(relation_doc)

        # Add to cache
        relation_key = f"{source_id}_{target_id}"
        self._relations_cache[relation_key] = relation

        return relation

    def get_canonical_reference(
        self, entity_id: UUID,
    ) -> EntityEquivalenceNode | None:
        """
        Get the canonical reference for an entity.

        Args:
            entity_id: ID of the entity reference

        Returns:
            The canonical entity reference node, or None if not found
        """
        # Find the group containing this entity
        for group in self._groups_cache.values():
            if entity_id in group.members:
                # Return the canonical node
                return self._nodes_cache.get(group.canonical_id)

        # If not in any group, return None
        return None

    def get_all_references(self, entity_id: UUID) -> list[EntityEquivalenceNode]:
        """
        Get all equivalent references for an entity.

        Args:
            entity_id: ID of the entity reference

        Returns:
            List of all equivalent entity reference nodes
        """
        references = []

        # Find the group containing this entity
        for group in self._groups_cache.values():
            if entity_id in group.members:
                # Add all members to the result
                for member_id in group.members:
                    node = self._nodes_cache.get(member_id)
                    if node:
                        references.append(node)
                break

        return references

    def merge_entities(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str = "same_entity",
        confidence: float = 1.0,
    ) -> bool:
        """
        Merge two entities into the same equivalence class.

        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            relation_type: The type of relation
            confidence: Confidence score for the relation

        Returns:
            True if the merge was successful, False otherwise
        """
        # Validate entities exist
        source_node = self._nodes_cache.get(source_id)
        target_node = self._nodes_cache.get(target_id)
        if not source_node or not target_node:
            return False

        # Find groups for source and target
        source_group = None
        target_group = None
        for group in self._groups_cache.values():
            if source_id in group.members:
                source_group = group
            if target_id in group.members:
                target_group = group

        # Add relation between entities
        self.add_relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
        )

        # Case 1: Neither has a group - create new group
        if not source_group and not target_group:
            # Determine which should be canonical
            canonical_id = target_id if target_node.canonical else source_id

            group = EntityEquivalenceGroup(
                canonical_id=canonical_id,
                entity_type=source_node.entity_type,
                members=[source_id, target_id],
            )

            # Insert into database
            group_doc = group.serialize()
            self.groups_collection.insert(group_doc)

            # Add to cache
            self._groups_cache[group.group_id] = group

        # Case 2: Source has group, target doesn't - add target to source group
        elif source_group and not target_group:
            source_group.members.append(target_id)
            self.groups_collection.update(
                {"group_id": str(source_group.group_id)},
                {"$set": {"members": [str(m) for m in source_group.members]}},
            )
            self._groups_cache[source_group.group_id] = source_group

        # Case 3: Target has group, source doesn't - add source to target group
        elif not source_group and target_group:
            target_group.members.append(source_id)
            self.groups_collection.update(
                {"group_id": str(target_group.group_id)},
                {"$set": {"members": [str(m) for m in target_group.members]}},
            )
            self._groups_cache[target_group.group_id] = target_group

        # Case 4: Both have groups - merge groups
        else:
            # Determine which group to keep
            keep_group = target_group if target_node.canonical else source_group
            remove_group = source_group if keep_group == target_group else target_group

            # Merge members
            for member_id in remove_group.members:
                if member_id not in keep_group.members:
                    keep_group.members.append(member_id)

            # Update the group in the database
            self.groups_collection.update(
                {"group_id": str(keep_group.group_id)},
                {"$set": {"members": [str(m) for m in keep_group.members]}},
            )
            self._groups_cache[keep_group.group_id] = keep_group

            # Remove the other group
            self.groups_collection.delete({"group_id": str(remove_group.group_id)})
            if remove_group.group_id in self._groups_cache:
                del self._groups_cache[remove_group.group_id]

        return True

    def get_entity_graph(self, entity_id: UUID) -> dict:
        """
        Get a representation of the entity's equivalence graph.

        Args:
            entity_id: ID of the entity reference

        Returns:
            Dictionary with nodes and edges of the entity's graph
        """
        nodes = []
        edges = []

        # Find the group containing this entity
        target_group = None
        for group in self._groups_cache.values():
            if entity_id in group.members:
                target_group = group
                break

        if not target_group:
            # Single node if not in any group
            node = self._nodes_cache.get(entity_id)
            if node:
                nodes.append(
                    {
                        "id": str(node.entity_id),
                        "name": node.name,
                        "type": node.entity_type,
                        "canonical": node.canonical,
                    },
                )
            return {"nodes": nodes, "edges": edges}

        # Add all members from the group
        for member_id in target_group.members:
            node = self._nodes_cache.get(member_id)
            if node:
                nodes.append(
                    {
                        "id": str(node.entity_id),
                        "name": node.name,
                        "type": node.entity_type,
                        "canonical": node.canonical,
                    },
                )

        # Add all relations between group members
        for source_id in target_group.members:
            for target_id in target_group.members:
                if source_id != target_id:
                    relation_key = f"{source_id}_{target_id}"
                    relation = self._relations_cache.get(relation_key)
                    if relation:
                        edges.append(
                            {
                                "source": str(relation.source_id),
                                "target": str(relation.target_id),
                                "type": relation.relation_type,
                                "confidence": relation.confidence,
                            },
                        )

        return {"nodes": nodes, "edges": edges}

    def get_stats(self) -> dict:
        """Get statistics about entity equivalence classes."""
        return {
            "node_count": len(self._nodes_cache),
            "group_count": len(self._groups_cache),
            "relation_count": len(self._relations_cache),
            "entity_types": {t.value: 0 for t in IndalekoNamedEntityType},
            "relation_types": {},
        }

    def list_entity_groups(self) -> list[dict]:
        """
        List all entity equivalence groups with their members.

        Returns:
            List of dictionaries with group information
        """
        results = []
        for group in self._groups_cache.values():
            # Get canonical node
            canonical_node = self._nodes_cache.get(group.canonical_id)
            if not canonical_node:
                continue

            # Get member nodes
            members = []
            for member_id in group.members:
                node = self._nodes_cache.get(member_id)
                if node:
                    members.append(
                        {
                            "id": str(node.entity_id),
                            "name": node.name,
                            "canonical": node.canonical,
                        },
                    )

            results.append(
                {
                    "group_id": str(group.group_id),
                    "canonical": {
                        "id": str(canonical_node.entity_id),
                        "name": canonical_node.name,
                    },
                    "entity_type": group.entity_type,
                    "member_count": len(members),
                    "members": members,
                },
            )

        return results


def main():
    """Test the entity equivalence functionality."""
    # Initialize the manager
    manager = EntityEquivalenceManager()

    # Add some test entities
    node1 = manager.add_entity_reference(
        name="Elizabeth Jones",
        entity_type=IndalekoNamedEntityType.person,
        canonical=True,
        source="test",
        context="Full name",
    )

    node2 = manager.add_entity_reference(
        name="Beth",
        entity_type=IndalekoNamedEntityType.person,
        source="test",
        context="Nickname",
    )

    node3 = manager.add_entity_reference(
        name="Dr. Jones",
        entity_type=IndalekoNamedEntityType.person,
        source="test",
        context="Professional reference",
    )

    # Explicitly merge entities
    manager.merge_entities(node2.entity_id, node1.entity_id, relation_type="nickname")
    manager.merge_entities(
        node3.entity_id, node1.entity_id, relation_type="professional",
    )

    # Location example
    loc1 = manager.add_entity_reference(
        name="New York City",
        entity_type=IndalekoNamedEntityType.location,
        canonical=True,
    )

    loc2 = manager.add_entity_reference(
        name="NYC", entity_type=IndalekoNamedEntityType.location,
    )

    loc3 = manager.add_entity_reference(
        name="The Big Apple", entity_type=IndalekoNamedEntityType.location,
    )

    # Merge location entities
    manager.merge_entities(loc2.entity_id, loc1.entity_id, relation_type="abbreviation")
    manager.merge_entities(loc3.entity_id, loc1.entity_id, relation_type="nickname")

    # Test retrieving canonical references
    canonical = manager.get_canonical_reference(node2.entity_id)
    print(
        f"Canonical reference for '{node2.name}': {canonical.name if canonical else 'None'}",
    )

    # Test retrieving all references
    all_refs = manager.get_all_references(node1.entity_id)
    print(f"All references for '{node1.name}':")
    for ref in all_refs:
        print(f"  - {ref.name}")

    # Test getting the entity graph
    graph = manager.get_entity_graph(node1.entity_id)
    print("\nEntity Graph:")
    print(f"Nodes: {len(graph['nodes'])}")
    print(f"Edges: {len(graph['edges'])}")

    # Test listing all groups
    groups = manager.list_entity_groups()
    print(f"\nEntity Groups ({len(groups)}):")
    for group in groups:
        print(f"  - {group['canonical']['name']} ({len(group['members'])} members)")
        for member in group["members"]:
            print(f"    - {member['name']}")

    # Statistics
    stats = manager.get_stats()
    print("\nStatistics:")
    print(f"  - Nodes: {stats['node_count']}")
    print(f"  - Groups: {stats['group_count']}")
    print(f"  - Relations: {stats['relation_count']}")


if __name__ == "__main__":
    main()
