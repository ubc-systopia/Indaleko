# Named Entity Generator

This module provides a comprehensive generator for creating synthetic named entities and relationships for the Indaleko system. It generates realistic data for people, organizations, locations, and items that can be stored in the ArangoDB database and used to test search and query functionality.

## Overview

The `NamedEntityGeneratorTool` creates named entities with rich attributes, relationships, and semantic annotations. These entities form the foundation for natural language queries that refer to entities by name or relationship.

## Features

- **Multiple Entity Types**: Generates people, organizations, locations, and items with appropriate attributes
- **Realistic Names**: Creates realistic names for all entity types based on common patterns
- **Rich Descriptions**: Provides detailed descriptions for each entity using templates
- **Semantic Attributes**: Generates searchable semantic attributes for each entity type
- **Relationship Generation**: Creates typed relationships between entities with confidence scores
- **Common Location References**: Shares common locations (home, work, etc.) across entities
- **Truth Set Creation**: Supports creating specific "truth" entities for testing targeted queries
- **Database Integration**: Generated entities are compatible with the ArangoDB schema

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.named_entity_generator import NamedEntityGeneratorTool

# Initialize the generator
generator = NamedEntityGeneratorTool()

# Generate entities with default parameters
result = generator.execute({
    "entity_counts": {
        "person": 5,
        "organization": 3,
        "location": 4,
        "item": 3
    },
    "relationship_density": 0.5
})

# Access the generated entities
people = result["entities"]["person"]
organizations = result["entities"]["organization"]
locations = result["entities"]["location"]
items = result["entities"]["item"]

# Access relationships
relationships = result["relationships"]

# Access common locations
common_locations = result["common_locations"]
```

### Advanced Usage

#### With Truth Criteria

```python
# Generate entities with specific "truth" entities for targeted testing
result = generator.execute({
    "entity_counts": {
        "person": 5,
        "organization": 3,
        "location": 4,
        "item": 3
    },
    "relationship_density": 0.5,
    "truth_criteria": {
        "person": {
            "name": "Tony Mason",
            "attributes": {
                "profession": "researcher",
                "expertise": "computer science"
            }
        },
        "location": {
            "name": "Redmond",
            "gis_location": {
                "latitude": 47.6739,
                "longitude": -122.1215
            }
        }
    }
})

