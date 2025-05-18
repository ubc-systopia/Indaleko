# Location Activity Implementation Plan

This document outlines the depth-first implementation approach for the location activity collector and recorder in the ablation study framework.

## Overview

We will implement a complete end-to-end pipeline for location activity data, including:

1. Location activity data generation (collector)
2. Database storage (recorder)
3. LLM-based query generation with PromptManager integration
4. Query-truth integration
5. Ablation testing and metrics

This will serve as a template for the other activity types and validate our architecture.

### PromptManager Integration

Our implementation leverages Indaleko's PromptManager system with AyniGuard for AI-safe prompt management. The primary benefits are:

1. **Cognitive Protection**: Protecting AI from cognitive dissonance caused by contradictory or ill-structured prompts
2. **Layered Prompts**: Structuring prompts into coherent sections (context, requirements, preferences) for clarity and consistency
3. **Prompt Stability**: Evaluating prompts against stability criteria to prevent confusing or contradictory instructions
4. **Template Management**: Centralizing prompt templates to ensure consistent, well-tested prompts across the system

This integration not only ensures that our query generation is consistent and maintainable, but it also protects the AI from potential confusion or instability caused by poorly constructed prompts.

## Components to Implement

### 1. Location Activity Collector

The location activity collector will generate synthetic location data that mimics real-world user patterns.

```python
# research/ablation/collectors/location_collector.py

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import random
import uuid

from research.ablation.models.location_activity import LocationActivity


class LocationActivityCollector:
    """Collector for synthetic location activity data."""

    def __init__(self):
        """Initialize the location activity collector."""
        # Common location names and coordinates
        self.common_locations = {
            "home": {"lat": 37.7749, "lon": -122.4194, "accuracy": 5},
            "work": {"lat": 37.7833, "lon": -122.4167, "accuracy": 10},
            "coffee shop": {"lat": 37.7899, "lon": -122.4103, "accuracy": 15},
            "library": {"lat": 37.7691, "lon": -122.4449, "accuracy": 12},
            "gym": {"lat": 37.7831, "lon": -122.4181, "accuracy": 8},
            "park": {"lat": 37.7694, "lon": -122.4862, "accuracy": 20},
            "restaurant": {"lat": 37.7873, "lon": -122.4232, "accuracy": 10},
            "airport": {"lat": 37.6213, "lon": -122.3790, "accuracy": 30},
        }

    def collect(self, count: int = 50) -> List[LocationActivity]:
        """Generate synthetic location activity data.

        Args:
            count: Number of location activities to generate

        Returns:
            List of synthetic location activities
        """
        activities = []

        for _ in range(count):
            # Select a location (or generate a random one)
            use_common = random.random() < 0.8  # 80% chance of using common location

            if use_common:
                location_name = random.choice(list(self.common_locations.keys()))
                location_data = self.common_locations[location_name]
                latitude = location_data["lat"] + random.uniform(-0.001, 0.001)
                longitude = location_data["lon"] + random.uniform(-0.001, 0.001)
                accuracy = location_data["accuracy"]
            else:
                # Generate random location
                location_name = f"location_{uuid.uuid4().hex[:8]}"
                latitude = random.uniform(37.7, 37.8)
                longitude = random.uniform(-122.5, -122.4)
                accuracy = random.uniform(5, 50)

            # Generate timestamp
            now = datetime.now(timezone.utc)
            timestamp = now.replace(
                day=now.day - random.randint(0, 30),
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )

            # Create activity
            activity = LocationActivity(
                id=uuid.uuid4(),
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                timestamp=timestamp,
                duration_minutes=random.randint(5, 240),
                source="synthetic",
            )

            activities.append(activity)

        return activities

    def get_common_locations(self) -> Dict[str, Dict[str, float]]:
        """Get the dictionary of common locations."""
        return self.common_locations
```

### 2. Location Activity Recorder

The location activity recorder will store the generated data in the ArangoDB database.

