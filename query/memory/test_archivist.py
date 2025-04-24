"""
Test script for the Archivist memory system.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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
import json
import os
import sys

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBCollections, IndalekoDBConfig
from query.memory.archivist_memory import ArchivistMemory

# pylint: enable=wrong-import-position


def test_create_memory():
    """Test creating an Archivist memory instance and saving it to the database."""
    print("Creating Archivist memory and saving to database...")

    # Create Archivist memory
    memory = ArchivistMemory()

    # Add test data
    memory.add_long_term_goal(
        "File Organization",
        "Organize personal documents by project and year",
    )
    memory.update_goal_progress("File Organization", 0.35)

    memory.add_insight(
        "organization",
        "User frequently searches for PDF documents",
        0.8,
    )
    memory.add_insight(
        "retrieval",
        "Location-based search helps narrow down results",
        0.7,
    )

    # Update preferences
    memory._add_or_update_preference(
        "search",
        "Prefers detailed results over summaries",
        0.85,
    )

    # Add topic
    memory.memory.semantic_topics["work"] = 0.9
    memory.memory.semantic_topics["personal"] = 0.6

    # Add content preference
    memory.memory.content_preferences["document"] = 0.75
    memory.memory.content_preferences["image"] = 0.45

    # Generate forward prompt (display it but don't use it)
    forward_prompt = memory.generate_forward_prompt()
    print("\nGenerated Forward Prompt:")
    print("=========================")
    print(forward_prompt)

    # Save to database
    memory.save_memory()
    print("\nMemory saved to database successfully.")


def verify_collection():
    """Verify that the Archivist memory collection exists and contains data."""
    # Connect to ArangoDB
    db_config = IndalekoDBConfig()
    collection_name = IndalekoDBCollections.Indaleko_Archivist_Memory_Collection

    print(f"\nVerifying collection {collection_name}...")

    # Check if collection exists
    if not db_config._arangodb.has_collection(collection_name):
        print(f"Error: Collection {collection_name} does not exist.")
        return False

    # Get collection
    collection = db_config._arangodb.collection(collection_name)

    # Count documents
    count = collection.count()
    print(f"Collection contains {count} documents.")

    # Get properties
    properties = collection.properties()
    print(f"Collection properties: {json.dumps(properties, indent=2)}")

    # Get most recent document
    if count > 0:
        # Use AQL to sort by timestamp in descending order
        aql = "FOR doc IN @@collection SORT doc.Record.Timestamp DESC LIMIT 1 RETURN doc"
        cursor = db_config._arangodb.aql.execute(
            aql,
            bind_vars={"@collection": collection_name},
        )
        documents = [doc for doc in cursor]

        if documents:
            # Print document summary
            doc = documents[0]
            print("\nMost recent document:")
            print(f"  Timestamp: {doc.get('Record', {}).get('Timestamp')}")
            print(f"  Memory ID: {doc.get('ArchivistMemory', {}).get('memory_id')}")
            created_at = doc.get("ArchivistMemory", {}).get("created_at")
            if created_at:
                print(f"  Created At: {created_at}")

            # Show goals
            goals = doc.get("ArchivistMemory", {}).get("long_term_goals", [])
            if goals:
                print("\n  Goals:")
                for goal in goals:
                    print(
                        f"    - {goal.get('name')}: {goal.get('progress', 0) * 100:.0f}% complete",
                    )

            # Show insights
            insights = doc.get("ArchivistMemory", {}).get("insights", [])
            if insights:
                print("\n  Insights:")
                for insight in insights:
                    print(
                        f"    - {insight.get('insight')} (confidence: {insight.get('confidence', 0):.2f})",
                    )

            return True

    return False


def test_load_memory():
    """Test loading Archivist memory from the database."""
    print("\nLoading Archivist memory from database...")

    # Create Archivist memory (which will load from database)
    memory = ArchivistMemory()

    # Check if memory was loaded
    if not memory.memory or not memory.memory.memory_id:
        print("Error: Failed to load memory from database.")
        return False

    # Print memory details
    print(f"Loaded memory ID: {memory.memory.memory_id}")
    print(f"Created at: {memory.memory.created_at}")
    print(f"Updated at: {memory.memory.updated_at}")

    # Print goals
    if memory.memory.long_term_goals:
        print("\nGoals:")
        for goal in memory.memory.long_term_goals:
            print(f"- {goal.name}: {goal.progress * 100:.0f}% complete")

    # Print insights
    if memory.memory.insights:
        print("\nInsights:")
        for insight in memory.memory.insights:
            print(f"- {insight.insight} (confidence: {insight.confidence:.2f})")

    # Print topics
    if memory.memory.semantic_topics:
        print("\nTopics:")
        for topic, importance in sorted(
            memory.memory.semantic_topics.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"- {topic}: {importance:.2f}")

    return True


def list_collections():
    """List all collections in the database."""
    print("\nListing all collections in the database...")

    # Connect to ArangoDB
    db_config = IndalekoDBConfig()

    # Get collections
    collections = db_config._arangodb.collections()

    # Filter out system collections
    user_collections = [c for c in collections if not c["name"].startswith("_")]

    # Print collections
    print(f"Found {len(user_collections)} user collections:")
    for collection in sorted(user_collections, key=lambda x: x["name"]):
        name = collection["name"]
        count = db_config._arangodb.collection(name).count()
        print(f"- {name}: {count} documents")


def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(description="Test the Archivist memory system")
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create and save test memory data",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the Archivist memory collection",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load memory from the database",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all collections in the database",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    if args.all or args.list:
        list_collections()

    if args.all or args.create:
        test_create_memory()

    if args.all or args.verify:
        verify_collection()

    if args.all or args.load:
        test_load_memory()


if __name__ == "__main__":
    main()
