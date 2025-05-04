#!/usr/bin/env python3
"""Test ArangoDB connection and functionality."""

from db import IndalekoDBConfig

# Create a database connection
db = IndalekoDBConfig()

# Test basic connectivity
print("Database connection status:", "Connected" if db.get_arangodb() else "Failed")
print("Database version:", db.get_arangodb().version())

# List collections
print("\nCollections (first 5):")
collections = db.get_arangodb().collections()
for collection in collections[:5]:
    print(f"- {collection['name']} ({collection['type']})")

# Test a simple AQL query
try:
    print("\nTesting AQL functionality:")
    res = db.get_arangodb().aql.execute("RETURN 1+1")
    print("AQL test result:", list(res)[0])
except Exception as e:
    print("AQL error:", str(e))

# Test for the specific error we saw
try:
    print("\nTesting admin execute endpoint:")
    db.get_arangodb().execute("RETURN 1+1")
    print("Execute test: Success")
except Exception as e:
    print("Execute error:", str(e))

print("\nTest completed")
