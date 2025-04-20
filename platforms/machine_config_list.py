#!/usr/bin/env python3
"""
Simple script to list machine configurations.
This is a lightweight version that bypasses the performance issues
in the circular dependency fix.
"""

import os
import sys
import json
from icecream import ic

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import DB config
from db.db_config import IndalekoDBConfig

def list_machine_configs():
    """List all machine configurations directly using AQL."""
    # Create DB config and connect
    db_config = IndalekoDBConfig()
    db_config.start()
    
    # Query machine configs directly
    collection_name = "MachineConfig"
    
    try:
        # Execute AQL query directly
        cursor = db_config.db.aql.execute(
            "FOR doc IN @@collection RETURN doc",
            bind_vars={"@collection": collection_name},
        )
        
        # Process results
        configs = list(cursor)
        print(f"Found {len(configs)} machine configurations:")
        
        # Print each config
        for config in configs:
            print(json.dumps(config, indent=4))
            print("-" * 40)
    
    except Exception as e:
        print(f"Error listing machine configurations: {e}")
        return None

if __name__ == "__main__":
    list_machine_configs()