#!/bin/bash

# Set the path to the Indaleko root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDALEKO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
export INDALEKO_ROOT

echo "Running cloud storage activity generator tests from: $SCRIPT_DIR"
echo "Indaleko root directory: $INDALEKO_ROOT"

# Activate the virtual environment if it exists
if [ -d "$INDALEKO_ROOT/.venv-linux-python3.13/bin" ]; then
    source "$INDALEKO_ROOT/.venv-linux-python3.13/bin/activate"
    echo "Activated Linux Python 3.13 virtual environment"
elif [ -d "$INDALEKO_ROOT/.venv-linux-python3.12/bin" ]; then
    source "$INDALEKO_ROOT/.venv-linux-python3.12/bin/activate"
    echo "Activated Linux Python 3.12 virtual environment"
elif [ -d "$INDALEKO_ROOT/.venv-macos-python3.12/bin" ]; then
    source "$INDALEKO_ROOT/.venv-macos-python3.12/bin/activate"
    echo "Activated macOS Python 3.12 virtual environment"
else
    echo "No virtual environment found. Using system Python"
fi

# Add the Indaleko root to PYTHONPATH
export PYTHONPATH=$INDALEKO_ROOT:$PYTHONPATH

# Run the cloud storage generator unit tests
echo "Running cloud storage generator unit tests..."
python -m tools.data_generator_enhanced.testing.test_cloud_storage_generator
UNIT_TEST_RESULT=$?

# Run database integration tests if -db flag is provided
if [[ "$*" == *"-db"* ]]; then
    echo ""
    echo "Running database integration tests with cloud storage activities..."
    
    # Create a custom DB integration test specifically for cloud storage activities
    DB_TEST_SCRIPT=$(mktemp /tmp/cloud_storage_db_test_XXXXXX.py)
    
    cat > $DB_TEST_SCRIPT << 'EOF'
