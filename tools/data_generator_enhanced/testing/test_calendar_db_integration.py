"""
Database integration test for calendar event generator.

Tests the complete roundtrip flow:
1. Generate calendar events with semantic attributes
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
from tools.data_generator_enhanced.agents.data_gen.tools.calendar_event_generator import (
    CalendarEventGeneratorTool,
    IndalekoNamedEntityType
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


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


class CalendarDBTest:
    """Calendar event database integration test suite."""
    
    def __init__(self, count=20, cleanup=True, debug=False):
        """Initialize the test suite.
        
        Args:
            count: Number of events to generate
            cleanup: Whether to clean up test data after running
            debug: Whether to enable debug logging
        """
        self.event_count = count
        self.cleanup = cleanup
        
        # Setup logging
        setup_logging(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger("CalendarDBTest")
        
        # Initialize test data
        self.db_config = None
        self.db = None
        self.events = []
        self.collection_name = "CalendarEvents"
        
        # Initialize the calendar event generator
        self.generator = CalendarEventGeneratorTool()
        
        # Test results
        self.results = {
            "event_count": 0,
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
    
    def generate_calendar_events(self) -> bool:
        """Generate calendar events with semantic attributes.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating {self.event_count} calendar events...")
            
            # Set up time range
            now = datetime.datetime.now(datetime.timezone.utc)
            start_time = now - datetime.timedelta(days=30)
            end_time = now + datetime.timedelta(days=30)
            
            # Create test entities for event generation
            test_entities = {
                "person": [
                    {
                        "Id": str(uuid.uuid4()),
                        "name": "John Smith",
                        "category": IndalekoNamedEntityType.person
                    },
                    {
                        "Id": str(uuid.uuid4()),
                        "name": "Jane Doe",
                        "category": IndalekoNamedEntityType.person
                    }
                ],
                "organization": [
                    {
                        "Id": str(uuid.uuid4()),
                        "name": "Acme Corp",
                        "category": IndalekoNamedEntityType.organization
                    }
                ],
                "location": [
                    {
                        "Id": str(uuid.uuid4()),
                        "name": "San Francisco",
                        "category": IndalekoNamedEntityType.location,
                        "gis_location": {
                            "latitude": 37.7749,
                            "longitude": -122.4194
                        }
                    }
                ]
            }
            
            # Create test location data
            test_location_data = [
                {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "name": "San Francisco"
                },
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "name": "New York"
                }
            ]
            
            # Generate calendar events
            result = self.generator.execute({
                "count": self.event_count,
                "criteria": {
                    "user_email": "test.user@example.com",
                    "user_name": "Test User",
                    "provider": "outlook",
                    "entities": test_entities,
                    "location_data": test_location_data,
                    "start_time": start_time,
                    "end_time": end_time
                }
            })
            
            self.events = result["events"]
            self.logger.info(f"Generated {len(self.events)} calendar events")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate calendar events: {e}")
            return False
    
    def upload_to_database(self) -> bool:
        """Upload the generated events to the database.
        
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
            
            # Upload events to database
            self.logger.info(f"Uploading {len(self.events)} events to database...")
            
            # Convert events to JSON serializable format
            serializable_events = []
            for event in self.events:
                serializable_events.append(convert_to_json_serializable(event))
            
            # Upload in batches
            batch_size = 10
            for i in range(0, len(serializable_events), batch_size):
                batch = serializable_events[i:i+batch_size]
                collection.import_bulk(batch)
            
            self.logger.info("Events uploaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload events to database: {e}")
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
            
            # 1. Basic query - find events with a specific subject
            self.results["queries_run"] += 1
            if self.events:
                test_subject = self.events[0]["subject"]
                self.logger.info(f"Testing query for subject: {test_subject}")
                
                aql_query = f"""
                FOR doc IN {self.collection_name}
                    FILTER doc.subject == @subject
                    RETURN doc
                """
                
                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars={"subject": test_subject}
                )
                results = list(cursor)
                
                self.logger.info(f"Found {len(results)} events with subject '{test_subject}'")
                if len(results) > 0:
                    self.logger.info("Basic subject query successful")
                    self.results["successful_queries"] += 1
                    self.results["results"].append({
                        "query_name": "subject_query",
                        "success": True,
                        "matches": len(results)
                    })
                else:
                    self.logger.warning("Basic subject query failed - no results found")
                    self.results["results"].append({
                        "query_name": "subject_query",
                        "success": False,
                        "matches": 0
                    })
            
            # 2. Semantic attribute query - find events with specific semantic attributes
            self.results["queries_run"] += 1
            if self.events:
                # Find an event with semantic attributes
                test_event = None
                for event in self.events:
                    if "SemanticAttributes" in event and event["SemanticAttributes"]:
                        test_event = event
                        break
                
                if test_event:
                    # Get a semantic attribute to query
                    test_attr = test_event["SemanticAttributes"][0]
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
                        
                        self.logger.info(f"Found {len(results)} events with attribute {attr_id}={attr_value}")
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
            
            # 3. Recurrence query - find recurring events
            self.results["queries_run"] += 1
            aql_query = f"""
            FOR doc IN {self.collection_name}
                FILTER doc.is_recurring == true
                RETURN doc
            """
            
            cursor = self.db.aql.execute(aql_query)
            results = list(cursor)
            
            self.logger.info(f"Found {len(results)} recurring events")
            if len(results) > 0:
                self.logger.info("Recurring events query successful")
                self.results["successful_queries"] += 1
                self.results["results"].append({
                    "query_name": "recurring_events_query",
                    "success": True,
                    "matches": len(results)
                })
            else:
                self.logger.warning("Recurring events query failed - no recurring events found")
                self.results["results"].append({
                    "query_name": "recurring_events_query",
                    "success": False,
                    "matches": 0
                })
            
            # 4. Online meeting query - find online meetings
            self.results["queries_run"] += 1
            aql_query = f"""
            FOR doc IN {self.collection_name}
                FILTER doc.is_online_meeting == true
                RETURN doc
            """
            
            cursor = self.db.aql.execute(aql_query)
            results = list(cursor)
            
            self.logger.info(f"Found {len(results)} online meetings")
            if len(results) > 0:
                self.logger.info("Online meetings query successful")
                self.results["successful_queries"] += 1
                self.results["results"].append({
                    "query_name": "online_meetings_query",
                    "success": True,
                    "matches": len(results)
                })
            else:
                self.logger.warning("Online meetings query failed - no online meetings found")
                self.results["results"].append({
                    "query_name": "online_meetings_query",
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
        self.logger.info("Starting calendar event database integration test...")
        
        success = (
            self.setup_db_connection() and
            self.generate_calendar_events() and
            self.upload_to_database() and
            self.run_queries()
        )
        
        # Always try to clean up, even if previous steps failed
        cleanup_success = self.cleanup_database()
        
        # Update final test results
        self.results["event_count"] = len(self.events)
        self.results["success"] = success and cleanup_success
        
        if success and cleanup_success:
            self.logger.info("Calendar event database integration test completed successfully")
        else:
            self.logger.warning("Calendar event database integration test failed")
        
        return self.results


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Database integration test for calendar events')
    
    parser.add_argument('--count', type=int, default=20,
                        help='Number of calendar events to generate (default: 20)')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='Skip database cleanup after test')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Create and run the test
    test = CalendarDBTest(
        count=args.count,
        cleanup=not args.no_cleanup,
        debug=args.debug
    )
    results = test.run()
    
    # Display summary
    print("\nCalendar Event Database Integration Test Summary:")
    print(f"- Event Count: {results['event_count']}")
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