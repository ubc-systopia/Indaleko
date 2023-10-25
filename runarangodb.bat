REM https://hub.docker.com/_/arangodb/
docker run -e ARANGO_ROOT_PASSWORD=Kwishut22 -d -p 8529:8529 --mount source=ArangoDB-wam-db-1,target=/var/lib/arangodb3 --name arangodb-instance arangodb