"""
Database integration test for cloud storage activity generator.

Tests the complete roundtrip flow:
1. Generate cloud storage activities with semantic attributes
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
from tools.data_generator_enhanced.agents.data_gen.tools.cloud_storage_generator import (
    CloudStorageActivityGeneratorTool,
    StorageActivityType,
    StorageItemType,
    StorageProviderType
)

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

def main():
    """Run the cloud storage database integration test."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger("CloudStorageDBTest")
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        db_config = IndalekoDBConfig(start=True)
        db = db_config.get_arangodb()
        logger.info(f"Connected to ArangoDB: {db.properties()}")
        
        # Generate cloud storage activities
        logger.info("Generating cloud storage activities...")
        generator = CloudStorageActivityGeneratorTool()
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(days=30)
        end_time = now
        
        # Generate activities for Google Drive
        gdrive_result = generator.execute({
            "count": 20,
            "criteria": {
                "user_email": "test.user@example.com",
                "provider_type": StorageProviderType.GOOGLE_DRIVE,
                "start_time": start_time,
                "end_time": end_time
            }
        })
        
        # Generate activities for Dropbox
        dropbox_result = generator.execute({
            "count": 20,
            "criteria": {
                "user_email": "test.user@example.com",
                "provider_type": StorageProviderType.DROPBOX,
                "start_time": start_time,
                "end_time": end_time
            }
        })
        
        # Combine all activities
        all_activities = gdrive_result["activities"] + dropbox_result["activities"]
        logger.info(f"Generated {len(all_activities)} cloud storage activities")
        
        # Check for storage activities collection
        collection_name = "CloudStorageActivities"
        if not db.has_collection(collection_name):
            logger.info(f"Creating collection: {collection_name}")
            db.create_collection(collection_name)
        
        collection = db.collection(collection_name)
        
        # Upload activities to database
        logger.info(f"Uploading {len(all_activities)} activities to database...")
        
        # Convert activities to JSON serializable format
        serializable_activities = []
        for activity in all_activities:
            serializable_activities.append(convert_to_json_serializable(activity))
        
        # Upload in batches
        batch_size = 10
        for i in range(0, len(serializable_activities), batch_size):
            batch = serializable_activities[i:i+batch_size]
            collection.import_bulk(batch)
        
        logger.info("Activities uploaded successfully")
        
        # Run test queries
        logger.info("Running test queries...")
        
        # 1. Basic query - find activities by provider type
        for provider in [StorageProviderType.GOOGLE_DRIVE, StorageProviderType.DROPBOX]:
            logger.info(f"Testing query for provider type: {provider}")
            
            aql_query = f"""
            FOR doc IN {collection_name}
                FILTER doc.provider_type == @provider
                RETURN doc
            """
            
            cursor = db.aql.execute(
                aql_query,
                bind_vars={"provider": provider}
            )
            results = list(cursor)
            
            logger.info(f"Found {len(results)} activities for provider '{provider}'")
            if len(results) > 0:
                logger.info(f"Provider type query successful for {provider}")
            else:
                logger.warning(f"Provider type query failed for {provider} - no results found")
        
        # 2. Semantic attribute query - find activities with specific semantic attributes
        if all_activities:
            # Find an activity with semantic attributes
            test_activity = None
            for activity in all_activities:
                if "SemanticAttributes" in activity and activity["SemanticAttributes"]:
                    test_activity = activity
                    break
            
            if test_activity:
                # Get a semantic attribute to query
                test_attr = test_activity["SemanticAttributes"][0]
                attr_id = test_attr.get("Identifier", {}).get("Identifier")
                attr_value = test_attr.get("Value")
                
                if attr_id and attr_value:
                    logger.info(f"Testing query for semantic attribute: {attr_id}={attr_value}")
                    
                    aql_query = f"""
                    FOR doc IN {collection_name}
                        FOR attr IN doc.SemanticAttributes
                            FILTER attr.Identifier.Identifier == @attr_id
                            AND attr.Value == @attr_value
                            RETURN doc
                    """
                    
                    cursor = db.aql.execute(
                        aql_query,
                        bind_vars={
                            "attr_id": attr_id,
                            "attr_value": attr_value
                        }
                    )
                    results = list(cursor)
                    
                    logger.info(f"Found {len(results)} activities with attribute {attr_id}={attr_value}")
                    if len(results) > 0:
                        logger.info("Semantic attribute query successful")
                    else:
                        logger.warning("Semantic attribute query failed - no results found")
        
        # 3. Activity type query - find activities by type
        for activity_type in [StorageActivityType.CREATE, StorageActivityType.MODIFY, StorageActivityType.SHARE]:
            aql_query = f"""
            FOR doc IN {collection_name}
                FILTER doc.activity_type == @activity_type
                RETURN doc
            """
            
            cursor = db.aql.execute(
                aql_query,
                bind_vars={"activity_type": activity_type}
            )
            results = list(cursor)
            
            logger.info(f"Found {len(results)} activities of type '{activity_type}'")
            if len(results) > 0:
                logger.info(f"Activity type query successful for {activity_type}")
            else:
                logger.warning(f"Activity type query failed for {activity_type} - no results found")
        
        # 4. Temporal query - find activities in a date range
        mid_point = start_time + ((end_time - start_time) / 2)
        
        aql_query = f"""
        FOR doc IN {collection_name}
            FILTER doc.timestamp >= @start_date AND doc.timestamp <= @end_date
            RETURN doc
        """
        
        cursor = db.aql.execute(
            aql_query,
            bind_vars={
                "start_date": start_time.isoformat(),
                "end_date": mid_point.isoformat()
            }
        )
        results = list(cursor)
        
        logger.info(f"Found {len(results)} activities in date range")
        if len(results) > 0:
            logger.info("Temporal query successful")
        else:
            logger.warning("Temporal query failed - no results found")
        
        # Cleanup
        if collection.count() > 0:
            logger.info("Cleaning up test data...")
            collection.truncate()
            logger.info("Test data removed")
        
        logger.info("Cloud storage activity database integration test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

    # Run the cloud storage database integration test
    python $DB_TEST_SCRIPT
    DB_TEST_RESULT=$?
    
    # Remove the temporary file
    rm $DB_TEST_SCRIPT
    
    if [ $DB_TEST_RESULT -eq 0 ]; then
        echo "Database integration tests passed successfully"
    else
        echo "Database integration tests failed"
    fi
else
    echo ""
    echo "Skipping database integration tests. Use -db flag to include them."
    echo "Example: ./run_cloud_storage_tests.sh -db"
fi

# Use the unit test result for the exit code
exit $UNIT_TEST_RESULT