# Access truth entities
truth_entities = result["truth_entities"]
```

#### With Custom Common Locations

```python
# Generate entities with pre-defined common locations
result = generator.execute({
    "entity_counts": {
        "person": 5,
        "organization": 3,
        "location": 4,
        "item": 3
    },
    "common_locations": {
        "home": "Seattle",
        "work": "Microsoft Campus",
        "favorite_restaurant": "The Barking Frog"
    }
})
```

## Entity Structure

### Person Entity

```json
{
  "Id": "uuid_string",
  "name": "John Smith",
  "category": "person",
  "description": "A 42-year-old software engineer who enjoys photography",
  "attributes": {
    "first_name": "John",
    "last_name": "Smith",
    "profession": "software engineer",
    "age": 42,
    "hobbies": ["photography", "hiking", "reading"],
    "expertise": "artificial intelligence"
  },
  "references": {
    "home": "Greenwood",
    "work": "Downtown Tech Center",
    "favorite_places": ["Central Park", "Joe's Coffee", "City Gym"]
  },
  "semantic_attributes": [
    {
      "Identifier": "entity_PERSON_NAME_id",
      "Value": "John Smith"
    },
    {
      "Identifier": "entity_PERSON_PROFESSION_id",
      "Value": "software engineer"
    }
  ],
  "created_at": "2024-05-05T12:34:56.789Z"
}
```

### Organization Entity

```json
{
  "Id": "uuid_string",
  "name": "Global Tech Solutions Inc",
  "category": "organization",
  "description": "A leading technology company specializing in cloud computing",
  "attributes": {
    "industry": "technology",
    "size": "large",
    "type": "corporation",
    "founded": 2005,
    "focus": "cloud computing"
  },
  "references": {
    "headquarters": "Silicon Valley",
    "key_people": ["Jane Doe", "Robert Johnson", "Maria Garcia"]
  },
  "semantic_attributes": [
    {
      "Identifier": "entity_ORGANIZATION_NAME_id",
      "Value": "Global Tech Solutions Inc"
    },
    {
      "Identifier": "entity_ORGANIZATION_INDUSTRY_id",
      "Value": "technology"
    }
  ],
  "created_at": "2024-05-05T12:34:56.789Z"
}
```

### Location Entity

```json
{
  "Id": "uuid_string",
  "name": "Westlake",
  "category": "location",
  "description": "A bustling neighborhood known for its shops and restaurants",
  "gis_location": {
    "source": "defined",
    "timestamp": "2024-05-05T12:34:56.789Z",
    "latitude": 47.6205,
    "longitude": -122.3393
  },
  "attributes": {
    "type": "neighborhood",
    "features": ["shopping district", "vibrant culture", "scenic waterfront"],
    "activities": ["shopping", "dining", "entertainment"],
    "population": "medium"
  },
  "references": {
    "nearby": ["Downtown", "Capitol Hill", "Queen Anne"],
    "notable_places": ["The Grand Mall", "Central Market", "Lakeside Park"]
  },
  "semantic_attributes": [
    {
      "Identifier": "entity_LOCATION_NAME_id",
      "Value": "Westlake"
    },
    {
      "Identifier": "entity_LOCATION_TYPE_id",
      "Value": "neighborhood"
    }
  ],
  "created_at": "2024-05-05T12:34:56.789Z"
}
```

### Item Entity

```json
{
  "Id": "uuid_string",
  "name": "Ultra Laptop Pro",
  "category": "item",
  "description": "A premium laptop featuring high-resolution display",
  "device_id": "uuid_string",
  "attributes": {
    "type": "laptop",
    "color": "silver",
    "material": "aluminum",
    "condition": "new",
    "features": ["high-resolution display", "fast processor", "long battery life"]
  },
  "references": {
    "manufacturer": "TechCorp Inc",
    "owner": "John Smith",
    "location": "Greenwood"
  },
  "semantic_attributes": [
    {
      "Identifier": "entity_ITEM_NAME_id",
      "Value": "Ultra Laptop Pro"
    },
    {
      "Identifier": "entity_ITEM_TYPE_id",
      "Value": "laptop"
    }
  ],
  "created_at": "2024-05-05T12:34:56.789Z"
}
```

### Relationship Structure

```json
{
  "Id": "uuid_string",
  "entity1_id": "uuid_of_entity1",
  "entity1_name": "John Smith",
  "entity1_type": "person",
  "relationship_type": "employee",
  "entity2_id": "uuid_of_entity2",
  "entity2_name": "Global Tech Solutions Inc",
  "entity2_type": "organization",
  "confidence": 0.95,
  "is_reversed": false,
  "created_at": "2024-05-05T12:34:56.789Z"
}
```

## Query Patterns

The NamedEntityGeneratorTool is designed to support the following query patterns:

1. **Direct entity lookup**:
   - "Find information about John Smith"
   - "What do we know about Global Tech Solutions?"

2. **Relationship queries**:
   - "Where does John Smith work?"
   - "Who are the employees of Global Tech Solutions?"
   - "What items does John Smith own?"

3. **Location-based queries**:
   - "What companies are headquartered in Silicon Valley?"
   - "Where is John Smith's home?"
   - "What organizations are located in Westlake?"

4. **Attribute-based queries**:
   - "Find people who are software engineers"
   - "What organizations are in the technology industry?"
   - "Find laptops with high-resolution displays"

5. **Combined queries**:
   - "Find items owned by people who work at Global Tech Solutions"
   - "What organizations are headquartered near John Smith's home?"
   - "Find people who live in Westlake and own laptops"

## Integration with Other Generators

The NamedEntityGeneratorTool is designed to integrate with other generators:

- **LocationGeneratorTool**: Named entities reference and complement location data
- **SocialMediaActivityGeneratorTool**: Social media posts can mention named entities
- **CalendarEventGeneratorTool**: Calendar events involve people, organizations, and locations
- **CloudStorageActivityGeneratorTool**: Storage activities involve people and items

## Running Tests

To run the tests for the NamedEntityGeneratorTool:

```bash
# On Linux/macOS
./tools/data_generator_enhanced/run_named_entity_tests.sh

# On Windows
.\tools\data_generator_enhanced\run_named_entity_tests.bat
```