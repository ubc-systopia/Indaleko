#!/usr/bin/env python3
"""
Test script for database reset functionality.
"""
import os
import sys
import logging
from db.db_config import IndalekoDBConfig

# Set up environment variables and paths
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def reset_database():
    """Reset the database to a clean state."""
    logging.info("Resetting database...")
    
    try:
        # Create a DB config instance first
        db_config = IndalekoDBConfig()
        # Then call start() with reset=True
        db_config.start(reset=True)
        logging.info("Database reset successful")
        return True
    except Exception as e:
        logging.error(f"Error resetting database: {e}")
        return False

def main():
    """Main entry point."""
    setup_logging()
    logging.info("Testing database reset functionality...")
    
    # Try resetting the database
    if reset_database():
        logging.info("Database reset SUCCESS!")
    else:
        logging.error("Database reset FAILED!")
    
    logging.info("Test complete")

if __name__ == "__main__":
    main()