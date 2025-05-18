#!/usr/bin/env python3
"""Fix truth data issues in the ablation framework.

This script repairs inconsistencies between truth data and actual collection data
by aligning truth data with what's actually available in the collections.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from db.db_config import IndalekoDBConfig


def setup_logging():
    """Set up logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


class TruthDataFixer:
    """Fix truth data inconsistencies in the ablation framework."""

    def __init__(self, dry_run: bool = False):
        """Initialize the truth data fixer.

        Args:
            dry_run: If True, don't actually make changes, just report what would be done.
        """
        self.logger = logging.getLogger(__name__)
        self.dry_run = dry_run
        self.db_config = None
        self.db = None
        self._setup_db_connection()

        # Define collections
        self.activity_collections = [
            "AblationLocationActivity",
            "AblationTaskActivity",
            "AblationMusicActivity",
            "AblationCollaborationActivity",
            "AblationStorageActivity",
            "AblationMediaActivity",
        ]
        
        # Define truth collection name
        self.truth_collection = "AblationTruthData"

    def _setup_db_connection(self) -> bool:
        """Set up the database connection.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False

    def get_truth_data(self) -> List[Dict]:
        """Get all truth data documents.

        Returns:
            List[Dict]: List of truth data documents.
        """
        try:
            # Get all truth data documents
            result = self.db.aql.execute(
                f"""
                FOR doc IN {self.truth_collection}
                RETURN doc
                """,
            )
            
            return list(result)
        except Exception as e:
            self.logger.error(f"Failed to get truth data: {e}")
            return []

    def get_collection_entities(self, collection_name: str) -> Set[str]:
        """Get all entity IDs in a collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            Set[str]: Set of entity IDs.
        """
        try:
            if not self.db.has_collection(collection_name):
                self.logger.warning(f"Collection {collection_name} does not exist")
                return set()
                
            result = self.db.aql.execute(
                f"""
                FOR doc IN {collection_name}
                RETURN doc._key
                """,
            )
            
            return set(result)
        except Exception as e:
            self.logger.error(f"Failed to get entities from {collection_name}: {e}")
            return set()

    def fix_nonexistent_entities(self) -> Tuple[int, int]:
        """Fix truth data entries that reference nonexistent entities.

        Returns:
            Tuple[int, int]: Number of documents fixed, number of documents processed.
        """
        self.logger.info("Fixing truth data with nonexistent entities...")
        
        # Get all truth documents
        truth_docs = self.get_truth_data()
        if not truth_docs:
            self.logger.error("No truth data found")
            return 0, 0
            
        # Get entities for each collection
        collection_entities = {}
        for collection_name in self.activity_collections:
            if self.db.has_collection(collection_name):
                collection_entities[collection_name] = self.get_collection_entities(collection_name)
        
        # Fix each truth document
        docs_fixed = 0
        docs_processed = 0
        
        for doc in truth_docs:
            docs_processed += 1
            collection = doc.get("collection")
            
            if not collection or collection not in collection_entities:
                self.logger.warning(f"Truth document {doc['_key']} references unknown collection '{collection}'")
                continue
                
            matching_entities = doc.get("matching_entities", [])
            if not matching_entities:
                continue
                
            # Find which entities exist in the collection
            existing_entities = []
            for entity_id in matching_entities:
                if entity_id in collection_entities[collection]:
                    existing_entities.append(entity_id)
                else:
                    self.logger.debug(f"Entity {entity_id} not found in collection {collection}")
            
            # Update truth document if needed
            if len(existing_entities) != len(matching_entities):
                self.logger.info(
                    f"Truth document {doc['_key']} has {len(matching_entities)} entities, "
                    f"but only {len(existing_entities)} exist in collection {collection}"
                )
                
                if not self.dry_run:
                    try:
                        # Update the document with only existing entities
                        self.db.collection(self.truth_collection).update({
                            "_key": doc["_key"],
                            "matching_entities": existing_entities
                        })
                        docs_fixed += 1
                        self.logger.info(f"Updated truth document {doc['_key']}")
                    except Exception as e:
                        self.logger.error(f"Failed to update truth document {doc['_key']}: {e}")
                else:
                    self.logger.info(f"Would update truth document {doc['_key']} (dry run)")
                    docs_fixed += 1
        
        return docs_fixed, docs_processed

    def fix_duplicate_query_ids(self) -> Tuple[int, int]:
        """Fix duplicate query IDs in truth data.

        Returns:
            Tuple[int, int]: Number of documents fixed, number of documents processed.
        """
        self.logger.info("Fixing duplicate query IDs in truth data...")
        
        # Get all truth documents
        truth_docs = self.get_truth_data()
        if not truth_docs:
            self.logger.error("No truth data found")
            return 0, 0
            
        # Find duplicate query IDs
        query_id_counts = {}
        for doc in truth_docs:
            query_id = doc.get("query_id")
            if not query_id:
                continue
                
            if query_id not in query_id_counts:
                query_id_counts[query_id] = []
                
            query_id_counts[query_id].append(doc["_key"])
        
        # Fix each duplicate
        docs_fixed = 0
        docs_processed = 0
        
        for query_id, doc_keys in query_id_counts.items():
            if len(doc_keys) <= 1:
                continue
                
            self.logger.info(f"Query ID {query_id} appears in {len(doc_keys)} documents")
            
            # Group documents by collection
            collection_docs = {}
            for doc_key in doc_keys:
                doc = self.db.collection(self.truth_collection).get(doc_key)
                if not doc:
                    continue
                    
                collection = doc.get("collection")
                if not collection:
                    continue
                    
                if collection not in collection_docs:
                    collection_docs[collection] = []
                    
                collection_docs[collection].append(doc)
            
            # Fix duplicates within each collection
            for collection, docs in collection_docs.items():
                docs_processed += len(docs)
                
                if len(docs) <= 1:
                    continue
                    
                self.logger.info(f"Query ID {query_id} appears in {len(docs)} documents for collection {collection}")
                
                # Keep the first document and merge the entities
                keep_doc = docs[0]
                all_entities = set(keep_doc.get("matching_entities", []))
                
                for i, doc in enumerate(docs[1:], 1):
                    all_entities.update(doc.get("matching_entities", []))
                    
                    if not self.dry_run:
                        try:
                            # Remove the duplicate document
                            self.db.collection(self.truth_collection).delete(doc["_key"])
                            docs_fixed += 1
                            self.logger.info(f"Removed duplicate truth document {doc['_key']}")
                        except Exception as e:
                            self.logger.error(f"Failed to remove duplicate truth document {doc['_key']}: {e}")
                    else:
                        self.logger.info(f"Would remove duplicate truth document {doc['_key']} (dry run)")
                        docs_fixed += 1
                
                # Update the kept document with all unique entities
                if not self.dry_run:
                    try:
                        self.db.collection(self.truth_collection).update({
                            "_key": keep_doc["_key"],
                            "matching_entities": list(all_entities)
                        })
                        self.logger.info(f"Updated truth document {keep_doc['_key']} with all unique entities")
                    except Exception as e:
                        self.logger.error(f"Failed to update truth document {keep_doc['_key']}: {e}")
                else:
                    self.logger.info(f"Would update truth document {keep_doc['_key']} with all unique entities (dry run)")
        
        return docs_fixed, docs_processed

    def run_all_fixes(self) -> bool:
        """Run all fixes.

        Returns:
            bool: True if all fixes were successful, False otherwise.
        """
        self.logger.info("Running all fixes...")
        
        # Fix nonexistent entities
        entity_fixes, entity_docs = self.fix_nonexistent_entities()
        self.logger.info(f"Fixed {entity_fixes} of {entity_docs} documents with nonexistent entities")
        
        # Fix duplicate query IDs
        duplicate_fixes, duplicate_docs = self.fix_duplicate_query_ids()
        self.logger.info(f"Fixed {duplicate_fixes} of {duplicate_docs} documents with duplicate query IDs")
        
        total_fixes = entity_fixes + duplicate_fixes
        total_docs = entity_docs + duplicate_docs
        
        if total_fixes > 0:
            if self.dry_run:
                self.logger.info(f"Would fix {total_fixes} issues (dry run)")
            else:
                self.logger.info(f"Fixed {total_fixes} issues")
        else:
            self.logger.info("No issues fixed")
        
        return True


def main():
    """Fix truth data issues in the ablation framework."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting truth data fixes for ablation framework")
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Fix truth data issues in ablation framework")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually make changes, just report what would be done")
    args = parser.parse_args()
    
    try:
        # Create fixer and run fixes
        fixer = TruthDataFixer(dry_run=args.dry_run)
        result = fixer.run_all_fixes()
        
        if result:
            logger.info("Truth data fixes completed successfully")
            sys.exit(0)
        else:
            logger.error("Truth data fixes failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error fixing truth data: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()