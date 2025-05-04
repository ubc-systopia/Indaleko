#!/usr/bin/env python3
"""
Test data generator script.

This script generates test storage, semantic, activity, and relationship metadata and 
inserts them into the database for testing the enhanced data generator.
"""

import hashlib
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Bootstrap project root so imports work
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    # Walk up until we find the project entry point
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from tools.data_generator_enhanced.generators.storage import StorageMetadataGeneratorImpl
from tools.data_generator_enhanced.generators.semantic import SemanticMetadataGeneratorImpl
from tools.data_generator_enhanced.generators.activity import ActivityMetadataGeneratorImpl
from tools.data_generator_enhanced.generators.relationships import RelationshipGeneratorImpl
from tools.data_generator_enhanced.generators.machine_config import MachineConfigGeneratorImpl


def setup_collections(db_config: IndalekoDBConfig) -> None:
    """Set up required collections in the database.
    
    Args:
        db_config: Database configuration
    """
    # Make sure the object collection exists
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_Object_Collection):
        logging.info(f"Creating Objects collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_Object_Collection)
    
    # Make sure the semantic data collection exists
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_SemanticData_Collection):
        logging.info(f"Creating SemanticData collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_SemanticData_Collection)
    
    # Make sure the activity data collections exist
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_GeoActivityData_Collection):
        logging.info(f"Creating GeoActivityData collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_GeoActivityData_Collection)
    
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_MusicActivityData_Collection):
        logging.info(f"Creating MusicActivityData collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_MusicActivityData_Collection)
    
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_TempActivityData_Collection):
        logging.info(f"Creating TempActivityData collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_TempActivityData_Collection)
    
    # Make sure the relationship collection exists
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_Relationship_Collection):
        logging.info(f"Creating Relationship collection as an edge collection")
        db_config.db.create_collection(
            IndalekoDBCollections.Indaleko_Relationship_Collection,
            edge=True  # This is important for ArangoDB to recognize it as an edge collection
        )
    
    # Make sure the machine config collection exists
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_MachineConfig_Collection):
        logging.info(f"Creating MachineConfig collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_MachineConfig_Collection)


def insert_storage_records(db_config: IndalekoDBConfig, records: list) -> None:
    """Insert storage records into the database.
    
    Args:
        db_config: Database configuration
        records: Storage records to insert
    """
    if not records:
        logging.info("No storage records to insert")
        return
    
    try:
        collection = db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
        logging.info(f"Inserting {len(records)} storage records into database")
        
        # Insert records one by one for better error handling
        success_count = 0
        for record in records:
            try:
                collection.insert(record)
                success_count += 1
            except Exception as inner_e:
                logging.error(f"Error inserting record {record.get('_key')}: {inner_e}")
        
        logging.info(f"Successfully inserted {success_count} storage records")
    except Exception as e:
        logging.error(f"Error setting up storage record insertion: {e}")
        raise


def main():
    """Generate test data and insert into database."""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    db_config = IndalekoDBConfig()
    db_config.setup_database(db_config.config["database"]["database"])
    
    # Set up collections
    setup_collections(db_config)
    
    # Configuration for storage generator
    storage_config = {
        "distributions": {
            "file_sizes": {"type": "lognormal", "mu": 8.5, "sigma": 2.0},
            "modification_times": {"type": "normal", "mean": "now-30d", "std": "15d"},
            "file_extensions": {
                "type": "weighted", 
                "values": {
                    ".pdf": 0.2, 
                    ".docx": 0.3, 
                    ".txt": 0.5
                }
            }
        }
    }
    
    # Generate storage records
    storage_generator = StorageMetadataGeneratorImpl(storage_config, seed=42)
    storage_records = storage_generator.generate(50)
    
    # Create some PDF files specifically for testing
    pdf_storage_config = storage_config.copy()
    pdf_storage_config["distributions"]["file_extensions"] = {
        "type": "weighted", 
        "values": {
            ".pdf": 1.0
        }
    }
    pdf_storage_generator = StorageMetadataGeneratorImpl(pdf_storage_config, seed=43)
    pdf_records = pdf_storage_generator.generate(20)
    storage_records.extend(pdf_records)
    
    # Use the regular function for inserting storage records first
    insert_storage_records(db_config, storage_records)
    
    # Generate truth records using the generator - this will ensure correct schema
    # First check if collections exist and create them if needed
    if not db_config.db.has_collection(IndalekoDBCollections.Indaleko_Object_Collection):
        logging.info(f"Creating Objects collection")
        db_config.db.create_collection(IndalekoDBCollections.Indaleko_Object_Collection)
    
    # Create truth records for financial reports
    criteria = {
        "file_extension": ".pdf",
        "time_range": {
            "start": (datetime.now() - timedelta(days=5)).timestamp(),
            "end": datetime.now().timestamp()
        },
        "name_pattern": "FinanceReport%"
    }
    
    # Generate storage records using predefined PDF config to ensure they're PDFs
    storage_generator = StorageMetadataGeneratorImpl(pdf_storage_config, seed=99)
    
    # Use the generate method to create records with the right schema
    truth_records = []
    
    # Let's create fewer records but more controlled
    for i in range(5):
        # Create record for a finance report with specific criteria
        finance_record = storage_generator.generate(1)[0]
        finance_record["Name"] = f"FinanceReport_{i+1}.pdf"
        finance_record["Path"] = f"C:\\Documents\\Finance\\Reports\\FinanceReport_{i+1}.pdf"
        finance_record["Label"] = f"FinanceReport_{i+1}.pdf"  # Using the Label field which is expected by the schema
        finance_record["LocalPath"] = "C:\\Documents\\Finance\\Reports"  # Required by schema
        finance_record["URI"] = f"file:///C:/Documents/Finance/Reports/FinanceReport_{i+1}.pdf"
        finance_record["ObjectIdentifier"] = str(uuid.uuid4())
        truth_records.append(finance_record)
    
    # Store the truth record keys in a separate list
    truth_storage_keys = [record["_key"] for record in truth_records]
    
    # Insert the real truth records one by one for better error visibility
    for record in truth_records:
        try:
            db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).insert(record)
            logging.info(f"Inserted truth record: {record['_key']} - {record.get('Label')}")
        except Exception as e:
            logging.error(f"Error inserting truth record {record['_key']}: {e}")
    
    # Re-verify all truth records are in the database, ensuring we use our collection reference
    verified_truth_keys = []
    objects_collection = db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
    for key in truth_storage_keys:
        try:
            record = objects_collection.get(key)
            if record:
                verified_truth_keys.append(key)
                logging.info(f"Verified truth record: {key} - {record.get('Name')}")
            else:
                logging.warning(f"Failed to verify truth record: {key}")
        except Exception as e:
            logging.error(f"Error verifying truth record {key}: {e}")
    
    # Update truth keys to only those verified
    truth_storage_keys = verified_truth_keys
    storage_generator.truth_list = verified_truth_keys
    
    # Generate semantic metadata
    semantic_generator = SemanticMetadataGeneratorImpl({}, db_config, seed=42)
    
    # Generate semantic metadata for all storage records
    semantic_records = semantic_generator.generate(100)
    
    # Create semantic records for our truth storage records using the generator API
    truth_semantic_records = []
    
    # Ensure we're only using verified keys
    verified_truth_keys = []
    for storage_key in truth_storage_keys:
        try:
            record = db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(storage_key)
            if record:
                verified_truth_keys.append(storage_key)
            else:
                logging.warning(f"Storage record not found for semantic generation: {storage_key}")
        except Exception as e:
            logging.error(f"Error verifying storage record for semantic generation {storage_key}: {e}")
    
    if not verified_truth_keys:
        logging.warning("No verified storage records found for semantic generation")
    else:
        # Use the generator API to create semantic records
        try:
            # Get the full storage records to pass to the generator
            storage_records = []
            for key in verified_truth_keys:
                record = db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(key)
                if record:
                    storage_records.append(record)
                    
            # Generate semantic criteria for finance reports
            semantic_criteria = {
                "MIMEType": "application/pdf",
                "ContentType": "report",
                "ContentSummary": "A report about financial performance and business metrics.",
                "Keywords": ["quarterly", "analysis", "metrics", "performance", "report", "financial"],
                "Topics": ["Finance", "Business"],
                "ContentLanguage": "en",
                "Title": "Quarterly Financial Report",
                "Author": "Finance Department"
            }
            
            # Use the generator's API to create semantic records with the right schema
            for storage_record in storage_records:
                try:
                    record_result = semantic_generator.generate_truth(1, {
                        "storage_keys": [storage_record["_key"]],
                        "semantic_criteria": semantic_criteria
                    })
                    
                    if record_result:
                        truth_semantic_records.extend(record_result)
                        logging.info(f"Generated semantic truth record for {storage_record['_key']}")
                except Exception as e:
                    logging.error(f"Error generating semantic record: {e}")
        except Exception as e:
            logging.error(f"Error in semantic record generation: {e}")
    
    # Generate activity metadata
    activity_generator = ActivityMetadataGeneratorImpl({}, db_config, seed=44)
    
    # Generate activity metadata for all storage records
    activity_records = activity_generator.generate(100)
    
    # Create truth activity records (location for finance reports in New York)
    truth_activity_records = []
    
    # Verify that the truth records exist in the database
    verified_truth_keys = []
    for storage_key in truth_storage_keys:
        storage_record = db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(storage_key)
        if storage_record:
            verified_truth_keys.append(storage_key)
        else:
            logging.warning(f"Truth storage record {storage_key} not found in database")
    
    if not verified_truth_keys:
        logging.warning("No verified truth records found. Cannot generate truth activity records.")
    else:
        logging.info(f"Found {len(verified_truth_keys)} verified truth records")
    
    # We'll use half of our truth storage records for location activity
    for i, storage_key in enumerate(verified_truth_keys):
        if i < len(verified_truth_keys) // 2:
            try:
                # Generate a specific location activity in New York for the finance report
                criteria = {
                    "activity_criteria": {
                        "type": "location",
                        "city": "New York",
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "days_ago": 5,  # 5 days ago
                        "description": "Report created in New York Financial District"
                    }
                }
                location_record = activity_generator.generate_truth(1, {
                    "storage_keys": [storage_key],
                    "activity_criteria": criteria["activity_criteria"]
                })
                if location_record:
                    truth_activity_records.extend(location_record)
                    logging.info(f"Generated location activity for {storage_key}")
            except Exception as e:
                logging.error(f"Error generating location record for {storage_key}: {e}")
        else:
            try:
                # Generate a specific music activity with classical music for the finance report
                criteria = {
                    "activity_criteria": {
                        "type": "music",
                        "artist": "Mozart",
                        "genre": "Classical",
                        "album": "Classical Focus",
                        "track": "Symphony No. 40",
                        "days_ago": 6,  # 6 days ago
                        "description": "Music played while creating financial report"
                    }
                }
                music_record = activity_generator.generate_truth(1, {
                    "storage_keys": [storage_key],
                    "activity_criteria": criteria["activity_criteria"]
                })
                if music_record:
                    truth_activity_records.extend(music_record)
                    logging.info(f"Generated music activity for {storage_key}")
            except Exception as e:
                logging.error(f"Error generating music record for {storage_key}: {e}")
            
    # Update the storage generator's truth list to match our actual inserted keys            
    storage_generator.truth_list = truth_storage_keys
    
    # Generate machine configurations
    logging.info("Generating machine configuration records")
    machine_config_generator = MachineConfigGeneratorImpl({}, db_config, seed=46)
    machine_config_records = machine_config_generator.generate(15)  # Generate 15 device configurations
    
    # Create specific truth machine configurations
    # Generate an iOS mobile device for testing
    mobile_truth_criteria = {
        "machine_criteria": {
            "device_type": "mobile",
            "os": "iOS",
            "version": "16.5.1",
            "days_ago": 5  # Configuration captured 5 days ago
        }
    }
    
    mobile_truth_records = machine_config_generator.generate_truth(2, mobile_truth_criteria)
    logging.info(f"Generated {len(mobile_truth_records)} truth mobile device records")
    
    # Generate a Windows laptop for testing
    laptop_truth_criteria = {
        "machine_criteria": {
            "device_type": "laptop",
            "os": "Windows",
            "version": "11 Pro",
            "days_ago": 3  # Configuration captured 3 days ago
        }
    }
    
    laptop_truth_records = machine_config_generator.generate_truth(1, laptop_truth_criteria)
    logging.info(f"Generated {len(laptop_truth_records)} truth laptop records")
    
    # Generate relationships between all metadata types
    logging.info("Generating relationships between metadata records")
    relationship_generator = RelationshipGeneratorImpl({}, db_config, seed=45)
    relationship_records = relationship_generator.generate(100)
    
    # Create truth relationships between certain storage and activity records
    truth_relationship_records = []
    
    # Create specific relationships between truth storage records and their activity records
    # First, identify the specific finance report that should be linked to New York location
    finance_storage_keys = []
    location_keys = []
    
    # Find finance reports with New York location records
    for storage_key in verified_truth_keys[:len(verified_truth_keys)//2]:
        # Check if there's a location activity record for this storage key
        for collection_name in [IndalekoDBCollections.Indaleko_GeoActivityData_Collection]:
            try:
                cursor = db_config.db.aql.execute(
                    f"""
                    FOR doc IN {collection_name}
                    FILTER doc.Object == @storage_key AND doc.city == "New York"
                    LIMIT 1
                    RETURN doc
                    """,
                    bind_vars={"storage_key": storage_key}
                )
                location_record = next(cursor, None)
                if location_record:
                    finance_storage_keys.append(storage_key)
                    location_keys.append(location_record["_key"])
                    break
            except Exception as e:
                logging.error(f"Error querying for location record: {e}")
    
    # Create truth relationships with specific criteria
    if finance_storage_keys and location_keys:
        try:
            # Generate truth relationships between finance reports and New York location
            truth_criteria = {
                "source_keys": finance_storage_keys[:2],  # First 2 finance reports
                "target_keys": location_keys[:2],         # Their corresponding location records
                "relationship_criteria": {
                    "type": "CREATED_AT",
                    "description": "Report created in New York Financial District"
                }
            }
            
            # Generate specific relationship records for our query testing
            truth_rels = relationship_generator.generate_truth(2, truth_criteria)
            truth_relationship_records.extend(truth_rels)
            logging.info(f"Generated {len(truth_rels)} truth relationships between finance reports and New York location")
        except Exception as e:
            logging.error(f"Error generating truth relationships: {e}")
    else:
        logging.warning("No suitable finance reports or location records found for truth relationships")
    
    # Print statistics
    logging.info(f"Generated and inserted {len(storage_records)} regular storage records")
    logging.info(f"Generated and inserted {len(truth_records)} truth storage records")
    logging.info(f"Generated and inserted {len(semantic_records)} regular semantic records")
    logging.info(f"Generated and inserted {len(truth_semantic_records)} truth semantic records")
    logging.info(f"Generated and inserted {len(activity_records)} regular activity records")
    logging.info(f"Generated and inserted {len(truth_activity_records)} truth activity records")
    logging.info(f"Generated and inserted {len(relationship_records)} regular relationship records")
    logging.info(f"Generated and inserted {len(truth_relationship_records)} truth relationship records")
    logging.info(f"Generated and inserted {len(machine_config_records)} regular machine configuration records")
    logging.info(f"Generated and inserted {len(mobile_truth_records) + len(laptop_truth_records)} truth machine configuration records")
    
    # Print truth lists for verification
    logging.info(f"Storage truth list: {storage_generator.truth_list}")
    logging.info(f"Semantic truth list: {semantic_generator.truth_list}")
    logging.info(f"Activity truth list: {activity_generator.truth_list}")
    logging.info(f"Relationship truth list: {relationship_generator.truth_list}")
    logging.info(f"Machine config truth list: {machine_config_generator.truth_list}")


if __name__ == "__main__":
    main()
