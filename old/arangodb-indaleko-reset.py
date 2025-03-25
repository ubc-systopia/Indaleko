from arango import ArangoClient


def reset_collections(db_name, collection_names):
    # ArangoDB connection settings
    arango_url = "http://localhost:8529"
    arango_username = "tony"
    arango_password = "Kwishut$23!"
    arango_db_name = db_name

    # Initialize the ArangoDB client
    client = ArangoClient()

    # Connect to the database
    db = client.db(
        arango_db_name,
        username=arango_username,
        password=arango_password,
        auth_method="basic",
    )

    # Iterate over the collection names
    for name in collection_names:
        # Delete the collection if it exists
        if db.has_collection(name):
            db.delete_collection(name)

        # Create the collection
        db.create_collection(name)


# Use the function
reset_collections("Indaleko", ["DataObjects", "contains", "contained_by"])
