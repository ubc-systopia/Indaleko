#!/usr/bin/env python3
"""
Pre-commit hook to enforce using IndalekoDBCollections constants for collection names.

This script scans Python files to ensure developers use the constant from
IndalekoDBCollections class instead of hardcoding collection name strings.

For example:
- BAD:  db.get_collection("Objects")
- GOOD: db.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)
"""
import argparse
import re
import sys
from collections.abc import Sequence

# Get all the collection and view names defined in IndalekoDBCollections
COLLECTION_NAMES = [
    "Objects",
    "Relationships",
    "Services",
    "MachineConfig",
    "ActivityDataProviders",
    "ActivityContext",
    "MusicActivityContext",
    "TempActivityContext",
    "GeoActivityContext",
    "IdentityDomains",
    "Users",
    "UserRelationships",
    "PerformanceData",
    "QueryHistory",
    "SemanticData",
    "NamedEntities",
    "CollectionMetadata",
    "ArchivistMemory",
    "EntityEquivalenceNodes",
    "EntityEquivalenceRelations",
    "EntityEquivalenceGroups",
    "LearningEvents",
    "KnowledgePatterns",
    "FeedbackRecords",
    "ObjectsTextView",
    "NamedEntityTextView",
    "ActivityTextView",
    "EntityEquivalenceTextView",
    "KnowledgeTextView",
]

# Dictionary mapping string values to their constant names
COLLECTION_CONSTANTS = {
    "Objects": "Indaleko_Object_Collection",
    "Relationships": "Indaleko_Relationship_Collection",
    "Services": "Indaleko_Service_Collection",
    "MachineConfig": "Indaleko_MachineConfig_Collection",
    "ActivityDataProviders": "Indaleko_ActivityDataProvider_Collection",
    "ActivityContext": "Indaleko_ActivityContext_Collection",
    "MusicActivityContext": "Indaleko_MusicActivityData_Collection",
    "TempActivityContext": "Indaleko_TempActivityData_Collection",
    "GeoActivityContext": "Indaleko_GeoActivityData_Collection",
    "IdentityDomains": "Indaleko_Identity_Domain_Collection",
    "Users": "Indaleko_User_Collection",
    "UserRelationships": "Indaleko_User_Relationship_Collection",
    "PerformanceData": "Indaleko_Performance_Data_Collection",
    "QueryHistory": "Indaleko_Query_History_Collection",
    "SemanticData": "Indaleko_SemanticData_Collection",
    "NamedEntities": "Indaleko_Named_Entity_Collection",
    "CollectionMetadata": "Indaleko_Collection_Metadata",
    "ArchivistMemory": "Indaleko_Archivist_Memory_Collection",
    "EntityEquivalenceNodes": "Indaleko_Entity_Equivalence_Node_Collection",
    "EntityEquivalenceRelations": "Indaleko_Entity_Equivalence_Relation_Collection",
    "EntityEquivalenceGroups": "Indaleko_Entity_Equivalence_Group_Collection",
    "LearningEvents": "Indaleko_Learning_Event_Collection",
    "KnowledgePatterns": "Indaleko_Knowledge_Pattern_Collection",
    "FeedbackRecords": "Indaleko_Feedback_Record_Collection",
    "ObjectsTextView": "Indaleko_Objects_Text_View",
    "NamedEntityTextView": "Indaleko_Named_Entity_Text_View",
    "ActivityTextView": "Indaleko_Activity_Text_View",
    "EntityEquivalenceTextView": "Indaleko_Entity_Equivalence_Text_View",
    "KnowledgeTextView": "Indaleko_Knowledge_Text_View",
}

# Files to skip
SKIP_FILES = [
    "db/db_collections.py",  # Skip the file that defines the constants
    "old/",  # Skip old code
    "scratch/",  # Skip scratch code
]


def should_skip_file(filename: str) -> bool:
    """Check if this file should be skipped.

    Args:
        filename: The file path to check

    Returns:
        True if this file should be skipped, False otherwise
    """
    # Convert to Unix-style path for consistent comparison
    filename = filename.replace("\\", "/")

    # Check if this file should be skipped
    for skip_pattern in SKIP_FILES:
        if skip_pattern in filename:
            return True

    return False


def check_file(filename: str) -> list[str]:
    """Check file for hardcoded collection names.

    Args:
        filename: The file to check

    Returns:
        List of error messages if violations found
    """
    errors = []

    # Skip non-Python files
    if not filename.endswith(".py"):
        return errors

    # Skip files we shouldn't check
    if should_skip_file(filename):
        return errors

    with open(filename, encoding="utf-8") as f:
        content = f.read()

    # Find all collection name strings in the file
    for collection_name in COLLECTION_NAMES:
        # Pattern to find strings like "Objects" used in various contexts
        # Look for this exact string either in quotes or being compared
        patterns = [
            r'["\']{1}' + collection_name + r'["\']{1}',  # "Objects" or 'Objects'
            r'==\s*["\']{1}' + collection_name + r'["\']{1}',  # == "Objects"
            r'["\']{1}' + collection_name + r'["\']{1}\s*==',  # "Objects" ==
            r'!=\s*["\']{1}' + collection_name + r'["\']{1}',  # != "Objects"
            r'["\']{1}' + collection_name + r'["\']{1}\s*!=',  # "Objects" !=
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Get the constant name
                constant_name = COLLECTION_CONSTANTS.get(collection_name)

                # Add error
                errors.append(
                    f"{filename}: Hardcoded collection name '{collection_name}' found. "
                    f"Use IndalekoDBCollections.{constant_name} instead.",
                )
                # Only report once per collection name per file
                break

    return errors


def main(argv: Sequence[str] = None) -> int:
    """Run the pre-commit hook.

    Args:
        argv: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    errors = []
    for filename in args.filenames:
        errors.extend(check_file(filename))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(
            "\nAlways use IndalekoDBCollections constants for collection names:\n"
            '- BAD:  db.get_collection("Objects")\n'
            "- GOOD: db.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)\n\n"
            "This ensures consistency and makes it easier to update collection names in the future.\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