```python
# research/ablation/recorders/location_recorder.py

import logging
from typing import Dict, List, Any, Optional
import uuid

from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from research.ablation.models.location_activity import LocationActivity


class LocationActivityRecorder:
    """Recorder for location activity data in ArangoDB."""

    def __init__(self):
        """Initialize the location activity recorder."""
        self.logger = logging.getLogger(__name__)

        # Set up database connection
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            self.collection_name = IndalekoDBCollections.Indaleko_Ablation_Location_Activity_Collection

            # Ensure collection exists
            if not self.db.has_collection(self.collection_name):
                self.db.create_collection(self.collection_name)
                self.logger.info(f"Created collection {self.collection_name}")

        except Exception as e:
            self.logger.error(f"FATAL: Failed to connect to database: {e}")
            # Database connection is required, so this is always a fatal error
            raise RuntimeError(f"Database connection is required. Error: {e}") from e

    def record(self, activities: List[LocationActivity]) -> int:
        """Record location activities to the database.

        Args:
            activities: List of location activities to record

        Returns:
            Number of successfully recorded activities
        """
        self.logger.info(f"Recording {len(activities)} location activities")

        collection = self.db.collection(self.collection_name)
        success_count = 0

        for activity in activities:
            try:
                # Convert activity to dictionary for storage
                doc = activity.model_dump()

                # Convert UUID to string
                doc["id"] = str(doc["id"])

                # Insert into the database
                result = collection.insert(doc)
                if result:
                    success_count += 1

            except Exception as e:
                self.logger.error(f"Error recording location activity: {e}")

        self.logger.info(f"Successfully recorded {success_count}/{len(activities)} location activities")
        return success_count

    def get_all_activities(self) -> List[Dict[str, Any]]:
        """Get all location activities from the database.

        Returns:
            List of all location activities
        """
        try:
            aql = f"""
            FOR doc IN {self.collection_name}
            RETURN doc
            """

            cursor = self.db.aql.execute(aql)
            return list(cursor)

        except Exception as e:
            self.logger.error(f"Error retrieving location activities: {e}")
            return []

    def get_activities_by_location(self, location_name: str) -> List[Dict[str, Any]]:
        """Get location activities for a specific location.

        Args:
            location_name: Name of the location to filter by

        Returns:
            List of matching location activities
        """
        try:
            aql = f"""
            FOR doc IN {self.collection_name}
            FILTER doc.location_name == @location_name
            RETURN doc
            """

            cursor = self.db.aql.execute(aql, bind_vars={"location_name": location_name})
            return list(cursor)

        except Exception as e:
            self.logger.error(f"Error retrieving location activities by name: {e}")
            return []

    def clear_all_activities(self) -> bool:
        """Clear all location activities from the database.

        Returns:
            True if successful, False otherwise
        """
        try:
            aql = f"""
            FOR doc IN {self.collection_name}
            REMOVE doc IN {self.collection_name}
            """

            self.db.aql.execute(aql)
            self.logger.info(f"Cleared all location activities from {self.collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error clearing location activities: {e}")
            return False
```

### 3. Location Activity Model

The location activity model will define the structure of location activity data.

```python
# research/ablation/models/location_activity.py

from datetime import datetime, timezone
import uuid
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator


class LocationActivity(BaseModel):
    """Model for location activity data."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    location_name: str
    latitude: float
    longitude: float
    accuracy: float = 10.0  # Accuracy in meters
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_minutes: int = 30  # How long the user was at this location
    source: str = "synthetic"  # Source of the data
    semantic_attributes: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('timestamp')
    def ensure_timezone(cls, v):
        """Ensure timestamp has timezone info."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
```

### 4. Demo Script

Create a demonstration script for the location activity components.

