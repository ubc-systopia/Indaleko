#!/usr/bin/env python
"""
Test script for NTFS Archival Memory Recorder.

This script tests the functionality of the NTFS Archival Memory Recorder,
including consolidation from long-term memory, ontology enhancement,
knowledge graph construction, and search capabilities.

Usage:
    python test_archival_recorder.py --test-ontology
    python test_archival_recorder.py --test-consolidation
    python test_archival_recorder.py --test-knowledge-graph
    python test_archival_recorder.py --test-search
    python test_archival_recorder.py --test-all

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
import logging
import os
import sys
import uuid


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the recorder
try:
    from activity.recorders.storage.ntfs.memory.archival.recorder import (
        NtfsArchivalMemoryRecorder,
    )
except ImportError:
    print("Error: NtfsArchivalMemoryRecorder not found")
    sys.exit(1)


def test_ontology_enhancement():
    """Test the ontology enhancement capabilities."""
    print("\n=== Testing Ontology Enhancement ===")

    # Create recorder in no_db mode for testing
    recorder = NtfsArchivalMemoryRecorder(no_db=True, debug=True)

    # Create sample W5H concepts
    w5h_concepts = {
        "what": ["document", "pdf", "report"],
        "who": ["user:john"],
        "where": ["documents_folder", "work_directory"],
        "when": ["recent_month_activity", "this_week_activity"],
        "why": ["project_work", "project:indaleko", "high_importance"],
        "how": ["frequently_modified", "work_in_progress"],
    }

    # Test ontology enhancement
    ontology = recorder._enhance_ontology(w5h_concepts)

    # Print results
    print("\nEnhanced Ontology:")
    print(f"  Total concepts: {len(ontology['concepts'])}")

    print("\nCategories:")
    for category, concepts in ontology["categories"].items():
        print(f"  {category}: {', '.join(concepts)}")

    print("\nInferences:")
    for inference in ontology["inferences"]:
        print(f"  {inference}")

    print("\nRelationships:")
    for relationship in ontology["relationships"]:
        print(
            f"  {relationship['source']} {relationship['relation']} {relationship['target']}",
        )

    # Verify ontology structure
    if "concepts" in ontology and "relationships" in ontology and "categories" in ontology:
        print("\n✅ Ontology enhancement test passed")
    else:
        print("\n❌ Ontology enhancement test failed")


def test_consolidation(db_config_path=None):
    """Test the consolidation from long-term memory to archival memory."""
    print("\n=== Testing Consolidation from Long-Term Memory ===")

    try:
        # Create recorder with db connection for testing
        recorder = NtfsArchivalMemoryRecorder(db_config_path=db_config_path, debug=True)

        # Check if connected to database
        if not hasattr(recorder, "_db") or recorder._db is None:
            print("❌ Not connected to database")
            return False

        # Get eligible entities count
        print("\nChecking for entities eligible for archival memory:")
        from activity.recorders.storage.ntfs.memory.long_term.recorder import (
            NtfsLongTermMemoryRecorder,
        )

        # Create long-term memory recorder
        long_term_recorder = NtfsLongTermMemoryRecorder(
            db_config_path=db_config_path,
            debug=True,
        )

        # Get eligible entities
        eligible_entities = long_term_recorder.get_entities_eligible_for_archival(
            min_importance=0.8,
            min_age_days=90,
            limit=5,
        )

        print(f"Found {len(eligible_entities)} entities eligible for archival memory")

        # If no eligible entities, create a test entity
        if not eligible_entities:
            print("No eligible entities found, creating a test entity")
            return False

        # Test consolidation with a single entity
        if eligible_entities:
            entity = eligible_entities[0]
            entity_id = entity.get("_key")

            print(f"\nTesting consolidation for entity {entity_id}:")

            # Prepare entity data
            entity_data = {
                "file_path": entity.get("Record", {}).get("Data", {}).get("file_path", "test_file.txt"),
                "volume": entity.get("Record", {}).get("Data", {}).get("volume_name", "C:"),
                "is_directory": False,
            }

            # Build archival memory document
            document = recorder._build_archival_memory_document(
                uuid.UUID(entity_id),
                entity_data,
                entity,
            )

            # Verify document structure
            has_ontology = "ontology" in document["Record"]["Data"]
            has_memory_lineage = "memory_lineage" in document["Record"]["Data"]
            has_historical_context = "historical_context" in document["Record"]["Data"]

            if has_ontology and has_memory_lineage and has_historical_context:
                print("\n✅ Document building test passed")
            else:
                print("\n❌ Document building test failed")

            return True

        return False

    except Exception as e:
        print(f"❌ Consolidation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_knowledge_graph(db_config_path=None):
    """Test the knowledge graph construction."""
    print("\n=== Testing Knowledge Graph Construction ===")

    try:
        # Create recorder with db connection for testing
        recorder = NtfsArchivalMemoryRecorder(db_config_path=db_config_path, debug=True)

        # Check if connected to database
        if not hasattr(recorder, "_db") or recorder._db is None:
            print("❌ Not connected to database")
            return False

        # Get an entity from archival memory
        query = """
            FOR doc IN @@collection
            LIMIT 1
            RETURN doc
        """

        cursor = recorder._db._arangodb.aql.execute(
            query,
            bind_vars={"@collection": recorder._collection_name},
        )

        entities = list(cursor)

        if not entities:
            print("No entities found in archival memory")
            return False

        entity = entities[0]
        entity_id = entity.get("_key")

        print(f"\nTesting knowledge graph for entity {entity_id}:")

        # Build knowledge graph relationships
        relationships = recorder._build_knowledge_graph_relationships(
            uuid.UUID(entity_id),
            entity,
        )

        print(f"Created {len(relationships)} knowledge graph relationships")

        # Verify relationship structure
        if relationships:
            rel = relationships[0]
            has_type = "type" in rel
            has_semantic_type = "semantic_type" in rel
            has_strength = "strength" in rel

            if has_type and has_semantic_type and has_strength:
                print("\n✅ Knowledge graph test passed")
            else:
                print("\n❌ Knowledge graph test failed")

            return True

        return False

    except Exception as e:
        print(f"❌ Knowledge graph test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_search(db_config_path=None):
    """Test the search capabilities."""
    print("\n=== Testing Search Capabilities ===")

    try:
        # Create recorder with db connection for testing
        recorder = NtfsArchivalMemoryRecorder(db_config_path=db_config_path, debug=True)

        # Check if connected to database
        if not hasattr(recorder, "_db") or recorder._db is None:
            print("❌ Not connected to database")
            return False

        # Test basic search
        print("\nTesting basic search:")

        # Use a general search term that should find something
        results = recorder.search_archival_memory(
            query="test",
            importance_min=0.0,
            limit=5,
        )

        print(f"Found {len(results)} results")

        # Test W5H filter search
        print("\nTesting W5H filter search:")

        # Create a W5H filter
        w5h_filter = {"what": ["document", "file"], "how": ["frequently_accessed"]}

        w5h_results = recorder.search_archival_memory(
            query="",
            w5h_filter=w5h_filter,
            importance_min=0.0,
            limit=5,
        )

        print(f"Found {len(w5h_results)} results with W5H filter")

        # Test knowledge graph inclusion
        print("\nTesting search with knowledge graph inclusion:")

        kg_results = recorder.search_archival_memory(
            query="test",
            importance_min=0.0,
            include_knowledge_graph=True,
            limit=5,
        )

        has_kg = all("knowledge_graph_relationships" in result for result in kg_results)

        if results or w5h_results or kg_results:
            print("\n✅ Search test passed")
        else:
            print("\n❌ Search test failed")

        return True

    except Exception as e:
        print(f"❌ Search test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function for testing the archival memory recorder."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Test script for NTFS Archival Memory Recorder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add general arguments
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--db-config",
        type=str,
        default=None,
        help="Path to database configuration file",
    )

    # Add test mode arguments
    test_group = parser.add_mutually_exclusive_group(required=True)
    test_group.add_argument(
        "--test-ontology",
        action="store_true",
        help="Test ontology enhancement",
    )
    test_group.add_argument(
        "--test-consolidation",
        action="store_true",
        help="Test consolidation from long-term memory",
    )
    test_group.add_argument(
        "--test-knowledge-graph",
        action="store_true",
        help="Test knowledge graph construction",
    )
    test_group.add_argument(
        "--test-search",
        action="store_true",
        help="Test search capabilities",
    )
    test_group.add_argument("--test-all", action="store_true", help="Run all tests")

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run tests
    try:
        if args.test_ontology or args.test_all:
            test_ontology_enhancement()

        if args.test_consolidation or args.test_all:
            test_consolidation(args.db_config)

        if args.test_knowledge_graph or args.test_all:
            test_knowledge_graph(args.db_config)

        if args.test_search or args.test_all:
            test_search(args.db_config)

    except Exception as e:
        print(f"Unhandled error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
