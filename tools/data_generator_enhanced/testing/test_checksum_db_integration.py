"""
Database integration test for checksum generator.

Tests the complete roundtrip flow:
1. Generate checksums for files with forced duplicates
2. Upload the data to ArangoDB
3. Execute real AQL queries against the uploaded data
4. Verify query results match expected outputs
"""

import os
import sys
import uuid
import json
import logging
import argparse
import datetime
import time
import random
from typing import Dict, List, Any, Tuple

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko database modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections

# Import data generator components
from tools.data_generator_enhanced.agents.data_gen.tools.checksum_generator import ChecksumGeneratorTool

# Custom JSON encoder for complex types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


def convert_to_json_serializable(obj):
    """Convert an object with UUIDs and datetimes to JSON serializable format."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            result[k] = convert_to_json_serializable(v)
        return result
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return obj


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


class ChecksumDBTest:
    """Checksum database integration test suite."""
    
    def __init__(self, count=20, cleanup=True, debug=False):
        """Initialize the test suite.
        
        Args:
            count: Number of files to generate
            cleanup: Whether to clean up test data after running
            debug: Whether to enable debug logging
        """
        self.file_count = count
        self.cleanup = cleanup
        
        # Setup logging
        setup_logging(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger("ChecksumDBTest")
        
        # Initialize test data
        self.db_config = None
        self.db = None
        self.checksums = []
        self.collection_name = "FileChecksums"
        
        # Initialize the checksum generator
        self.generator = ChecksumGeneratorTool()
        
        # Test results
        self.results = {
            "file_count": 0,
            "duplicate_count": 0,
            "queries_run": 0,
            "successful_queries": 0,
            "database_errors": 0,
            "results": []
        }
    
    def setup_db_connection(self) -> bool:
        """Set up the database connection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Connecting to database...")
            self.db_config = IndalekoDBConfig(start=True)
            self.db = self.db_config.get_arangodb()
            self.logger.info(f"Connected to ArangoDB: {self.db.properties()}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False
    
    def generate_test_files(self) -> bool:
        """Generate test files with checksums.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating {self.file_count} files with checksums...")
            
            # Generate random file data
            files = []
            for i in range(self.file_count):
                # Generate random file data
                file_type = random.choice(["document", "image", "video", "audio", "executable", "archive"])
                file_extension = {
                    "document": random.choice([".docx", ".pdf", ".txt", ".xlsx"]),
                    "image": random.choice([".jpg", ".png", ".gif", ".webp"]),
                    "video": random.choice([".mp4", ".mov", ".avi", ".mkv"]),
                    "audio": random.choice([".mp3", ".wav", ".flac", ".ogg"]),
                    "executable": random.choice([".exe", ".msi", ".dll", ".app"]),
                    "archive": random.choice([".zip", ".tar.gz", ".rar", ".7z"])
                }[file_type]
                
                file_name = f"file_{i}{file_extension}"
                file_path = f"/test/files/{file_type}/{file_name}"
                file_size = random.randint(1000, 10000000)  # 1KB to 10MB
                
                # Create timestamp a few days in the past
                days_ago = random.randint(1, 30)
                created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
                modified = created + datetime.timedelta(hours=random.randint(1, 24))
                
                file_data = {
                    "path": file_path,
                    "name": file_name,
                    "type": file_type,
                    "size": file_size,
                    "created": created.isoformat(),
                    "modified": modified.isoformat(),
                    "object_id": str(uuid.uuid4())
                }
                files.append(file_data)
            
            # Create duplicate groups - about 20% of files should be duplicates
            num_duplicates = self.file_count // 5
            duplicate_groups = []
            
            for _ in range(num_duplicates):
                # Pick a random file and make it a duplicate of another
                source_idx = random.randint(0, self.file_count - 1)
                duplicate_idx = random.randint(0, self.file_count - 1)
                
                # Avoid self-duplication
                while duplicate_idx == source_idx:
                    duplicate_idx = random.randint(0, self.file_count - 1)
                
                duplicate_groups.append([source_idx, duplicate_idx])
            
            # Generate checksums
            result = self.generator.execute({
                "files": files,
                "duplicate_groups": duplicate_groups
            })
            
            self.checksums = result["checksums"]
            
            # Store stats
            self.results["file_count"] = self.file_count
            self.results["duplicate_count"] = result["stats"]["duplicates"]
            
            self.logger.info(f"Generated checksums for {self.file_count} files with {result['stats']['duplicates']} duplicates")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate test files: {e}")
            return False
    
    def upload_to_database(self) -> bool:
        """Upload the generated checksums to the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Checking for {self.collection_name} collection...")
            
            # Create collection if it doesn't exist
            if not self.db.has_collection(self.collection_name):
                self.logger.info(f"Creating collection: {self.collection_name}")
                self.db.create_collection(self.collection_name)
            
            collection = self.db.collection(self.collection_name)
            
            # Upload checksums to database
            self.logger.info(f"Uploading {len(self.checksums)} checksum records to database...")
            
            # Convert checksums to JSON serializable format
            serializable_records = []
            for checksum in self.checksums:
                record = {
                    "MD5": checksum["checksums"]["MD5"],
                    "SHA1": checksum["checksums"]["SHA1"],
                    "SHA256": checksum["checksums"]["SHA256"],
                    "SHA512": checksum["checksums"]["SHA512"],
                    "Dropbox": checksum["checksums"].get("Dropbox", ""),
                    "is_duplicate": checksum.get("is_duplicate", False),
                    "duplicate_of": checksum.get("duplicate_of", None),
                    "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "SemanticAttributes": checksum.get("SemanticAttributes", [])
                }
                serializable_records.append(convert_to_json_serializable(record))
            
            # Upload in batches
            batch_size = 10
            for i in range(0, len(serializable_records), batch_size):
                batch = serializable_records[i:i+batch_size]
                collection.import_bulk(batch)
            
            self.logger.info("Checksums uploaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload checksums to database: {e}")
            self.results["database_errors"] += 1
            return False
    
    def run_queries(self) -> bool:
        """Run test queries against the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Running test queries...")
            self.results["queries_run"] = 0
            self.results["successful_queries"] = 0
            
            # 1. Basic query - find checksums by MD5
            self.results["queries_run"] += 1
            if self.checksums:
                test_md5 = self.checksums[0]["checksums"]["MD5"]
                self.logger.info(f"Testing query for MD5: {test_md5}")
                
                aql_query = f"""
                FOR doc IN {self.collection_name}
                    FILTER doc.MD5 == @md5
                    RETURN doc
                """
                
                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars={"md5": test_md5}
                )
                results = list(cursor)
                
                self.logger.info(f"Found {len(results)} records with MD5 '{test_md5}'")
                if len(results) > 0:
                    self.logger.info("Basic MD5 query successful")
                    self.results["successful_queries"] += 1
                    self.results["results"].append({
                        "query_name": "md5_query",
                        "success": True,
                        "matches": len(results)
                    })
                else:
                    self.logger.warning("Basic MD5 query failed - no results found")
                    self.results["results"].append({
                        "query_name": "md5_query",
                        "success": False,
                        "matches": 0
                    })
            
            # 2. Semantic attribute query - find checksums by semantic attribute
            self.results["queries_run"] += 1
            if self.checksums and self.checksums[0].get("SemanticAttributes"):
                test_attr = self.checksums[0]["SemanticAttributes"][0]
                attr_id = test_attr.get("Identifier", {}).get("Identifier")
                attr_value = test_attr.get("Value")
                
                if attr_id and attr_value:
                    self.logger.info(f"Testing query for semantic attribute: {attr_id}={attr_value}")
                    
                    aql_query = f"""
                    FOR doc IN {self.collection_name}
                        FOR attr IN doc.SemanticAttributes
                            FILTER attr.Identifier.Identifier == @attr_id
                            AND attr.Value == @attr_value
                            RETURN doc
                    """
                    
                    cursor = self.db.aql.execute(
                        aql_query,
                        bind_vars={
                            "attr_id": attr_id,
                            "attr_value": attr_value
                        }
                    )
                    results = list(cursor)
                    
                    self.logger.info(f"Found {len(results)} records with attribute {attr_id}={attr_value}")
                    if len(results) > 0:
                        self.logger.info("Semantic attribute query successful")
                        self.results["successful_queries"] += 1
                        self.results["results"].append({
                            "query_name": "semantic_attribute_query",
                            "success": True,
                            "matches": len(results)
                        })
                    else:
                        self.logger.warning("Semantic attribute query failed - no results found")
                        self.results["results"].append({
                            "query_name": "semantic_attribute_query",
                            "success": False,
                            "matches": 0
                        })
            
            # 3. Duplicate query - find duplicate files
            self.results["queries_run"] += 1
            aql_query = f"""
            FOR doc IN {self.collection_name}
                FILTER doc.is_duplicate == true
                RETURN doc
            """
            
            cursor = self.db.aql.execute(aql_query)
            results = list(cursor)
            
            self.logger.info(f"Found {len(results)} duplicate checksums")
            if len(results) > 0:
                self.logger.info("Duplicate query successful")
                self.results["successful_queries"] += 1
                self.results["results"].append({
                    "query_name": "duplicate_query",
                    "success": True,
                    "matches": len(results)
                })
            else:
                self.logger.warning("Duplicate query failed - no duplicates found")
                self.results["results"].append({
                    "query_name": "duplicate_query",
                    "success": False,
                    "matches": 0
                })
            
            # 4. SHA256 query - find files by SHA256
            self.results["queries_run"] += 1
            if self.checksums:
                test_sha256 = self.checksums[0]["checksums"]["SHA256"]
                self.logger.info(f"Testing query for SHA256: {test_sha256}")
                
                aql_query = f"""
                FOR doc IN {self.collection_name}
                    FILTER doc.SHA256 == @sha256
                    RETURN doc
                """
                
                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars={"sha256": test_sha256}
                )
                results = list(cursor)
                
                self.logger.info(f"Found {len(results)} records with SHA256 '{test_sha256}'")
                if len(results) > 0:
                    self.logger.info("SHA256 query successful")
                    self.results["successful_queries"] += 1
                    self.results["results"].append({
                        "query_name": "sha256_query",
                        "success": True,
                        "matches": len(results)
                    })
                else:
                    self.logger.warning("SHA256 query failed - no results found")
                    self.results["results"].append({
                        "query_name": "sha256_query",
                        "success": False,
                        "matches": 0
                    })
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to run queries: {e}")
            self.results["database_errors"] += 1
            return False
    
    def cleanup_database(self) -> bool:
        """Clean up test data from the database.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.cleanup:
            self.logger.info("Skipping database cleanup as requested")
            return True
        
        try:
            self.logger.info("Cleaning up test data...")
            
            # Truncate the collection
            if self.db.has_collection(self.collection_name):
                collection = self.db.collection(self.collection_name)
                if collection.count() > 0:
                    self.logger.info(f"Truncating collection: {self.collection_name}")
                    collection.truncate()
                    self.logger.info("Test data removed")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to clean up database: {e}")
            return False
    
    def run(self) -> Dict[str, Any]:
        """Run the complete test suite.
        
        Returns:
            Test results dictionary
        """
        self.logger.info("Starting checksum database integration test...")
        
        success = (
            self.setup_db_connection() and
            self.generate_test_files() and
            self.upload_to_database() and
            self.run_queries()
        )
        
        # Always try to clean up, even if previous steps failed
        cleanup_success = self.cleanup_database()
        
        # Update final test results
        self.results["success"] = success and cleanup_success
        
        if success and cleanup_success:
            self.logger.info("Checksum database integration test completed successfully")
        else:
            self.logger.warning("Checksum database integration test failed")
        
        return self.results


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Database integration test for checksums')
    
    parser.add_argument('--count', type=int, default=20,
                        help='Number of files to generate checksums for (default: 20)')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='Skip database cleanup after test')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Create and run the test
    test = ChecksumDBTest(
        count=args.count,
        cleanup=not args.no_cleanup,
        debug=args.debug
    )
    results = test.run()
    
    # Display summary
    print("\nChecksum Database Integration Test Summary:")
    print(f"- File Count: {results['file_count']}")
    print(f"- Duplicate Count: {results['duplicate_count']}")
    print(f"- Queries Run: {results['queries_run']}")
    print(f"- Successful Queries: {results['successful_queries']}")
    print(f"- Database Errors: {results['database_errors']}")
    print(f"- Success Rate: {results['successful_queries'] / max(1, results['queries_run']) * 100:.1f}%")
    
    print("\nIndividual Query Results:")
    for result in results["results"]:
        status = "✓ Success" if result["success"] else "✗ Failed"
        print(f"- {result['query_name']}: {status} ({result['matches']} matches)")
    
    # Return success status based on all queries succeeding
    success = (results["successful_queries"] == results["queries_run"])
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())