```python
# test_location_activity.py

#!/usr/bin/env python3
"""
Test script for location activity in the ablation framework.

This script demonstrates the integration between the LocationActivityCollector and
LocationActivityRecorder, showing the complete pipeline for synthetic location data.
"""

import logging
import argparse
import sys
from pathlib import Path

# Adjust Python path
current_path = Path(__file__).parent.resolve()
sys.path.append(str(current_path))

from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.query.llm_query_generator import LLMQueryGenerator
from research.ablation.models.activity import ActivityType


def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Run the location activity test."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test location activity components")
    parser.add_argument(
        "--activity-count", type=int, default=50,
        help="Number of synthetic location activities to generate"
    )
    parser.add_argument(
        "--query-count", type=int, default=5,
        help="Number of test queries to generate"
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear existing location activities before adding new ones"
    )
    parser.add_argument(
        "--llm-provider", default="anthropic",
        help="LLM provider for query generation (anthropic, openai, etc.)"
    )
    parser.add_argument(
        "--no-prompt-manager", action="store_true",
        help="Disable PromptManager integration for query generation"
    )
    args = parser.parse_args()

    # Initialize the location activity collector and recorder
    collector = LocationActivityCollector()
    recorder = LocationActivityRecorder()

    # Clear existing activities if requested
    if args.clear:
        logger.info("Clearing existing location activities")
        recorder.clear_all_activities()

    # Generate synthetic location activities
    logger.info(f"Generating {args.activity_count} synthetic location activities")
    activities = collector.collect(count=args.activity_count)

    # Record activities to the database
    success_count = recorder.record(activities)
    logger.info(f"Recorded {success_count}/{len(activities)} location activities")

    # Generate location-based queries using LLM
    logger.info(f"Generating {args.query_count} location-based queries")
    query_generator = LLMQueryGenerator(
        llm_provider=args.llm_provider,
        use_prompt_manager=not args.no_prompt_manager
    )
    queries = query_generator.generate_queries(
        count=args.query_count,
        activity_types=[ActivityType.LOCATION],
        temperature=0.7
    )

    # Log prompt manager usage
    if not args.no_prompt_manager:
        logger.info("Using PromptManager for query generation")
    else:
        logger.info("Using direct prompts for query generation (PromptManager disabled)")

    # Display generated queries
    logger.info("Generated queries:")
    for i, query in enumerate(queries):
        logger.info(f"Query {i+1}: {query.query_text}")
        logger.info(f"  Expected matches: {len(query.expected_matches)}")
        logger.info(f"  Difficulty: {query.difficulty}")

        # Display metadata if available
        if "reasoning" in query.metadata:
            logger.info(f"  Reasoning: {query.metadata['reasoning']}")

        logger.info("")

    # Retrieve and display location activities
    all_activities = recorder.get_all_activities()
    logger.info(f"Total location activities in database: {len(all_activities)}")

    # Show activities for common locations
    for location in ["home", "work", "coffee shop"]:
        activities = recorder.get_activities_by_location(location)
        logger.info(f"Activities at {location}: {len(activities)}")


if __name__ == "__main__":
    main()
```

## Implementation Steps

1. **Create Models**: Implement the LocationActivity model
2. **Implement Collector**: Create the LocationActivityCollector
3. **Implement Recorder**: Create the LocationActivityRecorder
4. **Create Demo Script**: Implement the test_location_activity.py script
5. **Test End-to-End**: Run the demo script to validate the complete pipeline
6. **Integrate with Ablation**: Add location activity support to the ablation framework
7. **Test Ablation**: Validate the ablation testing with location activity data

## Database Schema

The location activity collection will use the following schema:

```
{
  "id": "string (UUID)",
  "location_name": "string",
  "latitude": "float",
  "longitude": "float",
  "accuracy": "float",
  "timestamp": "string (ISO-8601 datetime)",
  "duration_minutes": "integer",
  "source": "string",
  "semantic_attributes": "object"
}
```

## Expected Queries

Example location-related queries that users might naturally ask:

1. "Find documents I worked on while at the coffee shop"
2. "Show me files I accessed at home last week"
3. "What documents did I edit at the airport?"
4. "Files I worked on at the library"
5. "Documents I viewed while downtown"

## Validation Criteria

To validate the implementation, ensure:

1. The collector generates realistic location activity data
2. The recorder properly stores and retrieves data from ArangoDB
3. The generated queries are diverse and target location activity
4. The expected matches contain appropriate location references
5. The system can be ablated (collection removed) for testing
6. Metrics correctly identify the impact of ablation on search quality

## Next Steps After Completion

After successfully implementing the location activity components:

1. Implement the next activity type (e.g., task activity)
2. Create an integration test that uses multiple activity types
3. Enhance the metrics collection and reporting
4. Prepare for the ablation study experiments
