import time
import uuid

from arango import ArangoClient

# ArangoDB connection settings
arango_url = "http://localhost:8529"
arango_username = "tony"
arango_password = None
arango_db_name = "Indaleko"
arango_collection_name = "load-test"

# Number of UUIDs to generate and insert
num_uuids = 1000000

# Connect to ArangoDB
client = ArangoClient()
db = client.db(
    arango_db_name,
    username=arango_username,
    password=arango_password,
    auth_method="basic",
)

# Start with a clean collection each run
if db.has_collection(arango_collection_name):
    db.delete_collection(arango_collection_name)
collection = db.create_collection(arango_collection_name)

# Generate and insert UUIDs
start_time = time.time()

# Generate and insert UUIDs
uuids = [str(uuid.uuid4()) for _ in range(num_uuids)]
dummy_files = [{"objectid": uuid, "creator": "tony"} for uuid in uuids]
result = collection.insert_many(dummy_files)

end_time = time.time()
elapsed_time = end_time - start_time

print("UUIDs inserted:", num_uuids)
print("Elapsed time:", elapsed_time, "seconds")
