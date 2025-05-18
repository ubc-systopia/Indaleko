# For AblationCollaborationActivity collection
  {
      "type": "hash",
      "fields": ["platform"],
      "unique": False
  },
  {
      "type": "hash",
      "fields": ["event_type"],
      "unique": False
  },
  {
      "type": "hash",
      "fields": ["source"],
      "unique": False
  },
  {
      "type": "persistent",
      "fields": ["participants[*].name"],
      "sparse": True
  },
  {
      "type": "persistent",
      "fields": ["participants[*].email"],
      "sparse": True
  }

  # For AblationTruthData collection
  {
      "type": "hash",
      "fields": ["query_id"],
      "unique": False
  },
  {
      "type": "hash",
      "fields": ["collection"],
      "unique": False
  },
  {
      "type": "hash",
      "fields": ["query_id", "collection"],
      "unique": True
  }

 def create_indices():
      """Create indices for ablation test collections to improve performance."""
      db_config = IndalekoDBConfig()
      db = db_config.get_arangodb()

      # Create indices for CollaborationActivity
      collab_collection = db.collection("AblationCollaborationActivity")
      collab_collection.add_hash_index(["platform"], unique=False)
      collab_collection.add_hash_index(["event_type"], unique=False)
      collab_collection.add_hash_index(["source"], unique=False)

      # This creates an index on array elements
      collab_collection.add_index({
          "type": "persistent",
          "fields": ["participants[*].name"],
          "sparse": True
      })

      collab_collection.add_index({
          "type": "persistent",
          "fields": ["participants[*].email"],
          "sparse": True
      })

      # Create indices for TruthData
      truth_collection = db.collection("AblationTruthData")
      truth_collection.add_hash_index(["query_id"], unique=False)
      truth_collection.add_hash_index(["collection"], unique=False)

      # For the combined key, a unique hash index would be appropriate
      truth_collection.add_hash_index(["query_id", "collection"], unique=True)
