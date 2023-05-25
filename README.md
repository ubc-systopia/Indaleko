# Test Scripts

These are some test scripts I have written for the Indaleko project.  There's
nothing deep here.

* README.md - this flie
* arangodb-indaleko-reset.py - this will reset the Indaleko database inside
  ArangoDB.  Note you will need to add your own passwords.
* arangodb-insert-test.py - this is my "insert an object" test where I used a
  UUID as the contents of the node being inserted.
* arangodb-local-ingest.py - this is my "scan the file system and insert
  everything into ArangoDB" script
* docker-compose.yml - not used
* enumerate-volume.py - Used to count the number of files and directories on a
  given volume (or a tree)
* neo4j-insert-test.py - Used to insert nodes into Neo4j with a UUID as the
  creamy filling.
* neo4j-local-ingest.py - this is the script I was using to stuff data into the
  Neo4j database from my local file system.


