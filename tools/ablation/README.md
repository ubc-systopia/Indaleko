# Ablation Study Framework

This package provides a comprehensive framework for conducting ablation studies on the impact of different activity data types on query performance in the Indaleko system. The framework is designed to generate synthetic activity data, track truth data for queries, and measure the impact of removing specific collections on query results.

## Current Implementation Status

The current implementation focuses on the query generation and synthetic metadata components of the ablation study framework. The actual ablation mechanism will be designed and implemented in a future phase.

### Implemented Components

1. **Base Interfaces**
   - Core interfaces for collectors, recorders, query generators, and truth data trackers
   - Base model classes for activity data and named entities

2. **Query Generation**
   - Query generator for creating natural language queries
   - Rule-based and LLM-based query parsing
   - Component extraction for matching metadata generation

3. **Truth Data Tracking**
   - Mechanism for recording which records should match each query
   - Metrics calculation for precision, recall, and F1 score

4. **Named Entity Recognition**
   - Management of named entities across queries and metadata
   - Database integration for persistent entity storage

5. **Data Models**
   - Base activity model shared across all activity types
   - Music activity models for tracks, artists, albums, and playback sessions
   - Semantic attribute structure for standardized metadata

### Pending Components

1. **Activity Data Collectors**
   - Synthetic data generators for all six activity types
   - Matching metadata generation based on query components
   - Non-matching metadata generation for distractor records

2. **Activity Data Recorders**
   - Database integration for storing synthetic data
   - Collection management and metadata normalization

3. **Ablation Testing Framework**
   - Collection ablation mechanism
   - Query execution with ablated collections
   - Comprehensive test runner and reporting

4. **Remaining Activity Models**
   - Location activity models
   - Task activity models
   - Collaboration activity models
   - Storage activity models
   - Media activity models

## Usage

This framework is still under development. The current components can be used as follows:

### Query Generation

```python
from tools.ablation.query.generator import QueryGenerator

# Create a query generator
generator = QueryGenerator()

# Generate queries for a specific activity type
music_queries = generator.generate_queries("music", 10)

# Parse a query to extract components
query_text = "What songs did I listen to by Taylor Swift last week?"
components = generator.parse_query(query_text, activity_type="music")
```

### Truth Data Tracking

```python
from tools.ablation.query.truth_tracker import TruthDataTracker

# Create a truth data tracker
tracker = TruthDataTracker()

# Record truth data for a query
tracker.record_query_truth(
    query_id="123",
    matching_ids=["a1", "a2", "a3"],
    activity_type="music",
    query_text="What songs did I listen to by Taylor Swift last week?"
)

# Calculate metrics for query results
result_ids = ["a1", "a2", "a4", "a5"]
metrics = tracker.calculate_metrics("123", result_ids)
```

### Named Entity Management

```python
from tools.ablation.ner.entity_manager import EntityManager

# Create an entity manager
manager = EntityManager()

# Add a named entity
entity_id = manager.add_entity(
    name="Seattle",
    entity_type="location",
    attributes={
        "country": "USA",
        "state": "Washington",
        "coordinates": {
            "latitude": 47.6062,
            "longitude": -122.3321
        }
    }
)

# Get a named entity
entity = manager.get_entity("Seattle", "location")
```

### Music Activity Models

```python
from tools.ablation.models.music_activity import (
    MusicActivityModel,
    TrackModel,
    ArtistModel,
    AlbumModel,
    create_semantic_attributes_from_music_activity
)

# Create artist, album, and track
artist = ArtistModel(name="Taylor Swift", genres=["pop", "country"])
album = AlbumModel(title="1989", artist="Taylor Swift")
track = TrackModel(title="Shake It Off", artist="Taylor Swift", duration_seconds=219)

# Create a music activity
activity = MusicActivityModel(
    track=track,
    artist=artist,
    album=album,
    start_time=datetime.now(timezone.utc)
)

# Add events to the activity
activity.add_event("play", 0)
activity.add_event("pause", 60)

# Update the end time
activity.update_end_time()

# Generate semantic attributes
attributes = create_semantic_attributes_from_music_activity(activity)
```

## Testing

The framework includes comprehensive unit tests for all components. To run the tests:

```bash
python -m unittest discover -s tools/ablation/tests
```

## Next Steps

The next phase of development will focus on:

1. Implementing the collectors for all six activity types
2. Developing the corresponding recorders for database integration
3. Designing and implementing the ablation testing mechanism
4. Creating a comprehensive test runner and reporting system

See the implementation plan for more details.
