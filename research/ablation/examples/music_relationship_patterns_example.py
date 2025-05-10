"""Example demonstrating new music-based relationship patterns with enhanced recorders."""

import logging
import sys

from db.db_config import IndalekoDBConfig
from research.ablation.models.location_activity import LocationActivity
from research.ablation.models.music_activity import MusicActivity
from research.ablation.models.relationship_patterns import MusicLocationPattern, MusicTaskPattern
from research.ablation.models.task_activity import TaskActivity
from research.ablation.query.aql_translator import AQLQueryTranslator
from research.ablation.recorders.enhanced_base import EnhancedActivityRecorder
from research.ablation.registry import SharedEntityRegistry


# Create enhanced recorders for different activity types
class EnhancedTaskRecorder(EnhancedActivityRecorder):
    """Enhanced recorder for task activities."""

    COLLECTION_NAME = "TaskActivity"
    TRUTH_COLLECTION = "TaskTruthData"
    ActivityClass = TaskActivity


class EnhancedLocationRecorder(EnhancedActivityRecorder):
    """Enhanced recorder for location activities."""

    COLLECTION_NAME = "LocationActivity"
    TRUTH_COLLECTION = "LocationTruthData"
    ActivityClass = LocationActivity


class EnhancedMusicRecorder(EnhancedActivityRecorder):
    """Enhanced recorder for music activities."""

    COLLECTION_NAME = "MusicActivity"
    TRUTH_COLLECTION = "MusicTruthData"
    ActivityClass = MusicActivity


def run_example():
    """Run the music relationship patterns example."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Create shared entity registry
    registry = SharedEntityRegistry()

    # Create recorders with the shared registry
    task_recorder = EnhancedTaskRecorder(registry)
    location_recorder = EnhancedLocationRecorder(registry)
    music_recorder = EnhancedMusicRecorder(registry)

    # Create relationship pattern generators
    music_location_pattern = MusicLocationPattern(registry)
    music_task_pattern = MusicTaskPattern(registry)

    # Create AQL translator for queries
    aql_translator = AQLQueryTranslator()

    try:
        # Example 1: Generate music activity at a location
        logger.info("Generating music activity at a location")
        location, music = music_location_pattern.generate_music_at_location()

        # Record the location
        logger.info(f"Recording location: {location['location_name']}")
        location_recorder.record(location)

        # Record the music activity
        logger.info(f"Recording music: {music['artist']} - {music['track']}")
        music_recorder.record(music)

        # Example 2: Generate a task with background music
        logger.info("Generating task with background music")
        task, music_activity = music_task_pattern.generate_music_during_task()

        # Record the task
        logger.info(f"Recording task: {task['task_name']}")
        task_recorder.record(task)

        # Record the music
        logger.info(f"Recording music: {music_activity['artist']} - {music_activity['track']}")
        music_recorder.record(music_activity)

        # Example 3: Generate a task with a playlist
        logger.info("Generating task with a playlist")
        task_with_playlist, playlist = music_task_pattern.generate_task_playlist()

        # Record the task
        logger.info(f"Recording task: {task_with_playlist['task_name']}")
        task_recorder.record(task_with_playlist)

        # Record the playlist
        logger.info(f"Recording playlist with {len(playlist)} tracks")
        for track in playlist:
            music_recorder.record(track)
            logger.info(f"  - {track['artist']} - {track['track']} ({track['genre']})")

        # Generate AQL query examples to demonstrate the cross-collection queries
        logger.info("\nExample 1: AQL Query - Find music listened to at a specific location")
        query1 = "Find all music by Taylor Swift played at home"
        aql, bind_vars = aql_translator.translate_to_aql(
            query_text=query1,
            collection="MusicActivity",
            activity_types=[ActivityType.MUSIC, ActivityType.LOCATION],
            relationship_type="listened_at",
        )
        logger.info(f"Query: {query1}")
        logger.info(f"Translated AQL:\n{aql}")

        logger.info("\nExample 2: AQL Query - Find productivity music for coding tasks")
        query2 = "Find what music I listen to during coding tasks"
        aql, bind_vars = aql_translator.translate_to_aql(
            query_text=query2,
            collection="MusicActivity",
            activity_types=[ActivityType.MUSIC, ActivityType.TASK],
            relationship_type="played_during",
        )
        logger.info(f"Query: {query2}")
        logger.info(f"Translated AQL:\n{aql}")

        logger.info("\nExample 3: Multi-hop Query - Find music listened to during tasks at specific locations")
        query3 = "What music do I listen to when working at the coffee shop"
        relationship_paths = [
            ("TaskActivity", "background_music", "MusicActivity"),
            ("MusicActivity", "listened_at", "LocationActivity"),
        ]
        aql, bind_vars = aql_translator.translate_multi_hop_query(
            query_text=query3,
            primary_collection="TaskActivity",
            relationship_paths=relationship_paths,
        )
        logger.info(f"Query: {query3}")
        logger.info(f"Translated AQL:\n{aql}")

        # Execute one of the queries to demonstrate the results
        logger.info("\nExecuting query to find music played during tasks")

        # Connect to the database
        db = IndalekoDBConfig().get_arangodb()

        # Build a simplified query that works with our test data
        aql_query = """
        FOR task IN TaskActivity
          FILTER task.references != null AND task.references.background_music != null
          FOR music IN MusicActivity
            FILTER music._key IN task.references.background_music
            RETURN {
                task_name: task.task_name,
                music_artist: music.artist,
                music_track: music.track,
                genre: music.genre,
                task_application: task.application
            }
        """

        try:
            cursor = db.aql.execute(aql_query)
            results = [doc for doc in cursor]
            logger.info(f"Found {len(results)} music activities during tasks:")
            for result in results:
                logger.info(f"  - Task: '{result['task_name']}' using {result['task_application']}")
                logger.info(f"    Music: {result['music_artist']} - {result['music_track']} ({result['genre']})")
        except Exception as e:
            logger.error(f"Error executing query: {e}")

        logger.info("Music relationship patterns example completed successfully")

    except Exception as e:
        logger.error(f"Error in example: {e}")
        sys.exit(1)  # Fail-stop principle


if __name__ == "__main__":
    # Import ActivityType here to avoid circular imports
    from ..query.llm_query_generator import ActivityType

    run_example()
