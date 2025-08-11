import time
import uuid

from neo4j import GraphDatabase


# Neo4j connection settings
neo4j_uri = "bolt://127.0.0.1:7687"
neo4j_username = "neo4j"
neo4j_password = None

# Number of UUIDs to generate and insert
num_uuids = 10  # 0000

batch_size = 10

# Connect to Neo4j
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

# Generate and insert UUIDs
start_time = time.time()

# Generate and insert UUIDs
successful_create_count = 0
with driver.session() as session:
    for _i in range(0, num_uuids, batch_size):
        batch_uuids = [str(uuid.uuid4()) for _ in range(batch_size)]
        query = "UNWIND $batch AS uuid CREATE (:DataObject {value: uuid})"
        result = session.run(query, batch=batch_uuids)
        # Check the result (optional)
        summary = result.consume()
        if summary.counters.nodes_created == 1:
            successful_create_count += 1


end_time = time.time()
elapsed_time = end_time - start_time

