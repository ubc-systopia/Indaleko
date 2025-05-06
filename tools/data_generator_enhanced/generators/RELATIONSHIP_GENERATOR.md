# Relationship Metadata Generator

The Relationship Generator creates connections between different metadata records in the enhanced data generator. It establishes meaningful relationships between storage, semantic, and activity metadata to create a realistic and interconnected data model for testing Indaleko's search capabilities.

## Core Features

- Generates relationships between files (storage-to-storage)
- Creates links between files and their semantic metadata
- Establishes connections between files and activity contexts (location, music, temperature)
- Directly integrates with the ArangoDB database
- Uses weighted probabilities for realistic relationship distribution
- Supports generating specific "truth records" for testing search accuracy

## Relationship Types

The generator supports various relationship types, including:

### File-File Relationships
- **DERIVED_FROM**: Indicates one file is derived from another
- **CONTAINS**: Indicates a file contains another file (e.g., ZIP archive)
- **CONTAINED_BY**: Indicates a file is contained by another file
- **RELATED_TO**: Indicates files are related in some way
- **SAME_FOLDER**: Indicates files are in the same folder
- **VERSION_OF**: Indicates one file is a version of another

### File-Activity Relationships
- **CREATED_AT**: Links a file to a location where it was created
- **MODIFIED_AT**: Links a file to a location where it was modified
- **ACCESSED_AT**: Links a file to a location where it was accessed
- **PLAYING_MUSIC**: Links a file to music being played during file activity
- **TEMPERATURE_CONTEXT**: Links a file to temperature conditions during file activity

## Implementation Details

The relationship generator:

1. Queries the database for existing storage, semantic, and activity records
2. Creates appropriate edges in the relationship collection based on record types
3. Uses weighted probabilities to distribute relationship types realistically
4. Ensures the relationship collection is configured as an edge collection
5. Creates unique keys for each relationship to prevent duplicates
6. Includes proper semantic attributes to define the relationship type

## Database Schema

Relationships are stored in the `Relationships` collection with the following structure:

- **_key**: Unique identifier for the relationship (MD5 hash of source, target, and type)
- **_from**: Source vertex identifier (collection/key)
- **_to**: Target vertex identifier (collection/key)
- **Record**: Metadata about the relationship (timestamp, source identifier)
- **Objects**: List of object UUIDs in the relationship
- **Relationships**: List of semantic attributes defining the relationship type

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.generators.relationships import RelationshipGeneratorImpl
from db.db_config import IndalekoDBConfig

# Initialize database connection
db_config = IndalekoDBConfig()

# Create relationship generator
relationship_generator = RelationshipGeneratorImpl({}, db_config, seed=42)

# Generate relationships between existing records
relationship_records = relationship_generator.generate(100)
```

### Generating Truth Records

For testing specific queries, you can create truth records with known relationship patterns:

```python
# Generate specific relationships for testing
truth_criteria = {
    "source_keys": ["storage_key1", "storage_key2"],  # Storage objects
    "target_keys": ["location_key1", "location_key2"],  # Location records
    "relationship_criteria": {
        "type": "CREATED_AT",
        "description": "Files created in New York"
    }
}

# Generate truth relationships
truth_relationships = relationship_generator.generate_truth(2, truth_criteria)
```

## Integration with Test Data Generation

The relationship generator is integrated with the enhanced data generator pipeline:

1. Storage metadata is generated and inserted
2. Semantic metadata is generated for storage objects
3. Activity metadata is generated for storage objects
4. Relationships are created between all metadata types
5. Specific truth relationships are created for testing

## Error Handling

The relationship generator includes robust error handling:

- Database connection failures
- Record validation
- Record existence verification
- Collection validation
- Proper edge creation requirements

## Extending the Generator

To add new relationship types:

1. Add the new type to the `relationship_types` dictionary in the constructor
2. Specify an appropriate weight for the relationship type
3. Implement any custom logic for relationship creation in the relevant methods

## Performance Considerations

- Batch insertion for better performance
- Unique key generation to prevent duplicates
- Collection lookup optimization
- Error handling to prevent database failures
